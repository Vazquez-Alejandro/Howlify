import os
import re
import time
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv 
load_dotenv()
from playwright.sync_api import sync_playwright
from duffel_api import Duffel
from utils.logic import obtener_dolar_tarjeta

get_dolar_tarjeta = obtener_dolar_tarjeta

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

def generar_fechas_busqueda(meses_adelante=12):
    """Genera una lista de tuplas (ida, vuelta) para los próximos meses."""
    fechas = []
    hoy = datetime.now()
    for i in range(1, meses_adelante + 1):
        # Buscamos el día 15 de cada mes para estandarizar la búsqueda
        fecha_base = hoy + timedelta(days=30 * i)
        ida = fecha_base.replace(day=15).strftime("%Y-%m-%d")
        vuelta = fecha_base.replace(day=25).strftime("%Y-%m-%d")
        fechas.append((ida, vuelta))
    return fechas

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
        print(f"🚀 [API] Buscando vuelos EZE -> {dest_iata} para los próximos 12 meses...")
        ventanas = generar_fechas_busqueda(12)
        all_results = []
        
        cotizacion = get_dolar_tarjeta()
        print(f"💵 Cotización Dólar Tarjeta: ${cotizacion}")

        for ida, vuelta in ventanas:
            payload = {
                "data": {
                    "slices": [
                        {"origin": "EZE", "destination": dest_iata, "departure_date": ida},
                        {"origin": dest_iata, "destination": "EZE", "departure_date": vuelta}
                    ],
                    "passengers": [{"type": "adult"}]
                }
            }
            
            res = requests.post("https://api.duffel.com/air/offer_requests", json=payload, headers=headers)
            res_data = res.json()
            
            if "errors" in res_data:
                continue # Si un mes falla, seguimos con el siguiente

            offers = res_data["data"].get("offers", [])

            for o in offers:
                price_usd = float(o["total_amount"])
                price_ars = int(price_usd * cotizacion)
                
                if max_price > 0 and price_ars > max_price:
                    continue
                
                is_ganga = price_usd < 450 or (price_usd < 950 and "EUROPA" in url.upper())

                owner = o.get("owner", {})
                airline_name = owner.get("name", "Aerolínea")
                logo_url = owner.get("logo_symbol_url")

                display_title = f"Vuelo EZE ✈️ {dest_iata} ({ida})"
                if is_ganga:
                    display_title += " 🔥 ¡OFERTA!"

                all_results.append({
                    "title": display_title,
                    "price": price_ars,
                    "price_usd": price_usd,
                    "airline": airline_name,
                    "logo": logo_url,
                    "is_ganga": is_ganga,
                    "url": url,
                    "source": "duffel",
                    "date": ida
                })
            
        return sorted(all_results, key=lambda x: x["price"])[:10]

    except Exception as e:
        print(f"❌ Error fatal en Duffel: {e}")
        return []

# --- FUNCIONES DE SOPORTE ---

def _scrape_monthly_matrix(url, max_price=0):
    print("👀 MODO HUMANO: Buscando precios con espera inteligente...")
    mejores_ofertas = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) 
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            # Esperamos a que la red esté inactiva (cargo todo)
            page.goto(url, wait_until="networkidle", timeout=60000)
            
            # Esperamos a que aparezca al menos un signo de pesos o dólar
            page.wait_for_selector("text=/$ /", timeout=20000)
            
            # Scroll suave para disparar el lazy loading de la grilla
            page.mouse.wheel(0, 1000)
            time.sleep(3) 

            content = page.content()
            precios_encontrados = re.findall(r'(?:USD|\$)\s?(\d[\d\.,]*)', content)
            
            for p_raw in precios_encontrados:
                precio = _parse_price(p_raw)
                if precio and precio > 300:
                    if max_price == 0 or precio <= max_price:
                        mejores_ofertas.append({
                            "title": "Vuelo detectado en Calendario",
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

def hunt_despegar_vuelos(url, keyword="", max_price=0, es_pro=False, headless=True, user_agent=None, **kwargs):
    url_l = url.lower()
    kw_l = str(keyword or "").lower().strip()
    
    destinos_dict = {
        "barcelona": "BCN", "madrid": "MAD", "miami": "MIA", 
        "roma": "FCO", "cancun": "CUN", "rio": "GIG"
    }
    iata_esperado = destinos_dict.get(kw_l, kw_l.upper() if len(kw_l) == 3 else "")

    iata_url = ""
    deep_match = re.search(r'/(?P<orig>[a-z]{3})/(?P<dest>[a-z]{3})(?:/|\?|$)', url_l)
    if deep_match:
        iata_url = deep_match.group("dest").upper()

    alerta_match = ""
    if iata_url and iata_esperado and iata_url != iata_esperado:
        alerta_match = f"⚠️ (Link a {iata_url}, no {iata_esperado})"

    # --- MODO MENSUAL (PRO) ---
    if es_pro and ("flexible" in url_l or "calendar" in url_l or "vuelos-a-" in url_l):
        return _scrape_monthly_matrix(url, max_price)

    # --- PRIORIDAD URL / API ---
    destino_final = iata_url or iata_esperado
    
    if destino_final and len(destino_final) == 3:
        res = hunt_vuelos_api(destino_final, max_price, url=url)
        for r in res:
            r["title"] = f"{r['title']} {alerta_match}".strip()
        return res
    
    # --- SCRAPER FALLBACK ---
    print(f"🕵️ Iniciando Scraper de respaldo...")
    presas = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=60000)
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