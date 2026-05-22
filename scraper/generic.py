from __future__ import annotations

import json
import re
import os
import time
from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup

CACHE_DIR = Path(__file__).resolve().parents[1] / ".scraper_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

PRICE_SELECTORS = [
    'meta[itemprop="price"]',
    'meta[property="product:price:amount"]',
    ".andes-money-amount__fraction",
    ".price",
    '[data-price]',
    ".product-price",
    ".sale-price",
    ".offer-price",
    '[class*="price"]',
    '[id*="price"]',
]


def _cache_key(url: str) -> str:
    import hashlib
    return hashlib.md5(url.encode()).hexdigest()


def _cache_get(key: str):
    path = CACHE_DIR / key
    if path.exists():
        import pickle
        try:
            data = pickle.loads(path.read_bytes())
            if time.time() - data["ts"] < 300:
                return data["val"]
        except Exception:
            pass
    return None


def _cache_set(key: str, val):
    import pickle
    path = CACHE_DIR / key
    path.write_bytes(pickle.dumps({"ts": time.time(), "val": val}))


def extract_price_from_text(text: str) -> int | None:
    m = re.search(r'\$\s*([\d\.,]+)', text)
    if m:
        raw = m.group(1).replace(".", "").replace(",", "")
        try:
            return int(raw)
        except ValueError:
            pass
    return None


def extract_jsonld(soup: BeautifulSoup) -> list[dict]:
    results = []
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                items = data
            else:
                items = [data]
            for item in items:
                if isinstance(item, dict):
                    name = item.get("name", "")
                    offers = item.get("offers", {})
                    if isinstance(offers, list):
                        for o in offers:
                            price = o.get("price", 0)
                            if price:
                                results.append({
                                    "title": name,
                                    "price": int(float(price)),
                                    "url": o.get("url", ""),
                                    "source": "jsonld",
                                })
                    elif isinstance(offers, dict):
                        price = offers.get("price", 0)
                        if price:
                            results.append({
                                "title": name,
                                "price": int(float(price)),
                                "url": offers.get("url", ""),
                                "source": "jsonld",
                            })
        except Exception:
            continue
    return results


def extract_meta(soup: BeautifulSoup, url: str) -> list[dict]:
    for selector in PRICE_SELECTORS:
        tag = soup.select_one(selector)
        if tag:
            content = tag.get("content") or tag.get_text(strip=True)
            if content:
                price = extract_price_from_text(content)
                if price:
                    title_tag = soup.select_one('meta[property="og:title"]') or soup.select_one("title")
                    title = title_tag.get("content") or title_tag.get_text(strip=True) if title_tag else ""
                    return [{"title": title.strip()[:100], "price": price, "url": url, "source": "meta"}]
    return []


def extract_selectors(soup: BeautifulSoup, url: str) -> list[dict]:
    results = []
    seen = set()
    for selector in PRICE_SELECTORS:
        for el in soup.select(selector):
            text = el.get("content") or el.get_text(strip=True)
            if text and text not in seen:
                seen.add(text)
                price = extract_price_from_text(text)
                if price:
                    title_tag = soup.select_one('meta[property="og:title"]') or soup.select_one("title")
                    title = title_tag.get("content") or title_tag.get_text(strip=True) if title_tag else ""
                    results.append({
                        "title": title.strip()[:100],
                        "price": price,
                        "url": url,
                        "source": f"selector:{selector}",
                    })
    return results[:5]


def extract_regex(soup: BeautifulSoup, url: str) -> list[dict]:
    results = []
    seen = set()
    body = soup.get_text() if soup.body else ""
    for m in re.finditer(r'\$\s*([\d\.,]+)', body):
        raw = m.group(1).replace(".", "").replace(",", "")
        try:
            price = int(raw)
        except ValueError:
            continue
        if price and price not in seen:
            seen.add(price)
            title_tag = soup.select_one('meta[property="og:title"]') or soup.select_one("title")
            title = title_tag.get("content") or title_tag.get_text(strip=True) if title_tag else ""
            results.append({
                "title": title.strip()[:100],
                "price": price,
                "url": url,
                "source": "regex",
            })
    return results[:5]


def _playwright_get(url: str) -> str:
    from playwright.sync_api import sync_playwright
    from playwright_stealth import Stealth
    html = ""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-gpu",
                ],
            )
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                locale="es-AR",
                timezone_id="America/Argentina/Buenos_Aires",
            )
            context.set_default_timeout(25000)
            page = context.new_page()
            Stealth().apply_stealth_sync(page)
            page.route("**/*.{png,jpg,jpeg,gif,webp,svg}", lambda route: route.abort())
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=25000)
                page.wait_for_timeout(4000)
                html = page.content()
            except Exception:
                html = page.content() if page.content() else ""
            browser.close()
    except Exception as e:
        print(f"❌ Playwright error: {e}")
    return html


def _extract_results(soup: BeautifulSoup, url: str) -> list[dict]:
    results = []
    results.extend(extract_jsonld(soup))
    if not results:
        results.extend(extract_meta(soup, url))
    if not results:
        results.extend(extract_selectors(soup, url))
    if not results:
        results.extend(extract_regex(soup, url))
    return results


def _google_shopping(keyword: str, max_price: int) -> list[dict]:
    url = f"https://www.google.com/search?q={keyword}&tbm=shop"
    html = _playwright_get(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for item in soup.select(".sh-dgr__content, .sh-dlr__list-result"):
        title_el = item.select_one(".tAxDx, .sh-dlr__title, a[href]")
        price_el = item.select_one(".a8Pemb, .OFss3, .sh-dlr__list-result-price")
        link_el = item.select_one("a[href]")
        title = title_el.get_text(strip=True) if title_el else keyword
        price_text = price_el.get_text(strip=True) if price_el else ""
        price = extract_price_from_text(price_text) if price_text else 0
        link = link_el.get("href", "") if link_el else ""
        if price:
            results.append({
                "title": title[:100],
                "price": price,
                "url": link if link.startswith("http") else f"https://www.google.com{link}" if link else "",
                "source": "google_shopping",
            })
    return results


def hunt_generic(url: str, keyword: str, max_price: int) -> list[dict]:
    ck = _cache_key(url or keyword)
    cached = _cache_get(ck)
    if cached:
        return cached

    # 1. Try direct URL
    results = []
    if url and "http" in url:
        html = _playwright_get(url)
        if html:
            soup = BeautifulSoup(html, "html.parser")
            results = _extract_results(soup, url)

    # 2. Fallback: Google Shopping with keyword
    if not results and keyword:
        results = _google_shopping(keyword, max_price)

    if max_price > 0:
        results = [r for r in results if r["price"] <= max_price]

    if results:
        results = results[:5]
        _cache_set(ck, results)
    else:
        _cache_set(ck, [])

    return results
