import os
import re
import time
import json
import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

import requests

from fastapi import FastAPI, HTTPException, Header, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from auth.supabase_client import supabase

# ─── Rate limiter ────────────────────────────────────────
_hunt_limits: dict[str, list[float]] = {}

def rate_limit_hunt(uid: str):
    now = time.time()
    window = 30.0
    max_requests = 2
    timestamps = _hunt_limits.get(uid, [])
    timestamps = [t for t in timestamps if now - t < window]
    if len(timestamps) >= max_requests:
        retry_after = int(window - (now - timestamps[0]))
        raise HTTPException(status_code=429, detail=f"Demasiadas solicitudes. Esperá {retry_after}s.")
    timestamps.append(now)
    _hunt_limits[uid] = timestamps

app = FastAPI(title="Howlify API", version="1.0.0")

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

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

    app.add_middleware(SPAFallbackMiddleware)

# ─── Auth ───────────────────────────────────────────────

def get_user_id(authorization: str = "") -> str:
    token = authorization.replace("Bearer ", "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Token requerido")
    try:
        payload_b64 = token.split(".")[1]
        padded = payload_b64 + "=" * (4 - len(payload_b64) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(padded))
        uid = decoded.get("sub")
        if not uid:
            raise HTTPException(status_code=401, detail="Token inválido: sin sub")
        return uid
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
    plan: str = "starter"

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

# ─── Helpers ────────────────────────────────────────────

def domain_from_url(url: str) -> str:
    try:
        host = urlparse(str(url)).netloc.lower().strip()
        return host[4:] if host.startswith("www.") else host or "unknown"
    except Exception:
        return "unknown"

def infer_source_from_url(url: str) -> str:
    d = domain_from_url(url)
    if "mercadolibre" in d: return "mercadolibre"
    if "fravega" in d: return "fravega"
    if "garbarino" in d: return "garbarino"
    if "tiendamia" in d: return "tiendamia"
    if "temu" in d: return "temu"
    if "tripstore" in d: return "tripstore"
    if "carrefour" in d: return "carrefour"
    if "despegar" in d: return "despegar"
    if "airbnb" in d: return "airbnb"
    return "unknown"

def parse_price_to_int(value) -> int:
    if value is None: return 0
    if isinstance(value, (int, float)): return int(value)
    s = str(value).strip()
    if not s: return 0
    if re.fullmatch(r"\d+\.\d{1,2}", s): s = s.split(".", 1)[0]
    digits = re.sub(r"[^\d]", "", s)
    return int(digits) if digits else 0

def clean_ml_url(url: str) -> str:
    if not url: return url
    cleaned = re.sub(r"#.*", "", url)
    cleaned = re.sub(r"https?://[^/]+/.*?/", lambda m: m.group(0), cleaned)
    return cleaned.rstrip("/?&")

def save_price_history(user_id: str, caza_id, results: list[dict]):
    if not user_id or not results: return
    rows = []
    for r in results:
        try: price = int(r.get("price") or r.get("precio") or 0)
        except: price = 0
        if price <= 0: continue
        rows.append({
            "caza_id": caza_id, "user_id": user_id,
            "title": (r.get("title") or r.get("titulo") or "").strip(),
            "url": (r.get("url") or r.get("link") or "").strip(),
            "source": (r.get("source") or "").strip(),
            "price": price, "checked_at": "now()",
        })
    if not rows: return
    try: supabase.table("price_history").insert(rows).execute()
    except Exception as e: print("[save_price_history] error:", e)

# ─── Endpoints ──────────────────────────────────────────

@app.get("/")
def root():
    if _HAS_REACT:
        return FileResponse(str(REACT_DIST / "index.html"))
    return {"name": "Howlify API", "version": "1.0.0", "status": "running"}

@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

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
    user, err = supa_signup(req.email, req.password, req.password, req.username, req.plan)
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
    report_enabled: bool | None = None
    report_time: str | None = None
    report_days: list[int] | None = None


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
    channel: str  # "telegram", "whatsapp", "email"


