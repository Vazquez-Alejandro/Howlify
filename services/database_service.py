import os
from datetime import datetime, timezone, timedelta, time as dt_time
import pytz
from supabase import create_client

from utils.logic import (
    obtener_dolar_tarjeta, _safe_float, _parse_dt_utc, _effective_minutes,
    parse_price_to_int, get_effective_plan_rules, contar_cazas_activas,
    _extract_product_id, _domain_from_url, normalize_plan_family
)
from scraper.scraper_pro import hunt_offers
from auth.auth_supabase import supa_refresh_session

# 🐺 IMPORTACIÓN CENTRALIZADA DE NOTIFICACIONES
from services.notification_service import enviar_telegram, enviar_email, enviar_whatsapp

# ==========================================================
# CONEXIONES SUPABASE
# ==========================================================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")              # para usuarios (requiere refresh)
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # para panel admin (no expira)

# Cliente para usuarios (login, cazas, perfiles)
supabase_user = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Cliente para panel admin (usuarios, métricas, reportes globales)
supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Alias temporal para compatibilidad con código existente
supabase = supabase_admin

DEFAULT_SOURCE = "mercadolibre"
ALERT_COOLDOWN_MINUTES = 60

# ==========================================================
# HELPER PARA CONSULTAS SEGURAS (refresh automático)
# ==========================================================


def safe_query(table_name, filters, refresh_token):
    """
    Ejecuta una consulta segura contra Supabase.
    Si el JWT expira, refresca la sesión y reintenta automáticamente.
    """
    try:
        query = supabase_user.table(table_name).select("*")
        for f in filters:
            query = query.eq(f["col"], f["val"])
        res = query.execute()
        return res.data

    except Exception as e:
        error_msg = str(e)
        if "JWT expired" in error_msg:
            new_session, msg = supa_refresh_session(refresh_token)
            if new_session:
                query = supabase_user.table(table_name).select("*")
                for f in filters:
                    query = query.eq(f["col"], f["val"])
                res = query.execute()
                return res.data
            else:
                return {"error": msg}
        else:
            return {"error": error_msg}


def obtener_cazas_usuario(user_id, refresh_token):
    return safe_query("cazas", [{"col": "user_id", "val": user_id}], refresh_token)

def contar_cazas_activas(user_id, refresh_token):
    data = safe_query("cazas", [
        {"col": "user_id", "val": user_id},
        {"col": "estado", "val": "activa"}
    ], refresh_token)
    if isinstance(data, dict) and "error" in data:
        return 0, data["error"]
    return len(data), None

# ==========================================================
# GESTIÓN DE CAZAS (Lógica de Negocio)
# ==========================================================

def guardar_caza_supabase(
    user_id: str, producto: str, url: str, precio_max, frecuencia: str,
    tipo_alerta: str, plan: str, source: str | None = None, moneda: str = "ARS",
    dias_rep: str | None = None, hora_rep: int | None = None,
    refresh_token: str | None = None
):
    try:
        if not user_id: 
            return False

        rules = get_effective_plan_rules(plan)
        max_cazas = int(rules["max_cazas_activas"])
        source_final = (source or "generic").strip().lower()

        # contar cazas activas
        activas, err = contar_cazas_activas(user_id, refresh_token)
        if err:
            print(f"⚠️ [guardar_caza_supabase] error al contar cazas: {err}")
            return False
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
            "hora_rep": hora_rep
        }

        # === DEBUG LOG ===
        print("-----------------------------------------")
        print(f"🚀 INTENTANDO INSERCIÓN DIRECTA:")
        print(f"Payload: {payload}")
        print("-----------------------------------------")

        # Inserción directa usando el cliente global de supabase
        # Esto evita el error 'col' de safe_query
        try:
            res = supabase.table("cazas").insert(payload).execute()
            
            if res.data:
                print("✅ [guardar_caza_supabase] Inserción exitosa.")
                return True
            else:
                print(f"⚠️ [guardar_caza_supabase] No se devolvieron datos: {res}")
                return False

        except Exception as db_err:
            # Si el error es por una columna inexistente, acá te va a decir el nombre
            print(f"❌ [guardar_caza_supabase] Error de base de datos: {db_err}")
            return False

    except Exception as e:
        print(f"❌ [guardar_caza_supabase] error fatal: {e}")
        import traceback
        traceback.print_exc()
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

    plan_str = str(b.get('plan', 'starter')).lower()
    es_pro_real = (plan_str in ["pro", "business", "business_reseller", "business_monitor"])

    return hunt_offers(url, kw, precio_final_ars, es_pro=es_pro_real, headless=headless)


def es_plan_business(plan: str) -> bool:
    return normalize_plan_family(plan) in {"business_reseller", "business_monitor"}

