import os
import json
from dotenv import load_dotenv
load_dotenv()
import time
import re
#import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import urlparse

from supabase import create_client
from apscheduler.schedulers.background import BackgroundScheduler

from scraper.scraper_pro import hunt_offers
from services.notification_service import enviar_whatsapp, enviar_telegram, enviar_email
from services.business_service import guardar_oportunidad_business
from services.duffel_service import buscar_ofertas_vuelos
from services.database_service import vigilar_ofertas
from utils.logic import normalize_plan_family
from utils.logger import get_logger
logger = get_logger("engine")



SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# ==========================================================
# PLANES / COMPATIBILIDAD
# ==========================================================

def plan_allows_whatsapp(plan: str) -> bool:
    return normalize_plan_family(plan) in {"pro", "business_reseller", "business_monitor"}


def plan_min_interval(plan: str) -> int:
    return 60 if normalize_plan_family(plan) == "starter" else 15


def plan_is_business(plan: str) -> bool:
    return normalize_plan_family(plan) in {"business_reseller", "business_monitor"}


# ==========================================================
# SCHEDULER GLOBAL
# ==========================================================

_scheduler = None

ALERT_COOLDOWN_MINUTES = int(os.getenv("ALERT_COOLDOWN_MINUTES", "30") or 30)

SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587") or 587)
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER).strip()
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "1") == "1"
SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "0") == "1"


# ==========================================================
# HELPERS GENERALES
# ==========================================================

def _execute_with_retry(builder, attempts=3, delay=1.2):
    last_error = None

    for i in range(attempts):
        try:
            return builder.execute()
        except Exception as e:
            last_error = e
            logger.warning(f"⚠ intento {i+1}/{attempts} falló: {e}")
            if i < attempts - 1:
                time.sleep(delay)

    raise last_error


def _safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default


def _domain_from_url(url: str) -> str:
    try:
        host = urlparse(str(url)).netloc.lower().strip()
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return "unknown"

def _run_scraper(link, producto, precio_max):
    domain = _domain_from_url(link)

    if "despegar" in domain:
        logger.info(f"✈️ [Howlify-API] Consultando Duffel para: {producto}")
        
        # 1. Llamada a la API
        resultado_raw = buscar_ofertas_vuelos("BUE", "MIA", "2026-05-20")
        
        # 2. Protección: Si Duffel no devuelve nada, salimos antes de que explote
        if not resultado_raw:
            logger.warning("🚨 Duffel no encontró vuelos. Revisá el Token o la fecha.")
            return []

        # 3. Mapeo seguro (Duffel usa estructuras anidadas)
        ofertas_limpias = []
        for r in resultado_raw:
            try:
                # Extraemos el precio y el destino con cuidado
                ofertas_limpias.append({
                    "title": f"Vuelo a {producto.upper()}", 
                    "price": float(r.total_amount), # Aseguramos que sea número
                    "url": link, # Usamos el link original para que puedas clickear
                    "source": "duffel"
                })
            except Exception as e:
                logger.error(f"⚠️ Error procesando una oferta individual: {e}")
                continue
        
        logger.info(f"✅ Se procesaron {len(ofertas_limpias)} ofertas de Duffel.")
        return ofertas_limpias

    if "mercadolibre" in domain:
        return hunt_offers(link, producto, precio_max) or []

    return []
def _freq_to_minutes(freq: str) -> int:
    if not freq:
        return 60

    s = str(freq).lower()

    if "15" in s:
        return 15
    if "30" in s:
        return 30
    if "45" in s:
        return 45
    if "1" in s and "h" in s:
        return 60
    if "2" in s and "h" in s:
        return 120
    if "3" in s and "h" in s:
        return 180
    if "4" in s and "h" in s:
        return 240
    if "12" in s and "h" in s:
        return 720

    return 60


def _parse_dt_utc(value):
    if not value:
        return None

    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    try:
        s = str(value)

        if s.endswith("Z"):
            s = s[:-1] + "+00:00"

        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _effective_minutes(plan: str, freq: str) -> int:
    requested = _freq_to_minutes(freq)
    minimum = plan_min_interval(plan)
    return max(requested, minimum)


