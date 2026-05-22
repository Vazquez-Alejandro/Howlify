import re
import os
import random
import time
import requests
from datetime import datetime, timezone
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from auth.supabase_client import supabase

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
    "starter": {"max_cazas_activas": 5, "freq_options": ["12h", "24h"], "plan_key": "starter", "reseller_markup": 0},
    "pro": {"max_cazas_activas": 15, "freq_options": ["1h", "6h", "12h", "24h"], "plan_key": "pro", "reseller_markup": 0},
    "business": {"max_cazas_activas": 100, "freq_options": ["15min", "1h", "6h"], "plan_key": "business", "reseller_markup": 0.40},
    "business_monitor": {"max_cazas_activas": 100, "freq_options": ["15min", "1h", "6h"], "plan_key": "business_monitor", "reseller_markup": 0},
    "business_reseller": {"max_cazas_activas": 100, "freq_options": ["15min", "1h", "6h"], "plan_key": "business_reseller", "reseller_markup": 0.40},
}

def normalize_plan_family(plan: str) -> str:
    raw = (plan or "starter").strip().lower()
    if raw in ["business_reseller", "business_monitor", "business"]: return raw
    if raw in ["pro", "beta", "alfa"]: return "pro"
    return "starter"

def get_effective_plan_rules(plan_name):
    family = normalize_plan_family(plan_name)
    return PLAN_RULES.get(family, PLAN_RULES["starter"])

def _effective_minutes(plan, freq_str):
    """Traduce la frecuencia a minutos reales."""
    if freq_str == "15min": return 15
    if freq_str == "1h": return 60
    if freq_str == "6h": return 360
    if freq_str == "12h": return 720
    return 1440

def contar_cazas_activas(user_id):
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

# ==========================================================
# 6. VALIDACIONES DE INTEGRIDAD
# ==========================================================

def id_valido(caza_id: int) -> bool:
    """Chequea si el caza_id existe en la tabla cazas."""
    try:
        res = supabase.table("cazas").select("id").eq("id", caza_id).execute()
        return len(res.data) > 0
    except:
        return False

def insertar_price_history(caza_id: int, payload: dict):
    """Inserta en price_history solo si el caza_id existe."""
    if id_valido(caza_id):
        supabase.table("price_history").insert(payload).execute()
    else:
        print(f"⚠️ caza_id {caza_id} no existe en cazas, se saltea")

def insertar_infraccion(caza_id: int, payload: dict):
    """Inserta en infracciones_log solo si el caza_id existe."""
    if id_valido(caza_id):
        supabase.table("infracciones_log").insert(payload).execute()
    else:
        print(f"⚠️ caza_id {caza_id} no existe en cazas, se saltea")

def insertar_caza(payload: dict):
    """Inserta en cazas solo si el producto tiene nombre."""
    if payload.get("producto") and payload["producto"].strip():
        supabase.table("cazas").insert(payload).execute()
    else:
        print("⚠️ Producto sin nombre, no se inserta")

# ==========================================================
# 8. PRICE ANOMALY DETECTION
# ==========================================================

def detectar_price_error(caza_id: int, precio_actual: float, umbral: float = 0.6) -> tuple[bool, float | None]:
    """
    Detecta si un precio es anómalamente bajo comparado al histórico.
    Retorna (es_error, precio_promedio_historico).
    Se considera error si precio_actual < promedio_historico * (1 - umbral).
    """
    try:
        res = supabase.table("price_history") \
            .select("price") \
            .eq("caza_id", caza_id) \
            .order("checked_at", desc=True) \
            .limit(10) \
            .execute()
        prices = [float(p["price"]) for p in (res.data or []) if float(p["price"]) > 0]
        if len(prices) < 3:
            return False, None
        avg = sum(prices) / len(prices)
        if precio_actual < avg * (1 - umbral):
            return True, round(avg, 2)
        return False, avg
    except Exception as e:
        print(f"⚠ error detectando price error: {e}")
        return False, None

# ==========================================================
# 7. EXPORTACIÓN
# ==========================================================

def _get_sheets_client():
    """Obtiene cliente de Google Sheets autenticado.
    Prioriza Service Account. Si no, usa OAuth con token guardado.
    """
    import json
    from google.oauth2.credentials import Credentials
    creds_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS", "credenciales.json")
    token_path = os.getenv("GOOGLE_SHEETS_TOKEN", "token.json")
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    # Intentar Service Account primero
    try:
        from google.oauth2.service_account import Credentials as SACredentials
        if os.path.exists(creds_path):
            try:
                with open(creds_path) as f:
                    data = json.load(f)
                if "type" in data and data["type"] == "service_account":
                    creds = SACredentials.from_service_account_file(creds_path, scopes=scope)
                    return gspread.authorize(creds)
            except Exception:
                pass
    except ImportError:
        pass

    # Fallback: OAuth con token guardado
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, scope)
        if creds and creds.valid:
            return gspread.authorize(creds)

    raise RuntimeError(
        "No hay credenciales válidas. "
        "Corré 'python scripts/auth_sheets.py' para autenticarte con Google."
    )


def exportar_a_sheets(df, nombre_hoja="Reporte Monitor Howlify"):
    """
    Exporta un DataFrame a Google Sheets.
    Si GOOGLE_SHEETS_ID está configurado, escribe en ese sheet existente.
    Si no, crea uno nuevo.
    """
    try:
        client = _get_sheets_client()
        sheet_id = os.getenv("GOOGLE_SHEETS_ID")

        if sheet_id:
            sheet = client.open_by_key(sheet_id)
            try:
                worksheet = sheet.worksheet(nombre_hoja)
            except gspread.WorksheetNotFound:
                worksheet = sheet.add_worksheet(title=nombre_hoja, rows=len(df) + 1, cols=len(df.columns))
        else:
            sheet = client.create(nombre_hoja)
            worksheet = sheet.get_worksheet(0)

        worksheet.clear()
        worksheet.update([df.columns.values.tolist()] + df.values.tolist())
        return True, sheet.url if not sheet_id else sheet_id
    except Exception as e:
        print(f"❌ Error exportando a Google Sheets: {e}")
        return False, str(e)
