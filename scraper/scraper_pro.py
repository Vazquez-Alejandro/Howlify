from __future__ import annotations

import os
import re
import time
import requests
from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from .despegar import hunt_despegar_vuelos
from utils.logic import get_random_user_agent, apply_human_jitter
from utils.proxy import requests_get, fetch_via_scraperapi
from utils.cache import cached, set_cache, cache_key

BASE_DIR = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = Path("evidence")
EVIDENCE_PATH.mkdir(parents=True, exist_ok=True)

# Playwright solo si se fuerza con env var
OH_PLAYWRIGHT = os.getenv("OH_PLAYWRIGHT", "0") == "1"


def _domain(url: str) -> str:
    try:
        host = urlparse(str(url)).netloc.lower().strip()
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return ""


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


def _scrape_mercadolibre(url_input: str, keyword: str, max_price: int) -> list[dict]:
    max_price_i = int(max_price or 0)
    target = url_input if (url_input and "http" in url_input) else f"https://listado.mercadolibre.com.ar/{(keyword or '').strip().replace(' ', '-')}"

    ck = cache_key(target, keyword, max_price_i)
    cached_res = cached(ck, ttl=300)
    if cached_res is not None:
        print(f"🔄 Cache hit para ML: {target[:50]}")
        return cached_res

    # 1. ScraperAPI
    html = fetch_via_scraperapi(target, render=True, premium=True, country="ar", timeout=60)
    if html:
        match = re.search(r'\"price\":\s*(\d+)', html)
        if match:
            precio = int(match.group(1))
            result = [{"title": "Producto ML", "price": precio, "url": target, "source": "mercadolibre (API)"}]
            set_cache(ck, result)
            return result
        soup = BeautifulSoup(html, 'html.parser')
        p_tag = soup.select_one(".andes-money-amount__fraction")
        if p_tag:
            precio = int(p_tag.get_text().replace(".", "").replace(",", "").strip())
            result = [{"title": "Producto ML", "price": precio, "url": target, "source": "mercadolibre (API)"}]
            set_cache(ck, result)
            return result

    # 2. Requests directos (con proxies gratuitos)
    resp = requests_get(target, timeout=30)
    if resp:
        match = re.search(r'\"price\":\s*(\d+)', resp.text)
        if match:
            precio = int(match.group(1))
            result = [{"title": "Producto ML", "price": precio, "url": target, "source": "mercadolibre"}]
            set_cache(ck, result)
            return result
        soup = BeautifulSoup(resp.text, 'html.parser')
        p_tag = soup.select_one(".andes-money-amount__fraction")
        if p_tag:
            precio = int(p_tag.get_text().replace(".", "").replace(",", "").strip())
            result = [{"title": "Producto ML", "price": precio, "url": target, "source": "mercadolibre"}]
            set_cache(ck, result)
            return result

    # 3. Playwright (solo si se fuerza con OH_PLAYWRIGHT=1)
    if OH_PLAYWRIGHT:
        print("🚀 Playwright forzado por env OH_PLAYWRIGHT=1...")
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage", "--single-process"])
                context = browser.new_context(viewport={"width": 800, "height": 600})
                page = context.new_page()
                page.route("**/*.{png,jpg,jpeg,gif,webp,svg,css,woff,ttf}", lambda route: route.abort())
                page.goto(target, wait_until="domcontentloaded", timeout=30000)
                p_meta = page.locator('meta[itemprop="price"]').get_attribute("content", timeout=5000)
                if p_meta:
                    precio = int(float(p_meta))
                    browser.close()
                    result = [{"title": "Producto ML", "price": precio, "url": target, "source": "mercadolibre"}]
                    set_cache(ck, result)
                    return result
                browser.close()
        except Exception as e:
            print(f"❌ Playwright falló: {e}")

    return []


def hunt_offers(url: str, keyword: str, max_price: int, es_pro: bool = False, headless: bool = True, user_id: str = None, caza_id: int = None, plan: str = 'starter'):
    disfraz = get_random_user_agent()
    apply_human_jitter()

    host = _domain(url)
    print(f"🔍 Host: {host} | URL: {url[:40]}...")

    vuelos_sites = ["despegar", "almundo", "turismocity", "avantrip", "smiles"]
    if any(site in host for site in vuelos_sites):
        return hunt_despegar_vuelos(url, keyword, max_price, es_pro=es_pro, headless=False, user_agent=disfraz)

    if "mercadolibre" in host:
        return _scrape_mercadolibre(url, keyword, max_price)

    print("🌐 Sin scraper especializado para este dominio")
    return []
