import os
import re
import time
import requests
from dotenv import load_dotenv 
load_dotenv()
from playwright.sync_api import sync_playwright
from duffel_api import Duffel
from utils.currency import get_dolar_tarjeta

# --- CONFIGURACIÓN ---
DUFFEL_TOKEN = os.getenv("DUFFEL_ACCESS_TOKEN")

def _parse_price(text):
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None

def _looks_blocked(html_lower: str) -> bool:
    needles = [
        "acceso restringido temporalmente",
        "hemos detectado un comportamiento inusual",
        "comportamiento del navegador",
        "servicio de asistencia al cliente",
        "access denied",
        "forbidden",
        "captcha",
        "recaptcha",
    ]
    return any(x in html_lower for x in needles)

def hunt_vuelos_api(dest_iata: str, max_price: int = 0, url: str = ""):
    if not DUFFEL_TOKEN:
        print("⚠️ [Duffel] No se encontró DUFFEL_ACCESS_TOKEN en el .env")
        return []

    headers = {
        "Authorization": f"Bearer {DUFFEL_TOKEN}",
        "Duffel-Version": "v2", 
        "Content-Type": "application/json"
    }

    try:
        print(f"🚀 [API] Buscando vuelos EZE -> {dest_iata}...")
        
        payload = {
            "data": {
                "slices": [
                    {"origin": "EZE", "destination": dest_iata, "departure_date": "2026-06-15"},
                    {"origin": dest_iata, "destination": "EZE", "departure_date": "2026-06-25"}
                ],
                "passengers": [{"type": "adult"}]
            }
        }
        
        res = requests.post("https://api.duffel.com/air/offer_requests", json=payload, headers=headers)
        res_data = res.json()
        
        if "errors" in res_data:
            print(f"❌ Error API: {res_data['errors'][0]['message']}")
            return []

        offers = res_data["data"].get("offers", [])
        results = []
        
        cotizacion = get_dolar_tarjeta()
        print(f"💵 Cotización Dólar Tarjeta: ${cotizacion}")

        for o in offers:
            price_usd = float(o["total_amount"])
            price_ars = int(price_usd * cotizacion)
            
            if max_price > 0 and price_ars > max_price:
                continue
            
            is_ganga = False
            if price_usd < 450:
                is_ganga = True
            elif price_usd < 950:
                is_ganga = True

            owner = o.get("owner", {})
            airline_name = owner.get("name", "Aerolínea")
            logo_url = owner.get("logo_symbol_url")

            display_title = f"Vuelo EZE ✈️ {dest_iata}"
            if is_ganga:
                display_title += " 🔥 ¡OFERTA REAL!"

            results.append({
                "title": display_title,
                "price": price_ars,
                "price_usd": price_usd,
                "airline": airline_name,
                "logo": logo_url,
                "is_ganga": is_ganga,
                "url": url,
                "source": "duffel"
            })
            
        return sorted(results, key=lambda x: x["price"])[:10]

    except Exception as e:
        print(f"❌ Error fatal en Duffel: {e}")
        return []



# --- FUNCIONES DE SOPORTE ---

def _scrape_monthly_matrix(url, max_price=0):
    print("👀 MODO HUMANO: Abriendo ventana para saltar bloqueos...")
    mejores_ofertas = []
    
    with sync_playwright() as p:
        # headless=False abre la ventana para que veas qué pasa
        browser = p.chromium.launch(headless=False) 
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            page.goto(url, wait_until="domcontentloaded")
            print("⏳ Esperando 10 segundos... Si ves un captcha, resolvelo.")
            time.sleep(10) # Te damos tiempo para que cargue la grilla

            # Buscamos por texto directamente en la pantalla
            content = page.content()
            # Buscamos patrones de precios (ej: USD 950 o $ 850.000)
            precios_encontrados = re.findall(r'(?:USD|\$)\s?(\d[\d\.,]*)', content)
            
            for p_raw in precios_encontrados:
                precio = _parse_price(p_raw)
                if precio and precio > 300:
                    if max_price == 0 or precio <= max_price:
                        mejores_ofertas.append({
                            "title": "Vuelo detectado en Grilla",
                            "price": precio,
                            "url": url,
                            "source": "visual_hunt"
                        })

            print(f"✅ El Lobo detectó {len(mejores_ofertas)} precios en pantalla.")

        except Exception as e:
            print(f"❌ Error en Modo Humano: {e}")
        finally:
            browser.close()
            
    return mejores_ofertas

def hunt_despegar_vuelos(url, keyword="", max_price=0, es_pro=False):
    url_l = url.lower()
    kw_l = str(keyword or "").lower().strip()
    
    # 1. Mapeo para comparar
    destinos_dict = {
        "barcelona": "BCN", "madrid": "MAD", "miami": "MIA", 
        "roma": "FCO", "cancun": "CUN", "rio": "GIG"
    }
    iata_esperado = destinos_dict.get(kw_l, kw_l.upper() if len(kw_l) == 3 else "")

    # 2. DETECTOR DE IATA REAL (Lo que dice la URL)
    iata_url = ""
    deep_match = re.search(r'/(?P<orig>[a-z]{3})/(?P<dest>[a-z]{3})(?:/|\?|$)', url_l)
    if deep_match:
        iata_url = deep_match.group("dest").upper()

    # 3. VALIDACIÓN DE DISCREPANCIA (Aviso sin bloqueo)
    alerta_match = ""
    if iata_url and iata_esperado and iata_url != iata_esperado:
        alerta_match = f"⚠️ (Link a {iata_url}, no {iata_esperado})"
        print(f"🚩 AVISO: Discrepancia detectada {iata_url} vs {iata_esperado}")

    # --- 4. MODO MENSUAL (PRO) ---
    if es_pro and ("flexible" in url_l or "calendar" in url_l or "vuelos-a-" in url_l):
        return _scrape_monthly_matrix(url, max_price)

    # --- 5. EJECUCIÓN: PRIORIDAD URL ---
    destino_final = iata_url or iata_esperado
    
    if destino_final and len(destino_final) == 3:
        print(f"🚀 Buscando por IATA: {destino_final}")
        res = hunt_vuelos_api(destino_final, max_price, url=url)
        for r in res:
            r["title"] = f"Vuelo a {destino_final} {alerta_match}".strip()
        return res
    
    # --- 6. SCRAPER LENTO (Fallback) ---
    print(f"🕵️ Iniciando Scraper...")
    presas = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            time.sleep(5)
            if _looks_blocked(page.content().lower()):
                return [{"source": "vuelos", "blocked": True, "url": url}]

            candidates = page.locator("text=/\\$\\s*\\d/")
            for i in range(min(candidates.count(), 10)):
                raw_price = candidates.nth(i).inner_text()
                price = _parse_price(raw_price)
                if price and (not max_price or price <= max_price):
                    presas.append({
                        "title": f"Vuelo a {destino_final or 'Destino'} {alerta_match}".strip(),
                        "price": price, "url": url, "source": "scraper_vuelo"
                    })
        except Exception as e:
            print(f"❌ Error Scraper: {e}")
        finally:
            browser.close()
    return presas