# ==========================================================
# ALERTAS ENVIADAS / DEDUP
# ==========================================================

def obtener_ultima_alerta(caza_id):
    try:
        res = _execute_with_retry(
            supabase.table("alertas_enviadas")
            .select("oferta_url, oferta_titulo, oferta_precio, created_at")
            .eq("caza_id", caza_id)
            .order("created_at", desc=True)
            .limit(1)
        )
        rows = res.data or []
        return rows[0] if rows else None

    except Exception as e:
        logger.error("⚠ error consultando última alerta:", e)
        return None


def guardar_alerta(caza_id, user_id, oferta):
    try:
        _execute_with_retry(
            supabase.table("alertas_enviadas").insert(
                {
                    "caza_id": caza_id,
                    "user_id": user_id,
                    "oferta_url": oferta.get("url"),
                    "oferta_titulo": oferta.get("title"),
                    "oferta_precio": oferta.get("price"),
                    "canal": "whatsapp" if oferta.get("_channel") == "whatsapp" else "email",
                }
            )
        )
    except Exception as e:
        logger.error("⚠ error guardando alerta:", e)

def too_soon(prev_alert, minutes=30):
    if not prev_alert:
        return False

    dt = _parse_dt_utc(prev_alert.get("created_at"))
    if not dt:
        return False

    return (datetime.now(timezone.utc) - dt) < timedelta(minutes=minutes)


# ==========================================================
# PERFIL / CONTACTO USUARIO
# ==========================================================

def obtener_contacto_usuario(user_id):
    try:
        res = _execute_with_retry(
            supabase.table("profiles")
            .select("whatsapp_number, email, plan, telegram_id")
            .eq("user_id", user_id)
            .limit(1)
        )
        rows = res.data or []
        if not rows:
            return {}
        return rows[0]

    except Exception as e:
        logger.error("⚠ error obteniendo contacto usuario:", e)
        return {}


# ==========================================================
# HISTORIAL DE PRECIOS
# ==========================================================

def _extract_product_id(url):
    if not url:
        return None

    try:
        s = str(url).strip()
    except Exception:
        return None

    m = re.search(r"\b([A-Z]{3}-\d{6,})\b", s, flags=re.IGNORECASE)
    if m:
        return m.group(1).upper()

    try:
        path = urlparse(s).path.strip("/")
        if path:
            last = path.split("/")[-1]
            last = re.sub(r"[^\w\-]", "", last)
            if len(last) >= 6:
                return last
    except Exception:
        return None

    return None

def obtener_precio_minimo(caza_id):
    try:
        res = _execute_with_retry(
            supabase.table("price_history")
            .select("price")
            .eq("caza_id", caza_id)
            .order("price")
            .limit(1)
        )

        rows = res.data or []

        if not rows:
            return None

        return _safe_float(rows[0]["price"])

    except Exception:
        return None

def calcular_diferencia_vs_minimo(caza_id, precio_actual):
    precio_minimo = obtener_precio_minimo(caza_id)

    if precio_minimo is None or precio_minimo <= 0:
        return None

    try:
        diff_pct = ((precio_actual - precio_minimo) / precio_minimo) * 100
        return round(diff_pct, 2)
    except Exception:
        return None

def guardar_historial(caza_id, resultados, user_id): # <-- Agregamos user_id aquí
    if not resultados:
        return

    rows = []

    for r in resultados:
        price = _safe_float(r.get("price"), 0)
        if price <= 0:
            continue

        url = r.get("url")
        source = r.get("source")
        product_id = _extract_product_id(url)

        rows.append(
            {
                "caza_id": caza_id,
                "user_id": user_id, # <--- ¡ESTA ES LA LÍNEA MÁGICA!
                "title": r.get("title"),
                "price": price,
                "url": url,
                "source": source,
                "product_id": product_id,
                "checked_at": datetime.now().isoformat() # Aseguramos el timestamp
            }
        )

    if not rows:
        return

    try:
        # Usamos execute() al final si _execute_with_retry no lo hace internamente
        _execute_with_retry(
            supabase.table("price_history").insert(rows)
        )
    except Exception as e:
        logger.error("⚠ error guardando historial:", e)

# ==========================================================
# ALERTA MINIMA
# ==========================================================

