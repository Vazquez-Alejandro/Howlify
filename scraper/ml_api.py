"""
scraper/ml_api.py — MercadoLibre Official API Client
Uses the public API instead of web scraping for stability.
"""
import os
import re
import time
import requests
from utils.logger import get_logger

logger = get_logger("ml_api")

ML_API_BASE = "https://api.mercadolibre.com"

# Rate limiting: ML allows 1000 requests/day for free tier
_last_request_time = 0
_MIN_REQUEST_INTERVAL = 0.3  # 300ms between requests


def _rate_limit():
    """Simple rate limiter for ML API."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < _MIN_REQUEST_INTERVAL:
        time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
    _last_request_time = time.time()


def _extract_item_id(url: str) -> str | None:
    """Extract MercadoLibre item ID from various URL formats."""
    if not url or "mercadolibre" not in url.lower():
        return None

    # MLA-1234567890 or MLA1234567890
    m = re.search(r'(ML[AU]-?\d{8,})', url, re.IGNORECASE)
    if m:
        return m.group(1).replace("-", "").upper()

    # /p/MLA123456
    m2 = re.search(r'/p/([A-Z0-9]+)', url, re.IGNORECASE)
    if m2:
        return m2.group(1).upper()

    return None


def get_item(item_id: str) -> dict | None:
    """Get item details from ML API."""
    _rate_limit()
    try:
        resp = requests.get(
            f"{ML_API_BASE}/items/{item_id}",
            timeout=10,
            headers={"User-Agent": "Howlify/1.0"},
        )
        if resp.status_code == 200:
            return resp.json()
        logger.warning(f"ML API returned {resp.status_code} for {item_id}")
        return None
    except Exception as e:
        logger.error(f"ML API error: {e}")
        return None


def search_items(query: str, limit: int = 10, offset: int = 0) -> list[dict]:
    """Search items on MercadoLibre."""
    _rate_limit()
    try:
        resp = requests.get(
            f"{ML_API_BASE}/sites/MLA/search",
            params={"q": query, "limit": limit, "offset": offset},
            timeout=10,
            headers={"User-Agent": "Howlify/1.0"},
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("results", [])
        logger.warning(f"ML search returned {resp.status_code}")
        return []
    except Exception as e:
        logger.error(f"ML search error: {e}")
        return []


def get_price_from_url(url: str) -> dict | None:
    """
    Get price information from a MercadoLibre URL.
    Returns dict with title, price, currency, url, source.
    """
    item_id = _extract_item_id(url)
    if not item_id:
        logger.info(f"Could not extract item ID from: {url}")
        return None

    item = get_item(item_id)
    if not item:
        return None

    price = item.get("price", 0)
    currency = item.get("currency_id", "ARS")
    title = item.get("title", "")
    status = item.get("status", "")

    if status != "active":
        logger.info(f"Item {item_id} is not active (status: {status})")
        return None

    return {
        "title": title[:100],
        "price": int(price) if price else 0,
        "currency": currency,
        "url": item.get("permalink", url),
        "source": "mercadolibre_api",
        "item_id": item_id,
        "condition": item.get("condition", ""),
        "seller_id": item.get("seller_id"),
        "stock": int(item.get("available_quantity") or 0),
    }


def get_seller_info(seller_id: int) -> dict | None:
    """Get seller reputation from ML API."""
    _rate_limit()
    try:
        resp = requests.get(
            f"{ML_API_BASE}/users/{seller_id}",
            timeout=10,
            headers={"User-Agent": "Howlify/1.0"},
        )
        if resp.status_code == 200:
            data = resp.json()
            rep = data.get("seller_reputation", {})
            transactions = rep.get("transactions", {})
            return {
                "nickname": data.get("nickname", ""),
                "level": rep.get("level_id", ""),
                "total_sales": transactions.get("total", 0),
                "completed": transactions.get("completed", 0),
            }
        return None
    except Exception as e:
        logger.error(f"ML seller API error: {e}")
        return None


def hunt_ml_api(url: str, keyword: str = "", max_price: int = 0) -> list[dict]:
    """
    Hunt for offers using ML API instead of scraping.
    Returns list of results compatible with the existing system.
    """
    results = []

    # Try to get item directly from URL
    item = get_price_from_url(url)
    if item and item["price"] > 0:
        if max_price <= 0 or item["price"] <= max_price:
            results.append(item)
        return results

    # Fallback: search by keyword
    if keyword:
        items = search_items(keyword, limit=5)
        for item_data in items:
            price = int(item_data.get("price", 0))
            if price > 0 and (max_price <= 0 or price <= max_price):
                results.append({
                    "title": item_data.get("title", "")[:100],
                    "price": price,
                    "currency": item_data.get("currency_id", "ARS"),
                    "url": item_data.get("permalink", ""),
                    "source": "mercadolibre_api",
                    "item_id": item_data.get("id", ""),
                    "stock": int(item_data.get("available_quantity") or 0),
                })

    return results
