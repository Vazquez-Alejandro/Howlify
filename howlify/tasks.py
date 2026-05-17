import os
import time
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

from supabase import create_client
from howlify.celery_app import celery_app
from scraper.scraper_pro import hunt_offers
from services.notification_service import enviar_telegram, enviar_email, enviar_whatsapp
from utils.logic import (
    obtener_dolar_tarjeta, _safe_float, _parse_dt_utc, _effective_minutes,
    parse_price_to_int, _extract_product_id, _domain_from_url, normalize_plan_family,
)
from services.business_service import guardar_oportunidad_business

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY) if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY else None

ALERT_COOLDOWN_MINUTES = int(os.getenv("ALERT_COOLDOWN_MINUTES", "30") or 30)
PLAN_ALIAS = {
    "omega": "starter", "trial": "starter", "starter": "starter",
    "beta": "pro", "alfa": "pro", "revendedor": "pro", "empresa": "pro", "pro": "pro",
    "business_reseller": "business_reseller", "business_monitor": "business_monitor",
}


def _norm_plan(plan: str) -> str:
    return PLAN_ALIAS.get((plan or "starter").strip().lower(), "starter")


def _save_price_history(caza_id: int, user_id: str, results: list[dict]):
    if not supabase or not results:
        return
    rows = []
    for r in results:
        p = _safe_float(r.get("price"))
        if p <= 0:
            continue
        rows.append({
            "caza_id": caza_id, "user_id": user_id,
            "title": r.get("title"), "price": p,
            "url": r.get("url"), "source": r.get("source"),
            "product_id": _extract_product_id(r.get("url")),
            "checked_at": datetime.now(timezone.utc).isoformat(),
        })
    if rows:
        try:
            supabase.table("price_history").insert(rows).execute()
        except Exception as e:
            print(f"[tasks] error saving price history: {e}")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def hunt_single_task(self, caza_id: int, user_id: str):
    if not supabase:
        raise RuntimeError("Supabase no configurado")
    res = supabase.table("cazas").select("*").eq("id", caza_id).limit(1).execute()
    if not res.data:
        return {"error": "Cacería no encontrada"}
    caza = res.data[0]
    url = caza.get("url") or caza.get("link") or ""
    kw = caza.get("producto") or caza.get("keyword") or ""
    precio_max = _safe_float(caza.get("precio_max"), 0)
    try:
        resultados = hunt_offers(url, kw, precio_max, headless=True) or []
        if resultados:
            _save_price_history(caza_id, user_id, resultados)
        return {"results": resultados}
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def hunt_all_user_task(self, user_id: str):
    if not supabase:
        raise RuntimeError("Supabase no configurado")
    res = supabase.table("cazas").select("*").eq("user_id", user_id).eq("estado", "activa").execute()
    results = {}
    for c in res.data or []:
        caza_id = c.get("id")
        url = c.get("url") or c.get("link") or ""
        kw = c.get("producto") or c.get("keyword") or ""
        precio_max = _safe_float(c.get("precio_max"), 0)
        try:
            r = hunt_offers(url, kw, precio_max, headless=True) or []
            if r:
                _save_price_history(caza_id, user_id, r)
            results[str(caza_id)] = r
        except Exception as e:
            results[str(caza_id)] = {"error": str(e)}
    return {"results": results}


