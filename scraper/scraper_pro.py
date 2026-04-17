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


    # --- CONFIGURACIÓN INICIAL ---
    max_price_i = int(max_price or 0)
    presas: list[dict] = []
    api_key = os.getenv("SCRAPERAPI_KEY")
    ua_final = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

    # =========================================================
    # RUTA C: DESPEGAR (LOW-RAM MODE)
    # =========================================================
    if url_input and "despegar.com" in url_input:
        print(f"✈️ Olfateando Despegar (Ahorro RAM): {url_input}")
        if not api_key: return []
        
        # Despegar requiere Render + Premium + IP Argentina
        proxy_url = f"http://api.scraperapi.com?api_key={api_key}&url={url_input}&render=true&premium=true&country_code=ar"
        try:
            resp = requests.get(proxy_url, timeout=90)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                price_tag = soup.select_one(".price-amount, .amount, .item-fare, .sub-amount")
                precio = None
                if price_tag:
                    raw_p = price_tag.get_text().replace(".","").replace(",","").replace("$","").strip()
                    precio = int(''.join(filter(str.isdigit, raw_p)))
                else:
                    match = re.search(r'\"amount\":\s*(\d+)', resp.text)
                    if match: precio = int(match.group(1))

                if precio:
                    print(f"✅ Vuelo encontrado: ${precio}")
                    return [{"title": "Vuelo Despegar", "price": precio, "url": url_input, "source": "despegar"}]
        except Exception as e:
            print(f"❌ Error en Despegar: {e}")
        return []

    # =========================================================
    # RUTA A y B: MERCADO LIBRE (MODO HÍBRIDO INTELIGENTE)
    # =========================================================
    target = url_input if (url_input and "http" in url_input) else f"https://listado.mercadolibre.com.ar/{(keyword or '').strip().replace(' ', '-')}"
    
    # 1. INTENTO CON REQUESTS (PARA NO USAR RAM DE CHROME)
    if api_key:
        print(f"🐺 Olfateando ML vía API (Modo Liviano): {target}")
        # Usamos premium=true para ML también, para asegurar éxito en Render
        proxy_url = f"http://api.scraperapi.com?api_key={api_key}&url={target}&render=true&premium=true&country_code=ar"
        try:
            resp = requests.get(proxy_url, timeout=60)
            if resp.status_code == 200:
                html = resp.text
                # Extracción por Regex (Rápida y efectiva)
                match = re.search(r'\"price\":\s*(\d+)', html)
                if match:
                    precio = int(match.group(1))
                    print(f"🎯 Rescate exitoso vía API: ${precio}")
                    return [{"title": "Producto ML", "price": precio, "url": target, "source": "mercadolibre (API)"}]
                
                # Extracción por BeautifulSoup (Si el regex falla)
                soup = BeautifulSoup(html, 'html.parser')
                p_tag = soup.select_one(".andes-money-amount__fraction")
                if p_tag:
                    precio = int(p_tag.get_text().replace(".","").replace(",","").strip())
                    return [{"title": "Producto ML", "price": precio, "url": target, "source": "mercadolibre (API)"}]
        except:
            print("⚠️ API falló o timeout. Saltando a Playwright...")

    # 2. ÚLTIMO RECURSO: PLAYWRIGHT (SOLO SI LO ANTERIOR FALLA)
    # Ponemos todo en un bloque try/finally para cerrar el browser sí o sí
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = None
        try:
            print("🚀 Abriendo Chrome (Último recurso, cuidado RAM)...")
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage", "--single-process"])
            context = browser.new_context(viewport={"width": 800, "height": 600}, user_agent=ua_final)
            page = context.new_page()
            
            # Bloqueamos basura para no saturar los 512MB
            page.route("**/*.{png,jpg,jpeg,gif,webp,svg,css,woff,ttf}", lambda route: route.abort())
            
            page.goto(target, wait_until="domcontentloaded", timeout=30000)
            
            # Intento de captura rápida
            p_meta = page.locator('meta[itemprop="price"]').get_attribute("content", timeout=5000)
            if p_meta:
                precio = int(float(p_meta))
                presas.append({"title": "Producto ML", "price": precio, "url": target, "source": "mercadolibre"})
        except Exception as e:
            print(f"❌ Playwright también falló: {e}")
        finally:
            if browser:
                browser.close()
                print("🛑 Chrome cerrado.")

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