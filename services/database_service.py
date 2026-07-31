"""
services/database_service.py — Guardar cazas, reportes y utilidades de DB.
safe_query() ELIMINADO: estaba roto (usaba nombres de tabla ficticios).
Todas las consultas ahora usan supabase.table() directamente.
"""

import os
from datetime import datetime, timezone, timedelta

from auth.supabase_client import supabase as supabase_admin
from utils.logic import (
    obtener_dolar_tarjeta, _safe_float, _parse_dt_utc, _effective_minutes,
    parse_price_to_int, get_effective_plan_rules, contar_cazas_activas,
    _extract_product_id, _domain_from_url, normalize_plan_family,
)
from scraper.scraper_pro import hunt_offers
from utils.logger import get_logger

logger = get_logger("db_service")

supabase = supabase_admin

DEFAULT_SOURCE = "mercadolibre"


def guardar_caza_supabase(
    user_id: str, producto: str, url: str, precio_max, frecuencia: str,
    tipo_alerta: str, plan: str, source: str | None = None, moneda: str = "ARS",
    dias_rep: str | None = None, hora_rep: int | None = None,
):
    try:
        if not user_id:
            return False

        rules = get_effective_plan_rules(plan)
        max_cazas = int(rules["max_cazas_activas"])
        source_final = (source or "generic").strip().lower()

        activas = contar_cazas_activas(user_id)
        if activas >= max_cazas:
            return "limite"

        precio_int = parse_price_to_int(precio_max)

        payload = {
            "user_id": user_id,
            "producto": (producto or "").strip(),
            "link": (url or "").strip(),
            "precio_max": precio_int,
            "frecuencia": (frecuencia or "").strip(),
            "tipo_alerta": (tipo_alerta or "piso").strip().lower(),
            "plan": rules.get("plan_key", plan),
            "estado": "activa",
            "source": source_final,
            "last_check": None,
            "currency": moneda.strip().upper(),
            "dias_rep": dias_rep,
            "hora_rep": hora_rep,
        }

        res = supabase.table("cazas").insert(payload).execute()
        if res.data:
            logger.info("✅ [guardar_caza_supabase] Inserción exitosa.")
            return True
        else:
            logger.warning(f"⚠️ [guardar_caza_supabase] No se devolvieron datos: {res}")
            return False

    except Exception as e:
        logger.error(f"❌ [guardar_caza_supabase] error: {e}")
        return False


def run_manual_hunt(b, headless=True):
    url = b.get("link") or b.get("url") or ""
    kw = b.get("producto") or b.get("keyword") or ""

    precio_base = _safe_float(b.get("precio_max"), 0)
    moneda = b.get("currency", "ARS").upper()

    precio_final_ars = precio_base
    if moneda == "USD":
        valor_dolar = obtener_dolar_tarjeta()
        precio_final_ars = precio_base * valor_dolar

    plan_str = str(b.get("plan", "starter")).lower()
    es_pro_real = (plan_str == "pro")

    return hunt_offers(url, kw, precio_final_ars, es_pro=es_pro_real, headless=headless)


# ==========================================================
# REPORTES
# ==========================================================

def armar_texto_reporte(user_id, cazas, familia_plan, nombre_usuario=""):
    total = len(cazas)
    ok = 0

    for c in cazas:
        cid = str(c["id"])
        if not c.get("last_check"):
            continue
        ok += 1

    saludo = f"wolf ¡Buen día, {nombre_usuario or 'Cazador'}! Reporte de Howlify listo.\n\n"
    cuerpo = (
        f"🔍 *Estado de tu Jauría:*\n"
        f"wolf {total} cacerías activas.\n"
        f"✅ El Lobo vigiló tus objetivos.\n"
        f"✨ Todo bajo control por ahora."
    )

    return saludo + cuerpo + "\n\n🔗 [Ver mi Panel](https://howlify.onrender.com)"