@celery_app.task(max_retries=2, default_retry_delay=60)
def vigilar_ofertas_task():
    if not supabase:
        return {"error": "Supabase no configurado"}
    print("[celery] vigilar_ofertas_task ejecutando...")
    now = datetime.now(timezone.utc)
    valor_dolar = obtener_dolar_tarjeta()
    try:
        cazas = supabase.table("cazas").select("*").eq("estado", "activa").execute()
    except Exception as e:
        print(f"[celery] error consultando cazas: {e}")
        return {"error": str(e)}
    for c in cazas.data or []:
        caza_id = c.get("id")
        user_id = c.get("user_id")
        link = c.get("link") or c.get("url") or ""
        if not link:
            continue
        producto = c.get("producto")
        precio_max_db = _safe_float(c.get("precio_max"))
        moneda = c.get("currency", "ARS")
        frecuencia = c.get("frecuencia")
        last_check = c.get("last_check")
        plan = c.get("plan", "starter")
        mins = _effective_minutes(plan, frecuencia)
        last_dt = _parse_dt_utc(last_check)
        if last_dt and (now - last_dt) < timedelta(minutes=mins):
            continue
        precio_limite = precio_max_db
        if moneda == "USD":
            precio_limite = precio_max_db * valor_dolar
        try:
            resultados = hunt_offers(link, producto, precio_limite, headless=True) or []
            resultados = [r for r in resultados if _safe_float(r.get("price"), 0) > 0]
            if not resultados:
                continue
            mejor = sorted(resultados, key=lambda x: _safe_float(x.get("price"), 999999999))[0]
            precio_actual = _safe_float(mejor.get("price"), 0)
            if _norm_plan(plan) in {"business_reseller", "business_monitor"}:
                min_res = supabase.table("price_history").select("price").eq("caza_id", caza_id).order("price").limit(1).execute()
                if min_res.data:
                    precio_minimo = _safe_float(min_res.data[0]["price"])
                    if precio_actual < precio_minimo:
                        pid = _extract_product_id(mejor.get("url"))
                        guardar_oportunidad_business(
                            caza_id, pid, mejor.get("title"),
                            mejor.get("source") or _domain_from_url(mejor.get("url")),
                            precio_actual, precio_minimo, None,
                        )
            if precio_actual <= precio_limite:
                prev_res = supabase.table("alertas_enviadas").select("*").eq("caza_id", caza_id).order("created_at", desc=True).limit(1).execute()
                enviar = True
                if prev_res.data:
                    prev = prev_res.data[0]
                    prev_dt = _parse_dt_utc(prev.get("created_at"))
                    if prev_dt and (now - prev_dt) < timedelta(minutes=ALERT_COOLDOWN_MINUTES):
                        enviar = False
                    elif precio_actual >= _safe_float(prev.get("oferta_precio"), 999999) and mejor.get("title") == prev.get("oferta_titulo"):
                        enviar = False
                if enviar:
                    profile_res = supabase.table("profiles").select("*").eq("user_id", user_id).limit(1).execute()
                    if profile_res.data:
                        p = profile_res.data[0]
                        _enviar_alerta(p, producto, mejor, precio_actual)
                        supabase.table("alertas_enviadas").insert({
                            "caza_id": caza_id, "user_id": user_id,
                            "oferta_url": mejor.get("url"), "oferta_titulo": mejor.get("title"),
                            "oferta_precio": precio_actual, "canal": "automatico",
                        }).execute()
            _save_price_history(caza_id, user_id, resultados)
            supabase.table("cazas").update({"last_check": now.isoformat()}).eq("id", caza_id).execute()
        except Exception as e:
            print(f"[celery] error caza {caza_id}: {e}")
    return {"status": "ok"}


def _enviar_alerta(profile: dict, producto: str, oferta: dict, precio: float):
    titulo = oferta.get("title", producto)
    mensaje = (
        f"🐺 *Howlify - Oferta Detectada*\n\n"
        f"📦 *{titulo}*\n💰 *${precio:,.0f}*\n"
        f"🔗 {oferta.get('url', '')}\n\n"
        f"🦴 _Enviado por Howlify_"
    )
    t_id = profile.get("telegram_id")
    email = profile.get("email")
    if t_id:
        try:
            enviar_telegram(t_id, mensaje)
        except Exception as e:
            print(f"[tasks] error telegram: {e}")
    if email:
        try:
            enviar_email(email, f"🐺 Oferta: {titulo}", mensaje)
        except Exception as e:
            print(f"[tasks] error email: {e}")
    if _norm_plan(profile.get("plan", "")) != "starter":
        wapp = profile.get("whatsapp_number")
        if wapp:
            try:
                enviar_whatsapp(wapp, mensaje.replace("*", ""))
            except Exception as e:
                print(f"[tasks] error whatsapp: {e}")


@celery_app.task
def enviar_notificacion_task(user_id: str, producto: str, oferta: dict, precio: float):
    if not supabase:
        return
    res = supabase.table("profiles").select("*").eq("user_id", user_id).limit(1).execute()
    if res.data:
        _enviar_alerta(res.data[0], producto, oferta, precio)
