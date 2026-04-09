from __future__ import annotations

import os
import random
import re
import time
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime 
from pathlib import Path
from playwright.sync_api import sync_playwright
import playwright_stealth

from .despegar import hunt_despegar_vuelos
from utils.logic import get_random_user_agent, apply_human_jitter, evaluar_oferta

# -------------------------------------------------
# Config
# -------------------------------------------------
# ML queda headful por defecto para evitar detección agresiva.
ML_FORCE_HEADLESS = os.getenv("OH_ML_HEADLESS", "") == "1"
ML_FORCE_HEADFUL = os.getenv("OH_ML_HEADLESS", "") == "0"

BASE_DIR = Path(__file__).resolve().parents[1]  # .../howlify
PROFILE_PATH = BASE_DIR / "sessions" / "ml_profile"
DEBUG_SHOT_PATH = BASE_DIR / "sessions" / "ml_debug.png"
EVIDENCE_PATH = Path("evidence")
EVIDENCE_PATH.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------
# Helpers
# -------------------------------------------------
def _domain(url: str) -> str:
    try:
        host = urlparse(str(url)).netloc.lower().strip()
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return ""


def _is_mercadolibre(url: str) -> bool:
    return "mercadolibre" in _domain(url)


def _to_int_price(text: str) -> int | None:
    if not text:
        return None

    m = re.search(r"\$\s*([\d\.\,]+)", text)
    if not m:
        return None

    raw = m.group(1).replace(".", "").replace(",", "")
    try:
        return int(raw)
    except Exception:
        return None


def _has_result_cards(page) -> bool:
    selectors = [
        "div.poly-card",
        "div.ui-search-result__wrapper",
        "li.ui-search-layout__item",
    ]
    for sel in selectors:
        try:
            if page.locator(sel).count() > 0:
                return True
        except Exception:
            pass
    return False


def _looks_like_block(html_lower: str) -> bool:
    needles = [
        "captcha",
        "recaptcha",
        "no soy un robot",
        "access denied",
        "forbidden",
        "hubo un problema al validar",
        "verifica que no seas un robot",
    ]
    return any(x in html_lower for x in needles)


def _human_touch(page) -> None:
    try:
        time.sleep(random.uniform(2.0, 4.5))
        page.mouse.move(
            random.randint(120, 500),
            random.randint(120, 500),
            steps=random.randint(12, 25),
        )
        time.sleep(random.uniform(0.3, 1.1))
        page.mouse.wheel(0, random.randint(400, 1400))
        time.sleep(random.uniform(0.7, 1.6))
    except Exception:
        pass


def _looks_like_noise_title(title_l: str) -> bool:
    if not title_l:
        return True

    exact_noise = {
        "apple tienda oficial",
        "tienda oficial",
        "patrocinado",
        "más vendido",
        "oferta imperdible",
    }
    if title_l in exact_noise:
        return True

    bad_fragments = [
        "disponible en",
        "colores",
        "envío gratis",
        "llega gratis",
        "cuotas sin interés",
        "mismo precio en",
    ]
    return any(frag in title_l for frag in bad_fragments)


def _keyword_match(title_l: str, keyword: str) -> bool:
    tokens = [t.strip().lower() for t in str(keyword or "").split() if t.strip()]
    if not tokens:
        return True

    match_count = sum(1 for tok in tokens if tok in title_l)
    return match_count > 0
# -------------------------------------------------
# MercadoLibre scraper: Listados (Persistente) + Directo (Multi-Disfraz)
# -------------------------------------------------
def _scrape_mercadolibre(url_input: str, keyword: str, max_price: int, *, headless: bool, plan: str = "starter", user_agent: str = None) -> list[dict]:
    if url_input and url_input.startswith("http") and not _is_mercadolibre(url_input):
        raise ValueError(f"[ML] URL no es MercadoLibre: {url_input}")

    max_price_i = int(max_price or 0)
    presas: list[dict] = []
    
    # 🔥 DEFINIMOS ES_PRO ACÁ PARA QUE TODO EL MUNDO LA CONOZCA
    es_pro = plan.lower() in ["pro", "business", "business_monitor", "business_reseller"]

