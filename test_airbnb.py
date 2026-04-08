# test_airbnb.py
from playwright.sync_api import sync_playwright
import re
import time

def test_airbnb_live(url):
    print(f"🏠 [TEST] Olfateando Airbnb en: {url}")
    
    with sync_playwright() as p:
        # Abrimos el browser para ver el proceso
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        try:

            # 1. Esperamos solo al DOM, no a que termine toda la red
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # 2. Esperamos específicamente a que aparezca una card de alojamiento
            print("⏳ Esperando a que aparezcan las propiedades...")
            page.wait_for_selector("[data-testid='card-container']", timeout=30000)
            
            # Un pequeño respiro extra para que renderice los precios
            time.sleep(3) 

            # El Lobo hace un scroll suave para cargar lazy images y precios
            page.mouse.wheel(0, 1000)
            time.sleep(2)

            # Buscamos las cards por el test-id oficial de Airbnb
            listings = page.locator("[data-testid='card-container']").all()
            
            print(f"🧐 Se detectaron {len(listings)} posibles alojamientos.")

            for i, item in enumerate(listings[:5]): # Probamos con los primeros 5
                texto = item.inner_text().replace('\n', ' | ')
                # Regex para capturar el precio (ignora puntos y comas)
                price_match = re.search(r"\$\s?([\d\.,]+)", texto)
                
                if price_match:
                    print(f"✅ {i+1}. Encontrado: {texto[:60]}... -> PRECIO: {price_match.group(0)}")
                else:
                    print(f"⚠️ {i+1}. No se pudo extraer precio de: {texto[:50]}")

        except Exception as e:
            print(f"❌ Error en el test: {e}")
        finally:
            print("\n🐺 Test finalizado. Cerrando browser...")
            browser.close()

# Probamos con una búsqueda real (Cualquier link de Airbnb sirve)
# Usé uno de Bariloche como ejemplo rápido
url_prueba = "https://www.airbnb.com.ar/s/San-Carlos-de-Bariloche--Río-Negro/homes"
test_airbnb_live(url_prueba)