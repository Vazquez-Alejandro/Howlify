import re
import random
import time
import requests
from datetime import datetime, timezone

# ==========================================================
# 1. UTILIDADES DE LIMPIEZA Y FORMATO
# ==========================================================

def _safe_float(val, default=0.0):
    """Convierte precios sucios a float."""
    if val is None: return default
    if isinstance(val, (int, float)): return float(val)
    try:
        if isinstance(val, str):
            val = val.replace("$", "").replace(" ", "").replace(".", "").replace(",", ".").strip()
        return float(val)
    except:
        return default

def parse_price_to_int(val):
    return int(_safe_float(val))

def _parse_dt_utc(dt_str):
    if not dt_str: return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except:
        return None

# ==========================================================
# 2. LÓGICA DE PLANES Y SCHEDULER
# ==========================================================

PLAN_RULES = {
    "starter": {"max_cazas_activas": 3, "freq_options": ["12h", "24h"], "plan_key": "starter"},
    "pro": {"max_cazas_activas": 15, "freq_options": ["1h", "6h", "12h", "24h"], "plan_key": "pro"},
    "business": {"max_cazas_activas": 100, "freq_options": ["15min", "1h", "6h"], "plan_key": "business"}
}

def normalize_plan_family(plan: str) -> str:
    raw = (plan or "starter").strip().lower()
    if raw in ["business_reseller", "business_monitor", "business"]: return "business"
    if raw in ["pro", "beta", "alfa"]: return "pro"
    return "starter"

def get_effective_plan_rules(plan_name):
    family = normalize_plan_family(plan_name)
    return PLAN_RULES.get(family, PLAN_RULES["starter"])

def _effective_minutes(plan, freq_str):
    """Traduce la frecuencia a minutos reales (La que faltaba)."""
    if freq_str == "15min": return 15
    if freq_str == "1h": return 60
    if freq_str == "6h": return 360
    if freq_str == "12h": return 720
    return 1440

def contar_cazas_activas(user_id):
    from auth.supabase_client import supabase
    try:
        res = supabase.table("cazas").select("id", count="exact").eq("user_id", user_id).eq("estado", "activa").execute()
        return res.count if res.count is not None else 0
    except:
        return 0

# ==========================================================
# 3. EXTRACCIÓN Y URLS
# ==========================================================

def _extract_product_id(url):
    if not url: return "unknown"
    match = re.search(r"(MLA|MLU|MLM|MLB)-?(\d+)", url, re.IGNORECASE)
    return match.group(0) if match else "generic"

def _domain_from_url(url):
    from urllib.parse import urlparse
    return urlparse(url).netloc.replace("www.", "")

def clean_ml_url(url: str) -> str:
    if not url or "mercadolibre" not in url: return url
    match = re.search(r'(MLA-?\d+)', url, re.IGNORECASE)
    if match:
        product_id = match.group(1).replace("-", "").upper()
        return f"https://www.mercadolibre.com.ar/p/{product_id}"
    return url.split('#')[0].split('?')[0].strip()

# ==========================================================
# 4. ESTRATEGIA ANTI-BLOQUEO
# ==========================================================

def get_random_user_agent():
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ]
    return random.choice(agents)

def apply_human_jitter():
    delay = random.uniform(1.5, 4.0)
    time.sleep(delay)
    return delay

# ==========================================================
# 5. ANÁLISIS Y DB
# ==========================================================

def evaluar_oferta(precio_actual, config):
    tipo = config.get('tipo', 'piso')
    objetivo = config.get('objetivo', 0)
    if tipo == 'piso' and precio_actual <= objetivo:
        return True, f"¡Bajó del piso de ${objetivo:,.0f}!"
    return False, ""

def obtener_dolar_tarjeta():
    try:
        url = "https://dolarapi.com/v1/dolares/tarjeta"
        response = requests.get(url, timeout=10)
        return float(response.json()['venta']) 
    except:
        return 1860.0

def upsert_monitor_rule(user_id, caza_id, product_name, product_url, source, target_price, min_price_allowed, max_price_allowed):
    from auth.supabase_client import supabase
    try:
        data = {
            "user_id": user_id, "caza_id": caza_id, "product_name": product_name,
            "product_url": product_url, "source": source, "target_price": target_price,
            "min_price_allowed": min_price_allowed, "max_price_allowed": max_price_allowed
        }
        res = supabase.table("monitor_rules").upsert(data, on_conflict="caza_id").execute()
        return True if res.data else False
    except Exception as e:
        print(f"❌ Error en upsert_monitor_rule: {e}")
        return False