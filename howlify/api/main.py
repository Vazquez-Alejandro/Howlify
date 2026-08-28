import os
import time
import json
import hashlib
import hmac
import logging
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv
import jwt

load_dotenv()

import requests

from fastapi import FastAPI, HTTPException, Header, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator

from auth.supabase_client import supabase
from utils.logic import infer_source_from_url, parse_price_to_int, clean_ml_url

from pywebpush import webpush, WebPushException

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("howlify")

# ─── Rate limiter (Redis con fallback a in-memory) ──────
import redis as redis_lib

_redis_client = None
_redis_url = os.getenv("REDIS_URL", "")
if _redis_url:
    try:
        _redis_client = redis_lib.from_url(_redis_url, decode_responses=True)
        _redis_client.ping()
        logger.info("Rate limiter: usando Redis")
    except Exception:
        _redis_client = None
        logger.warning("Rate limiter: Redis no disponible, usando in-memory")

_rate_limit_lock = threading.Lock()
_rate_limit_store: dict[str, list[float]] = {}
_RATE_WINDOW = float(os.getenv("RATE_WINDOW_SECONDS", "30"))
_RATE_MAX = int(os.getenv("RATE_MAX_REQUESTS", "2"))

def rate_limit_hunt(uid: str):
    now = time.time()

    if _redis_client:
        key = f"rl:{uid}"
        pipe = _redis_client.pipeline()
        pipe.zremrangebyscore(key, 0, now - _RATE_WINDOW)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, int(_RATE_WINDOW) + 1)
        results = pipe.execute()
        count = results[2]
        if count > _RATE_MAX:
            _redis_client.delete(key)
            raise HTTPException(status_code=429, detail=f"Demasiadas solicitudes. Esperá {_RATE_WINDOW:.0f}s.")
    else:
        with _rate_limit_lock:
            timestamps = _rate_limit_store.get(uid, [])
            timestamps = [t for t in timestamps if now - t < _RATE_WINDOW]
            if len(timestamps) >= _RATE_MAX:
                retry_after = int(_RATE_WINDOW - (now - timestamps[0]))
                raise HTTPException(status_code=429, detail=f"Demasiadas solicitudes. Esperá {retry_after}s.")
            timestamps.append(now)
            _rate_limit_store[uid] = timestamps

app = FastAPI(title="Howlify API", version="1.0.0")

from fastapi.middleware.cors import CORSMiddleware
_cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "https://howlify.vercel.app,http://localhost:5173").split(",")]
app.add_middleware(CORSMiddleware, allow_origins=_cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.middleware("http")
async def vary_origin_middleware(request: Request, call_next):
    response = await call_next(request)
    if "origin" in request.headers:
        response.headers.setdefault("Vary", "Origin")
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.exception("Unhandled exception at %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Error interno del servidor"})

REACT_DIST = Path(__file__).resolve().parents[2] / "frontend-react" / "dist"
_HAS_REACT = REACT_DIST.exists() and (REACT_DIST / "index.html").exists()
if _HAS_REACT:
    app.mount("/assets", StaticFiles(directory=str(REACT_DIST / "assets")), name="react-assets")

    from starlette.middleware.base import BaseHTTPMiddleware

    class SPAFallbackMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            response = await call_next(request)
            if response.status_code == 404 and not request.url.path.startswith("/api/"):
                return FileResponse(str(REACT_DIST / "index.html"))
            return response

    class SecurityHeadersMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            response = await call_next(request)
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
            response.headers["Content-Security-Policy"] = "default-src 'self'"
            if request.url.path.startswith("/api/"):
                response.headers["Cache-Control"] = "no-store"
            return response

    app.add_middleware(SPAFallbackMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

# ─── Auth ───────────────────────────────────────────────

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
if not SUPABASE_JWT_SECRET:
    raise RuntimeError("SUPABASE_JWT_SECRET no está configurado en el entorno")

def get_user_id(authorization: str = "") -> str:
    token = authorization.replace("Bearer ", "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Token requerido")
    if not SUPABASE_JWT_SECRET:
        raise HTTPException(status_code=500, detail="SUPABASE_JWT_SECRET no configurado")
    try:
        payload = jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=["HS256"], audience="authenticated")
        uid = payload.get("sub")
        if not uid:
            raise HTTPException(status_code=401, detail="Token inválido: sin sub")
        return uid
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidSignatureError:
        raise HTTPException(status_code=401, detail="Token inválido: firma incorrecta")
    except jwt.DecodeError:
        raise HTTPException(status_code=401, detail="Token inválido: no se pudo decodificar")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token inválido: {e}")

# ─── Schemas ────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str

class SignupRequest(BaseModel):
    email: str
    password: str
    username: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    access_token: str
    refresh_token: str
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class ResendVerificationRequest(BaseModel):
    email: str