def es_descuento_fuerte(precio, precio_referencia, umbral=30):
    """
    Detecta si el precio tiene un descuento fuerte respecto a un precio de referencia.
    """

    try:
        drop_pct = (precio_referencia - precio) / precio_referencia * 100
        return drop_pct >= umbral
    except Exception:
        return False
    
def _obtener_precio_referencia(caza_id):
    """Obtiene el precio promedio histórico como referencia para detectar descuentos fuertes."""
    try:
        res = supabase.table("price_history") \
            .select("price") \
            .eq("caza_id", caza_id) \
            .order("checked_at", desc=True) \
            .limit(5) \
            .execute()
        prices = [float(p["price"]) for p in (res.data or []) if float(p["price"]) > 0]
        if prices:
            return sum(prices) / len(prices)
    except Exception as e:
        logger.error(f"⚠ error obteniendo precio referencia para caza {caza_id}: {e}")
    return None


def disparar_alerta_minima(caza_id, oferta, precio_max):
    try:
        precio = float(oferta.get("price"))
    except Exception:
        return False

    precio_max = float(precio_max)

    if precio <= precio_max:
        pass
    else:
        precio_referencia = oferta.get("original_price") or _obtener_precio_referencia(caza_id) or precio

        if not es_descuento_fuerte(precio, float(precio_referencia)):
            return False

    logger.info(
        f"🚨 OFERTA ENCONTRADA | caza {caza_id} | "
        f"${precio} <= max ${precio_max} | "
        f"{oferta.get('title','')[:80]}"
    )

    return True

# ==========================================================
# EVALUACIÓN DE REGLAS DE ALERTA (alarma personalizada)
# ==========================================================

VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_CLAIM = os.getenv("VAPID_CLAIM_EMAIL", "mailto:howlify@example.com")

