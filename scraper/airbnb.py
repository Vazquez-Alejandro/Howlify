import re
import time
from playwright.sync_api import sync_playwright
from utils.logic import obtener_dolar_tarjeta

get_dolar_tarjeta = obtener_dolar_tarjeta

def _detect_currency(text: str, cotizacion: float) -> tuple[int, str]:
    """Detecta si el precio está en USD o ARS y convierte a ARS.
    Returns (precio_ars, moneda_detectada)."""
    price_match = re.search(r"\$\s?([\d\.,]+)", text)
    if not price_match:
        return 0, "unknown"

    raw = price_match.group(1)

    has_decimals = "," in raw and raw.split(",")[-1] in ("00", "0")
    dots = raw.count(".")

    if has_decimals and dots <= 1:
        price = int(raw.replace(".", "").replace(",", ""))
        return price, "ARS"

    clean = raw.replace(".", "").replace(",", "")
    if not clean.isdigit():
        return 0, "unknown"
    price = int(clean)

    usd_keywords = ["US$", "USD", "$US", "U$S"]
    is_usd_indicated = any(kw in text for kw in usd_keywords)

    if price < 10000 and not is_usd_indicated:
        price_ars = int(price * cotizacion)
        return price_ars, "USD"
    elif price >= 10000 and not is_usd_indicated:
        return price, "ARS"
    elif is_usd_indicated:
        return int(price * cotizacion), "USD"

    return price, "unknown"


def hunt_airbnb(url, max_price=0):
    print(f"🏠 [Airbnb] Iniciando rastreo Pro en: {url}")
    results = []
    cotizacion = get_dolar_tarjeta()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_selector("[data-testid='card-container']", timeout=30000)

            page.mouse.wheel(0, 1000)
            time.sleep(2)

            cards = page.locator("[data-testid='card-container']").all()

            for card in cards:
                text = card.inner_text().replace('\n', ' ')

                price_ars, moneda = _detect_currency(text, cotizacion)
                if price_ars <= 0:
                    continue

                if max_price == 0 or price_ars <= max_price:
                    title = text.split('$')[0].strip()[:50]
                    results.append({
                        "title": f"🏠 {title}",
                        "price": price_ars,
                        "url": url,
                        "source": "airbnb",
                        "currency_detected": moneda
                    })

        except Exception as e:
            print(f"❌ [Airbnb] Error en la cacería: {e}")
        finally:
            browser.close()

    return results