"""
engine/engine.py — Evaluación de reglas de alerta personalizadas.
Solo contiene evaluar_reglas_alerta() y _obtener_precio_referencia().
Toda la lógica de workers, alertas, historial y planes está en:
  - howlify/tasks.py (Celery worker)
  - services/alerts_service.py (alertas y dedup)
  - services/database_service.py (loop principal y reports)
  - utils/logic.py (utilidades compartidas)
"""

import os
import json
from datetime import datetime, timedelta, timezone

from auth.supabase_client import supabase
from services.notification_service import enviar_whatsapp, enviar_telegram, enviar_email
from utils.logic import _safe_float, normalize_plan_family
from utils.logger import get_logger

logger = get_logger("engine")

VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_CLAIM = os.getenv("VAPID_CLAIM_EMAIL", "mailto:howlify@example.com")


def _obtener_precio_referencia(caza_id):
    """Obtiene el precio más bajo histórico como referencia para detectar descuentos reales.
    Usa min() de los últimos 30 registros en vez de avg() de los últimos 5,
    para evitar trucos de vendedores que inflan precios y los 'bajan'."""
    try:
        res = supabase.table("price_history") \
            .select("price") \
            .eq("caza_id", caza_id) \
            .order("checked_at", desc=True) \
            .limit(30) \
            .execute()
        prices = [float(p["price"]) for p in (res.data or []) if float(p["price"]) > 0]
        if prices:
            return min(prices)
    except Exception as e:
        logger.error(f"⚠ error obteniendo precio referencia para caza {caza_id}: {e}")
    return None


def _ultimos_precios(caza_id, n=14):
    """Devuelve las últimas n precios (ordenados de más reciente a más viejo)."""
    try:
        res = supabase.table("price_history") \
            .select("price, stock") \
            .eq("caza_id", caza_id) \
            .order("checked_at", desc=True) \
            .limit(n) \
            .execute()
        return res.data or []
    except Exception as e:
        logger.error(f"⚠ error obteniendo últimos precios caza {caza_id}: {e}")
        return []


def _evaluar_restock(rows):
    """
    Evalúa restock con stock real si está disponible; fallback a precio (<=0).
    rows viene ordenado del más reciente al más viejo.
    """
    try:
        curr = rows[0] if rows else None
        if not curr:
            return False, ""
        stock_curr = curr.get("stock")
        price_curr = _safe_float(curr.get("price"), 0)
        if isinstance(stock_curr, (int, float)) and stock_curr > 0:
            for prev in rows[1:]:
                sp = prev.get("stock")
                if isinstance(sp, (int, float)):
                    if sp <= 0:
                        return True, "Producto nuevamente disponible"
                    break
        if len(rows) >= 2:
            prev_price = _safe_float(rows[1].get("price"), 0)
            if price_curr > 0 and prev_price <= 0:
                return True, "Producto nuevamente disponible"
        return False, ""
    except Exception:
        return False, ""


def detectar_inflado(caza_id):
    """
    Detecta un 'descuento falso': el vendedor infló el precio hace poco y después
    lo 'bajó' a un nivel que en realidad es su precio normal histórico.
    → True si hubo spike >15% reciente y el precio actual NO está por debajo del
    mínimo histórico (i.e., el 'descuento' no es real).
    """
    try:
        rows = _ultimos_precios(caza_id, n=14)
        prices = [float(r["price"]) for r in rows if r.get("price")]
        if len(prices) < 4:
            return None
        current = prices[0]
        if current <= 0:
            return None
        ref = _obtener_precio_referencia(caza_id)
        if not ref or ref <= 0:
            return None
        max_window = max(prices)
        spike = max_window > current * 1.15
        descuento_real = current <= ref * 0.95
        return bool(spike and not descuento_real)
    except Exception as e:
        logger.error(f"⚠ error detectar_inflado caza {caza_id}: {e}")
        return None


def detectar_restock(caza_id, results=None):
    """
    Detecta si un producto volvió a estar disponible: el registro anterior tenía
    stock 0 (o precio 0) y el actual tiene stock > 0.
    Retorna True/False o None si no hay datos suficientes.
    """
    try:
        rows = _ultimos_precios(caza_id, n=3)
        stock_actual = None
        stock_prev = None
        if results:
            for r in results:
                s = r.get("stock")
                if isinstance(s, (int, float)) and s > 0:
                    stock_actual = int(s)
                    break
        if stock_actual is None:
            for r in rows:
                s = r.get("stock")
                if isinstance(s, (int, float)):
                    stock_actual = int(s)
                    break
        if len(rows) >= 2:
            prev = rows[1]
            sp = prev.get("stock")
            if isinstance(sp, (int, float)):
                stock_prev = int(sp)
        if stock_actual is not None and stock_actual > 0:
            if stock_prev is not None and stock_prev <= 0:
                return True
        prices = [r.get("price") for r in rows]
        if len(prices) >= 2 and prices[0] and prices[1] is not None:
            try:
                if float(prices[0]) > 0 and float(prices[1]) <= 0:
                    return True
            except Exception:
                pass
        return None
    except Exception as e:
        logger.error(f"⚠ error detectar_restock caza {caza_id}: {e}")
        return None


