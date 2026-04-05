import re
import random
import time
import requests
from datetime import datetime, timezone


# ==========================================================
# 3. UTILIDADES DE LIMPIEZA Y FORMATO
# ==========================================================

def _safe_float(val, default=0.0):
    """Convierte cualquier cosa a float sin romper el motor."""
    if val is None: return default
    try:
        # Si es string, limpiamos símbolos de moneda y comas
        if isinstance(val, str):
            val = val.replace("$", "").replace(".", "").replace(",", ".").strip()
        return float(val)
    except:
        return default

def parse_price_to_int(val):
    """Convierte precios de la UI a enteros limpios."""
    return int(_safe_float(val))

def _parse_dt_utc(dt_str):
    """Convierte strings de Supabase a objetos datetime con zona horaria."""
    if not dt_str: return None
    try:
        # Reemplazamos Z por +00:00 para que Python lo entienda
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except:
        return None

# ==========================================================
# 4. LÓGICA DE PLANES (El 'Contrato' del Lobo)
# ==========================================================

PLAN_RULES = {
    "starter": {"max_cazas_activas": 3, "freq_options": ["12h", "24h"], "plan_key": "starter"},
    "pro": {"max_cazas_activas": 15, "freq_options": ["1h", "6h", "12h", "24h"], "plan_key": "pro"},
    "business": {"max_cazas_activas": 100, "freq_options": ["15min", "1h", "6h"], "plan_key": "business"}
}

def get_effective_plan_rules(plan_name):
    """Devuelve las reglas según el plan del usuario."""
    family = normalize_plan_family(plan_name)
    return PLAN_RULES.get(family, PLAN_RULES["starter"])

def normalize_plan_family(plan: str) -> str:
    """Mapea alias de planes a las familias principales."""
    raw = (plan or "starter").strip().lower()
    # Aquí podés agregar tus alias (omega, trial, etc)
    if raw in ["business_reseller", "business_monitor", "business"]: return "business"
    if raw in ["pro", "beta", "alfa"]: return "pro"
    return "starter"

def _effective_minutes(plan, freq_str):
    """Traduce '15min' o '1h' a minutos reales para el scheduler."""
    if freq_str == "15min": return 15
    if freq_str == "1h": return 60
    if freq_str == "6h": return 360
    if freq_str == "12h": return 720
    return 1440 # 24h por defecto

def contar_cazas_activas(user_id):
    """Consulta rápida a Supabase para ver cuántas tiene el usuario."""
    from services.database_service import supabase # Import local para evitar circularidad
    try:
        res = supabase.table("cazas").select("id", count="exact").eq("user_id", user_id).eq("estado", "activa").execute()
        return res.count if res.count is not None else 0
    except:
        return 0

def _extract_product_id(url):
    """Saca el ID de producto de la URL (ML, Amazon, etc)."""
    if not url: return "unknown"
    # Lógica simple para ML: MLA-123456
    match = re.search(r"(MLA|MLU|MLM|MLB)-?(\d+)", url, re.IGNORECASE)
    return match.group(0) if match else "generic"

def _domain_from_url(url):
    from urllib.parse import urlparse
    return urlparse(url).netloc.replace("www.", "")


# ==========================================================
# ESTRATEGIA NINJA (Anti-Bloqueo)
# ==========================================================

def get_random_user_agent():
    """Devuelve un User-Agent aleatorio para evitar bloqueos."""
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"
    ]
    return random.choice(agents)

def apply_human_jitter():
    """Pausa aleatoria para simular comportamiento humano."""
    delay = random.uniform(1.5, 4.0)
    time.sleep(delay)
    return delay

def evaluar_oferta(precio_actual, config):
    """Determina si el precio es una oferta según la configuración."""
    tipo = config.get('tipo', 'piso')
    objetivo = config.get('objetivo', 0)

    if tipo == 'piso':
        if precio_actual <= objetivo:
            return True, f"¡Bajó del piso de ${objetivo:,.0f}!"
    return False, ""


def obtener_dolar_tarjeta():
    """Consulta la cotización actualizada del dólar tarjeta"""
    try:
        # Usamos la API pública de dolarapi.com
        url = "https://dolarapi.com/v1/dolares/tarjeta"
        response = requests.get(url, timeout=10)
        data = response.json()
        # Retornamos el valor de venta
        return float(data['venta']) 
    except Exception as e:
        print(f"⚠️ Error obteniendo dólar: {e}")
        # Valor de respaldo por si la API falla
        return 1860.0
    
def _safe_float(val, default=0.0):
    """Convierte precios sucios o nulos a float sin romper nada."""
    if val is None: 
        return default
    
    # Si ya es un número, lo devolvemos
    if isinstance(val, (int, float)):
        return float(val)
        
    try:
        # Si es string, limpiamos todo lo que no sea número o punto
        if isinstance(val, str):
            # Quitamos $, espacios y puntos de miles, cambiamos coma decimal por punto
            val = val.replace("$", "").replace(" ", "").replace(".", "").replace(",", ".").strip()
        
        return float(val)
    except (ValueError, TypeError):
        print(f"⚠️ _safe_float: No pude convertir '{val}'")
        return default
    
def clean_ml_url(url: str) -> str:
    """
    Limpia las URLs de Mercado Libre eliminando parámetros de tracking 
    (?...) y anclas (#...) que rompen la redirección y el scraping.
    """
    if not url or not isinstance(url, str):
        return url
    # Cortamos primero por el ancla y luego por los parámetros de búsqueda
    return url.split('#')[0].split('?')[0].strip()

# ==========================================================
# 5. PERSISTENCIA Y REGLAS (Pegá esto al final de logic.py)
# ==========================================================

def guardar_caza_supabase(user_id, producto, url, precio_max, frecuencia, tipo_alerta, plan, source):
    """Inserta una nueva cacería en la tabla principal de Supabase."""
    from auth.supabase_client import supabase # Import local para evitar líos
    try:
        data = {
            "user_id": user_id,
            "producto": producto,
            "link": url,
            "precio_max": precio_max,
            "frecuencia": frecuencia,
            "plan": plan,
            "tipo_alerta": tipo_alerta,
            "source": source,
            "estado": "activa"
        }
        res = supabase.table("cazas").insert(data).execute()
        return True if res.data else False
    except Exception as e:
        print(f"❌ Error en guardar_caza_supabase: {e}")
        return False

def upsert_monitor_rule(user_id, caza_id, product_name, product_url, source, target_price, min_price_allowed, max_price_allowed):
    """Guarda o actualiza las reglas específicas para el Dashboard Business."""
    from auth.supabase_client import supabase
    try:
        data = {
            "user_id": user_id,
            "caza_id": caza_id,
            "product_name": product_name,
            "product_url": product_url,
            "source": source,
            "target_price": target_price,
            "min_price_allowed": min_price_allowed,
            "max_price_allowed": max_price_allowed
        }
        # Intentamos actualizar si ya existe para ese caza_id, sino insertamos
        res = supabase.table("monitor_rules").upsert(data, on_conflict="caza_id").execute()
        return True if res.data else False
    except Exception as e:
        print(f"❌ Error en upsert_monitor_rule: {e}")
        return False