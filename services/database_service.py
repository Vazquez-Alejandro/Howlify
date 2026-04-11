import os
from datetime import datetime, timezone, timedelta
from supabase import create_client
from utils.logic import (
    obtener_dolar_tarjeta, _safe_float, _parse_dt_utc, _effective_minutes,
    parse_price_to_int, get_effective_plan_rules, contar_cazas_activas,
    _extract_product_id, _domain_from_url, normalize_plan_family
)
from scraper.scraper_pro import hunt_offers

# 🐺 IMPORTACIÓN CENTRALIZADA DE NOTIFICACIONES
from services.notification_service import enviar_telegram, enviar_email, enviar_whatsapp

# Conexión central
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

DEFAULT_SOURCE = "mercadolibre"
ALERT_COOLDOWN_MINUTES = 60

# ==========================================================
# GESTIÓN DE CAZAS (Lógica de Negocio)
# ==========================================================

def guardar_caza_supabase(
    user_id: str, producto: str, url: str, precio_max, frecuencia: str,
    tipo_alerta: str, plan: str, source: str | None = None, moneda: str = "ARS",
    dias_rep: str | None = None, hora_rep: int | None = None
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
            "hora_rep": hora_rep
        }

        ins = supabase.table("cazas").insert(payload).execute()
        return True if getattr(ins, "data", None) else False

    except Exception as e:
        print(f"❌ [guardar_caza_supabase] error fatal: {e}")
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

def vigilar_ofertas():
    print("🐺 Vigilando ofertas...")
    now = datetime.now(timezone.utc)
    valor_dolar_hoy = obtener_dolar_tarjeta()

    try:
        res = supabase.table("cazas").select("*").execute()
        cazas = res.data or []
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

        if not link: continue

        mins = _effective_minutes(c.get("plan"), frecuencia)
        last_dt = _parse_dt_utc(last_check)
        if (not force_run) and last_dt and (now - last_dt) < timedelta(minutes=mins):
            continue

        precio_limite_final = precio_max_db
        if moneda == "USD":
            precio_limite_final = precio_max_db * valor_dolar_hoy

        try:
            resultados = hunt_offers(link, producto, precio_limite_final)
            resultados = [r for r in resultados if _safe_float(r.get("price"), 0) > 0]
            if not resultados: continue

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

            # Alertas - Usamos la lógica centralizada de notificaciones
            from scraper.alertas import disparar_alerta_minima, obtener_ultima_alerta, too_soon, obtener_contacto_usuario, enviar_alerta_por_canal, guardar_alerta
            if disparar_alerta_minima(caza_id, mejor, precio_limite_final):
                prev = obtener_ultima_alerta(caza_id)
                enviar = False
                if not prev or precio_actual < _safe_float(prev.get("oferta_precio"), 0) or str(mejor.get("title")) != str(prev.get("oferta_titulo")):
                    enviar = True

                if prev and too_soon(prev, ALERT_COOLDOWN_MINUTES):
                    enviar = False

                if enviar:
                    contacto = obtener_contacto_usuario(user_id)
                    # Aquí la función enviar_alerta_por_canal ya debe usar notification_service internamente
                    if enviar_alerta_por_canal(contacto, mejor, caza_nombre=producto):
                        guardar_alerta(caza_id, user_id, mejor)

            guardar_historial(caza_id, resultados, user_id)

        except Exception as e:
            print(f"⚠ error en caza {caza_id}: {e}")
        finally:
            supabase.table("cazas").update({"last_check": datetime.now(timezone.utc).isoformat()}).eq("id", caza_id).execute()

def guardar_historial(caza_id, resultados, user_id):
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
        supabase.table("price_history").insert(rows).execute()

def armar_texto_reporte(user_id, cazas, familia_plan, nombre_usuario=""):
    total = len(cazas)
    infracciones, ok, errores = 0, 0, 0
    
    rules_map = {}
    if familia_plan == "business_monitor":
        res_rules = supabase.table("monitor_rules").select("*").eq("user_id", user_id).execute()
        rules_map = {str(r["caza_id"]): r for r in (res_rules.data or [])}

    for c in cazas:
        cid = str(c["id"])
        if not c.get("last_check"):
            errores += 1
            continue
            
        if familia_plan == "business_monitor":
            rule = rules_map.get(cid)
            if rule:
                res_p = supabase.table("price_history").select("price").eq("caza_id", cid).order("checked_at", desc=True).limit(1).execute()
                precio_actual = res_p.data[0]["price"] if res_p.data else 0
                min_p = float(rule.get("min_price_allowed") or 0)
                if precio_actual > 0 and min_p > 0 and precio_actual < min_p:
                    infracciones += 1
                else: ok += 1
            else: ok += 1 
        else: ok += 1

    saludo = f"🐺 *¡Buen día, {nombre_usuario or 'Cazador'}!* Reporte de Howlify listo.\n\n"
    if familia_plan == "business_monitor":
        cuerpo = f"📊 *Resumen de Radar:*\n✅ Productos OK: {ok}\n🔴 Infracciones MAP: {infracciones}\n⚠️ Errores técnicos: {errores}\n\n{'🚨 ¡Atención! Hay desviaciones.' if infracciones > 0 else '🟢 Todo OK.'}"
    else:
        cuerpo = f"✈️ *Estado:* {total} activas.\n🔎 El Lobo vigiló tus links.\n✅ Todo bajo control."

    return saludo + cuerpo + "\n\n🔗 [Ver mi Panel](https://howlify.com)"

def ejecutar_reporte_diario_total():
    import pytz
    tz = pytz.timezone('America/Argentina/Buenos_Aires')
    now = datetime.now(tz)
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    dia_actual = dias_semana[now.weekday()]
    hora_actual = now.strftime("%H:%M:00") 

    try:
        res_usuarios = (supabase.table("profiles")
            .select("user_id, username, plan, telegram_id, report_days, report_time")
            .eq("report_enabled", True)
            .eq("report_time", hora_actual)
            .contains("report_days", [dia_actual])
            .execute())
        
        usuarios = res_usuarios.data or []
        for u in usuarios:
            uid = u["user_id"]
            res_cazas = supabase.table("cazas").select("*").eq("user_id", uid).eq("estado", "activa").execute()
            cazas = res_cazas.data or []
            if not cazas: continue 

            mensaje = armar_texto_reporte(uid, cazas, normalize_plan_family(u.get("plan")), u.get("username"))
            
            if u.get("telegram_id"):
                enviar_telegram(u["telegram_id"], mensaje)
                
    except Exception as e:
        print(f"❌ Error en reporte diario: {e}")

def guardar_config_reporte(user_id, enabled, hora, dias):
    try:
        res = supabase.table("profiles").update({
            "report_enabled": enabled, "report_time": hora, "report_days": dias
        }).eq("user_id", user_id).execute()
        return len(res.data) > 0
    except: return False
    
def registrar_infraccion(user_id, caza_id, precio_detectado, precio_minimo, url_foto=None):
    try:
        data = {"user_id": user_id, "caza_id": caza_id, "precio_detectado": precio_detectado, "precio_minimo_regla": precio_minimo, "url_captura": url_foto}
        res = supabase.table("infracciones_log").insert(data).execute()
        return True if res.data else False
    except: return False
    
def subir_evidencia_storage(file_path, file_name):
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