from __future__ import annotations
from urllib.parse import urlparse
from auth.supabase_client import supabase
from config import PLAN_LIMITS
import re

# --- UTILIDADES ---
def _parse_price_to_int(value) -> int:
    if value is None: return 0
    if isinstance(value, (int, float)): return int(value)
    s = str(value).strip()
    if not s: return 0
    if re.fullmatch(r"\d+\.\d{1,2}", s): s = s.split(".", 1)[0]
    digits = re.sub(r"[^\d]", "", s)
    return int(digits) if digits else 0

def _infer_source_from_url(url: str) -> str:
    try:
        host = urlparse(str(url)).netloc.lower().strip()
        if host.startswith("www."): host = host[4:]
    except: host = ""
    sources = ["mercadolibre", "fravega", "garbarino", "tiendamia", "temu", "tripstore"]
    for s in sources:
        if s in host: return s
    return "unknown"

# --- FUNCIONES DE CAZAS ---
def guardar_caza(user_id, producto, url, precio_max, frecuencia, tipo_alerta, plan, source=None):
    try:
        if not user_id: return False
        plan = (plan or "omega").strip().lower()
        source = source or _infer_source_from_url(url)
        limite = PLAN_LIMITS.get(plan, 2)

        count_res = supabase.table("cazas").select("id", count="exact").eq("user_id", user_id).eq("estado", "activa").execute()
        if int(getattr(count_res, "count", 0) or 0) >= limite: return "limite"

        payload = {
            "user_id": user_id,
            "producto": (producto or "").strip(),
            "link": (url or "").strip(),
            "precio_max": _parse_price_to_int(precio_max),
            "frecuencia": (frecuencia or "").strip(),
            "tipo_alerta": (tipo_alerta or "piso").strip().lower(),
            "plan": plan, "estado": "activa", "source": source, "last_check": None,
        }
        ins = supabase.table("cazas").insert(payload).execute()
        return True if getattr(ins, "data", None) else False
    except Exception as e:
        print(f"[guardar_caza] error: {e}")
        return False

def obtener_cazas(user_id: str, plan: str):
    try:
        if not user_id: return []
        res = supabase.table("cazas").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return getattr(res, "data", []) or []
    except Exception as e:
        print(f"[obtener_cazas] error: {e}")
        return []

# --- FUNCIONES DE PERFIL (CORREGIDAS) ---
def get_user_profile(user_id: str):
    """Trae el perfil usando user_id como columna."""
    try:
        if not user_id: return {}
        res = supabase.table("profiles").select("*").eq("user_id", user_id).single().execute()
        return getattr(res, "data", {}) or {}
    except Exception as e:
        print(f"[get_user_profile] error: {e}")
        return {}

def save_user_telegram(user_id: str, tg_id: str) -> bool:
    try:
        # Limpiamos el ID por las dudas
        clean_id = str(tg_id).strip()
        
        # Intentamos un UPSERT (Actualiza si existe, crea si no)
        res = (
            supabase.table("profiles")
            .upsert({
                "user_id": user_id, 
                "telegram_id": clean_id
            }, on_conflict="user_id") 
            .execute()
        )
        
        # DEBUG: Miramos qué nos dice Supabase en la terminal
        print(f"DEBUG: Supabase respondió con data: {res.data}")
        
        return len(res.data) > 0
    except Exception as e:
        print(f"[save_user_telegram] ERROR CRÍTICO: {e}")
        return False

def save_user_whatsapp(user_id: str, whatsapp_number: str) -> bool:
    try:
        res = supabase.table("profiles").update({"whatsapp_number": str(whatsapp_number).strip()}).eq("user_id", user_id).execute()
        return len(getattr(res, "data", [])) > 0
    except Exception as e:
        print(f"[save_user_whatsapp] error: {e}")
        return False