from __future__ import annotations

import os
import random
import re
import time
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

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
# 🔥 Agregamos 'user_agent' al final para que el disfraz sea real
def _scrape_mercadolibre(url_input: str, keyword: str, max_price: int, *, headless: bool, plan: str = "starter", user_agent: str = None) -> list[dict]:
    if url_input and url_input.startswith("http") and not _is_mercadolibre(url_input):
        raise ValueError(f"[ML] URL no es MercadoLibre: {url_input}")

    max_price_i = int(max_price or 0)
    presas: list[dict] = []

    # =========================================================
    # RUTA A: LINK DIRECTO (CON DISFRAZ DINÁMICO) - REFORZADA
    # =========================================================
    es_producto_directo = bool(url_input and url_input.startswith("http") and "listado." not in url_input)
    
    if es_producto_directo:
        ua_final = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        print(f"🐺 [ML] Link directo. Plan: {plan.upper()} | Disfraz: {ua_final[:40]}...")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False, # Lo dejamos en False para que veas si ML te tira un Captcha
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
            )
            
            contextos = {}
            contextos["Disfraz Lobo"] = browser.new_context(
                user_agent=ua_final,
                viewport={"width": 1280, "height": 720}
            )
            
            resultados_temporales = []
            
            for nombre_disfraz, ctx in contextos.items():
                ctx.add_init_script('''
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                ''')
                page = ctx.new_page()
                page.set_default_timeout(45000)
                
                try:
                    page.goto(url_input, wait_until="domcontentloaded", timeout=45000)
                    
                    # 1. SELECTOR MULTICAPA (Inyectamos meta y data-testid)
                    selector_precio = 'meta[itemprop="price"], .ui-pdp-price__second-line .andes-money-amount__fraction, .ui-pdp-price .andes-money-amount__fraction, [data-testid="price-part"] .andes-money-amount__fraction'
                    
                    try:
                        page.wait_for_selector(selector_precio, timeout=12000)
                    except:
                        print("⚠️ El Lobo no detectó el selector de precio visual, intentando vía Meta...")

                    # 2. EXTRACCIÓN LÓGICA (Primero Meta, después DOM)
                    precio = None
                    
                    # Intento A: Meta Tag (El más robusto para catálogo/UP)
                    meta_p = page.locator('meta[itemprop="price"]').get_attribute("content")
                    if meta_p:
                        try:
                            precio = int(float(meta_p))
                            print(f"✅ Precio capturado vía Meta: ${precio}")
                        except: pass

                    # Intento B: Si el Meta falló, buscamos en el DOM visual
                    if not precio:
                        precio_loc = page.locator('.ui-pdp-price__second-line .andes-money-amount__fraction, .ui-pdp-price .andes-money-amount__fraction, [data-testid="price-part"] .andes-money-amount__fraction').first
                        if precio_loc.count() > 0:
                            raw = (precio_loc.inner_text() or "").replace(".", "").replace(",", "")
                            if raw.isdigit():
                                precio = int(raw)
                                print(f"✅ Precio capturado vía DOM: ${precio}")
                    
                    if not precio:
                        print("❌ El Lobo no pudo morder el precio. Posible bloqueo o cambio de diseño.")
                        continue
                        
                    # 3. ESCUDO ANTI-CHANTAS
                    alerta = None
                    if plan in ["pro", "business"]:
                        seller_info = page.locator(".ui-pdp-seller-profile__title, .ui-seller-info, .ui-pdp-seller-profile__subtitle").first
                        if seller_info.count() > 0:
                            seller_text = seller_info.inner_text().lower()
                            if "demora en entregar" in seller_text or "no brinda buena" in seller_text:
                                alerta = "🚩 RED FLAG: Vendedor con mala reputación."
                            elif "mercadolíder" not in seller_text and "nuevo" in seller_text:
                                alerta = "⚠️ CUIDADO: Vendedor nuevo sin historial."
                            
                    title_loc = page.locator(".ui-pdp-title").first
                    title = title_loc.inner_text() if title_loc.count() > 0 else "Producto ML"

                    if max_price_i == 0 or precio <= max_price_i:
                        resultados_temporales.append({
                            "title": title[:120],
                            "price": precio,
                            "url": url_input,
                            "source": "mercadolibre",
                            "alerta": alerta,
                            "disfraz_usado": nombre_disfraz
                        })
                        
                except Exception as e:
                    print(f"❌ Error en cacería: {e}")
                finally:
                    page.close()
            
            browser.close()
            
            if resultados_temporales:
                mejor = sorted(resultados_temporales, key=lambda x: x["price"])[0]
                print(f"🐺 🏆 Caza confirmada a ${mejor['price']}")
                presas.append(mejor)
                
        return presas

    # =========================================================
    # RUTA B: ES UNA BÚSQUEDA POR KEYWORD O LINK DE LISTADO
    # =========================================================
    if url_input and "listado." in url_input:
        print("🐺 [ML] Link de Listado detectado. Usando Perfil Persistente...")
        target_url = url_input
    else:
        print("🐺 [ML] Búsqueda por Keyword detectada. Usando Perfil Persistente...")
        slug = (keyword or "").strip().replace(" ", "-")
        target_url = f"https://listado.mercadolibre.com.ar/{slug}"

    PROFILE_PATH.mkdir(parents=True, exist_ok=True)
    DEBUG_SHOT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_PATH),
            headless=False,
            channel="chrome",
            locale="es-AR",
            viewport={"width": 1365, "height": 900},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )

        context.add_init_script(
            '''
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'languages', { get: () => ['es-AR', 'es', 'en-US', 'en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            window.chrome = window.chrome || { runtime: {} };
            '''
        )

        page = context.pages[0] if context.pages else context.new_page()
        page.set_default_timeout(60000)

        try:
            page.goto(target_url, wait_until="domcontentloaded", timeout=60000)

            if not headless:
                try:
                    page.bring_to_front()
                except Exception:
                    pass

            _human_touch(page)

            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass

            # PRIMERO: si ya hay cards, NO es bloqueo
            if not _has_result_cards(page):
                html_lower = ""
                try:
                    html_lower = page.content().lower()
                except Exception:
                    pass

                if html_lower and _looks_like_block(html_lower):
                    if headless:
                        return [{"source": "mercadolibre", "blocked": True, "url": target_url}]

                    try:
                        page.bring_to_front()
                    except Exception:
                        pass

                    try:
                        page.wait_for_selector(
                            "div.poly-card, div.ui-search-result__wrapper, li.ui-search-layout__item",
                            timeout=75000,
                        )
                    except Exception:
                        pass

                    _human_touch(page)

                    if not _has_result_cards(page):
                        try:
                            html_lower = page.content().lower()
                        except Exception:
                            html_lower = ""

                        if html_lower and _looks_like_block(html_lower):
                            try:
                                page.screenshot(path=str(DEBUG_SHOT_PATH), full_page=True)
                            except Exception:
                                pass
                            return [{"source": "mercadolibre", "blocked": True, "url": target_url}]

            try:
                page.wait_for_selector(
                    "div.poly-card, div.ui-search-result__wrapper, li.ui-search-layout__item",
                    timeout=15000,
                )
                cards = page.locator(
                    "div.poly-card, div.ui-search-result__wrapper, li.ui-search-layout__item"
                )
            except Exception:
                try:
                    page.screenshot(path=str(DEBUG_SHOT_PATH), full_page=True)
                except Exception:
                    pass
                return []

            _human_touch(page)

            count_cards = cards.count()
            if count_cards == 0:
                try:
                    page.screenshot(path=str(DEBUG_SHOT_PATH), full_page=True)
                except Exception:
                    pass
                return []

            n = min(count_cards, 120)
            seen_keys = set()

            for i in range(n):
                try:
                    card = cards.nth(i)

                    link = None
                    a = card.locator("a.ui-search-link").first
                    if a.count() == 0:
                        a = card.locator("a").first
                    if a.count() > 0:
                        link = a.get_attribute("href")
                        if link and link.startswith("/"):
                            link = "https://www.mercadolibre.com.ar" + link

                    title = ""

                    for sel in [
                        "h2.ui-search-item__title",
                        "span.poly-component__title",
                        "a.ui-search-link",
                        "h2",
                    ]:
                        try:
                            loc = card.locator(sel).first
                            if loc.count() == 0:
                                continue

                            txt = (loc.inner_text() or "").strip()
                            if not txt:
                                continue

                            txt_l = txt.lower().strip()
                            if _looks_like_noise_title(txt_l):
                                continue

                            title = txt
                            break
                        except Exception:
                            continue

                    if not title:
                        txt = (card.inner_text() or "").strip()
                        lines = [x.strip() for x in txt.split("\n") if x.strip()]
                        for ln in lines:
                            ln_l = ln.lower().strip()
                            if _looks_like_noise_title(ln_l):
                                continue

                            if "$" in ln and len(ln.strip()) < 12:
                                continue

                            title = ln
                            break

                    if not title:
                        continue

                    title_l = title.lower().strip()

                    if _looks_like_noise_title(title_l):
                        continue

                    if keyword and not _keyword_match(title_l, keyword):
                        continue

                    precio = None
                    ploc = card.locator(
                        "span.andes-money-amount__fraction, span.price-tag-fraction"
                    ).first
                    if ploc.count() > 0:
                        raw = (ploc.inner_text() or "").strip().replace(".", "").replace(",", "")
                        if raw.isdigit():
                            precio = int(raw)

                    if precio is None:
                        precio = _to_int_price(card.inner_text() or "")

                    if precio is None:
                        continue

                    if max_price_i > 0 and int(precio) > max_price_i:
                        continue

                    key = ((link or target_url).strip(), int(precio))
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)

                    presas.append(
                        {
                            "title": title[:120],
                            "price": int(precio),
                            "url": link or target_url,
                            "source": "mercadolibre",
                        }
                    )
                except Exception:
                    continue

            return presas

        finally:
            try:
                context.close()
            except Exception:
                pass
