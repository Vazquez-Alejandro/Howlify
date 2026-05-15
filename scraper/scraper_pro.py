from __future__ import annotations

import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from .despegar import hunt_despegar_vuelos
from .generic import hunt_generic
from utils.logic import get_random_user_agent, apply_human_jitter

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


def hunt_offers(url: str, keyword: str, max_price: int, es_pro: bool = False, headless: bool = True, user_id: str = None, caza_id: int = None, plan: str = "starter"):
    disfraz = get_random_user_agent()
    apply_human_jitter()

    host = _domain(url)
    print(f"🔍 Host: {host} | URL: {url[:40]}...")

    vuelos_sites = ["despegar", "almundo", "turismocity", "avantrip", "smiles"]
    if any(site in host for site in vuelos_sites):
        return hunt_despegar_vuelos(url, keyword, max_price, es_pro=es_pro, headless=False, user_agent=disfraz)

    return hunt_generic(url, keyword, max_price)
