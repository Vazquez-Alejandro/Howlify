from __future__ import annotations
from auth.supabase_client import supabase
from config import PLAN_LIMITS
from utils.logic import parse_price_to_int, infer_source_from_url
from utils.logger import get_logger
logger = get_logger("db")


# --- FUNCIONES DE CAZAS ---
def guardar_caza(user_id, producto, url, precio_max, frecuencia, tipo_alerta, plan, source=None):
    try:
        if not user_id: return False
        plan = (plan or "omega").strip().lower()
        source = source or infer_source_from_url(url)
        limite = PLAN_LIMITS.get(plan, 2)

        count_res = supabase.table("cazas").select("id", count="exact").eq("user_id", user_id).eq("estado", "activa").execute()
        if int(getattr(count_res, "count", 0) or 0) >= limite: return "limite"

        payload = {
            "user_id": user_id,
            "producto": (producto or "").strip(),
            "link": (url or "").strip(),
            "precio_max": parse_price_to_int(precio_max),
            "frecuencia": (frecuencia or "").strip(),
            "tipo_alerta": (tipo_alerta or "piso").strip().lower(),
            "plan": plan, "estado": "activa", "source": source, "last_check": None,
        }
        ins = supabase.table("cazas").insert(payload).execute()
        return True if getattr(ins, "data", None) else False
    except Exception as e:
        logger.error(f"[guardar_caza] error: {e}")
        return False

def obtener_cazas(user_id: str, plan: str):
    try:
        if not user_id: return []
        res = supabase.table("cazas").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        cazas = getattr(res, "data", []) or []
        _enriquecer_precio_venta(cazas)
        return cazas
    except Exception as e:
        logger.error(f"[obtener_cazas] error: {e}")
        return []


def _enriquecer_precio_venta(cazas: list[dict]):
    """Agrega precio_venta a cada caza leyendo la regla 'margen' de monitor_rules."""
    if not cazas:
        return
    ids = [c.get("id") for c in cazas if c.get("id")]
    if not ids:
        return
    try:
        import json
        res = supabase.table("monitor_rules") \
            .select("caza_id, alert_config") \
            .in_("caza_id", ids) \
            .execute()
        for row in (res.data or []):
            cfg = row.get("alert_config")
            if isinstance(cfg, str):
                try:
                    cfg = json.loads(cfg)
                except Exception:
                    cfg = None
            sale = 0
            if isinstance(cfg, list):
                for r in cfg:
                    if isinstance(r, dict) and r.get("type") == "margen":
                        sale = int(r.get("threshold") or 0)
                        break
            if sale > 0:
                for c in cazas:
                    if c.get("id") == row.get("caza_id"):
                        c["precio_venta"] = sale
                        break
    except Exception as e:
        logger.error(f"[_enriquecer_precio_venta] error: {e}")

# --- FUNCIONES DE PERFIL (CORREGIDAS) ---
def get_user_profile(user_id: str):
    """Trae el perfil usando user_id como columna."""
    try:
        if not user_id: return {}
        res = supabase.table("profiles").select("*").eq("user_id", user_id).single().execute()
        return getattr(res, "data", {}) or {}
    except Exception as e:
        logger.error(f"[get_user_profile] error: {e}")
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
        logger.info(f"DEBUG: Supabase respondió con data: {res.data}")
        
        return len(res.data) > 0
    except Exception as e:
        logger.error(f"[save_user_telegram] ERROR CRÍTICO: {e}")
        return False

def save_user_whatsapp(user_id: str, whatsapp_number: str) -> bool:
    try:
        res = supabase.table("profiles").update({"whatsapp_number": str(whatsapp_number).strip()}).eq("user_id", user_id).execute()
        return len(getattr(res, "data", [])) > 0
    except Exception as e:
        logger.error(f"[save_user_whatsapp] error: {e}")
        return False