# =========================================================
    # RUTA A: LINK DIRECTO (CON DISFRAZ NINJA Y PERSISTENCIA)
    # =========================================================
    es_producto_directo = bool(url_input and url_input.startswith("http") and "listado." not in url_input)
    
    if es_producto_directo:
        # 🎭 1. IDENTIDAD Y PERFIL
        ua_final = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        print(f"🐺 [ML] Link directo ROBUSTO. Plan: {plan.upper()} | Usando Sesión + Stealth...")
        
        PROFILE_PATH.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as p:
            try:
                # Lanzamos el contexto persistente para guardar el login para siempre
                context = p.chromium.launch_persistent_context(
                    user_data_dir=str(PROFILE_PATH),
                    headless=headless,
                    channel="chrome", 
                    user_agent=ua_final,
                    viewport={"width": 1280, "height": 720},
                    args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"]
                )
                
                page = context.pages[0] if context.pages else context.new_page()
                
                # 🐺 CAPA DE CAMUFLAJE
                try:
                    if hasattr(playwright_stealth, 'stealth_sync'):
                        playwright_stealth.stealth_sync(page)
                    elif hasattr(playwright_stealth, 'stealth_page_sync'):
                        playwright_stealth.stealth_page_sync(page)
                except Exception as e:
                    print(f"⚠️ Aviso: No se pudo aplicar camuflaje ({e}), siguiendo igual...")
                
                # 🕒 2. PAUSA HUMANA
                time.sleep(random.uniform(2.0, 4.0))

                # Navegación
                page.goto(url_input, wait_until="domcontentloaded", timeout=60000)
                
                # 🛡️ GESTIÓN DE LOGIN MANUAL (EL PARACAÍDAS)
                # Si detecta login y NO estás en headless, te espera 2 minutos
                if "login" in page.url.lower() or "challenge" in page.url.lower():
                    print("⚠️ BLOQUEO: ML pide Login/QR. ¡Tenés 2 minutos para loguearte en la ventana!")
                    if not headless:
                        try:
                            # Espera a que la URL deje de decir "login" o "challenge"
                            page.wait_for_url(lambda url: "login" not in url.lower() and "challenge" not in url.lower(), timeout=120000)
                            print("✅ ¡Login exitoso! Guardando sesión y continuando...")
                            # Re-navegamos al producto por las dudas
                            page.goto(url_input, wait_until="domcontentloaded", timeout=60000)
                        except:
                            print("❌ Se acabó el tiempo. No se detectó el login manual.")
                            return []
                    else:
                        print("❌ Error: ML pide login y estás en modo invisible. Cambiá FORCE_HEADLESS a False.")
                        context.close()
                        return []

                # 🔍 3. EXTRACCIÓN ELÁSTICA
                precio = None
                try:
                    page.wait_for_selector('.andes-money-amount__fraction', timeout=10000)
                except: pass

                # Intento 1: Meta
                meta_p = page.locator('meta[itemprop="price"]').get_attribute("content")
                if meta_p:
                    try: precio = int(float(meta_p))
                    except: pass

                # Intento 2: Selectores visuales
                if not precio:
                    p_loc = page.locator('.ui-pdp-price__second-line .andes-money-amount__fraction, .ui-pdp-price .andes-money-amount__fraction').first
                    if p_loc.count() > 0:
                        raw = (p_loc.inner_text() or "").replace(".", "").replace(",", "")
                        if raw.isdigit(): precio = int(raw)

                # 4. RESULTADOS Y EVIDENCIA
                if precio:
                    title_loc = page.locator(".ui-pdp-title").first
                    title = title_loc.inner_text() if title_loc.count() > 0 else "Producto ML"
                    
                    foto_path = None
                    if es_pro:
                        try:
                            base_path = os.path.abspath("evidence")
                            os.makedirs(base_path, exist_ok=True)
                            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filename = f"directo_{ts}.png"
                            full_path = os.path.join(base_path, filename)
                            page.evaluate("window.scrollTo(0, 0)")
                            time.sleep(1.0) 
                            page.screenshot(path=full_path)
                            foto_path = full_path if os.path.exists(full_path) else None
                        except: pass

                    if max_price_i == 0 or precio <= max_price_i:
                        presas.append({
                            "title": title[:120],
                            "price": precio,
                            "url": url_input,
                            "source": "mercadolibre",
                            "screenshot": foto_path
                        })
                else:
                    print(f"🛡️ No se detectó precio en: {page.url}")

            except Exception as e:
                print(f"❌ Error crítico en cacería: {e}")
            finally:
                context.close()
        
        return presas
    
    # =========================================================
    # RUTA B: BÚSQUEDA POR KEYWORD O LISTADO
    # =========================================================
    target_url = url_input if (url_input and "listado." in url_input) else f"https://listado.mercadolibre.com.ar/{(keyword or '').strip().replace(' ', '-')}"

    PROFILE_PATH.mkdir(parents=True, exist_ok=True)
    DEBUG_SHOT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # FIX: Volvemos al context manager estándar de Playwright
    with sync_playwright() as p:
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(PROFILE_PATH),
                headless=headless,
                channel="chrome",
                locale="es-AR",
                viewport={"width": 1365, "height": 900},
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            )
            page = context.pages[0] if context.pages else context.new_page()

            # 🐺 CAPA DE CAMUFLAJE (A prueba de errores de versión)
            try:
                if hasattr(playwright_stealth, 'stealth_sync'):
                    playwright_stealth.stealth_sync(page)
                elif hasattr(playwright_stealth, 'stealth_page_sync'):
                    playwright_stealth.stealth_page_sync(page)
            except Exception as e:
                print(f"⚠️ Aviso: No se pudo aplicar camuflaje en Ruta B ({e}), siguiendo...")

            page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
            _human_touch(page)

            # Esperamos las cards
            try:
                page.wait_for_selector("div.poly-card, .ui-search-result__wrapper", timeout=15000)
                cards = page.locator("div.poly-card, .ui-search-result__wrapper")
            except:
                context.close()
                return []

            n = min(cards.count(), 20)

            for i in range(n):
                try:
                    card = cards.nth(i)
                    
                    # 🔗 Link
                    link = None
                    a_tag = card.locator("a").first
                    if a_tag.count() > 0:
                        link = a_tag.get_attribute("href")
                        if link and link.startswith("/"): 
                            link = "https://www.mercadolibre.com.ar" + link
                    
                    # 🏷️ Título
                    title = (card.locator("h2").first.inner_text() or "Producto").strip()
                    
                    # 💰 Precio
                    precio = None
                    ploc = card.locator("span.andes-money-amount__fraction").first
                    if ploc.count() > 0:
                        raw = (ploc.inner_text() or "").replace(".", "").replace(",", "")
                        if raw.isdigit(): precio = int(raw)

                    if not precio or (max_price_i > 0 and precio > max_price_i):
                        continue

                    # 📸 Screenshot (Solo si es PRO)
                    foto_path = None
                    if es_pro:
                        try:
                            Path("evidence").mkdir(parents=True, exist_ok=True)
                            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                            foto_path = f"evidence/evidencia_{i}_{ts}.png"
                            card.screenshot(path=foto_path)
                        except: pass

                    presas.append({
                        "title": title[:120],
                        "price": precio,
                        "url": link or target_url,
                        "source": "mercadolibre",
                        "screenshot": foto_path
                    })
                except: continue

            return presas
        except Exception as e:
            print(f"❌ Error en Ruta B: {e}")
            return []
        finally:
            context.close()
