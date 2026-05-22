from __future__ import annotations

import os
import random
import time
import requests
from typing import Optional


PROXY_BACKEND = os.getenv("PROXY_BACKEND", "direct")
SCRAPERAPI_KEY = os.getenv("SCRAPERAPI_KEY", "")


FREE_PROXIES: list[dict] = []
_last_refresh = 0


def _fetch_free_proxies() -> list[dict]:
    global _last_refresh, FREE_PROXIES
    now = time.time()
    if now - _last_refresh < 300:
        return FREE_PROXIES
    _last_refresh = now
    try:
        r = requests.get(
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
            timeout=10,
        )
        if r.status_code == 200:
            lines = [l.strip() for l in r.text.splitlines() if l.strip()]
            FREE_PROXIES = [
                {"http": f"http://{p}", "https": f"http://{p}"}
                for p in lines[:50]
            ]
            print(f"[proxy] Cargados {len(FREE_PROXIES)} proxies libres")
    except Exception as e:
        print(f"[proxy] Error fetching free proxies: {e}")
    return FREE_PROXIES


def get_proxies() -> dict:
    backend = os.getenv("PROXY_BACKEND", PROXY_BACKEND)
    if backend == "direct":
        return {}
    if backend == "scraperapi":
        return {}
    if backend == "free":
        proxies = _fetch_free_proxies()
        if proxies:
            return random.choice(proxies)
        return {}
    if backend == "residential":
        user = os.getenv("RESIDENTIAL_PROXY_USER", "")
        pwd = os.getenv("RESIDENTIAL_PROXY_PASS", "")
        host = os.getenv("RESIDENTIAL_PROXY_HOST", "")
        port = os.getenv("RESIDENTIAL_PROXY_PORT", "")
        if user and host:
            return {
                "http": f"http://{user}:{pwd}@{host}:{port}",
                "https": f"http://{user}:{pwd}@{host}:{port}",
            }
        return {}
    return {}


def fetch_via_scraperapi(url: str, *, render: bool = True, premium: bool = True, country: str = "ar", timeout: int = 60) -> Optional[str]:
    if not SCRAPERAPI_KEY:
        return None
    api_url = (
        f"http://api.scraperapi.com"
        f"?api_key={SCRAPERAPI_KEY}"
        f"&url={url}"
        f"&country_code={country}"
    )
    if render:
        api_url += "&render=true"
    if premium:
        api_url += "&premium=true"
    try:
        resp = requests.get(api_url, timeout=timeout)
        if resp.status_code == 200:
            return resp.text
    except Exception as e:
        print(f"[proxy] ScraperAPI error: {e}")
    return None


def requests_get(url: str, *, timeout: int = 30, retries: int = 3, headers: Optional[dict] = None) -> Optional[requests.Response]:
    backend = os.getenv("PROXY_BACKEND", PROXY_BACKEND)

    if backend == "scraperapi":
        html = fetch_via_scraperapi(url, timeout=timeout)
        if html:
            r = requests.Response()
            r.status_code = 200
            r._content = html.encode()
            return r
        return None

    ua = random.choice([
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    ])

    merged_headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    if headers:
        merged_headers.update(headers)

    last_error = None
    for attempt in range(1, retries + 1):
        proxies = get_proxies()
        try:
            r = requests.get(url, headers=merged_headers, proxies=proxies, timeout=timeout)
            if r.status_code == 200:
                return r
            last_error = f"status {r.status_code}"
        except Exception as e:
            last_error = e
        if attempt < retries:
            time.sleep(1.5 * attempt)
    print(f"[proxy] GET failed after {retries} retries: {last_error}")
    return None
