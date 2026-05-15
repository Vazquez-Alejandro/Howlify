from __future__ import annotations

import os
import re
import time
import unicodedata
import requests
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urljoin, urlparse

from services.database_service import subir_evidencia_storage, registrar_infraccion
from utils.proxy import requests_get
from utils.cache import cached, set_cache, cache_key

DEBUG = os.getenv("OH_SCRAPER_DEBUG", "0") == "1"
OH_PLAYWRIGHT = os.getenv("OH_PLAYWRIGHT", "0") == "1"
VTEX_HOST_HINTS = ("carrefour", "jumbo", "disco", "vea", "easy", "libertad", "vtex")

PRODUCT_LINK_SELECTORS = (
    "a[href*='/p/']", "a[href*='/product/']", "a[href*='/producto/']",
    "a[href*='/prod-']", "a[data-testid*='product']", "a[data-product-id]", "a[title]",
)
PRICE_TEXT_SELECTORS = (
    r"text=/\$\s*\d/", "[data-testid*='price']", "[class*='price']", "[class*='Price']",
    "[class*='amount']", "[class*='Amount']",
)


def _log(*args):
    if DEBUG:
        print("[generic]", *args)


def is_vtex_site(url: str) -> bool:
    parsed = urlparse(url)
    full = f"{parsed.netloc or ''}{parsed.path or ''}".lower()
    if any(hint in full for hint in VTEX_HOST_HINTS):
        return True
    return any(tok in full for tok in ("/busca", "/api/catalog_system/pub/products/search", "/_v/segment/"))


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
    tokens = [x for x in k.split() if x]
    return all(tok in t for tok in tokens)


def _parse_price_ar(raw: Any) -> Optional[int]:
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
    for tok in ("Vendido por", "$", "Precio s/imp", "Precio s/imp.", "Precio s/imp. nac", "Precio sin impuestos"):
        if tok in title:
            title = title.split(tok)[0].strip()
    title = title.split("\n")[0].strip()
    return title[:180].strip() if len(title) > 180 else title


def _normalize_result(item: Dict[str, Any], source_fallback: str = "generic") -> Optional[Dict[str, Any]]:
    title = _clean_title(str(item.get("title") or item.get("titulo") or ""))
    if not title:
        return None
    price = _parse_price_ar(item.get("price") or item.get("precio"))
    if price is None or price <= 0:
        return None
    url = str(item.get("url") or item.get("link") or "").strip()
    source = str(item.get("source") or source_fallback).strip() or source_fallback
    return {"title": title, "price": price, "url": url, "source": source}


