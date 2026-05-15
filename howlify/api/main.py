import os
import re
import time
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel

from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

app = FastAPI(title="Howlify API", version="1.0.0")

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ─── Auth ───────────────────────────────────────────────

def get_user_id(authorization: str = "") -> str:
    token = authorization.replace("Bearer ", "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Token requerido")
    try:
        user = supabase.auth.get_user(token)
        return user.id
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
            {"redirect_to": "http://localhost:5173/reset-password"}
        )
        return {"message": "Correo enviado"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/auth/profile")
def get_profile(authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    from db.database import get_user_profile
    profile = get_user_profile(uid)
    return {"user_id": uid, "profile": profile}

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
    url_limpia = clean_ml_url(caza.url)
    src = infer_source_from_url(url_limpia) or "generic"
    precio_int = parse_price_to_int(caza.precio_max)
    ok = guardar_caza_supabase(uid, caza.keyword, url_limpia, precio_int, caza.frecuencia, caza.tipo, "starter", src)
    if ok is not True:
        raise HTTPException(status_code=400, detail=str(ok))
    return {"message": "Cacería creada"}

@app.delete("/api/cazas/{caza_id}")
def delete_caza(caza_id: int, authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    supabase.table("cazas").delete().eq("id", caza_id).eq("user_id", uid).execute()
    return {"message": "Cacería eliminada"}

# ─── Hunt ───────────────────────────────────────────────

@app.post("/api/hunt/{caza_id}")
def hunt_single(caza_id: int, authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    res = supabase.table("cazas").select("*").eq("id", caza_id).limit(1).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Cacería no encontrada")

    caza = res.data[0]
    url = caza.get("url") or caza.get("link") or ""
    precio = caza.get("precio_max") or 0
    src = infer_source_from_url(url).strip().lower()

    if src == "airbnb":
        from scraper.airbnb import hunt_airbnb
        resultados = hunt_airbnb(url, precio) or []
    else:
        from scraper.scraper_pro import hunt_offers
        resultados = hunt_offers(url, caza.get("keyword", ""), precio, headless=True) or []

    if resultados:
        save_price_history(uid, caza_id, resultados)
    return {"results": resultados}

@app.post("/api/hunt/all")
def hunt_all(authorization: str = Header(default="")):
    uid = get_user_id(authorization)
    from db.database import obtener_cazas
    cazas = obtener_cazas(uid, "starter")
    results = {}
    for c in cazas:
        rid = str(c.get("id", ""))
        try:
            url = c.get("url") or c.get("link") or ""
            precio = c.get("precio_max") or 0
            src = infer_source_from_url(url).strip().lower()
            if src == "airbnb":
                from scraper.airbnb import hunt_airbnb
                res = hunt_airbnb(url, precio) or []
            else:
                from scraper.scraper_pro import hunt_offers
                res = hunt_offers(url, c.get("keyword", ""), precio, headless=True) or []
            if res:
                save_price_history(uid, c.get("id"), res)
            results[rid] = res
        except Exception as e:
            results[rid] = {"error": str(e)}
    return {"results": results}

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

@app.get("/api/monitor/grupos")
def get_grupos():
    res = supabase.table("grupos").select("*").execute()
    return {"grupos": res.data or []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