@app.post("/api/auth/test-notification")
def test_notification(data: TestNotificationRequest, authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    from db.database import get_user_profile
    profile = get_user_profile(uid)
    if not profile:
        raise HTTPException(status_code=404, detail="Perfil no encontrado")

    from services.notification_service import enviar_telegram, enviar_whatsapp, enviar_email
    mensaje = "🐺 ¡Howlify funciona correctamente! Esta es una notificación de prueba."

    if data.channel == "telegram":
        tg_id = profile.get("telegram_id")
        if not tg_id:
            raise HTTPException(status_code=400, detail="No hay Telegram ID configurado")
        ok = enviar_telegram(str(tg_id), mensaje)
        return {"ok": ok, "channel": "telegram"}

    if data.channel == "whatsapp":
        num = profile.get("whatsapp_number")
        if not num:
            raise HTTPException(status_code=400, detail="No hay WhatsApp configurado")
        ok = enviar_whatsapp(str(num), mensaje)
        return {"ok": ok, "channel": "whatsapp"}

    if data.channel == "email":
        email = profile.get("email") or profile.get("user_email")
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
    cazas = obtener_cazas(uid, "starter")
    return {"cazas": cazas}

@app.post("/api/cazas")
def create_caza(caza: CazaCreate, authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    from services.database_service import guardar_caza_supabase
    profile = supabase.table("profiles").select("plan").eq("user_id", uid).limit(1).execute()
    plan = profile.data[0]["plan"] if profile.data else "starter"
    url_limpia = clean_ml_url(caza.url)
    src = infer_source_from_url(url_limpia) or "generic"
    precio_int = parse_price_to_int(caza.precio_max)
    ok = guardar_caza_supabase(uid, caza.keyword, url_limpia, precio_int, caza.frecuencia, caza.tipo, plan, src)
    if ok is not True:
        raise HTTPException(status_code=400, detail=str(ok))
    return {"message": "Cacería creada"}

@app.put("/api/cazas/{caza_id}")
def update_caza(caza_id: int, data: CazaCreate, authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    url_limpia = clean_ml_url(data.url)
    src = infer_source_from_url(url_limpia) or "generic"
    precio_int = parse_price_to_int(data.precio_max)
    supabase.table("cazas").update({
        "producto": data.keyword,
        "link": url_limpia,
        "precio_max": precio_int,
        "frecuencia": data.frecuencia,
        "tipo_alerta": data.tipo,
        "source": src,
    }).eq("id", caza_id).eq("user_id", uid).execute()
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
    res = supabase.table("cazas").select("*").eq("id", caza_id).limit(1).execute()
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
        for r in resultados:
            precio_r = r.get("price") or 0
            if precio_r > 0:
                es_error, prom = detectar_price_error(caza_id, float(precio_r))
                if es_error:
                    r["price_error"] = True
                    r["price_avg"] = prom
                if tipo_alerta == "descuento":
                    from engine.engine import _obtener_precio_referencia
                    ref = _obtener_precio_referencia(caza_id) or precio_r
                    descuento = int((1 - precio_r / ref) * 100) if ref > 0 else 0
                    r["descuento"] = descuento
                    r["match_descuento"] = descuento >= max(precio_max_raw, 0)
    return {"results": resultados}

@app.post("/api/hunt/all")
def hunt_all(authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    rate_limit_hunt(uid)
    from db.database import obtener_cazas
    cazas = obtener_cazas(uid, "starter")
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
                for r in res:
                    precio_r = r.get("price") or 0
                    if precio_r > 0:
                        es_error, prom = detectar_price_error(c.get("id"), float(precio_r))
                        if es_error:
                            r["price_error"] = True
                            r["price_avg"] = prom
                        if tipo_alerta == "descuento":
                            from engine.engine import _obtener_precio_referencia
                            ref = _obtener_precio_referencia(c.get("id")) or precio_r
                            descuento = int((1 - precio_r / ref) * 100) if ref > 0 else 0
                            r["descuento"] = descuento
                            r["match_descuento"] = descuento >= max(precio_max_raw, 0)
            results[rid] = res
        except Exception as e:
            results[rid] = {"error": str(e)}
    return {"results": results}

# ─── Async Hunt (via Celery) ────────────────────────────


@app.post("/api/hunt/async/{caza_id}")
def hunt_single_async(caza_id: int, authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    rate_limit_hunt(uid)
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
def get_task_status(task_id: str):
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
        .order("checked_at", desc=True) \
        .limit(50) \
        .execute()
    return {"history": res.data or []}

# ─── Monitor ────────────────────────────────────────────

@app.get("/api/monitor/rules")
def get_monitor_rules(authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    res = supabase.table("monitor_rules").select("*").eq("user_id", uid).execute()
    return {"rules": res.data or []}

@app.put("/api/monitor/rules/{caza_id}")
def upsert_monitor_rule(caza_id: int, body: dict, authorization: str = Header(default="")):
    try:
        uid = get_user_id(authorization)
        payload = {
            "user_id": uid,
            "caza_id": caza_id,
            "product_name": body.get("product_name", "").strip(),
            "product_url": body.get("product_url", "").strip(),
            "source": body.get("source", "generic").strip().lower(),
            "target_price": int(body.get("target_price", 0)),
            "min_price_allowed": int(body.get("min_price_allowed", 0)),
            "max_price_allowed": int(body.get("max_price_allowed", 0)),
            "is_active": True,
        }
        supabase.table("monitor_rules").upsert(payload, on_conflict="caza_id").execute()
        return {"message": "Regla actualizada"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Error upsert monitor rule: {e}"})

@app.delete("/api/monitor/rules/{caza_id}")
def delete_monitor_rule(caza_id: int, authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    supabase.table("monitor_rules").update({"is_active": False}).eq("user_id", uid).eq("caza_id", caza_id).execute()
    return {"message": "Regla desactivada"}

@app.get("/api/monitor/infracciones")
def get_infracciones(authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    res = supabase.table("monitor_rules").select("caza_id").eq("user_id", uid).execute()
    caza_ids = [r["caza_id"] for r in res.data if r.get("caza_id")]
    if not caza_ids:
        return {"infracciones": []}
    inf = supabase.table("infracciones_log").select("*").in_("caza_id", caza_ids).order("fecha", desc=True).limit(200).execute()
    return {"infracciones": inf.data or []}

@app.get("/api/monitor/grupos")
def get_grupos():
    res = supabase.table("grupos").select("*").execute()
    return {"grupos": res.data or []}

@app.post("/api/monitor/grupos")
def create_grupo(body: dict, authorization: str = Header(default="")):
    get_user_id(authorization)
    nombre = body.get("nombre", "").strip()
    color = body.get("color", "📁")
    if nombre:
        supabase.table("grupos").insert({"nombre": nombre, "color": color}).execute()
    return {"message": "Grupo creado"}

@app.delete("/api/monitor/grupos/{grupo_id}")
def delete_grupo(grupo_id: int, authorization: str = Header(default="")):
    get_user_id(authorization)
    supabase.table("grupo_cazas").delete().eq("grupo_id", grupo_id).execute()
    supabase.table("grupos").delete().eq("id", grupo_id).execute()
    return {"message": "Grupo eliminado"}

@app.get("/api/monitor/grupo-cazas")
def get_grupo_cazas():
    res = supabase.table("grupo_cazas").select("*").execute()
    return {"relaciones": res.data or []}

@app.put("/api/monitor/grupo-cazas")
def assign_grupo_caza(body: dict, authorization: str = Header(default="")):
    try:
        get_user_id(authorization)
        caza_id = body.get("caza_id")
        grupo_id = body.get("grupo_id")
        supabase.table("grupo_cazas").delete().eq("caza_id", caza_id).execute()
        if grupo_id:
            supabase.table("grupo_cazas").insert({"caza_id": caza_id, "grupo_id": grupo_id}).execute()
        return {"message": "Asignación actualizada"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Error assign grupo: {e}"})

@app.get("/api/monitor/price-history/{caza_id}")
def get_monitor_price_history(caza_id: int, authorization: str = Header(default="")):
    get_user_id(authorization)
    res = supabase.table("price_history").select("checked_at, price").eq("caza_id", caza_id).order("checked_at").limit(100).execute()
    return {"history": res.data or []}

@app.get("/api/monitor/latest-prices")
def get_latest_prices(authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    rules = supabase.table("monitor_rules").select("caza_id").eq("user_id", uid).execute()
    ids = [r["caza_id"] for r in rules.data if r.get("caza_id")]
    result = {}
    for cid in ids:
        row = supabase.table("price_history").select("price, checked_at").eq("caza_id", cid).order("checked_at", desc=True).limit(1).execute()
        if row.data:
            result[str(cid)] = {"price": row.data[0]["price"], "checked_at": row.data[0]["checked_at"]}
    return {"prices": result}

@app.get("/api/monitor/all-history")
def get_all_history(authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    rules = supabase.table("monitor_rules").select("caza_id").eq("user_id", uid).execute()
    ids = [r["caza_id"] for r in rules.data if r.get("caza_id")]
    if not ids:
        return {"history": []}
    res = supabase.table("price_history").select("caza_id, price, checked_at").in_("caza_id", ids).order("checked_at").limit(2000).execute()
    return {"history": res.data or []}

@app.get("/api/monitor/evidencia/{caza_id}")
def get_evidencia(caza_id: int, authorization: str = Header(default=""), token: str = Query(default="")):
    auth = authorization or token
    get_user_id(auth)
    inf = supabase.table("infracciones_log").select("url_captura").eq("caza_id", caza_id).order("fecha", desc=True).limit(1).execute()
    if not inf.data or not inf.data[0].get("url_captura"):
        raise HTTPException(status_code=404, detail="Evidencia no encontrada")
    path = inf.data[0]["url_captura"]
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(path, media_type="image/png")

# ─── Google Sheets Export ─────────────────────────────────

@app.post("/api/export/sheets")
def export_to_sheets(data: dict, authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    try:
        import pandas as pd
        from utils.logic import exportar_a_sheets
        df = pd.DataFrame(data.get("rows", []))
        if df.empty:
            raise HTTPException(status_code=400, detail="Sin datos para exportar")
        ok, info = exportar_a_sheets(df, nombre_hoja=data.get("sheet_name", f"Howlify Export {uid[:8]}"))
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
    cazas = obtener_cazas(uid, "starter")
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

# ─── Mercado Pago / Billing ─────────────────────────────

MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN", "")
MP_API_BASE = "https://api.mercadopago.com"

MP_PRICES = {
    "pro": int(os.getenv("MP_PRICE_PRO_ARS", "3000")),
    "business_reseller": int(os.getenv("MP_PRICE_RESELLER_ARS", "8000")),
    "business_monitor": int(os.getenv("MP_PRICE_MONITOR_ARS", "12000")),
}

MP_DURATION_DAYS = 30  # días de acceso por pago

@app.post("/api/mp/create-preference")
def mp_create_preference(data: dict, authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    plan = data.get("plan", "pro")
    if plan not in MP_PRICES:
        raise HTTPException(status_code=400, detail=f"Plan inválido: {plan}")

    price = MP_PRICES[plan]
    profile = supabase.table("profiles").select("email, username").eq("user_id", uid).limit(1).execute()
    if not profile.data:
        raise HTTPException(status_code=404, detail="Profile not found")
    email = profile.data[0].get("email", "")
    username = profile.data[0].get("username", "")

    PLAN_LABEL = {"pro": "Pro", "business_reseller": "Business Reseller", "business_monitor": "Business Monitor"}
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

    # MP puede enviar el id por query o por body
    topic = request.query_params.get("topic", "") or body.get("topic", "")
    payment_id = request.query_params.get("id", "") or body.get("id", "")

    if topic == "payment" or topic == "merchant_order" or (not topic and payment_id):
        if not payment_id:
            return {"received": True}
        headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
        try:
            resp = requests.get(f"{MP_API_BASE}/v1/payments/{payment_id}", headers=headers)
            if resp.status_code != 200:
                return JSONResponse(status_code=400, content={"error": "Cannot verify payment"})
            payment = resp.json()
            if payment.get("status") == "approved" or payment.get("status") == "authorized":
                ext_ref = payment.get("external_reference", "")
                if ext_ref:
                    try:
                        ref = json.loads(ext_ref)
                        user_id = ref.get("user_id", "")
                        plan = ref.get("plan", "pro")
                        if user_id:
                            # Actualizar plan + fecha de expiración
                            expires_at = (datetime.utcnow() + timedelta(days=MP_DURATION_DAYS)).isoformat()
                            supabase.table("profiles").update({
                                "plan": plan,
                                "mp_plan_expires_at": expires_at,
                            }).eq("user_id", user_id).execute()
                            print(f"✅ Plan actualizado a {plan} para user {user_id} (expira {expires_at})")
                    except json.JSONDecodeError:
                        print(f"❌ Invalid external_reference: {ext_ref}")
        except requests.RequestException as e:
            print(f"❌ Error consultando pago MP: {e}")
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
    uid = get_user_id(authorization)
    profile = supabase.table("profiles").select("role").eq("user_id", uid).limit(1).execute()
    role = profile.data[0].get("role", "user") if profile.data else "user"
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    res = supabase.table("profiles").select("user_id, email, username, plan, role, created_at").order("created_at", desc=True).limit(30).execute()
    return {"users": res.data or []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
