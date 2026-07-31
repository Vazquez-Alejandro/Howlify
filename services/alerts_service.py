"""
services/alerts_service.py — Alertas, dedup y contacto de usuario.
Funciones centralizadas para el sistema de notificaciones.
"""

import os
import time
from datetime import datetime, timezone, timedelta

from auth.supabase_client import supabase
from services.notification_service import enviar_whatsapp as send_whatsapp, enviar_email as send_email
from utils.logic import (
    _parse_dt_utc, _safe_float, normalize_plan_family,
    plan_allows_whatsapp, execute_with_retry,
)
from utils.logger import get_logger

logger = get_logger("alerts")

ALERT_COOLDOWN_MINUTES = int(os.getenv("ALERT_COOLDOWN_MINUTES", "30") or 30)


def obtener_ultima_alerta(caza_id):
    if not supabase:
        return None
    try:
        res = execute_with_retry(
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
    if not supabase:
        return
    try:
        execute_with_retry(
            supabase.table("alertas_enviadas").insert({
                "caza_id": caza_id,
                "user_id": user_id,
                "oferta_url": oferta.get("url"),
                "oferta_titulo": oferta.get("title"),
                "oferta_precio": oferta.get("price"),
                "canal": "whatsapp" if oferta.get("_channel") == "whatsapp" else "email",
            })
        )
    except Exception as e:
        logger.error("⚠ error guardando alerta:", e)


def too_soon(prev_alert, minutes=None):
    if minutes is None:
        minutes = ALERT_COOLDOWN_MINUTES
    if not prev_alert:
        return False
    dt = _parse_dt_utc(prev_alert.get("created_at"))
    if not dt:
        return False
    return (datetime.now(timezone.utc) - dt) < timedelta(minutes=minutes)


def obtener_contacto_usuario(user_id):
    if not supabase:
        return {}
    try:
        res = execute_with_retry(
            supabase.table("profiles")
            .select("whatsapp_number, email, plan, telegram_id")
            .eq("user_id", user_id)
            .limit(1)
        )
        rows = res.data or []
        return rows[0] if rows else {}
    except Exception as e:
        logger.error("⚠ error obteniendo contacto usuario:", e)
        return {}


def es_descuento_fuerte(precio, precio_referencia, umbral=30):
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
    if precio <= precio_max:
        pass
    else:
        precio_referencia = oferta.get("original_price") or precio
        if not es_descuento_fuerte(precio, float(precio_referencia)):
            return False
    logger.warning(
        f"🚨 OFERTA ENCONTRADA | caza {caza_id} | "
        f"${precio} <= max ${precio_max} | "
        f"{oferta.get('title', '')[:80]}"
    )
    return True


def _format_alerta_msg(oferta, caza_nombre=""):
    titulo = oferta.get("title", caza_nombre or "Producto")
    precio = oferta.get("price", "?")
    url = oferta.get("url", "")
    return (
        f"🐺 Howlify - Oferta Detectada\n"
        f"📦 {titulo}\n"
        f"💰 ${precio}\n"
        f"🔗 {url}\n"
        f"🦴 Enviado por Howlify"
    )


def enviar_alerta_por_canal(user_contact, oferta, caza_nombre=""):
    plan = user_contact.get("plan") or "starter"
    email = (user_contact.get("email") or "").strip()
    numero = (user_contact.get("whatsapp_number") or "").strip()
    ok_whatsapp = False
    ok_email = False
    mensaje = _format_alerta_msg(oferta, caza_nombre)

    if plan_allows_whatsapp(plan):
        if numero:
            oferta["_channel"] = "whatsapp"
            ok_whatsapp = send_whatsapp(numero, mensaje)
        if email:
            oferta["_channel"] = "email"
            asunto = f"🐺 Oferta encontrada: {caza_nombre or 'Howlify'}"
            ok_email = send_email(email, asunto, mensaje)
        return ok_whatsapp or ok_email

    oferta["_channel"] = "email"
    asunto = f"🐺 Oferta encontrada: {caza_nombre or 'Howlify'}"
    return send_email(email, asunto, mensaje)