def ejecutar_reporte_diario_total(force=False):
    import pytz
    from services.notification_service import enviar_whatsapp, enviar_telegram

    tz = pytz.timezone("America/Argentina/Buenos_Aires")
    now = datetime.now(tz)
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    dia_actual = dias_semana[now.weekday()]
    hora_minuto = now.strftime("%H:%M")

    try:
        logger.info(f"🕒 [{now.strftime('%H:%M:%S')}] Chequeando reportes para {dia_actual} {hora_minuto} (Force={force})...")

        query = (supabase.table("profiles")
            .select("user_id, username, plan, telegram_id, whatsapp_number, report_days, report_time")
            .eq("report_enabled", True))

        if not force:
            query = query.ilike("report_time", f"{hora_minuto}%").contains("report_days", [dia_actual])

        res_usuarios = query.execute()
        usuarios = res_usuarios.data or []

        for u in usuarios:
            uid = u["user_id"]
            username = u.get("username", "Cazador")

            res_cazas = supabase.table("cazas").select("*").eq("user_id", uid).eq("estado", "activa").execute()
            cazas = res_cazas.data or []

            if not cazas:
                logger.info(f"ℹ️ {username} no tiene cacerías activas para reportar.")
                continue

            mensaje = armar_texto_reporte(uid, cazas, u.get("plan", "starter"), username)

            if u.get("telegram_id"):
                enviar_telegram(u["telegram_id"], mensaje)
                logger.info(f"✅ Reporte Telegram enviado a {username}")

            if u.get("whatsapp_number"):
                enviar_whatsapp(u["whatsapp_number"], mensaje)
                logger.info(f"✅ Reporte WhatsApp enviado a {username}")

    except Exception as e:
        logger.error(f"❌ Error crítico en reporte diario: {e}")


def ejecutar_reporte_semanal(force=False):
    import pytz
    from services.notification_service import enviar_whatsapp, enviar_telegram

    tz = pytz.timezone("America/Argentina/Buenos_Aires")
    now = datetime.now(tz)
    if not force and now.weekday() != 6:
        logger.info("⏭️ No es domingo, saltando reporte semanal")
        return

    try:
        logger.info(f"📅 Reporte semanal {now.strftime('%d/%m/%Y')}...")
        res = supabase.table("profiles") \
            .select("user_id, username, telegram_id, whatsapp_number") \
            .eq("report_enabled", True).execute()
        for u in (res.data or []):
            uid = u["user_id"]
            username = u.get("username", "Cazador")
            res_cazas = supabase.table("cazas").select("*").eq("user_id", uid).execute()
            cazas = res_cazas.data or []
            if not cazas:
                continue
            total = len(cazas)
            activas = sum(1 for c in cazas if c.get("estado") in ("active", None))
            con_precio = sum(1 for c in cazas if c.get("last_price"))
            en_alerta = sum(1 for c in cazas if c.get("last_price") and c.get("precio_max") and c["last_price"] <= c["precio_max"])
            ahorro = sum(c["precio_max"] - c["last_price"] for c in cazas if c.get("last_price") and c.get("precio_max") and c["last_price"] < c["precio_max"])

            mensaje = (
                f"🐺 *Howlify — Resumen Semanal*\n"
                f"Hola {username}, esto pasó esta semana:\n\n"
                f"📦 *Cacerías activas:* {activas} / {total}\n"
                f"💰 *Con precio detectado:* {con_precio}\n"
                f"🚨 *En alerta:* {en_alerta}\n"
                f"💵 *Ahorro potencial:* ${ahorro:,.0f}\n\n"
                f"🧠 *Tip:* Revisá tus cacerías en howlify.app/dashboard\n"
                f"🐺 ¡Seguí olfateando!"
            )

            if u.get("telegram_id"):
                enviar_telegram(u["telegram_id"], mensaje)
            if u.get("whatsapp_number"):
                enviar_whatsapp(u["whatsapp_number"], mensaje)
            logger.info(f"✅ Reporte semanal enviado a {username}")

    except Exception as e:
        logger.error(f"❌ Error en reporte semanal: {e}")


def notificar_presa(caza, precio_anterior, precio_nuevo, telegram_id):
    from services.notification_service import enviar_telegram
    try:
        porcentaje = int((1 - precio_nuevo / precio_anterior) * 100)
    except Exception:
        porcentaje = 0

    mensaje = (
        f"🚨 <b>¡PRESA DETECTADA!</b> 🐺\n"
        f"───────────────────\n"
        f"📌 <b>{caza.get('keyword', 'Producto')}</b>\n"
        f"💰 Precio: <s>${precio_anterior:,.0f}</s> → <b>${precio_nuevo:,.0f}</b>\n"
        f"📉 ¡Bajó un <b>{porcentaje}%</b>!\n\n"
        f"🔗 <a href='{caza.get('url', '#')}'>IR A LA OFERTA</a>"
    )

    try:
        enviar_telegram(telegram_id, mensaje)
    except Exception as e:
        logger.error(f"❌ Error al notificar presa: {e}")


def subir_evidencia_storage(file_path, file_name):
    try:
        with open(file_path, "rb") as f:
            supabase.storage.from_("evidencia-lobos").upload(
                path=file_name, file=f, file_options={"content-type": "image/jpeg"}
            )
            return supabase.storage.from_("evidencia-lobos").get_public_url(file_name)
    except Exception:
        return None
