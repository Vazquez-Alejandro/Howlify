import os
import re
import time
import requests
from urllib.parse import urlparse
from utils.logger import get_logger
logger = get_logger("seller")


ML_API_BASE = "https://api.mercadolibre.com"

def _extract_ml_item_id(url: str) -> str | None:
    if not url or "mercadolibre" not in url:
        return None
    m = re.search(r"[A-Z]{3}\d{6,}", url, re.IGNORECASE)
    if m:
        return m.group(0).upper()
    m2 = re.search(r"/p/([A-Z0-9]+)", url, re.IGNORECASE)
    if m2:
        return m2.group(1)
    path = urlparse(url).path.strip("/")
    parts = path.split("/")
    for p in reversed(parts):
        if re.match(r"^[A-Z0-9\-]{6,}$", p, re.IGNORECASE):
            return p.upper()
    return None


def get_seller_info(item_id: str) -> dict | None:
    if not item_id:
        return None
    try:
        item_res = requests.get(f"{ML_API_BASE}/items/{item_id}", timeout=5)
        if item_res.status_code != 200:
            return None
        item_data = item_res.json()
        seller_id = item_data.get("seller_id")
        if not seller_id:
            return None

        time.sleep(0.3)
        user_res = requests.get(f"{ML_API_BASE}/users/{seller_id}", timeout=5)
        if user_res.status_code != 200:
            return None
        user_data = user_res.json()

        seller_reputation = user_data.get("seller_reputation", {})
        transactions = seller_reputation.get("transactions", {})
        total = transactions.get("total", 0)
        completed = transactions.get("completed", 0)
        ratings = seller_reputation.get("level_id", "")

        level_map = {
            "5_green": "🟢 Mercado Líder",
            "4_light_green": "🟢 Mercado Líder",
            "3_yellow": "🟡 Buen vendedor",
            "2_orange": "🟠 Nuevo",
            "1_red": "🔴 Baja reputación",
        }

        return {
            "seller_id": seller_id,
            "nickname": user_data.get("nickname", ""),
            "reputation": ratings,
            "reputation_label": level_map.get(ratings, "⚪ Sin datos"),
            "total_sales": total,
            "completed_sales": completed,
            "positive_ratio": seller_reputation.get("power_seller_status"),
            "permalink": f"https://www.mercadolibre.com.ar/perfil/{seller_id}",
        }
    except Exception as e:
        logger.error(f"⚠ Error getting seller info for {item_id}: {e}")
        return None


def enrich_results_with_sellers(results: list[dict]) -> list[dict]:
    for r in results:
        url = r.get("url", "")
        item_id = _extract_ml_item_id(url)
        if item_id:
            seller = get_seller_info(item_id)
            if seller:
                r["seller"] = seller
    return results
