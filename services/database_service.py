import os
from datetime import datetime, timezone, timedelta
from supabase import create_client
from utils.logic import (
    obtener_dolar_tarjeta, _safe_float, _parse_dt_utc, _effective_minutes,
    parse_price_to_int, get_effective_plan_rules, contar_cazas_activas,
    _extract_product_id, _domain_from_url, normalize_plan_family
)
from scraper.scraper_pro import hunt_offers

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
    tipo_alerta: str, plan: str, source: str | None = None, moneda: str = "ARS"
):
    try:
        if not user_id: return False

        # Validación de límites de plan
        rules = get_effective_plan_rules(plan)
        max_cazas = int(rules["max_cazas_activas"])
        source = (source or DEFAULT_SOURCE).strip().lower()

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
            "plan": rules["plan_key"],
            "estado": "activa",
            "source": source,
            "last_check": None,
            "currency": moneda.strip().upper(),
        }

        ins = supabase.table("cazas").insert(payload).execute()

        if getattr(ins, "data", None):
            print(f"[guardar_caza_supabase] insert ok ({moneda}):", ins.data)
            return True
        return False

    except Exception as e:
        print("[guardar_caza_supabase] error:", e)
        return False

def run_manual_hunt(b, headless=True):
    # Traemos los datos del diccionario 'b' (que viene de la UI)
    url = b.get("url") or b.get("link") or ""
    kw = b.get("keyword") or b.get("producto") or ""
    precio = b.get("precio_max") or 0
    
    # Lógica de planes para habilitar funciones PRO en el scraper
    plan_str = b.get('plan', 'starter').lower()
    es_pro_real = (plan_str in ["pro", "business", "business_reseller", "business_monitor"])

    # IMPORTANTE: El import debe estar aquí o al principio del archivo
    from scraper.scraper_pro import hunt_offers
    
    # Ejecutamos el rastreo manual
    return hunt_offers(url, kw, precio, es_pro=es_pro_real, headless=headless)


def es_plan_business(plan: str) -> bool:
    return normalize_plan_family(plan) in {"business_reseller", "business_monitor"}

# ==========================================================
# LOOP PRINCIPAL (Vigilancia con Conversión de Moneda)
# ==========================================================

def vigilar_ofertas():
    print("🐺 Vigilando ofertas...")
    now = datetime.now(timezone.utc)
    
    # Cotización para cálculos en USD
    valor_dolar_hoy = obtener_dolar_tarjeta()
    print(f"💵 Cotización Dólar Tarjeta: ${valor_dolar_hoy}")

    try:
        res = supabase.table("cazas").select("*").execute()
        cazas = res.data or []
    except Exception as e:
        print("⚠ error consultando cazas:", e)
        return

    print(f"📦 Total cazas activas: {len(cazas)}")
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

        # Validación de tiempos
        mins = _effective_minutes(c.get("plan"), frecuencia)
        last_dt = _parse_dt_utc(last_check)
        if (not force_run) and last_dt and (now - last_dt) < timedelta(minutes=mins):
            continue

        print(f"🔎 Caza #{caza_id} | {producto} ({moneda})")

        # CONVERSIÓN USD -> ARS para el scraper
        precio_limite_final = precio_max_db
        if moneda == "USD":
            precio_limite_final = precio_max_db * valor_dolar_hoy
            print(f"   💰 Límite convertido: {precio_max_db} USD -> ${precio_limite_final:,.2f} ARS")

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
                print(f"   💥 NUEVO MINIMO: {precio_actual} < {precio_minimo}")
                product_id = _extract_product_id(mejor.get("url"))
                guardar_oportunidad_business(
                    caza_id, product_id, mejor.get("title"),
                    mejor.get("source") or _domain_from_url(mejor.get("url")),
                    precio_actual, precio_minimo, diff_vs_minimo
                )

            # Alertas
            from scraper.alertas import disparar_alerta_minima, obtener_ultima_alerta, too_soon, obtener_contacto_usuario, enviar_alerta_por_canal, guardar_alerta
            if disparar_alerta_minima(caza_id, mejor, precio_limite_final):
                prev = obtener_ultima_alerta(caza_id)
                enviar = False
                if not prev:
                    enviar = True
                else:
                    if precio_actual < _safe_float(prev.get("oferta_precio"), 0) or str(mejor.get("title")) != str(prev.get("oferta_titulo")):
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