def _obtener_contacto(user_id):
    """Obtiene datos de contacto del usuario para notificaciones."""
    try:
        res = supabase.table("profiles") \
            .select("whatsapp_number, email, plan, telegram_id") \
            .eq("user_id", user_id) \
            .limit(1) \
            .execute()
        rows = res.data or []
        return rows[0] if rows else {}
    except Exception as e:
        logger.error("⚠ error obteniendo contacto:", e)
        return {}


def evaluar_reglas_alerta(caza_id, user_id):
    """Evalúa las alert_config de un monitor_rule y envía notificaciones si corresponde."""
    try:
        rules = supabase.table("monitor_rules") \
            .select("alert_config") \
            .eq("caza_id", caza_id) \
            .eq("user_id", user_id) \
            .limit(1) \
            .execute()
        if not rules.data:
            return
        alert_config = rules.data[0].get("alert_config")
        if not alert_config:
            return
        if isinstance(alert_config, str):
            alert_config = json.loads(alert_config)

        history = supabase.table("price_history") \
            .select("price, checked_at, stock") \
            .eq("caza_id", caza_id) \
            .order("checked_at", desc=True) \
            .limit(10) \
            .execute()
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
                    if prices[i] < prices[i - 1]:
                        consec += 1
                    else:
                        consec = 0
                    if consec >= int(threshold):
                        match = True
                        detail = f"{consec} bajas consecutivas"
                        break
            elif rtype == "velocity_drop":
                h24 = supabase.table("price_history") \
                    .select("price") \
                    .eq("caza_id", caza_id) \
                    .gte("checked_at", (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()) \
                    .order("checked_at") \
                    .limit(2) \
                    .execute()
                hp = [float(h["price"]) for h in (h24.data or []) if h.get("price")]
                if len(hp) >= 2 and hp[0] > 0:
                    pct = ((hp[0] - current) / hp[0]) * 100
                    match = pct >= threshold
                    detail = f"Caída de {pct:.1f}% en 24hs"
            elif rtype == "below_hist_min":
                all_p = supabase.table("price_history") \
                    .select("price") \
                    .eq("caza_id", caza_id) \
                    .order("price") \
                    .limit(1) \
                    .execute()
                if all_p.data:
                    hist_min = float(all_p.data[0]["price"])
                    if hist_min > 0 and current <= hist_min * 1.01:
                        match = True
                        detail = f"Nuevo mínimo histórico: ${current:.0f}"
            elif rtype == "restock":
                match, detail = _evaluar_restock(history.data or [])
            elif rtype == "inflado":
                det = detectar_inflado(caza_id)
                match = det is True
                detail = "Posible descuento falso: el precio se infló antes de bajar"
            elif rtype == "margen":
                sale_price = float(r.get("threshold", 0))
                min_margin = float(r.get("min_margin", 15))
                if sale_price > 0 and current > 0:
                    margen = ((sale_price - current) / sale_price) * 100
                    if margen >= min_margin:
                        match = True
                        detail = f"Margen {margen:.0f}% (venta ${sale_price:.0f} → compra ${current:.0f})"

            if match:
                channel = r.get("channel", "push")
                body = f"\u201c{detail}\u201d — Actual: ${current:.0f}"
                title = f"⚡ Alerta {rtype.replace('_', ' ').title()}"

                if channel in ("push", "all"):
                    from pywebpush import webpush, WebPushException
                    subs = supabase.table("push_subscriptions") \
                        .select("subscription") \
                        .eq("user_id", user_id) \
                        .execute()
                    for row in subs.data or []:
                        try:
                            sub = json.loads(row["subscription"]) if isinstance(row["subscription"], str) else row["subscription"]
                            webpush(
                                subscription_info=sub,
                                data=json.dumps({"title": title, "body": body, "url": f"/monitor?caza={caza_id}"}),
                                vapid_private_key=VAPID_PRIVATE_KEY,
                                vapid_claims={"sub": VAPID_CLAIM},
                            )
                        except Exception:
                            supabase.table("push_subscriptions").delete().eq("user_id", user_id).execute()

                contacto = _obtener_contacto(user_id)

                if channel in ("whatsapp", "all"):
                    numero = (contacto.get("whatsapp_number") or "").strip()
                    if numero:
                        msg_wa = f"{title}\n{body}"
                        enviar_whatsapp(numero, msg_wa)

                if channel in ("telegram", "all"):
                    tid = contacto.get("telegram_id") or ""
                    if tid:
                        enviar_telegram(tid, f"{title}\n{body}")

                if channel in ("email", "all"):
                    email = (contacto.get("email") or "").strip()
                    if email:
                        enviar_email(email, title, body)

    except Exception as e:
        logger.error(f"⚠ error evaluando reglas alerta caza {caza_id}: {e}")