def evaluar_reglas_alerta(caza_id, user_id):
    """Evalúa las alert_config de un monitor_rule y envía notificaciones si corresponde."""
    try:
        rules = supabase.table("monitor_rules").select("alert_config").eq("caza_id", caza_id).eq("user_id", user_id).limit(1).execute()
        if not rules.data:
            return
        alert_config = rules.data[0].get("alert_config")
        if not alert_config:
            return
        if isinstance(alert_config, str):
            alert_config = json.loads(alert_config)

        history = supabase.table("price_history").select("price, checked_at").eq("caza_id", caza_id).order("checked_at", desc=True).limit(10).execute()
        prices = [float(h["price"]) for h in (history.data or []) if h.get("price")]
        if not prices:
            return
        current = prices[0]

        for r in alert_config:
            if not r.get("enabled", True):
                continue
            rtype = r.get("type", "")
            threshold = float(r.get("threshold", 0))
            match = False
            detail = ""

            if rtype == "below_price":
                match = current <= threshold
                detail = f"Precio ${current:.0f} ≤ ${threshold:.0f}"
            elif rtype == "above_price":
                match = current >= threshold
                detail = f"Precio ${current:.0f} ≥ ${threshold:.0f}"
            elif rtype == "pct_drop" and len(prices) >= 2:
                pct = ((prices[1] - current) / prices[1]) * 100
                match = pct >= threshold
                detail = f"Bajó {pct:.1f}% (umbral: {threshold:.0f}%)"
            elif rtype == "consecutive_drop" and len(prices) >= int(threshold):
                consec = 0
                for i in range(1, len(prices)):
                    if prices[i] < prices[i-1]:
                        consec += 1
                    else:
                        consec = 0
                    if consec >= int(threshold):
                        match = True
                        detail = f"{consec} bajas consecutivas"
                        break
            elif rtype == "velocity_drop":
                h24 = supabase.table("price_history").select("price").eq("caza_id", caza_id).gte("checked_at", (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()).order("checked_at").limit(2).execute()
                hp = [float(h["price"]) for h in (h24.data or []) if h.get("price")]
                if len(hp) >= 2 and hp[0] > 0:
                    pct = ((hp[0] - current) / hp[0]) * 100
                    match = pct >= threshold
                    detail = f"Caída de {pct:.1f}% en 24hs"
            elif rtype == "below_hist_min":
                all_p = supabase.table("price_history").select("price").eq("caza_id", caza_id).order("price").limit(1).execute()
                if all_p.data:
                    hist_min = float(all_p.data[0]["price"])
                    if hist_min > 0 and current <= hist_min * 1.01:
                        match = True
                        detail = f"Nuevo mínimo histórico: ${current:.0f}"
            elif rtype == "restock":
                match = current > 0 and prices[-1] <= 0 if len(prices) >= 2 else False
                detail = "Producto nuevamente disponible"

            if match:
                channel = r.get("channel", "push")
                body = f"“{detail}” — Actual: ${current:.0f}"
                title = f"⚡ Alerta {rtype.replace('_', ' ').title()}"
                if channel in ("push", "all"):
                    from pywebpush import webpush, WebPushException
                    subs = supabase.table("push_subscriptions").select("subscription").eq("user_id", user_id).execute()
                    for row in subs.data or []:
                        try:
                            sub = json.loads(row["subscription"]) if isinstance(row["subscription"], str) else row["subscription"]
                            webpush(subscription_info=sub, data=json.dumps({"title": title, "body": body, "url": f"/monitor?caza={caza_id}"}), vapid_private_key=VAPID_PRIVATE_KEY, vapid_claims={"sub": VAPID_CLAIM})
                        except:
                            supabase.table("push_subscriptions").delete().eq("user_id", user_id).execute()
                if channel in ("whatsapp", "all"):
                    contacto = obtener_contacto_usuario(user_id)
                    numero = (contacto.get("whatsapp_number") or "").strip()
                    if numero:
                        enviar_whatsapp(numero, {"title": title, "price": current, "url": ""}, caza_nombre=title)
                if channel in ("telegram", "all"):
                    contacto = obtener_contacto_usuario(user_id)
                    tid = contacto.get("telegram_id") or ""
                    if tid:
                        enviar_telegram(tid, f"{title}\n{body}")
                if channel in ("email", "all"):
                    contacto = obtener_contacto_usuario(user_id)
                    email = (contacto.get("email") or "").strip()
                    if email:
                        enviar_email(email, title, body)
    except Exception as e:
        logger.error(f"⚠ error evaluando reglas alerta caza {caza_id}: {e}")

# ==========================================================
# ENVIO POR CANAL (AHORA CENTRALIZADO)
# ==========================================================

def enviar_email(destino, oferta, caza_nombre=""):
    """
    Función puente que delega al notification_service.
    """
    from services.notification_service import enviar_email as enviar_nuevo
    
    asunto = f"🐺 Oferta encontrada: {caza_nombre or 'Howlify'}"
    cuerpo = f"Producto: {oferta.get('title')}\nPrecio: ${oferta.get('price')}"
    
    # Llamamos al nuevo servicio unificado
    return enviar_nuevo(destino, asunto, cuerpo)

def enviar_alerta_por_canal(user_contact, oferta, caza_nombre=""):
    plan = user_contact.get("plan") or "starter"
    email = (user_contact.get("email") or "").strip()
    numero = (user_contact.get("whatsapp_number") or "").strip()

    ok_whatsapp = False
    ok_email = False

    if plan_allows_whatsapp(plan):
        if numero:
            oferta["_channel"] = "whatsapp"
            ok_whatsapp = enviar_whatsapp(numero, oferta, caza_nombre=caza_nombre)

        if email:
            oferta["_channel"] = "email"
            ok_email = enviar_email(email, oferta, caza_nombre=caza_nombre)

        return ok_whatsapp or ok_email

    oferta["_channel"] = "email"
    return enviar_email(email, oferta, caza_nombre=caza_nombre)



# ==========================================================
# SCHEDULER
# ==========================================================

def start_engine(run_once=False):
    global _scheduler

    logger.info("🔥 start_engine() fue llamado")

    if run_once:
        logger.info("⚡ Ejecutando vigilar_ofertas() manualmente")
        vigilar_ofertas()

    if _scheduler is not None:
        return

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        vigilar_ofertas,
        "interval",
        minutes=1,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=30,
    )
    _scheduler.start()

    logger.info("🚀 Motor Howlify iniciado (tick 1 min)")


if __name__ == "__main__":
    start_engine(run_once=True)