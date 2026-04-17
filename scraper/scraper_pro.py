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
# MercadoLibre scraper: Listados + Directo (Doble Capa + Diagnóstico Profundo)
# -------------------------------------------------
def _scrape_mercadolibre(url_input: str, keyword: str, max_price: int, *, headless: bool, plan: str = "starter", user_agent: str = None) -> list[dict]:

    # 1. Validaciones e inicialización
    if url_input and url_input.startswith("http") and not _is_mercadolibre(url_input):
        raise ValueError(f"[ML] URL no es MercadoLibre: {url_input}")

    max_price_i = int(max_price or 0)
    presas: list[dict] = []
    es_producto_directo = bool(url_input and url_input.startswith("http") and "listado." not in url_input)
    ua_final = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    api_key = os.getenv("SCRAPERAPI_KEY")

    # =========================================================
    # RUTA A: LINK DIRECTO
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
                print("⚠️ Playwright bloqueado en Ruta A. Activando Diagnóstico Profundo...")
            finally:
                if context: context.close()

        # --- PLAN B DE DIAGNÓSTICO (RUTA A) ---
        if not presas and api_key:
            print("🕵️ Iniciando Diagnóstico Profundo via Túnel AR...")
            proxy_url = f"http://api.scraperapi.com?api_key={api_key}&url={url_input}&render=true&country_code=ar"
            try:
                resp = requests.get(proxy_url, timeout=60)
                print(f"📡 Status de la API: {resp.status_code}")
                
                if resp.status_code == 200:
                    html = resp.text
                    precio = None
                    
                    # Diagnóstico visual rápido en logs
                    soup = BeautifulSoup(html, 'html.parser')
                    t_diag = soup.find("h1")
                    print(f"📝 Título visto por el Túnel: {t_diag.get_text(strip=True) if t_diag else 'NO ENCONTRADO'}")

                    # Intento 1: Regex sobre JSON interno (Fuerza bruta)
                    match = re.search(r'\"price\":\s*(\d+)', html)
                    if match: 
                        precio = int(match.group(1))
                        print(f"🎯 Precio hallado por Regex: {precio}")
                    
                    # Intento 2: Selectores visuales
                    if not precio:
                        p_tag = soup.select_one(".andes-money-amount__fraction, [itemprop='price']")
                        if p_tag:
                            val = p_tag.get("content") or p_tag.get_text()
                            precio = int(float(str(val).replace(".","").replace(",","").strip()))
                            print(f"🎯 Precio hallado por BeautifulSoup: {precio}")

                    if precio:
                        presas.append({
                            "title": (t_diag.get_text(strip=True) if t_diag else "Producto Rescatado")[:120],
                            "price": precio, "url": url_input, "source": "mercadolibre (Tunnel AR)"
                        })
                else:
                    print(f"❌ Error de API: {resp.status_code}. Revisar créditos en ScraperAPI.")
            except Exception as e:
                print(f"❌ Fallo crítico en el Túnel: {e}")
        return presas

    # =========================================================
    # RUTA B: BÚSQUEDA / LISTADO
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
            print("⚠️ Playwright falló en Ruta B. Activando Túnel AR...")
        finally:
            if context: context.close()

    # --- PLAN B DE DIAGNÓSTICO (RUTA B) ---
    if not presas and api_key:
        print("🕵️ Extrayendo listado vía Túnel Residencial AR...")
        proxy_url = f"http://api.scraperapi.com?api_key={api_key}&url={target_url}&country_code=ar"
        try:
            resp = requests.get(proxy_url, timeout=45)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                items = soup.select(".ui-search-result__wrapper, .andes-card, .poly-card")
                print(f"📦 Items detectados en el listado: {len(items)}")
                for item in items[:10]:
                    try:
                        p_raw = item.select_one(".andes-money-amount__fraction").get_text()
                        price = int(p_raw.replace(".","").replace(",",""))
                        link = item.select_one("a")["href"]
                        if link.startswith("/"): link = "https://www.mercadolibre.com.ar" + link
                        if max_price_i == 0 or price <= max_price_i:
                            presas.append({"title": "Resultado (Tunnel)", "price": price, "url": link, "source": "mercadolibre (via Tunnel)"})
                    except: continue
            else:
                print(f"❌ Error API en Ruta B: {resp.status_code}")
        except Exception as e:
            print(f"❌ Error en Túnel Ruta B: {e}")

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