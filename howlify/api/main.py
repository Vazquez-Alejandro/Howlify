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

from pywebpush import webpush, WebPushException

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
from fastapi.responses import JSONResponse as _JSONResponse
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    print(f"[UNHANDLED] {request.method} {request.url.path}: {exc}")
    return _JSONResponse(status_code=500, content={"detail": "Error interno del servidor"})

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
    etiqueta: str = ""

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
    email_notifications: bool | None = None
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
        "etiqueta": data.etiqueta,
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
                if tipo_alerta == "grande":
                    from engine.engine import _obtener_precio_referencia
                    ref = _obtener_precio_referencia(caza_id) or precio_r
                    drop_pct = int((1 - precio_r / ref) * 100) if ref > 0 else 0
                    r["drop_pct"] = drop_pct
                    r["match_grande"] = drop_pct >= 25
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
                        if tipo_alerta == "grande":
                            from engine.engine import _obtener_precio_referencia
                            ref = _obtener_precio_referencia(c.get("id")) or precio_r
                            drop_pct = int((1 - precio_r / ref) * 100) if ref > 0 else 0
                            r["drop_pct"] = drop_pct
                            r["match_grande"] = drop_pct >= 25
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
            "alert_config": body.get("alert_config", []),
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

@app.post("/api/monitor/evaluate-rules/{caza_id}")
def evaluate_monitor_rules(caza_id: int, authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    rules = supabase.table("monitor_rules").select("*").eq("user_id", uid).eq("caza_id", caza_id).limit(1).execute()
    if not rules.data:
        return {"triggered": []}
    rule = rules.data[0]
    if not rule.get("is_active"):
        return {"triggered": []}
    alert_config = rule.get("alert_config")
    if not alert_config:
        return {"triggered": []}
    if isinstance(alert_config, str):
        alert_config = json.loads(alert_config)

    history = supabase.table("price_history").select("price, checked_at").eq("caza_id", caza_id).order("checked_at", desc=True).limit(10).execute()
    prices = [float(h["price"]) for h in (history.data or []) if h.get("price")]
    if not prices:
        return {"triggered": []}
    current = prices[0]
    triggered = []

    for r in alert_config:
        if not r.get("enabled", True):
            continue
        rtype = r.get("type", "")
        threshold = float(r.get("threshold", 0))
        match = False

        if rtype == "below_price":
            match = current <= threshold
        elif rtype == "above_price":
            match = current >= threshold
        elif rtype == "pct_drop" and len(prices) >= 2:
            pct = ((prices[1] - current) / prices[1]) * 100
            match = pct >= threshold
        elif rtype == "consecutive_drop" and len(prices) >= int(threshold):
            consec = 0
            for i in range(1, len(prices)):
                if prices[i] < prices[i-1]:
                    consec += 1
                else:
                    consec = 0
                if consec >= int(threshold) and i >= int(threshold) - 1:
                    match = True
                    break
        elif rtype == "velocity_drop":
            history24 = supabase.table("price_history").select("price").eq("caza_id", caza_id).gte("checked_at", (datetime.utcnow() - timedelta(hours=24)).isoformat()).order("checked_at").limit(2).execute()
            hp = [float(h["price"]) for h in (history24.data or []) if h.get("price")]
            if len(hp) >= 2 and hp[0] > 0:
                pct = ((hp[0] - current) / hp[0]) * 100
                match = pct >= threshold
        elif rtype == "below_hist_min":
            all_prices = supabase.table("price_history").select("price").eq("caza_id", caza_id).order("price").limit(1).execute()
            if all_prices.data:
                historical_min = float(all_prices.data[0]["price"])
                if historical_min > 0:
                    match = current <= historical_min * 1.01

        if match:
            triggered.append({"rule": r, "current_price": current})

    return {"triggered": triggered, "current_price": current}

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

# ─── Alert History + KPIs ─────────────────────────────────

@app.get("/api/alerts/history")
def get_alert_history(authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    res = supabase.table("alertas_enviadas").select("*").eq("user_id", uid).order("created_at", desc=True).limit(100).execute()
    return {"alerts": res.data or []}

@app.get("/api/kpi/summary")
def get_kpi_summary(authorization: str = Header(default="")):
    uid = get_user_id(authorization)

    cazas = supabase.table("cazas").select("id, precio_max").eq("user_id", uid).execute()
    cazas_data = cazas.data or []
    total_cazas = len(cazas_data)
    ahorro_total = 0
    productos_con_precio = 0

    c_ids = [str(c["id"]) for c in cazas_data]
    if c_ids:
        all_hist = supabase.table("price_history").select("caza_id, price").in_("caza_id", c_ids).execute()
        hist_map: dict[int, list[float]] = {}
        for h in (all_hist.data or []):
            cid = h.get("caza_id")
            if cid:
                hist_map.setdefault(int(cid), []).append(float(h["price"]))
    else:
        hist_map = {}

    for c in cazas_data:
        cid = int(c["id"])
        pm = c.get("precio_max") or 0
        prices = hist_map.get(cid, [])
        lp = max(prices) if prices else 0
        if lp > 0 and pm > 0 and lp < pm:
            ahorro_total += pm - lp
        if lp > 0:
            productos_con_precio += 1

    alertas = supabase.table("alertas_enviadas").select("id, created_at").eq("user_id", uid).execute()
    total_alertas = len(alertas.data or [])

    res_hist = supabase.table("price_history").select("price, checked_at").eq("user_id", uid).order("checked_at", desc=True).limit(5000).execute()
    prices = [float(h["price"]) for h in (res_hist.data or []) if h.get("price")]
    precio_promedio = round(sum(prices) / len(prices), 2) if prices else 0

    try:
        rules = supabase.table("monitor_rules").select("caza_id, alert_config").eq("user_id", uid).eq("is_active", True).execute()
        reglas_activas = 0
        for r in (rules.data or []):
            ac = r.get("alert_config")
            if ac and (isinstance(ac, list) and len(ac) > 0):
                reglas_activas += 1
    except Exception:
        reglas_activas = 0

    return {
        "total_cazas": total_cazas,
        "productos_con_precio": productos_con_precio,
        "ahorro_total": ahorro_total,
        "total_alertas": total_alertas,
        "precio_promedio": precio_promedio,
        "reglas_activas": reglas_activas,
    }

@app.get("/api/kpi/seasonality/{caza_id}")
def get_seasonality(caza_id: int, authorization: str = Header(default="")):
    get_user_id(authorization)
    res = supabase.table("price_history").select("price, checked_at").eq("caza_id", caza_id).order("checked_at").limit(200).execute()
    data = res.data or []
    from collections import defaultdict
    day_map = defaultdict(list)
    for h in data:
        try:
            dt = datetime.fromisoformat(h["checked_at"].replace("Z", "+00:00"))
            day_map[dt.strftime("%A")].append(float(h["price"]))
        except:
            pass
    seasonality = {}
    for day, prices in day_map.items():
        if len(prices) >= 2:
            seasonality[day] = {
                "avg": round(sum(prices) / len(prices), 2),
                "min": min(prices),
                "max": max(prices),
                "count": len(prices),
            }
    return {"seasonality": seasonality}

@app.get("/api/kpi/inflated-prices")
def get_inflated_prices(authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    cazas = supabase.table("cazas").select("id, producto").eq("user_id", uid).execute()
    caza_ids = [c["id"] for c in (cazas.data or [])]
    if not caza_ids:
        return {"inflated": []}

    all_hist = supabase.table("price_history").select("caza_id, price, checked_at").in_("caza_id", caza_ids).order("checked_at").limit(5000).execute()
    hist_by_caza: dict[int, list[dict]] = {}
    for h in (all_hist.data or []):
        cid = h["caza_id"]
        if cid not in hist_by_caza:
            hist_by_caza[cid] = []
        hist_by_caza[cid].append(h)

    inflated = []
    for cid, hist in hist_by_caza.items():
        if len(hist) < 5:
            continue
        prices = [float(h["price"]) for h in hist if h.get("price")]
        # Look for a spike (price up >15%) followed by a drop
        for i in range(1, len(prices) - 2):
            spike = (prices[i] - prices[i-1]) / prices[i-1] * 100
            drop = (prices[i+2] - prices[i+1]) / prices[i+1] * 100
            if spike > 15 and drop < -10:
                from services.database_service import safe_query
                caza_info = safe_query("cazas_get", [{"col": "id", "val": cid}])
                nombre = ""
                if caza_info:
                    nombre = caza_info[0].get("producto", "") if isinstance(caza_info, list) else caza_info.get("producto", "")
                inflated.append({
                    "caza_id": cid,
                    "producto": nombre,
                    "fecha_spike": hist[i]["checked_at"],
                    "precio_spike": prices[i],
                    "fecha_drop": hist[i+2]["checked_at"],
                    "precio_drop": prices[i+2],
                    "spike_pct": round(spike, 1),
                    "drop_pct": round(drop, 1),
                })
                break
    return {"inflated": inflated}

# ─── Reportes ────────────────────────────────────────────

@app.post("/api/reports/generate")
def generate_report(body: dict, authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    tipo = body.get("type", "daily")
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
def test_alert_rule(body: dict, authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    caza_id = body.get("caza_id")
    if not caza_id:
        raise HTTPException(400, "Falta caza_id")
    try:
        from engine.engine import evaluar_reglas_alerta
        evaluar_reglas_alerta(caza_id, uid)
        return {"message": "Reglas evaluadas. Revisá tus notificaciones."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Error: {e}"})

@app.get("/api/reports/pdf")
def download_pdf_report(authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    try:
        from services.pdf_service import generate_monitor_pdf

        user = supabase.table("profiles").select("username, email").eq("user_id", uid).limit(1).execute()
        user_name = (user.data or [{}])[0].get("username") or (user.data or [{}])[0].get("email") or "Usuario"

        cazas = supabase.table("cazas").select("id, producto, precio_max").eq("user_id", uid).execute()
        cazas_data = cazas.data or []
        rules = supabase.table("monitor_rules").select("*").eq("user_id", uid).execute()
        rules_map = {str(r["caza_id"]): r for r in (rules.data or [])}
        price_map = {}
        for c in cazas_data:
            row = supabase.table("price_history").select("price").eq("caza_id", c["id"]).order("checked_at", desc=True).limit(1).execute()
            if row.data:
                price_map[c["id"]] = float(row.data[0]["price"])

        ahorro_total = 0
        radar_data = []
        for c in cazas_data:
            cid = c["id"]
            curr = price_map.get(cid, 0)
            pm = c.get("precio_max") or 0
            rule = rules_map.get(str(cid))
            mn = float(rule["min_price_allowed"]) if rule and rule.get("min_price_allowed") else 0
            mx = float(rule["max_price_allowed"]) if rule and rule.get("max_price_allowed") else 0
            riesgo = "⚪"
            if mn > 0 or mx > 0:
                if curr <= 0: riesgo = "⚪"
                elif (mn > 0 and curr < mn - 0.01) or (mx > 0 and curr > mx + 0.01): riesgo = "🔴"
                elif curr == mn or curr == mx: riesgo = "🟠"
                elif (mn > 0 and curr <= mn * 1.05) or (mx > 0 and curr >= mx * 0.95): riesgo = "🟡"
                else: riesgo = "🟢"
            if curr < pm:
                ahorro_total += pm - curr
            radar_data.append({"producto": c.get("producto") or f"#{cid}", "precio": curr, "minP": mn, "maxP": mx, "riesgo": riesgo})

        alertas = supabase.table("alertas_enviadas").select("id").eq("user_id", uid).execute()
        total_alertas = len(alertas.data or [])
        all_prices = [p["price"] for p in (supabase.table("price_history").select("price").eq("user_id", uid).execute().data or []) if p.get("price")]
        precio_prom = round(sum(all_prices) / len(all_prices), 2) if all_prices else 0

        kpi = {"total_cazas": len(cazas_data), "productos_con_precio": len(price_map), "ahorro_total": ahorro_total, "total_alertas": total_alertas, "precio_promedio": precio_prom}
        pdf_bytes = generate_monitor_pdf(uid, user_name, radar_data, kpi)

        return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=howlify_reporte_{datetime.now().strftime('%Y%m%d')}.pdf"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": f"Error generando PDF: {e}"})

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

@app.get("/api/rates")
def get_rates():
    import requests as req
    try:
        blue = req.get("https://dolarapi.com/v1/dolares/blue", timeout=5).json()
        tarjeta = req.get("https://dolarapi.com/v1/dolares/tarjeta", timeout=5).json()
        return {
            "blue": float(blue.get("venta", 0)),
            "tarjeta": float(tarjeta.get("venta", 0)),
            "oficial": float(req.get("https://dolarapi.com/v1/dolares/oficial", timeout=5).json().get("venta", 0)),
        }
    except:
        return {"blue": 1300, "tarjeta": 1500, "oficial": 1000}

# ─── PWA Push Notifications ──────────────────────────────

VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_CLAIM = os.getenv("VAPID_CLAIM_EMAIL", "mailto:howlify@example.com")

def push_notify_user(uid: str, title: str, body: str, url: str = ""):
    if not VAPID_PRIVATE_KEY:
        return
    subs = supabase.table("push_subscriptions").select("subscription").eq("user_id", uid).execute()
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
            supabase.table("push_subscriptions").delete().eq("user_id", uid).execute()
        except Exception:
            pass

@app.post("/api/push/subscribe")
def push_subscribe(data: dict, authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    sub = data.get("subscription", {})
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
    push_notify_user(uid, "🧪 Prueba", "Si ves esto, las notificaciones push funcionan.", "/monitor")
    return {"message": "Notificación enviada"}

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
        print(f"[admin_users] error: {e}")
        return JSONResponse(status_code=500, content={"detail": "Error al obtener usuarios"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
