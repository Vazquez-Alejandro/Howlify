import os
from dotenv import load_dotenv
load_dotenv()
import time
import re
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import urlparse

from apscheduler.schedulers.background import BackgroundScheduler

from scraper.scraper_pro import hunt_offers
from services.whatsapp_service import enviar_whatsapp
from services.business_service import guardar_oportunidad_business

from supabase import create_client
import os

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# ==========================================================
# PLANES / COMPATIBILIDAD
# ==========================================================

PLAN_ALIAS = {
    "omega": "starter",
    "trial": "starter",
    "starter": "starter",
    "beta": "pro",
    "alfa": "pro",
    "revendedor": "pro",
    "empresa": "pro",
    "pro": "pro",
    "business_reseller": "business_reseller",
    "business_monitor": "business_monitor",
}


def normalize_plan_family(plan: str) -> str:
    raw = (plan or "starter").strip().lower()
    return PLAN_ALIAS.get(raw, "starter")


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
            print(f"⚠ intento {i+1}/{attempts} falló:", e)
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

    if "mercadolibre" in domain or "despegar" in domain:
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
        print("⚠ error consultando última alerta:", e)
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
        print("⚠ error guardando alerta:", e)

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
            .select("whatsapp_number, email, plan")
            .eq("user_id", user_id)
            .limit(1)
        )
        rows = res.data or []
        if not rows:
            return {}
        return rows[0]

    except Exception as e:
        print("⚠ error obteniendo contacto usuario:", e)
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

def guardar_historial(caza_id, resultados):
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
                "title": r.get("title"),
                "price": price,
                "url": url,
                "source": source,
                "product_id": product_id,
            }
        )

    if not rows:
        return

    try:
        _execute_with_retry(
            supabase.table("price_history").insert(rows)
        )
    except Exception as e:
        print("⚠ error guardando historial:", e)


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
    
def disparar_alerta_minima(caza_id, oferta, precio_max):
    try:
        precio = float(oferta.get("price"))
    except Exception:
        return False

    precio_max = float(precio_max)

    # precio dentro del máximo definido por el usuario
    if precio <= precio_max:
        pass
    else:
        # chequeo de descuento fuerte (placeholder por ahora)
        precio_referencia = oferta.get("original_price") or precio

        if not es_descuento_fuerte(precio, float(precio_referencia)):
            return False

    print(
        f"🚨 OFERTA ENCONTRADA | caza {caza_id} | "
        f"${precio} <= max ${precio_max} | "
        f"{oferta.get('title','')[:80]}"
    )

    return True


# ==========================================================
# ENVIO POR CANAL
# ==========================================================