# -------------------------------------------------
# Router central (VERSIÓN NINJA DEFINITIVA)
# -------------------------------------------------

def hunt_offers(url: str, keyword: str, max_price: int, es_pro: bool = False, headless: bool = True, user_id: str = None, caza_id: int = None):
    # 1. GENERAMOS LA IDENTIDAD NINJA
    disfraz = get_random_user_agent()
    delay = apply_human_jitter() # Esto ya hace el time.sleep() internamente
    
    url_low = url.lower()
    host = _domain(url).lower()
    
    # 2. LOGS DE COMBATE (Para que veas la rotación en la terminal)
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
            user_agent=disfraz # <--- Pasamos el disfraz al scraper de vuelos
        )

    # 4. Mercado Libre
    if "mercadolibre" in host:
        print(f"🛒 MATCH ML detectado (Headless: {headless})...")
        plan_str = "pro" if es_pro else "starter"
        
        # Ejecutamos con el disfraz y el modo que nos mandaron
        res = _scrape_mercadolibre(
            url, 
            keyword, 
            max_price, 
            headless=False, 
            plan=plan_str,
            user_agent=disfraz # <--- Pasamos el disfraz al scraper de ML
        )
        
        if res and isinstance(res[0], dict) and res[0].get("blocked"):
            print("🛡️ El Lobo fue detectado. Intentando camuflaje más profundo...")
            return []
        return res

    # 5. Todo lo demás
    print("🌐 Usando buscador genérico...")
    return []