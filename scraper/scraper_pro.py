from __future__ import annotations

import os
import re
import time
import random
from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from .despegar import hunt_despegar_vuelos
from .generic import hunt_generic, extract_price_from_text
from utils.logic import get_random_user_agent, apply_human_jitter
from utils.logger import get_logger
logger = get_logger("scraper")


BASE_DIR = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = BASE_DIR / "evidence"
EVIDENCE_PATH.mkdir(parents=True, exist_ok=True)

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


def _extraer_precio_desde_html(html: str) -> int | None:
    """Extrae el primer precio numérico del HTML de una página de ML."""
    soup = BeautifulSoup(html, "html.parser")
    # Selector típico de ML para el precio
    el = soup.select_one("span.andes-money-amount__fraction")
    if el:
        texto = el.get_text(strip=True)
        return extract_price_from_text(f"${texto}")
    # Fallback: meta tags
    for meta in soup.select('meta[itemprop="price"], meta[property="product:price:amount"]'):
        content = meta.get("content", "")
        if content:
            try:
                return int(float(content))
            except (ValueError, TypeError):
                pass
    # Fallback: cualquier texto con $
    body = soup.get_text() if soup.body else ""
    for m in re.finditer(r'\$\s*([\d\.,]+)', body):
        raw = m.group(1).replace(".", "").replace(",", "")
        try:
            return int(raw)
        except ValueError:
            continue
    return None


def _verificar_precio_personalizado(url: str, precio_original: int | None) -> dict:
    """
    Consulta la misma URL con una identidad diferente (User-Agent, viewport,
    locale) y devuelve True si el precio detectado difiere del original.
    """
    if precio_original is None:
        return {"precio_personalizado": False, "precio_alternativo": None}

    from playwright.sync_api import sync_playwright

    personas = [
        {
            "ua": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            "viewport": {"width": 390, "height": 844},
            "locale": "es-AR",
        },
        {
            "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "viewport": {"width": 1920, "height": 1080},
            "locale": "en-US",
        },
    ]

    persona = random.choice(personas)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"],
            )
            context = browser.new_context(
                user_agent=persona["ua"],
                viewport=persona["viewport"],
                locale=persona["locale"],
                timezone_id="America/Argentina/Buenos_Aires",
            )
            context.set_default_timeout(20000)
            page = context.new_page()
            page.route("**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf}", lambda route: route.abort())
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(random.uniform(3000, 5000))
                html = page.content()
            except Exception:
                html = page.content() if page.content() else ""
            browser.close()

        precio_alt = _extraer_precio_desde_html(html) if html else None
        es_personalizado = (
            precio_alt is not None
            and precio_original is not None
            and abs(precio_alt - precio_original) > 0
        )

        if es_personalizado:
            logger.info(f"🎭 Precio personalizado detectado: ${precio_original} vs ${precio_alt}")

        return {
            "precio_personalizado": es_personalizado,
            "precio_alternativo": precio_alt,
        }
    except Exception as e:
        logger.error(f"⚠️ Error verificando precio personalizado: {e}")
        return {"precio_personalizado": False, "precio_alternativo": None}


def hunt_offers(url: str, keyword: str, max_price: int, es_pro: bool = False, headless: bool = True, user_id: str = None, caza_id: int = None, plan: str = "starter"):
    disfraz = get_random_user_agent()
    apply_human_jitter()

    host = _domain(url)
    logger.info(f"🔍 Host: {host} | URL: {url[:40]}...")

    vuelos_sites = ["despegar", "almundo", "turismocity", "avantrip", "smiles"]
    if any(site in host for site in vuelos_sites):
        return hunt_despegar_vuelos(url, keyword, max_price, es_pro=es_pro, headless=False, user_agent=disfraz)

    resultados = hunt_generic(url, keyword, max_price)

    # Verificar precio personalizado en ML
    if "mercadolibre" in host and resultados:
        precio_base = resultados[0].get("price")
        info = _verificar_precio_personalizado(url, precio_base)
        for r in resultados:
            r["precio_personalizado"] = info["precio_personalizado"]
            if info["precio_alternativo"] and info["precio_alternativo"] != precio_base:
                r["precio_alternativo"] = info["precio_alternativo"]

    return resultados
