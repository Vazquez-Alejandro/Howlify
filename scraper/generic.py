# -*- coding: utf-8 -*-
"""
Howlify - Generic scraper

Estrategia:
- Sitios VTEX: intentar API pública de catálogo (categoría/path) y,
  si eso falla, fallback a búsqueda full-text por keyword.
- Otros sitios: Playwright + scroll + extracción DOM (fallback).

Env vars:
- OH_SCRAPER_DEBUG=1  -> imprime logs [generic]
- OH_HEADLESS=0       -> abre navegador visible (para debug)
"""

from __future__ import annotations

import os
import re
import time
import unicodedata
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urljoin, urlparse

import requests

DEBUG = os.getenv("OH_SCRAPER_DEBUG", "0") == "1"
HEADLESS = os.getenv("OH_HEADLESS", "1") != "0"

DEFAULT_HEADERS = {
    "user-agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "accept": "application/json,text/plain,*/*",
    "accept-language": "es-AR,es;q=0.9,en;q=0.8",
    "cache-control": "no-cache",
    "pragma": "no-cache",
}

VTEX_HOST_HINTS = (
    "carrefour",
    "jumbo",
    "disco",
    "vea",
    "easy",
    "libertad",
    "vtex",
)

PRODUCT_LINK_SELECTORS = (
    "a[href*='/p/']",
    "a[href*='/product/']",
    "a[href*='/producto/']",
    "a[href*='/prod-']",
    "a[data-testid*='product']",
    "a[data-product-id]",
    "a[title]",
)

PRICE_TEXT_SELECTORS = (
    r"text=/\$\s*\d/",
    "[data-testid*='price']",
    "[class*='price']",
    "[class*='Price']",
    "[class*='amount']",
    "[class*='Amount']",
)


def _log(*args):
    if DEBUG:
        print("[generic]", *args)


def is_vtex_site(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").lower()
    full = f"{host}{path}"

    if any(hint in full for hint in VTEX_HOST_HINTS):
        return True

    return any(
        token in full
        for token in (
            "/busca",
            "/api/catalog_system/pub/products/search",
            "/_v/segment/",
        )
    )


def _ensure_int(x: Any, default: int = 0) -> int:
    try:
        return int(float(x))
    except Exception:
        return default


def _norm(s: str) -> str:
    s = (s or "").lower().strip()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _kw_match(title: str, keyword: str) -> bool:
    k = _norm(keyword)
    if not k:
        return True
    t = _norm(title)
    tokens = [x for x in k.split() if x]
    return all(tok in t for tok in tokens)


def _parse_price_ar(raw: Any) -> Optional[int]:
    """
    Convierte:
      "$ 5.639,00" -> 5639
      "18.000"     -> 18000
      5639.0       -> 5639
    """
    if raw is None:
        return None

    if isinstance(raw, (int, float)):
        try:
            return int(raw)
        except Exception:
            return None

    s = str(raw).strip()
    if not s:
        return None

    s = s.replace("$", "").replace(" ", "")
    s = re.sub(r"[^0-9\.,]", "", s)

    if "," in s:
        s = s.split(",")[0]
    s = s.replace(".", "")

    if not s.isdigit():
        return None

    try:
        return int(s)
    except Exception:
        return None


def _clean_title(raw: str) -> str:
    title = (raw or "").strip()
    if not title:
        return ""

    title = re.sub(r"\s+", " ", title)
    cut_tokens = [
        "Vendido por",
        "$",
        "Precio s/imp",
        "Precio s/imp.",
        "Precio s/imp. nac",
        "Precio sin impuestos",
    ]
    for tok in cut_tokens:
        if tok in title:
            title = title.split(tok)[0].strip()

    title = title.split("\n")[0].strip()
    if len(title) > 180:
        title = title[:180].strip()
    return title


def _normalize_result(item: Dict[str, Any], source_fallback: str = "generic") -> Optional[Dict[str, Any]]:
    title = _clean_title(str(item.get("title") or item.get("titulo") or ""))
    if not title:
        return None

    price = _parse_price_ar(item.get("price") or item.get("precio"))
    if price is None or price <= 0:
        return None

    url = str(item.get("url") or item.get("link") or "").strip()
    source = str(item.get("source") or source_fallback).strip() or source_fallback

    return {
        "title": title,
        "price": price,
        "url": url,
        "source": source,
    }


def _dedupe_results(items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out: List[Dict[str, Any]] = []

    for item in items:
        norm = _normalize_result(item)
        if not norm:
            continue

        key = (
            _norm(norm["title"]),
            int(norm["price"]),
            (norm["url"] or "").strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(norm)

    out.sort(key=lambda x: (x.get("price", 10**12), _norm(x.get("title", ""))))
    return out


def _filter_results(items: Iterable[Dict[str, Any]], keyword: str, max_price: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for item in items:
        norm = _normalize_result(item)
        if not norm:
            continue
        if keyword and not _kw_match(norm["title"], keyword):
            continue
        if max_price > 0 and norm["price"] > max_price:
            continue
        out.append(norm)
    return _dedupe_results(out)


def _requests_get_json(url: str, *, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None,
                       timeout: int = 12, retries: int = 3, backoff: float = 1.2) -> Optional[Any]:
    merged_headers = dict(DEFAULT_HEADERS)
    if headers:
        merged_headers.update(headers)

    last_error = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, params=params, headers=merged_headers, timeout=timeout)
            if r.status_code == 200:
                return r.json()
            last_error = f"status {r.status_code}"
            _log("GET json failed:", url, last_error, "attempt", attempt)
        except Exception as e:
            last_error = e
            _log("GET json error:", url, e, "attempt", attempt)

        if attempt < retries:
            time.sleep(backoff * attempt)

    _log("GET json giving up:", url, "error:", last_error)
    return None


# ----------------------------
# VTEX API strategy
# ----------------------------

def _vtex_category_path(u: str) -> str:
    """
    Toma una URL como:
      https://www.carrefour.com.ar/Bebidas/Fernet-y-aperitivos/Fernet?order=
    y devuelve:
      /Bebidas/Fernet-y-aperitivos/Fernet
    """
    p = urlparse(u)
    path = p.path.strip("/")
    return "/" + path if path else "/"


def _vtex_base_from_url(u: str) -> str:
    p = urlparse(u)
    return f"{p.scheme or 'https'}://{p.netloc}"


def _vtex_api_search(category_url: str, keyword: str, max_price: int, limit: int = 80) -> List[Dict[str, Any]]:
    """
    Busca productos usando la API pública de VTEX por path/categoría:
      https://host/api/catalog_system/pub/products/search/<categoryPath>?_from=0&_to=49

    Devuelve items:
      {title, price, url, source}
    """
    base = _vtex_base_from_url(category_url)
    path = _vtex_category_path(category_url)
    api = base + "/api/catalog_system/pub/products/search" + path

    headers = {
        "referer": base + "/",
    }

    out: List[Dict[str, Any]] = []
    batch = 50
    kw = (keyword or "").strip()

    _log("vtex category API:", api)
    _log("keyword:", repr(kw), "max_price:", max_price)

    for start in range(0, max(limit, batch), batch):
        end = start + batch - 1
        params = {"_from": start, "_to": end}

        data = _requests_get_json(api, params=params, headers=headers, timeout=12, retries=3)
        if not isinstance(data, list) or not data:
            _log("vtex category API: sin datos (fin paginado)")
            break

        batch_out: List[Dict[str, Any]] = []
        for prod in data:
            title = (prod.get("productName") or "").strip()
            if not title:
                continue

            link = prod.get("link") or ""
            if link and link.startswith("/"):
                link = base + link

            price_raw = None
            try:
                price_raw = prod["items"][0]["sellers"][0]["commertialOffer"]["Price"]
            except Exception:
                price_raw = None

            batch_out.append(
                {
                    "title": title,
                    "price": price_raw,
                    "url": link,
                    "source": "vtex_api_category",
                }
            )

        out.extend(_filter_results(batch_out, kw, max_price))
        out = _dedupe_results(out)
        if len(out) >= limit:
            out = out[:limit]
            _log("vtex category API returned:", len(out))
            return out

    _log("vtex category API returned:", len(out))
    return out


def _vtex_api_search_by_keyword(url: str, keyword: str, max_price: int, limit: int = 80) -> List[Dict[str, Any]]:
    """
    Fallback para VTEX usando búsqueda full-text:
      https://host/api/catalog_system/pub/products/search?ft=keyword&_from=0&_to=49
    """
    base = _vtex_base_from_url(url)
    api = base + "/api/catalog_system/pub/products/search"

    headers = {
        "referer": base + "/",
    }

    out: List[Dict[str, Any]] = []
    batch = 50
    kw = (keyword or "").strip()

    if not kw:
        _log("vtex ft fallback skipped: empty keyword")
        return []

    _log("vtex FT API:", api)
    _log("keyword:", repr(kw), "max_price:", max_price)

    for start in range(0, max(limit, batch), batch):
        end = start + batch - 1
        params = {"ft": kw, "_from": start, "_to": end}

        data = _requests_get_json(api, params=params, headers=headers, timeout=12, retries=3)
        if not isinstance(data, list) or not data:
            _log("vtex FT API: sin datos (fin paginado)")
            break

        batch_out: List[Dict[str, Any]] = []
        for prod in data:
            title = (prod.get("productName") or "").strip()
            if not title:
                continue

            link = prod.get("link") or ""
            if link and link.startswith("/"):
                link = base + link

            price_raw = None
            try:
                price_raw = prod["items"][0]["sellers"][0]["commertialOffer"]["Price"]
            except Exception:
                price_raw = None

            batch_out.append(
                {
                    "title": title,
                    "price": price_raw,
                    "url": link,
                    "source": "vtex_api_ft",
                }
            )

        out.extend(_filter_results(batch_out, kw, max_price))
        out = _dedupe_results(out)
        if len(out) >= limit:
            out = out[:limit]
            _log("vtex FT API returned:", len(out))
            return out

    _log("vtex FT API returned:", len(out))
    return out


# ---------------------------------
# Fallback genérico: Playwright DOM
# ---------------------------------

def _playwright_available() -> bool:
    try:
        import playwright  # noqa: F401
        return True
    except Exception:
        return False


def _join_product_selectors() -> str:
    return ", ".join(PRODUCT_LINK_SELECTORS)


def _looks_product_link(href: str) -> bool:
    h = (href or "").lower().strip()
    if not h or h.startswith("javascript:") or h.startswith("#"):
        return False
    return any(
        token in h
        for token in (
            "/p/",
            "/product/",
            "/producto/",
            "/prod-",
            "/_",
        )
    ) or "sku" in h or "product" in h


def _extract_price_from_container(container) -> Optional[int]:
    for selector in PRICE_TEXT_SELECTORS:
        try:
            price_candidates = container.locator(selector)
            total_prices = min(price_candidates.count(), 12)
            parsed_prices: List[int] = []

            for j in range(total_prices):
                try:
                    raw_price = (price_candidates.nth(j).inner_text() or "").strip().lower()
                    if not raw_price or "imp" in raw_price or "nac" in raw_price:
                        continue

                    p = _parse_price_ar(raw_price)
                    if p is not None and p > 0:
                        parsed_prices.append(p)
                except Exception:
                    continue

            if parsed_prices:
                return min(parsed_prices)
        except Exception:
            continue
    return None


def _hunt_offers_playwright_dom(url: str, keyword: str, max_price: int, limit: int = 80) -> List[Dict[str, Any]]:
    """
    Fallback general para sitios que sí renderizan productos en DOM.
    """
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception:
        _log("Playwright no disponible.")
        return []

    base = "{u.scheme}://{u.netloc}".format(u=urlparse(url))
    out: List[Dict[str, Any]] = []
    selector = _join_product_selectors()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context(
            user_agent=DEFAULT_HEADERS["user-agent"],
            viewport={"width": 1365, "height": 900},
            locale="es-AR",
        )
        page = context.new_page()
        page.set_default_timeout(45000)

        try:
            page.goto(url, wait_until="domcontentloaded")
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                _log("networkidle timeout - continuing")
            time.sleep(1.0)

            last_count = 0
            stable = 0
            for _ in range(12):
                page.mouse.wheel(0, 2600)
                time.sleep(1.0)

                links = page.locator(selector)
                cnt = links.count()
                _log("scroll cards:", cnt)

                if cnt <= last_count:
                    stable += 1
                else:
                    stable = 0
                    last_count = cnt

                if stable >= 3:
                    break

            links = page.locator(selector)
            total = min(links.count(), 160)
            _log("total anchors:", links.count(), "-> scanning:", total)

            raw_out: List[Dict[str, Any]] = []
            for i in range(total):
                if len(raw_out) >= limit * 2:
                    break

                try:
                    a = links.nth(i)
                    href = a.get_attribute("href") or ""
                    if not href or not _looks_product_link(href):
                        continue

                    full_url = urljoin(base, href)

                    title = (a.get_attribute("title") or "").strip()
                    if not title:
                        try:
                            title = (a.inner_text() or "").strip()
                        except Exception:
                            title = ""

                    title = _clean_title(title)
                    if not title:
                        continue

                    if keyword and not _kw_match(title, keyword):
                        continue

                    price = None
                    try:
                        container = a.locator("xpath=ancestor::*[self::article or self::div][1]")
                        price = _extract_price_from_container(container)
                    except Exception:
                        price = None

                    if price is None:
                        continue
                    if max_price > 0 and price > max_price:
                        continue

                    raw_out.append(
                        {
                            "title": title,
                            "price": price,
                            "url": full_url,
                            "source": "generic_dom",
                        }
                    )
                except Exception:
                    continue

            out = _dedupe_results(raw_out)[:limit]
        finally:
            try:
                context.close()
            except Exception:
                pass
            try:
                browser.close()
            except Exception:
                pass

    _log("dom returned:", len(out))
    return out


# ----------------------------
# Public entrypoint
# ----------------------------

def hunt_offers_generic(url: str, keyword: str = "", max_price: Any = 0, depth: int = 1) -> List[Dict[str, Any]]:
    """
    Un único entrypoint para Howlify.
    Decide estrategia según dominio/plataforma.
    """
    max_price_i = _ensure_int(max_price, 0)

    _log("URL:", url)
    _log("keyword:", repr(keyword), "max_price:", max_price_i)

    results: List[Dict[str, Any]] = []

    if is_vtex_site(url):
        _log("strategy: vtex_api_category")
        results = _vtex_api_search(url, keyword, max_price_i, limit=80)
        _log("vtex_api_category results:", len(results))

        if not results:
            _log("vtex category failed -> fallback keyword search")
            results = _vtex_api_search_by_keyword(url, keyword, max_price_i, limit=80)
            _log("vtex_api_ft results:", len(results))

    if not results:
        _log("strategy: playwright_dom")
        results = _hunt_offers_playwright_dom(url, keyword, max_price_i, limit=80)
        _log("playwright_dom results:", len(results))

    results = _filter_results(results, keyword, max_price_i)
    _log("final results:", len(results))
    return results[:80]