def _dedupe_results(items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out: List[Dict[str, Any]] = []
    for item in items:
        norm = _normalize_result(item)
        if not norm:
            continue
        key = (_norm(norm["title"]), int(norm["price"]), (norm["url"] or "").strip().lower())
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


# --- VTEX ---

def _vtex_base_from_url(u: str) -> str:
    p = urlparse(u)
    return f"{p.scheme or 'https'}://{p.netloc}"


def _vtex_category_path(u: str) -> str:
    path = urlparse(u).path.strip("/")
    return "/" + path if path else "/"


def _vtex_api_search(url: str, keyword: str, max_price: int, limit: int = 80) -> List[Dict[str, Any]]:
    ck = cache_key(f"vtex:{url}", keyword, max_price)
    cached_res = cached(ck, ttl=600)
    if cached_res is not None:
        return cached_res

    base = _vtex_base_from_url(url)
    path = _vtex_category_path(url)
    api = f"{base}/api/catalog_system/pub/products/search{path}"
    out: List[Dict[str, Any]] = []
    kw = (keyword or "").strip()

    for start in range(0, max(limit, 50), 50):
        params = {"_from": start, "_to": start + 49}
        try:
            r = requests.get(api, params=params, headers={"referer": base + "/"}, timeout=12)
            if r.status_code != 200:
                break
            data = r.json()
            if not isinstance(data, list) or not data:
                break
            batch = []
            for prod in data:
                title = (prod.get("productName") or "").strip()
                if not title:
                    continue
                link = prod.get("link") or ""
                if link.startswith("/"):
                    link = base + link
                price_raw = None
                try:
                    price_raw = prod["items"][0]["sellers"][0]["commertialOffer"]["Price"]
                except Exception:
                    price_raw = None
                batch.append({"title": title, "price": price_raw, "url": link, "source": "vtex"})
            out.extend(_filter_results(batch, kw, max_price))
            out = _dedupe_results(out)
            if len(out) >= limit:
                out = out[:limit]
                break
        except Exception as e:
            _log("vtex API error:", e)
            break

    set_cache(ck, out)
    return out


# --- Playwright fallback ---

def _hunt_offers_playwright_dom(url: str, keyword: str, max_price: int, user_id: str, caza_id: str, limit: int = 80) -> List[Dict[str, Any]]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print("Playwright no disponible.")
        return []

    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    out: List[Dict[str, Any]] = []
    selector = ", ".join(PRODUCT_LINK_SELECTORS)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            viewport={"width": 1365, "height": 900}, locale="es-AR",
        )
        page = context.new_page()
        page.set_default_timeout(45000)
        try:
            page.goto(url, wait_until="domcontentloaded")
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            time.sleep(1.0)

            last_count, stable = 0, 0
            for _ in range(12):
                page.mouse.wheel(0, 2600)
                time.sleep(1.0)
                cnt = page.locator(selector).count()
                if cnt <= last_count:
                    stable += 1
                else:
                    stable, last_count = 0, cnt
                if stable >= 3:
                    break

            links = page.locator(selector)
            total = min(links.count(), 160)
            raw_out: List[Dict[str, Any]] = []

            for i in range(total):
                if len(raw_out) >= limit * 2:
                    break
                try:
                    a = links.nth(i)
                    href = a.get_attribute("href") or ""
                    full_url = urljoin(base, href)
                    title = _clean_title(a.get_attribute("title") or a.inner_text() or "")
                    if not title or (keyword and not _kw_match(title, keyword)):
                        continue
                    price = None
                    try:
                        container = a.locator("xpath=ancestor::*[self::article or self::div][1]")
                        for sel in PRICE_TEXT_SELECTORS:
                            try:
                                pc = container.locator(sel)
                                for j in range(min(pc.count(), 12)):
                                    raw_price = pc.nth(j).inner_text().strip().lower()
                                    if raw_price and "imp" not in raw_price and "nac" not in raw_price:
                                        p = _parse_price_ar(raw_price)
                                        if p and p > 0:
                                            price = p
                                            break
                            except Exception:
                                continue
                            if price:
                                break
                    except Exception:
                        pass
                    if price is None:
                        continue

                    if max_price > 0 and price < max_price:
                        nombre_foto = f"evidencia_{caza_id}_{int(datetime.now().timestamp())}.jpg"
                        ruta = os.path.join("evidence", nombre_foto)
                        try:
                            container.scroll_into_view_if_needed()
                            os.makedirs("evidence", exist_ok=True)
                            container.screenshot(path=ruta, type="jpeg", quality=60)
                            size = os.path.getsize(ruta)
                            if size < 2000:
                                registrar_infraccion(user_id, caza_id, price, max_price, None)
                            else:
                                url_evidencia = subir_evidencia_storage(ruta, nombre_foto)
                                registrar_infraccion(user_id, caza_id, price, max_price, url_evidencia)
                        except Exception:
                            registrar_infraccion(user_id, caza_id, price, max_price, None)

                    if max_price > 0 and price > max_price * 10:
                        continue
                    raw_out.append({"title": title, "price": price, "url": full_url, "source": "generic_dom"})
                except Exception:
                    continue

            out = _dedupe_results(raw_out)[:limit]
        finally:
            context.close()
            browser.close()
    return out


def hunt_offers_generic(url: str, keyword: str = "", max_price: Any = 0, depth: int = 1, user_id: str = None, caza_id: str = None) -> List[Dict[str, Any]]:
    max_price_i = _ensure_int(max_price, 0)
    results: List[Dict[str, Any]] = []

    if is_vtex_site(url):
        results = _vtex_api_search(url, keyword, max_price_i)

    if not results and OH_PLAYWRIGHT:
        results = _hunt_offers_playwright_dom(url, keyword, max_price_i, user_id=user_id, caza_id=caza_id)

    results = _filter_results(results, keyword, max_price_i)
    return results[:80]