def enviar_email(destino, oferta, caza_nombre=""):
    destino = (destino or "").strip()
    if not destino:
        print("⚠ email vacío, no se puede enviar alerta")
        return False

    if not SMTP_HOST or not SMTP_FROM:
        print(f"⚠ SMTP no configurado. No se pudo enviar email a {destino}")
        return False

    subject = f"🐺 Oferta encontrada: {caza_nombre or 'Howlify'}"

    title = str(oferta.get("title") or "Oferta detectada").strip()
    try:
        price = int(float(oferta.get("price") or 0))
    except Exception:
        price = 0

    url = str(oferta.get("url") or "").strip()
    source = str(oferta.get("source") or "").strip()

    text_body = (
        f"Howlify detectó una oferta.\n\n"
        f"Caza: {caza_nombre or '-'}\n"
        f"Producto: {title}\n"
        f"Precio: ${price:,.0f}\n"
        f"Fuente: {source or '-'}\n"
        f"Link: {url}\n"
    ).replace(",", ".")

    html_body = f"""
    <html>
      <body>
        <h2>🐺 Howlify detectó una oferta</h2>
        <p><strong>Caza:</strong> {caza_nombre or '-'}</p>
        <p><strong>Producto:</strong> {title}</p>
        <p><strong>Precio:</strong> ${format(price, ',.0f').replace(',', '.')}</p>
        <p><strong>Fuente:</strong> {source or '-'}</p>
        <p><a href="{url}">Ver oferta</a></p>
      </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = destino
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        if SMTP_USE_SSL:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=20) as server:
                if SMTP_USER and SMTP_PASSWORD:
                    server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(SMTP_FROM, [destino], msg.as_string())
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
                server.ehlo()
                if SMTP_USE_TLS:
                    server.starttls()
                    server.ehlo()
                if SMTP_USER and SMTP_PASSWORD:
                    server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(SMTP_FROM, [destino], msg.as_string())

        print(f"📧 email enviado a {destino}")
        return True

    except Exception as e:
        print(f"⚠ falló envío email a {destino}: {e}")
        return False

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
# LOOP PRINCIPAL
# ==========================================================

def vigilar_ofertas():
    print("🐺 Vigilando ofertas...")

    now = datetime.now(timezone.utc)

    try:
        res = _execute_with_retry(
            supabase.table("cazas")
            .select("*")
        )
        cazas = res.data or []
        
    except Exception as e:
        print("⚠ error consultando cazas:", e)
        return

    print("📦 Total cazas activas:", len(cazas))

    force_run = os.getenv("FORCE_RUN", "0") == "1"

    for c in cazas:
        caza_id = c.get("id")
        user_id = c.get("user_id")
        producto = c.get("producto")
        link = c.get("link")
        precio_max = _safe_float(c.get("precio_max"))
        frecuencia = c.get("frecuencia")
        last_check = c.get("last_check")

        if not link:
            continue

        mins = _effective_minutes(c.get("plan"), frecuencia)
        last_dt = _parse_dt_utc(last_check)

        if (not force_run) and last_dt and (now - last_dt) < timedelta(minutes=mins):
            continue

        print(f"🔎 Caza #{caza_id} | {producto}")

        try:
            resultados = _run_scraper(link, producto, precio_max)
            print("📊 Resultados scraper:", len(resultados))

            precios = [_safe_float(r.get("price"), 0) for r in resultados]

            if precios:
                print("💰 rango de precios:", min(precios), "-", max(precios))

            resultados = [
                r for r in resultados
                if _safe_float(r.get("price"), 0) > 0
            ]

            if not resultados:
                continue

            mejor = sorted(
                resultados,
                key=lambda x: _safe_float(x.get("price"), 999999999)
            )[0]

            precio_actual = _safe_float(mejor.get("price"), 0)

            precio_minimo = obtener_precio_minimo(caza_id)
            diff_vs_minimo = calcular_diferencia_vs_minimo(caza_id, precio_actual)

            if precio_minimo:
                print("📉 diferencia vs mínimo histórico:", diff_vs_minimo, "%")

            if plan_is_business(c.get("plan")) and precio_minimo and precio_actual < precio_minimo:
                print("💥 NUEVO MINIMO HISTORICO:", precio_actual, "<", precio_minimo)

                product_id = _extract_product_id(mejor.get("url"))

                guardar_oportunidad_business(
                    caza_id,
                    product_id,
                    mejor.get("title"),
                    mejor.get("source") or _domain_from_url(mejor.get("url")),
                    precio_actual,
                    precio_minimo,
                    diff_vs_minimo
                )

            if disparar_alerta_minima(caza_id, mejor, precio_max):
                prev = obtener_ultima_alerta(caza_id)

                precio_actual = float(mejor.get("price"))
                titulo_actual = str(mejor.get("title") or "").strip()

                enviar = False

                if not prev:
                    enviar = True
                else:
                    try:
                        precio_anterior = float(prev.get("oferta_precio") or 0)
                    except Exception:
                        precio_anterior = 0

                    titulo_anterior = str(prev.get("oferta_titulo") or "").strip()

                    if titulo_actual == titulo_anterior and precio_actual == precio_anterior:
                        enviar = False
                    elif precio_actual < precio_anterior:
                        enviar = True
                    elif titulo_actual != titulo_anterior:
                        enviar = True

                if prev and too_soon(prev, ALERT_COOLDOWN_MINUTES):
                    print(f"⏳ cooldown activo en caza {caza_id}, no se envía alerta")
                    enviar = False

                if enviar:
                    contacto = obtener_contacto_usuario(user_id)

                    # 👇 AGREGÁS ESTO
                    ok = enviar_alerta_por_canal(contacto, mejor, caza_nombre=producto)

                    if ok:
                        guardar_alerta(caza_id, user_id, mejor)

            guardar_historial(caza_id, resultados)

        except Exception as e:
            print("⚠ error en caza:", e)

        finally:
            try:
                _execute_with_retry(
                    supabase.table("cazas")
                    .update(
                        {
                            "last_check": datetime.now(timezone.utc).isoformat()
                        }
                    )
                    .eq("id", caza_id)
                )
            except Exception as e:
                print("⚠ no pude actualizar last_check:", e)

    print("✅ ciclo terminado")


# ==========================================================
# SCHEDULER
# ==========================================================

def start_engine(run_once=False):
    global _scheduler

    print("🔥 start_engine() fue llamado")

    if run_once:
        print("⚡ Ejecutando vigilar_ofertas() manualmente")
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

    print("🚀 Motor Howlify iniciado (tick 1 min)")


if __name__ == "__main__":
    start_engine(run_once=True)