class CazaCreate(BaseModel):
    keyword: str
    url: str
    precio_max: int
    frecuencia: str = "1 h"
    tipo: str = "piso"
    source: str = "generic"
    etiqueta: str = ""
    precio_venta: int = 0

class GenerateReportRequest(BaseModel):
    type: str = "daily"

class TestAlertRuleRequest(BaseModel):
    caza_id: int

class ExportSheetsRequest(BaseModel):
    rows: list = []
    sheet_name: str = ""

class PushSubscribeRequest(BaseModel):
    subscription: dict

class CreatePreferenceRequest(BaseModel):
    plan: str = "pro"

# ─── Helpers ────────────────────────────────────────────

def save_price_history(user_id: str, caza_id, results: list[dict]):
    if not user_id or not results: return
    rows = []
    for r in results:
        try: price = int(r.get("price") or r.get("precio") or 0)
        except Exception: price = 0
        if price <= 0: continue
        row = {
            "caza_id": caza_id, "user_id": user_id,
            "title": (r.get("title") or r.get("titulo") or "").strip(),
            "url": (r.get("url") or r.get("link") or "").strip(),
            "source": (r.get("source") or "").strip(),
            "price": price, "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        stock = r.get("stock")
        if isinstance(stock, (int, float)):
            row["stock"] = int(stock)
        rows.append(row)
    if not rows: return
    from utils.logic import insert_price_history_rows
    insert_price_history_rows(rows)

# ─── Endpoints ──────────────────────────────────────────

@app.get("/")
def root():
    if _HAS_REACT:
        return FileResponse(str(REACT_DIST / "index.html"))
    return {"name": "Howlify API", "version": "1.0.0", "status": "running"}

@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/api/health/detailed")
def health_detailed(authorization: str = ""):
    uid = get_user_id(authorization)
    if not uid:
        raise HTTPException(status_code=401, detail="Not authenticated")
    checks = {}
    all_ok = True

    try:
        supabase.table("cazas").select("id").limit(1).execute()
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)[:100]}"
        all_ok = False

    checks["scraper"] = "ok" if os.getenv("OH_PLAYWRIGHT") else "disabled"
    checks["version"] = "1.0.0"
    checks["environment"] = os.getenv("HOWLIFY_MODE", "unknown")

    try:
        from scraper.rate_limiter import rate_limiter
        checks["rate_limiter"] = rate_limiter.get_stats()
    except ImportError:
        checks["rate_limiter"] = "unavailable"

    return {
        "status": "ok" if all_ok else "degraded",
        "timestamp": datetime.now().isoformat(),
        "checks": checks,
    }

@app.get("/api/health/scraper")
def scraper_health(authorization: str = Header(...)):
    get_user_id(authorization)
    from scraper.scraper_pro import _domain
    test_url = "https://www.mercadolibre.com.ar/"
    domain = _domain(test_url)
    return {
        "status": "ok",
        "scraper_module": "loaded",
        "test_domain": domain,
        "playwright": os.getenv("OH_PLAYWRIGHT", "0"),
    }

# ─── Auth ───────────────────────────────────────────────

