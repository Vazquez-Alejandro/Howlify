from __future__ import annotations

import os
import random
import re
import time
import requests
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime 
from pathlib import Path
from playwright.sync_api import sync_playwright
import playwright_stealth
from bs4 import BeautifulSoup

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
# Scraper Pro: Despegar (Ruta C) + MercadoLibre (Ruta A y B)
# -------------------------------------------------
def _scrape_mercadolibre(url_input: str, keyword: str, max_price: int, *, headless: bool, plan: str = "starter", user_agent: str = None) -> list[dict]:
    import requests
    import re
    import os
    from bs4 import BeautifulSoup

    # 1. Definición de variables base
    max_price_i = int(max_price or 0)
    presas: list[dict] = []
    api_key = os.getenv("SCRAPERAPI_KEY")
    ua_final = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

    # =========================================================
    # RUTA C: DESPEGAR (ULTRA-RESIDENCIAL) - EVALUAR PRIMERO
    # =========================================================
    if url_input and "despegar.com" in url_input:
        print(f"✈️ Olfateando Vuelo en Despegar: {url_input}")
        if api_key:
            # Despegar SIEMPRE requiere Premium + Render + IP Argentina
            proxy_url = f"http://api.scraperapi.com?api_key={api_key}&url={url_input}&render=true&premium=true&country_code=ar"
            try:
                resp = requests.get(proxy_url, timeout=90)
                if resp.status_code == 200:
                    html = resp.text
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Intento 1: Selectores de Despegar
                    price_tag = soup.select_one(".price-amount, .amount, .item-fare")
                    precio = None
                    if price_tag:
                        raw_p = price_tag.get_text().replace(".","").replace(",","").replace("$","").strip()
                        precio = int(''.join(filter(str.isdigit, raw_p)))
                    else:
                        # Intento 2: Regex por si cargó el JSON pero no el DOM
                        match = re.search(r'\"amount\":\s*(\d+)', html)
                        if match: precio = int(match.group(1))

                    if precio:
                        print(f"🎯 ¡Vuelo encontrado! Precio: ${precio}")
                        return [{
                            "title": "Vuelo (Despegar)", "price": precio,
                            "url": url_input, "source": "despegar"
                        }]
                else:
                    print(f"❌ Despegar rechazó la conexión. Status: {resp.status_code}")
            except Exception as e:
                print(f"❌ Error en Ruta C (Despegar): {e}")
        return []

    # --- VALIDACIÓN SOLO PARA MERCADO LIBRE SI NO ES DESPEGAR ---
    if url_input and url_input.startswith("http") and not _is_mercadolibre(url_input):
        raise ValueError(f"[ML] URL no reconocida: {url_input}")

    es_producto_directo = bool(url_input and url_input.startswith("http") and "listado." not in url_input)

    # =========================================================
    # RUTA A: LINK DIRECTO (ML)
    # =========================================================
    if es_producto_directo:
        print(f"🐺 [ML] Ruta A (Directo): {url_input}")
        with sync_playwright() as p:
            context = None
            try:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=str(PROFILE_PATH), headless=headless, channel="chrome", user_agent=ua_final,
                    args=["--no-sandbox", "--disable-dev-shm-usage"]
                )
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(url_input, wait_until="domcontentloaded", timeout=20000)
                p_meta = page.locator('meta[itemprop="price"]').get_attribute("content", timeout=7000)
                if p_meta:
                    precio = int(float(p_meta))
                    t_loc = page.locator(".ui-pdp-title").first
                    title = t_loc.inner_text() if t_loc.count() > 0 else "Producto ML"
                    presas.append({"title": title[:120], "price": precio, "url": url_input, "source": "mercadolibre"})
            except:
                print("⚠️ Playwright bloqueado en ML Ruta A. Activando Plan B...")
            finally:
                if context: context.close()

        # Plan B ML Directo (Residencial)
        if not presas and api_key:
            proxy_url = f"http://api.scraperapi.com?api_key={api_key}&url={url_input}&render=true&premium=true&country_code=ar"
            try:
                resp = requests.get(proxy_url, timeout=60)
                if resp.status_code == 200:
                    html = resp.text
                    match = re.search(r'\"price\":\s*(\d+)', html)
                    precio = int(match.group(1)) if match else None
                    if precio:
                        presas.append({"title": "Producto Rescatado", "price": precio, "url": url_input, "source": "mercadolibre (Tunnel)"})
            except: pass
        return presas

    # =========================================================
    # RUTA B: BÚSQUEDA / LISTADO (ML)
    # =========================================================
    target_url = url_input if (url_input and "listado." in url_input) else f"https://listado.mercadolibre.com.ar/{(keyword or '').strip().replace(' ', '-')}"
    print(f"🐺 [ML] Ruta B (Listado): {target_url}")

    with sync_playwright() as p:
        context = None
        try:
            context = p.chromium.launch_persistent_context(user_data_dir=str(PROFILE_PATH), headless=headless, channel="chrome", args=["--no-sandbox"])
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(target_url, wait_until="networkidle", timeout=30000)
            cards = page.locator(".ui-search-result__wrapper, .andes-card, .poly-card")
            for i in range(min(cards.count(), 10)):
                try:
                    card = cards.nth(i)
                    p_raw = card.locator(".andes-money-amount__fraction").first.inner_text()
                    precio = int(p_raw.replace(".","").replace(",","").strip())
                    link = card.locator("a").first.get_attribute("href")
                    if link and link.startswith("/"): link = "https://www.mercadolibre.com.ar" + link
                    if max_price_i == 0 or precio <= max_price_i:
                        presas.append({"title": "Resultado ML", "price": precio, "url": link or target_url, "source": "mercadolibre"})
                except: continue
        except:
            print("⚠️ Playwright bloqueado en ML Ruta B. Activando Plan B...")
        finally:
            if context: context.close()

    if not presas and api_key:
        proxy_url = f"http://api.scraperapi.com?api_key={api_key}&url={target_url}&country_code=ar"
        try:
            resp = requests.get(proxy_url, timeout=45)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                items = soup.select(".ui-search-result__wrapper, .andes-card, .poly-card")
                for item in items[:10]:
                    try:
                        p_raw = item.select_one(".andes-money-amount__fraction").get_text()
                        price = int(p_raw.replace(".","").replace(",",""))
                        link = item.select_one("a")["href"]
                        if link.startswith("/"): link = "https://www.mercadolibre.com.ar" + link
                        presas.append({"title": "Resultado (Tunnel)", "price": price, "url": link, "source": "mercadolibre (Tunnel)"})
                    except: continue
        except: pass

    return presas
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
        
        # 🔥 Definimos el plan para la lógica de negocio
        plan_final = plan if plan else ("pro" if es_pro else "starter")
        
        # --- 🐺 MEJORA DE EXTRACCIÓN (FIX TIMEOUT ID 90) ---
        # Ejecutamos el scrape enviando el timeout reducido para el primer intento
        res = _scrape_mercadolibre(
            url, 
            keyword, 
            max_price, 
            headless=headless, 
            plan=plan_final,   
            user_agent=disfraz 
        )

        # Si el resultado viene vacío o falló por timeout, el Worker ya no se clava.
        if res and isinstance(res[0], dict) and res[0].get("blocked"):
            print("🛡️ El Lobo fue detectado. Intentando camuflaje más profundo...")
            return []
            
        return res

    # 5. Todo lo demás
    print("🌐 Usando buscador genérico...")
    return []