import re
import time
from playwright.sync_api import sync_playwright
from utils.currency import get_dolar_tarjeta

def hunt_airbnb(url, max_price=0):
    print(f"🏠 [Airbnb] Iniciando rastreo Pro en: {url}")
    results = []
    cotizacion = get_dolar_tarjeta()
    
    with sync_playwright() as p:
        # Headless=True para que corra de fondo sin molestar
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_selector("[data-testid='card-container']", timeout=30000)
            
            # Scroll para cargar precios dinámicos
            page.mouse.wheel(0, 1000)
            time.sleep(2)

            cards = page.locator("[data-testid='card-container']").all()
            
            for card in cards:
                text = card.inner_text().replace('\n', ' ')
                # Buscamos el precio (asumiendo que viene con $)
                price_match = re.search(r"\$\s?([\d\.,]+)", text)
                
                if price_match:
                    # Limpiamos el precio y convertimos
                    p_clean = int(price_match.group(1).replace(".", "").replace(",", ""))
                    
                    # OJO: Si Airbnb te da USD, multiplicamos. 
                    # Si detectás que ya está en ARS, podrías poner un IF.
                    price_ars = int(p_clean * cotizacion) if p_clean < 10000 else p_clean
                    
                    if max_price == 0 or price_ars <= max_price:
                        # Sacamos un título digno (primeras palabras antes del precio)
                        title = text.split('$')[0].strip()[:50]
                        results.append({
                            "title": f"🏠 {title}",
                            "price": price_ars,
                            "url": url,
                            "source": "airbnb"
                        })

        except Exception as e:
            print(f"❌ [Airbnb] Error en la cacería: {e}")
        finally:
            browser.close()
            
    return results