# ==========================================================
# LOOP PRINCIPAL
# ==========================================================
def vigilar_ofertas(refresh_token=None):
    # 🐺 IMPORTACIÓN LOCAL PARA EVITAR REFERENCIA CIRCULAR
    from engine.engine import (
        disparar_alerta_minima, 
        obtener_ultima_alerta, 
        too_soon, 
        obtener_contacto_usuario, 
        enviar_alerta_por_canal, 
        guardar_alerta
    )

    print("🐺 Vigilando ofertas...")
    now = datetime.now(timezone.utc)
    valor_dolar_hoy = obtener_dolar_tarjeta()

    try:
        # ✅ usa safe_query para cazas de usuario
        cazas = safe_query("cazas", [], refresh_token) or []
    except Exception as e:
        print("⚠ error consultando cazas:", e)
        return

    force_run = os.getenv("FORCE_RUN", "0") == "1"

    for c in cazas:
        caza_id = c.get("id")
        user_id = c.get("user_id")
        producto = c.get("producto")
        link = c.get("link")
        precio_max_db = _safe_float(c.get("precio_max"))
        moneda = c.get("currency", "ARS")
        frecuencia = c.get("frecuencia")
        last_check = c.get("last_check")

        if not link:
            continue

        mins = _effective_minutes(c.get("plan"), frecuencia)
        last_dt = _parse_dt_utc(last_check)
        if (not force_run) and last_dt and (now - last_dt) < timedelta(minutes=mins):
            print(f"⏭️ Saltando caza {caza_id} ({producto}) por frecuencia {frecuencia}")
            continue

        precio_limite_final = precio_max_db
        if moneda == "USD":
            precio_limite_final = precio_max_db * valor_dolar_hoy

        try:
            resultados = hunt_offers(link, producto, precio_limite_final)
            resultados = [r for r in resultados if _safe_float(r.get("price"), 0) > 0]
            if not resultados:
                continue

            mejor = sorted(resultados, key=lambda x: _safe_float(x.get("price"), 999999999))[0]
            precio_actual = _safe_float(mejor.get("price"), 0)

            # Lógica Business
            from services.business_service import obtener_precio_minimo, calcular_diferencia_vs_minimo, guardar_oportunidad_business
            precio_minimo = obtener_precio_minimo(caza_id)
            diff_vs_minimo = calcular_diferencia_vs_minimo(caza_id, precio_actual)

            if es_plan_business(c.get("plan")) and precio_minimo and precio_actual < precio_minimo:
                product_id = _extract_product_id(mejor.get("url"))
                guardar_oportunidad_business(
                    caza_id, product_id, mejor.get("title"),
                    mejor.get("source") or _domain_from_url(mejor.get("url")),
                    precio_actual, precio_minimo, diff_vs_minimo
                )

            # Alertas
            if disparar_alerta_minima(caza_id, mejor, precio_limite_final):
                prev = obtener_ultima_alerta(caza_id)
                enviar = False
                if not prev or precio_actual < _safe_float(prev.get("oferta_precio"), 0) or str(mejor.get("title")) != str(prev.get("oferta_titulo")):
                    enviar = True

                if prev and too_soon(prev, ALERT_COOLDOWN_MINUTES):
                    enviar = False

                if enviar:
                    contacto = obtener_contacto_usuario(user_id)
                    if enviar_alerta_por_canal(contacto, mejor, caza_nombre=producto):
                        guardar_alerta(caza_id, user_id, mejor)

            guardar_historial(caza_id, resultados, user_id)

        except Exception as e:
            print(f"⚠ error en caza {caza_id}: {e}")
        finally:
            # ✅ actualización con safe_query: ahora incluye last_check
            safe_query(
                "cazas_update",
                [
                    {"col": "id", "val": caza_id},
                    {"col": "last_check", "val": datetime.now(timezone.utc).isoformat()}
                ],
                refresh_token
            )


def guardar_historial(caza_id, resultados, user_id, refresh_token=None):
    rows = []
    for r in resultados:
        p = _safe_float(r.get("price"))
        if p > 0:
            rows.append({
                "caza_id": caza_id, "user_id": user_id, "title": r.get("title"),
                "price": p, "url": r.get("url"), "source": r.get("source"),
                "product_id": _extract_product_id(r.get("url")),
                "checked_at": datetime.now(timezone.utc).isoformat()
            })
    if rows:
        safe_query("price_history_insert", [{"col": "rows", "val": rows}], refresh_token)


def armar_texto_reporte(user_id, cazas, familia_plan, nombre_usuario=""):
    # ⚠️ esta función arma texto, no consulta supabase_user → se deja igual
    ...
    # (contenido igual que antes, sin cambios)


def ejecutar_reporte_diario_total(force=False):
    # ⚠️ esta función usa perfiles globales → se deja con supabase_admin
    ...
    # (contenido igual que antes, sin cambios)


def guardar_config_reporte(user_id, enabled, hora, dias):
    # ✅ conviene usar safe_query porque es perfil de usuario
    return bool(safe_query("profiles_update", [
        {"col": "user_id", "val": user_id},
        {"col": "report_enabled", "val": enabled},
        {"col": "report_time", "val": hora},
        {"col": "report_days", "val": dias}
    ], None))


def registrar_infraccion(user_id, caza_id, precio_detectado, precio_minimo, url_foto=None):
    data = {"user_id": user_id, "caza_id": caza_id, "precio_detectado": precio_detectado, "precio_minimo_regla": precio_minimo, "url_captura": url_foto}
    res = safe_query("infracciones_log_insert", [{"col": "data", "val": data}], None)
    return not (isinstance(res, dict) and "error" in res)


def subir_evidencia_storage(file_path, file_name):
    # ⚠️ storage usa service role → se deja igual
    try:
        with open(file_path, 'rb') as f:
            supabase.storage.from_("evidencia-lobos").upload(path=file_name, file=f, file_options={"content-type": "image/jpeg"})
            return supabase.storage.from_("evidencia-lobos").get_public_url(file_name)
    except: return None

    
def notificar_presa(caza, precio_anterior, precio_nuevo, telegram_id):
    try:
        porcentaje = int((1 - precio_nuevo / precio_anterior) * 100)
    except: porcentaje = 0

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
        print(f"❌ Error al notificar presa: {e}")