@app.post("/api/auth/login")
def login(req: LoginRequest):
    try:
        res = supabase.auth.sign_in_with_password({"email": req.email, "password": req.password})
        user = res.user
        session = res.session
        return {
            "user": {"id": user.id, "email": user.email},
            "token": session.access_token,
            "refresh_token": session.refresh_token,
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@app.post("/api/auth/signup")
def signup(req: SignupRequest):
    from auth.auth_supabase import supa_signup
    user, err = supa_signup(req.email, req.password, req.password, req.username, "starter")
    if err:
        raise HTTPException(status_code=400, detail=err)
    return {"user": {"id": user.id, "email": user.email} if user else None, "message": "Cuenta creada. Revisá tu email."}

@app.post("/api/auth/forgot-password")
def forgot_password(req: ForgotPasswordRequest):
    try:
        supabase.auth.reset_password_for_email(
            req.email.strip().lower(),
            {"redirect_to": f"{os.getenv('APP_BASE_URL', 'http://localhost:5173')}/reset-password"}
        )
        return {"message": "Correo enviado"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/auth/resend-verification")
def resend_verification(req: ResendVerificationRequest):
    try:
        supabase.auth.resend({"type": "signup", "email": req.email.strip().lower()})
        return {"message": "Correo de verificación reenviado"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/auth/reset-password")
def reset_password(req: ResetPasswordRequest):
    try:
        supabase.auth.set_session(req.access_token, req.refresh_token)
        update = supabase.auth.update_user({"password": req.password})
        if update.user:
            return {"message": "Contraseña actualizada correctamente"}
        raise HTTPException(status_code=400, detail="No se pudo actualizar la contraseña")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/auth/refresh")
def refresh_token(refresh_req: RefreshTokenRequest):
    try:
        res = supabase.auth.refresh_session(refresh_req.refresh_token)
        if res.session:
            return {
                "token": res.session.access_token,
                "refresh_token": res.session.refresh_token,
            }
        raise HTTPException(status_code=401, detail="No se pudo renovar la sesión")
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@app.get("/api/auth/profile")
def get_profile(authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    from db.database import get_user_profile
    profile = get_user_profile(uid)
    return {"user_id": uid, "profile": profile}


class ProfileUpdate(BaseModel):
    username: str | None = None
    telegram_id: str | None = None
    whatsapp_number: str | None = None
    email_notifications: bool | None = None
    terms_accepted: bool | None = None
    report_enabled: bool | None = None
    report_time: str | None = None
    report_days: list[int] | None = None
    telegram_bind_token: str | None = None


@app.put("/api/auth/profile")
def update_profile(data: ProfileUpdate, authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    payload = {k: v for k, v in data.model_dump().items() if v is not None}
    if not payload:
        raise HTTPException(status_code=400, detail="Sin datos para actualizar")
    try:
        supabase.table("profiles").update(payload).eq("user_id", uid).execute()
        return {"message": "Perfil actualizado"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class TestNotificationRequest(BaseModel):
    channel: str = ""
    canal: str = ""  # alias frontend sends "canal"

    def get_channel(self) -> str:
        return self.canal or self.channel


@app.post("/api/auth/telegram-bind-token")
def generate_telegram_bind_token(authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    token = hashlib.sha256(f"{uid}:{time.time()}:{os.urandom(16).hex()}".encode()).hexdigest()[:16]
    supabase.table("profiles").update({"telegram_bind_token": token}).eq("user_id", uid).execute()
    return {"token": token, "bot_username": os.getenv("TELEGRAM_BOT_USERNAME", "HowlifyBot")}

@app.post("/api/auth/test-notification")
def test_notification(data: TestNotificationRequest, authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    from db.database import get_user_profile
    profile = get_user_profile(uid)
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")

    from services.notification_service import enviar_telegram, enviar_whatsapp, enviar_email
    mensaje = "🐺 ¡Howlify funciona correctamente! Esta es una notificación de prueba."
    canal = data.get_channel()

    if canal == "telegram":
        tg_id = profile.get("telegram_id")
        if not tg_id:
            raise HTTPException(status_code=400, detail="No hay Telegram ID configurado")
        ok = enviar_telegram(str(tg_id), mensaje)
        return {"ok": ok, "channel": "telegram"}

    if canal == "whatsapp":
        from config import PLAN_LIMITS
        user_plan = profile.get("plan", "starter")
        if not PLAN_LIMITS.get(user_plan, {}).get("features", {}).get("whatsapp", False):
            raise HTTPException(status_code=403, detail="WhatsApp no disponible en tu plan. Upgrade a Beta o Alpha.")
        num = profile.get("whatsapp_number")
        if not num:
            raise HTTPException(status_code=400, detail="No hay WhatsApp configurado")
        ok = enviar_whatsapp(str(num), mensaje)
        return {"ok": ok, "channel": "whatsapp"}

    if canal == "email":
        email = profile.get("email")
        if not email:
            try:
                user_res = supabase.auth.admin.get_user_by_id(uid)
                email = user_res.user.email if user_res and user_res.user else None
            except Exception:
                email = None
        if not email:
            raise HTTPException(status_code=400, detail="No se pudo obtener el email")
        ok = enviar_email(str(email), "🐺 Prueba Howlify", mensaje)
        return {"ok": ok, "channel": "email"}

    raise HTTPException(status_code=400, detail="Canal inválido. Usar: telegram, whatsapp, email")


# ─── Cazas ──────────────────────────────────────────────

@app.get("/api/cazas")
def list_cazas(authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    from db.database import obtener_cazas
    profile = supabase.table("profiles").select("plan").eq("user_id", uid).limit(1).execute()
    plan = profile.data[0]["plan"] if profile.data else "starter"
    cazas = obtener_cazas(uid, plan)
    return {"cazas": cazas}

@app.post("/api/cazas")
def create_caza(caza: CazaCreate, authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    from services.database_service import guardar_caza_supabase
    from utils.logic import get_effective_plan_rules, _effective_minutes
    profile = supabase.table("profiles").select("plan").eq("user_id", uid).limit(1).execute()
    plan = profile.data[0]["plan"] if profile.data else "starter"
    rules = get_effective_plan_rules(plan)
    freq_opts = rules.get("freq_options", ["1h", "6h", "12h", "24h"])
    if caza.frecuencia not in freq_opts:
        raise HTTPException(status_code=400, detail=f"Frecuencia '{caza.frecuencia}' no permitida en tu plan. Opciones: {', '.join(freq_opts)}")
    url_limpia = clean_ml_url(caza.url)
    if url_limpia:
        from scraper.generic import is_safe_url
        if not is_safe_url(url_limpia):
            raise HTTPException(status_code=400, detail="URL inválida o no permitida (SSRF)")
    src = infer_source_from_url(url_limpia) or "generic"
    precio_int = parse_price_to_int(caza.precio_max)
    ok = guardar_caza_supabase(uid, caza.keyword, url_limpia, precio_int, caza.frecuencia, caza.tipo, plan, src)
    if ok is not True:
        raise HTTPException(status_code=400, detail=str(ok))
    if caza.precio_venta and caza.precio_venta > 0:
        from utils.logic import set_margen_rule
        row = supabase.table("cazas").select("id").eq("user_id", uid).order("created_at", desc=True).limit(1).execute()
        if row.data:
            set_margen_rule(uid, row.data[0]["id"], caza.precio_venta)
    return {"message": "Cacería creada"}

@app.put("/api/cazas/{caza_id}")
def update_caza(caza_id: int, data: CazaCreate, authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    url_limpia = clean_ml_url(data.url)
    if url_limpia:
        from scraper.generic import is_safe_url
        if not is_safe_url(url_limpia):
            raise HTTPException(status_code=400, detail="URL inválida o no permitida (SSRF)")
    src = infer_source_from_url(url_limpia) or "generic"
    precio_int = parse_price_to_int(data.precio_max)
    supabase.table("cazas").update({
        "producto": data.keyword,
        "link": url_limpia,
        "precio_max": precio_int,
        "frecuencia": data.frecuencia,
        "tipo_alerta": data.tipo,
        "source": src,
        "etiqueta": data.etiqueta,
    }).eq("id", caza_id).eq("user_id", uid).execute()
    if data.precio_venta is not None:
        from utils.logic import set_margen_rule
        set_margen_rule(uid, caza_id, data.precio_venta)
    return {"message": "Cacería actualizada"}

@app.delete("/api/cazas/{caza_id}")
def delete_caza(caza_id: int, authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    supabase.table("cazas").delete().eq("id", caza_id).eq("user_id", uid).execute()
    return {"message": "Cacería eliminada"}

# ─── Hunt ───────────────────────────────────────────────

@app.post("/api/hunt/{caza_id}")
def hunt_single(caza_id: int, authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    rate_limit_hunt(uid)
    res = supabase.table("cazas").select("*").eq("id", caza_id).eq("user_id", uid).limit(1).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Cacería no encontrada")

    caza = res.data[0]
    url = caza.get("url") or caza.get("link") or ""
    tipo_alerta = (caza.get("tipo_alerta") or "piso").strip().lower()
    precio_max_raw = caza.get("precio_max") or 0
    precio_scraper = 0 if tipo_alerta == "descuento" else precio_max_raw
    src = infer_source_from_url(url).strip().lower()

    if src == "airbnb":
        from scraper.airbnb import hunt_airbnb
        resultados = hunt_airbnb(url, precio_scraper) or []
    else:
        from scraper.scraper_pro import hunt_offers
        resultados = hunt_offers(url, caza.get("keyword", ""), precio_scraper, headless=True) or []

    if resultados:
        save_price_history(uid, caza_id, resultados)
        from utils.logic import detectar_price_error
        from engine.engine import _obtener_precio_referencia, detectar_inflado, detectar_restock
        ref = _obtener_precio_referencia(caza_id)
        inflado = detectar_inflado(caza_id) if ref else None
        for r in resultados:
            precio_r = r.get("price") or 0
            if precio_r > 0:
                es_error, prom = detectar_price_error(caza_id, float(precio_r))
                if es_error:
                    r["price_error"] = True
                    r["price_avg"] = prom
                if tipo_alerta == "descuento":
                    refx = ref or precio_r
                    descuento = int((1 - precio_r / refx) * 100) if refx > 0 else 0
                    r["descuento"] = descuento
                    r["match_descuento"] = descuento >= max(precio_max_raw, 0)
                if tipo_alerta == "grande":
                    refx = ref or precio_r
                    drop_pct = int((1 - precio_r / refx) * 100) if refx > 0 else 0
                    r["drop_pct"] = drop_pct
                    r["match_grande"] = drop_pct >= 25
            if inflado:
                r["inflado_detectado"] = True
        restock = detectar_restock(caza_id, resultados)
        if restock is not None:
            for r in resultados:
                r["restock_detectado"] = restock
    if resultados:
        try:
            from services.seller_service import enrich_results_with_sellers
            enrich_results_with_sellers(resultados)
        except Exception:
            pass
    return {"results": resultados}

@app.post("/api/hunt/all")
def hunt_all(authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    rate_limit_hunt(uid)
    from db.database import obtener_cazas
    profile = supabase.table("profiles").select("plan").eq("user_id", uid).limit(1).execute()
    plan = profile.data[0]["plan"] if profile.data else "starter"
    cazas = obtener_cazas(uid, plan)
    results = {}
    for c in cazas:
        rid = str(c.get("id", ""))
        try:
            url = c.get("url") or c.get("link") or ""
            tipo_alerta = (c.get("tipo_alerta") or "piso").strip().lower()
            precio_max_raw = c.get("precio_max") or 0
            precio_scraper = 0 if tipo_alerta == "descuento" else precio_max_raw
            src = infer_source_from_url(url).strip().lower()
            if src == "airbnb":
                from scraper.airbnb import hunt_airbnb
                res = hunt_airbnb(url, precio_scraper) or []
            else:
                from scraper.scraper_pro import hunt_offers
                res = hunt_offers(url, c.get("keyword", ""), precio_scraper, headless=True) or []
            if res:
                save_price_history(uid, c.get("id"), res)
                from utils.logic import detectar_price_error
                from engine.engine import _obtener_precio_referencia, detectar_inflado, detectar_restock
                ref = _obtener_precio_referencia(c.get("id"))
                inflado = detectar_inflado(c.get("id")) if ref else None
                for r in res:
                    precio_r = r.get("price") or 0
                    if precio_r > 0:
                        es_error, prom = detectar_price_error(c.get("id"), float(precio_r))
                        if es_error:
                            r["price_error"] = True
                            r["price_avg"] = prom
                        if tipo_alerta == "descuento":
                            refx = ref or precio_r
                            descuento = int((1 - precio_r / refx) * 100) if refx > 0 else 0
                            r["descuento"] = descuento
                            r["match_descuento"] = descuento >= max(precio_max_raw, 0)
                        if tipo_alerta == "grande":
                            refx = ref or precio_r
                            drop_pct = int((1 - precio_r / refx) * 100) if refx > 0 else 0
                            r["drop_pct"] = drop_pct
                            r["match_grande"] = drop_pct >= 25
                    if inflado:
                        r["inflado_detectado"] = True
                restock = detectar_restock(c.get("id"), res)
                if restock is not None:
                    for r in res:
                        r["restock_detectado"] = restock
            results[rid] = res
        except Exception as e:
            results[rid] = {"error": str(e)}
    return {"results": results}

# ─── Async Hunt (via Celery) ────────────────────────────


@app.post("/api/hunt/async/{caza_id}")
def hunt_single_async(caza_id: int, authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    rate_limit_hunt(uid)
    res = supabase.table("cazas").select("id").eq("id", caza_id).eq("user_id", uid).limit(1).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Cacería no encontrada")
    try:
        from howlify.tasks import hunt_single_task
        task = hunt_single_task.delay(caza_id, uid)
        return {"task_id": task.id, "status": "queued"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error encolando tarea: {e}")


@app.post("/api/hunt/async/all")
def hunt_all_async(authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    rate_limit_hunt(uid)
    try:
        from howlify.tasks import hunt_all_user_task
        task = hunt_all_user_task.delay(uid)
        return {"task_id": task.id, "status": "queued"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error encolando tarea: {e}")


@app.get("/api/task/{task_id}")
def get_task_status(task_id: str, authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    try:
        from howlify.celery_app import celery_app
        result = celery_app.AsyncResult(task_id)
        return {
            "task_id": task_id,
            "status": result.status,
            "ready": result.ready(),
            "successful": result.successful() if result.ready() else None,
            "result": result.result if result.ready() else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Price History ──────────────────────────────────────

@app.get("/api/history/{caza_id}")
def get_history(caza_id: int, authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    res = supabase.table("price_history") \
        .select("checked_at, price, title, url") \
        .eq("caza_id", caza_id) \
        .eq("user_id", uid) \
        .order("checked_at", desc=True) \
        .limit(50) \
        .execute()
    return {"history": res.data or []}

@app.get("/api/public/history/{caza_id}")
def public_history(caza_id: int):
    res = supabase.table("cazas").select("id, producto, keyword, link, url, precio_max").eq("id", caza_id).limit(1).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Cacería no encontrada")
    caza = res.data[0]
    hist = supabase.table("price_history") \
        .select("checked_at, price, title") \
        .eq("caza_id", caza_id) \
        .order("checked_at", desc=True) \
        .limit(50) \
        .execute()
    prices = [{"price": float(h["price"]), "checked_at": h["checked_at"]} for h in (hist.data or []) if h.get("price")]
    return {
        "id": caza.get("id"),
        "producto": caza.get("producto") or caza.get("keyword", "Producto"),
        "url": caza.get("link") or caza.get("url", ""),
        "precio_max": caza.get("precio_max", 0),
        "history": prices,
    }

@app.get("/api/predict/{caza_id}")
def predict_price(caza_id: int, authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    res = supabase.table("price_history") \
        .select("checked_at, price") \
        .eq("caza_id", caza_id) \
        .eq("user_id", uid) \
        .order("checked_at", desc=False) \
        .limit(30) \
        .execute()
    prices = [float(p["price"]) for p in (res.data or []) if p.get("price")]
    if len(prices) < 3:
        return {"predictable": False, "reason": "Se necesitan al menos 3 mediciones"}
    import numpy as np
    xs = np.arange(len(prices))
    ys = np.array(prices)
    slope, intercept = np.polyfit(xs, ys, 1)
    trend = "subiendo" if slope > 0 else "bajando" if slope < 0 else "estable"
    next_val = intercept + slope * len(prices)
    cambio_pct = ((next_val - prices[-1]) / prices[-1]) * 100
    ma_3 = np.mean(prices[-3:]) if len(prices) >= 3 else prices[-1]
    ma_7 = np.mean(prices) if len(prices) >= 7 else None
    prob_baja = max(0, min(100, round(-slope / (prices[-1] / 100) * 10 + 50))) if slope < 0 else max(0, min(30, 30 - slope * 100))
    return {
        "predictable": True,
        "trend": trend,
        "last_price": prices[-1],
        "predicted_next": round(next_val),
        "cambio_pct": round(cambio_pct, 1),
        "prob_baja_7d": round(prob_baja),
        "min_30d": round(float(np.min(ys))),
        "max_30d": round(float(np.max(ys))),
        "avg_30d": round(float(np.mean(ys))),
        "ma_3": round(float(ma_3)),
        "ma_7": round(float(ma_7)) if ma_7 else None,
    }












# ─── Reportes ────────────────────────────────────────────

@app.post("/api/reports/generate")
def generate_report(body: GenerateReportRequest, authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    from config import PLAN_LIMITS
    profile = supabase.table("profiles").select("plan").eq("user_id", uid).limit(1).execute()
    plan = profile.data[0]["plan"] if profile.data else "starter"
    if not PLAN_LIMITS.get(plan, {}).get("features", {}).get("reporte_diario", False):
        raise HTTPException(status_code=403, detail="Reportes no disponibles en tu plan. Upgrade a Beta o Alpha.")
    tipo = body.type
    try:
        from services.database_service import ejecutar_reporte_diario_total, ejecutar_reporte_semanal
        if tipo == "daily":
            ejecutar_reporte_diario_total(force=True)
            return {"message": "Reporte diario generado y enviado"}
        elif tipo == "weekly":
            ejecutar_reporte_semanal(force=True)
            return {"message": "Reporte semanal generado y enviado"}
        return {"message": f"Reporte {tipo} no soportado"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Error generando reporte: {e}"})

@app.post("/api/reports/test-alert")
def test_alert_rule(body: TestAlertRuleRequest, authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    caza_id = body.caza_id
    if not caza_id:
        raise HTTPException(400, "Falta caza_id")
    try:
        from engine.engine import evaluar_reglas_alerta
        evaluar_reglas_alerta(caza_id, uid)
        return {"message": "Reglas evaluadas. Revisá tus notificaciones."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Error: {e}"})



# ─── Google Sheets Export ─────────────────────────────────

@app.post("/api/export/sheets")
def export_to_sheets(data: ExportSheetsRequest, authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    try:
        import pandas as pd
        from utils.logic import exportar_a_sheets
        df = pd.DataFrame(data.rows)
        if df.empty:
            raise HTTPException(status_code=400, detail="Sin datos para exportar")
        ok, info = exportar_a_sheets(df, nombre_hoja=data.sheet_name or f"Howlify Export {uid[:8]}")
        if not ok:
            raise HTTPException(status_code=500, detail=info)
        return {"ok": True, "url": f"https://docs.google.com/spreadsheets/d/{info}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

import csv, io

@app.get("/api/export/csv")
def export_csv(authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    from db.database import obtener_cazas
    from config import PLAN_LIMITS
    profile = supabase.table("profiles").select("plan").eq("user_id", uid).limit(1).execute()
    plan = profile.data[0]["plan"] if profile.data else "starter"
    if not PLAN_LIMITS.get(plan, {}).get("features", {}).get("export_csv", False):
        raise HTTPException(status_code=403, detail="Exportación CSV no disponible en tu plan. Upgrade a Beta o Alpha.")
    cazas = obtener_cazas(uid, plan)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Producto", "URL", "Precio Máx", "Último Precio", "Estado", "Creado"])
    for c in cazas:
        writer.writerow([
            c.get("id", ""),
            c.get("producto") or c.get("keyword", ""),
            c.get("url") or c.get("link", ""),
            c.get("precio_max", 0),
            c.get("last_price", ""),
            c.get("estado", "active"),
            c.get("created_at", ""),
        ])
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=howlify_cazas.csv"},
    )

@app.get("/api/rates")
def get_rates():
    try:
        blue = requests.get("https://dolarapi.com/v1/dolares/blue", timeout=5).json()
        tarjeta = requests.get("https://dolarapi.com/v1/dolares/tarjeta", timeout=5).json()
        return {
            "blue": float(blue.get("venta", 0)),
            "tarjeta": float(tarjeta.get("venta", 0)),
            "oficial": float(requests.get("https://dolarapi.com/v1/dolares/oficial", timeout=5).json().get("venta", 0)),
        }
    except Exception as e:
        logger.warning("Error fetching rates: %s", e)
        raise HTTPException(status_code=503, detail="No se pudieron obtener las cotizaciones")

# ─── PWA Push Notifications ──────────────────────────────

VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_CLAIM = os.getenv("VAPID_CLAIM_EMAIL", "mailto:howlify@example.com")

def push_notify_user(uid: str, title: str, body: str, url: str = ""):
    if not VAPID_PRIVATE_KEY:
        return
    subs = supabase.table("push_subscriptions").select("id, subscription").eq("user_id", uid).execute()
    for row in subs.data or []:
        try:
            sub = json.loads(row["subscription"]) if isinstance(row["subscription"], str) else row["subscription"]
            webpush(
                subscription_info=sub,
                data=json.dumps({"title": title, "body": body, "url": url}),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": VAPID_CLAIM},
            )
        except WebPushException:
            supabase.table("push_subscriptions").delete().eq("id", row["id"]).execute()
        except Exception:
            pass

@app.post("/api/push/subscribe")
def push_subscribe(data: PushSubscribeRequest, authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    sub = data.subscription
    if not sub.get("endpoint"):
        raise HTTPException(400, "Falta endpoint")
    supabase.table("push_subscriptions").upsert({
        "user_id": uid,
        "subscription": json.dumps(sub),
    }, on_conflict="user_id").execute()
    push_notify_user(uid, "Howlify", "Notificaciones push activadas ✅")
    return {"message": "Suscripción guardada"}

@app.delete("/api/push/subscribe")
def push_unsubscribe(authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    supabase.table("push_subscriptions").delete().eq("user_id", uid).execute()
    return {"message": "Suscripción eliminada"}

@app.post("/api/push/test")
def push_test(authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    push_notify_user(uid, "🧪 Prueba", "Si ves esto, las notificaciones push funcionan.", "/dashboard")
    return {"message": "Notificación enviada"}

# ─── Mercado Pago / Billing ─────────────────────────────

MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN", "")
MP_WEBHOOK_SECRET = os.getenv("MP_WEBHOOK_SECRET", "")
MP_API_BASE = "https://api.mercadopago.com"

MP_PRICES = {
    "pro": int(os.getenv("MP_PRICE_PRO_ARS", "6500")),
    "alpha": int(os.getenv("MP_PRICE_ALPHA_ARS", "12500")),
}

MP_DURATION_DAYS = int(os.getenv("MP_DURATION_DAYS", "30"))

@app.post("/api/mp/create-preference")
def mp_create_preference(data: CreatePreferenceRequest, authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    plan = data.plan
    if plan not in MP_PRICES:
        raise HTTPException(status_code=400, detail=f"Plan inválido: {plan}")

    price = MP_PRICES[plan]
    profile = supabase.table("profiles").select("email, username").eq("user_id", uid).limit(1).execute()
    if not profile.data:
        raise HTTPException(status_code=404, detail="Profile not found")
    email = profile.data[0].get("email", "")
    username = profile.data[0].get("username", "")

    PLAN_LABEL = {"pro": "Pro"}
    title = f"Howlify - Plan {PLAN_LABEL.get(plan, plan)}"
    base_url = os.getenv("APP_BASE_URL", "http://localhost:5173")

    payload = {
        "items": [
            {
                "title": title,
                "quantity": 1,
                "unit_price": price,
                "currency_id": "ARS",
            }
        ],
        "payer": {"email": email} if email else {},
        "external_reference": json.dumps({"user_id": uid, "plan": plan}),
        "back_urls": {
            "success": f"{base_url}/dashboard?billing=success",
            "failure": f"{base_url}/dashboard?billing=failure",
            "pending": f"{base_url}/dashboard?billing=pending",
        },
        "notification_url": f"{base_url}/api/mp/webhook",
        "auto_return": "approved",
        "binary_mode": True,
        "statement_descriptor": "HOWLIFY",
    }

    headers = {
        "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(f"{MP_API_BASE}/checkout/preferences", json=payload, headers=headers)
        if resp.status_code not in (200, 201):
            raise HTTPException(status_code=500, detail=f"Error MP: {resp.text}")
        data = resp.json()
        return {"url": data.get("init_point", data.get("sandbox_init_point", ""))}
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/mp/webhook")
async def mp_webhook(request: Request):
    """IPN webhook - Mercado Pago nos avisa cuando un pago se concreta."""
    try:
        body = await request.json()
    except Exception:
        body = {}

    # Verify X-Signature if webhook secret is configured
    if MP_WEBHOOK_SECRET:
        x_signature = request.headers.get("X-Signature", "")
        if not x_signature:
            logger.warning("MP webhook: missing X-Signature header")
            return JSONResponse(status_code=401, content={"error": "Missing signature"})
        try:
            parts = {}
            for pair in x_signature.split(","):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    parts[k.strip()] = v.strip()
            ts = parts.get("ts", "")
            v1 = parts.get("v1", "")
            if not ts or not v1:
                raise ValueError("Missing ts or v1")
            verification_str = f"id:{body.get('data', {}).get('id', '')};request-id:{request.headers.get('x-request-id', '')};ts:{ts};"
            expected = hmac.new(MP_WEBHOOK_SECRET.encode(), verification_str.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, v1):
                logger.warning("MP webhook: invalid signature")
                return JSONResponse(status_code=401, content={"error": "Invalid signature"})
        except Exception as e:
            logger.warning("MP webhook: signature verification error: %s", e)
            return JSONResponse(status_code=401, content={"error": "Signature verification failed"})

    topic = request.query_params.get("topic", "") or body.get("topic", "")
    payment_id = request.query_params.get("id", "") or body.get("id", "") or request.query_params.get("data.id", "")

    if topic == "payment" or (not topic and payment_id):
        if not payment_id:
            return {"received": True}
        headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
        try:
            resp = requests.get(f"{MP_API_BASE}/v1/payments/{payment_id}", headers=headers, timeout=10)
            if resp.status_code != 200:
                return JSONResponse(status_code=400, content={"error": "Cannot verify payment"})
            payment = resp.json()
            if payment.get("status") in ("approved", "authorized"):
                ext_ref = payment.get("external_reference", "")
                if ext_ref:
                    try:
                        ref = json.loads(ext_ref)
                        user_id = ref.get("user_id", "")
                        plan = ref.get("plan", "pro")
                        if user_id:
                            expires_at = (datetime.utcnow() + timedelta(days=MP_DURATION_DAYS)).isoformat()
                            supabase.table("profiles").update({
                                "plan": plan,
                                "mp_plan_expires_at": expires_at,
                            }).eq("user_id", user_id).execute()
                            logger.info("Plan actualizado a %s para user %s (expira %s)", plan, user_id, expires_at)
                    except json.JSONDecodeError:
                        logger.error("Invalid external_reference: %s", ext_ref)
        except requests.RequestException as e:
            logger.error("Error consultando pago MP: %s", e)
    return {"received": True}


@app.get("/api/mp/subscription")
def mp_get_subscription(authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    profile = supabase.table("profiles").select("plan, email, mp_plan_expires_at").eq("user_id", uid).limit(1).execute()
    if not profile.data:
        raise HTTPException(status_code=404, detail="Profile not found")
    p = profile.data[0]
    plan = p.get("plan", "starter")
    expires_at = p.get("mp_plan_expires_at")

    # Si expiró, volver a starter
    if expires_at and plan != "starter":
        try:
            exp = datetime.fromisoformat(expires_at)
            if exp < datetime.utcnow():
                supabase.table("profiles").update({"plan": "starter", "mp_plan_expires_at": None}).eq("user_id", uid).execute()
                plan = "starter"
                expires_at = None
        except (ValueError, TypeError):
            pass

    return {"plan": plan, "email": p.get("email", ""), "expires_at": expires_at}

# ─── Admin ───────────────────────────────────────────────

@app.get("/api/admin/users")
def admin_users(authorization: str = Header(default="")):
    try:
        uid = get_user_id(authorization)
        profile = supabase.table("profiles").select("role").eq("user_id", uid).limit(1).execute()
        role = profile.data[0].get("role", "user") if profile.data else "user"
        if role != "admin":
            raise HTTPException(status_code=403, detail="Admin only")
        res = supabase.table("profiles").select("user_id, email, username, plan, role, created_at").order("created_at", desc=True).limit(30).execute()
        return {"users": res.data or []}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("admin_users error: %s", e)
        return JSONResponse(status_code=500, content={"detail": "Error al obtener usuarios"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