# -------------------------------------------------
# Router central (VERSIÓN NINJA DEFINITIVA)
# -------------------------------------------------

def hunt_offers(url: str, keyword: str, max_price: int, es_pro: bool = False, headless: bool = True, user_id: str = None, caza_id: int = None, plan: str = 'starter'):
    # 1. GENERAMOS LA IDENTIDAD NINJA
    disfraz = get_random_user_agent()
    # Asegurate de tener importado 'apply_human_jitter'
    delay = apply_human_jitter() 
    
    url_low = url.lower()
    host = _domain(url).lower() if '_domain' in locals() or '_domain' in globals() else urlparse(url).netloc
    
    # 2. LOGS DE COMBATE
    print(f"🔍 DEBUG: Host: {host} | URL: {url_low[:40]}... | Headless: {headless}")
    print(f"🕵️‍♂️ LOBO CAMALEÓN: Usando {disfraz[:40]}... | Pausa: {delay:.2f}s")

    # 3. Vuelos (Almundo / Despegar / etc)
    vuelos_sites = ["despegar", "almundo", "turismocity", "avantrip", "smiles"]
    
    if any(site in host for site in vuelos_sites):
        print(f"✈️ ¡MATCH VUELOS! Derivando a hunt_despegar_vuelos...")
        return hunt_despegar_vuelos(
            url, 
            keyword, 
            max_price, 
            es_pro=es_pro, 
            headless=False,
            user_agent=disfraz
        )

    # 4. Mercado Libre
    if "mercadolibre" in host:
        print(f"🛒 MATCH ML detectado (Headless: {headless})...")
        
        # 🔥 ACÁ ESTÁ EL CAMBIO: Usamos el plan que llega por parámetro
        # Si no llega nada, usamos 'pro' si es_pro es True, sino 'starter'
        plan_final = plan if plan else ("pro" if es_pro else "starter")
        
        # Ejecutamos pasando el plan a la función interna
        res = _scrape_mercadolibre(
            url, 
            keyword, 
            max_price, 
            headless=headless, # Usamos el headless que viene por parámetro
            plan=plan_final,   # <--- Ahora sí acepta el argumento 'plan'
            user_agent=disfraz 
        )
        
        if res and isinstance(res[0], dict) and res[0].get("blocked"):
            print("🛡️ El Lobo fue detectado. Intentando camuflaje más profundo...")
            return []
        return res

    # 5. Todo lo demás
    print("🌐 Usando buscador genérico...")
    return []