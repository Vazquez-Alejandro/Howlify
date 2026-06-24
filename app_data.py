"""
app_data.py — Funciones de datos y lógica extraídas de app.py
"""

import os
import time
import re
import base64
import subprocess
import pandas as pd
from datetime import datetime, timedelta

from auth.supabase_client import supabase
from utils.logic import (
    normalize_plan_family,
    parse_price_to_int,
    infer_source_from_url,
    domain_from_url,
    clean_ml_url,
    exportar_a_sheets,
    save_price_history,
)
from utils.logger import get_logger
logger = get_logger("app_data")


# Sound
WOLF_PATH = os.path.join(os.path.dirname(__file__), "assets", "wolf.mp3")

def monitor_status(current_price, min_allowed, max_allowed):
    price = _safe_int(current_price, 0)
    min_p = _safe_int(min_allowed, 0)
    max_p = _safe_int(max_allowed, 0)

    if price <= 0:
        return "⚪ Sin precio"

    if min_p > 0 and price < min_p:
        return "🔻 Debajo del mínimo"

    if max_p > 0 and price > max_p:
        return "🔺 Encima del máximo"

    # zona amarilla: dentro de ±5% del límite configurado
    if min_p > 0 and price <= int(min_p * 1.05):
        return "🟡 Cerca del mínimo"
    if max_p > 0 and price >= int(max_p * 0.95):
        return "🟡 Cerca del máximo"

    if min_p > 0 or max_p > 0:
        return "✅ En rango"

    return "⚪ Sin rango"


def compliance_pct_from_series(df: pd.DataFrame, min_allowed, max_allowed):
    if df is None or df.empty:
        return None

    min_p = _safe_int(min_allowed, 0)
    max_p = _safe_int(max_allowed, 0)

    if min_p <= 0 and max_p <= 0:
        return None

    series = df["price"].dropna().astype(float)
    if series.empty:
        return None

    in_range = pd.Series([True] * len(series), index=series.index)
    if min_p > 0:
        in_range &= series >= min_p
    if max_p > 0:
        in_range &= series <= max_p

    return round(float(in_range.mean() * 100), 1)


def _make_histogram_df(series: pd.Series, bins: int = 8):
    if series is None or series.empty:
        return pd.DataFrame()
    try:
        cuts = pd.cut(series, bins=min(bins, max(2, series.nunique())), duplicates="drop")
        hist = cuts.value_counts().sort_index()
        labels = [f"{int(interval.left):,}-{int(interval.right):,}".replace(",", ".") for interval in hist.index]
        return pd.DataFrame({"rango": labels, "cantidad": hist.values}).set_index("rango")
    except Exception:
        return pd.DataFrame()
def delete_monitor_rule(user_id: str, caza_id) -> bool:
    try:
        if not user_id or caza_id is None:
            return False

        res = (
            supabase.table("monitor_rules")
            .update({"is_active": False})
            .eq("user_id", user_id)
            .eq("caza_id", caza_id)
            .execute()
        )
        return True if getattr(res, "data", None) is not None else True
    except Exception as e:
        logger.error("[delete_monitor_rule] error:", e)
def get_monitor_rules_map(user_id: str, caza_ids: list):
    caza_ids = [x for x in caza_ids if x is not None]
    if not user_id or not caza_ids:
        return {}

    try:
        res = (
            supabase.table("monitor_rules")
            .select("*")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .in_("caza_id", caza_ids)
            .execute()
        )
        rows = res.data or []
        return {row.get("caza_id"): row for row in rows if row.get("caza_id") is not None}
    except Exception as e:
        logger.error("[get_monitor_rules_map] error:", e)
def get_price_history_series_by_caza(user_id: str, caza_id):
    if not user_id or caza_id is None:
        return pd.DataFrame()

    try:
        res = (
            supabase.table("price_history")
            .select("checked_at, price")
            .eq("user_id", user_id)
            .eq("caza_id", caza_id)
            .order("checked_at", desc=False)
            .execute()
        )
        rows = res.data or []
    except Exception as e:
        logger.error("[get_price_history_series_by_caza] error:", e)
        return pd.DataFrame()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    if "checked_at" in df.columns:
        df["checked_at"] = pd.to_datetime(df["checked_at"], errors="coerce")
    if "price" in df.columns:
        df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df.dropna(subset=["checked_at", "price"]).sort_values("checked_at")
    return df
def get_price_history_stats_by_caza(user_id: str, caza_ids: list):
    caza_ids = [x for x in caza_ids if x is not None]
    if not user_id or not caza_ids:
        return {}

    try:
        res = (
            supabase.table("price_history")
            .select("caza_id, price, checked_at, title, url, source")
            .eq("user_id", user_id)
            .in_("caza_id", caza_ids)
            .order("checked_at", desc=True)
            .execute()
        )
        rows = res.data or []
    except Exception as e:
        logger.error("[get_price_history_stats_by_caza] error:", e)
        return {}

    stats = {}

    for row in rows:
        caza_id = row.get("caza_id")
        if caza_id is None:
            continue

        price = _safe_int(row.get("price"), 0)
        if price <= 0:
            continue

        if caza_id not in stats:
            stats[caza_id] = {
                "prices": [],
                "latest_price": price,
                "latest_checked_at": row.get("checked_at"),
                "title": row.get("title") or "",
                "url": row.get("url") or "",
                "source": row.get("source") or "",
            }

        stats[caza_id]["prices"].append(price)

    for caza_id, item in stats.items():
        prices = item.pop("prices", [])
        if not prices:
            continue

        item["min_price"] = min(prices)
        item["max_price"] = max(prices)
        item["avg_price"] = sum(prices) / len(prices)
        item["samples"] = len(prices)

    return stats
def collect_live_business_ops():
    live_ops = []

    for key, value in st.session_state.items():
        if not str(key).startswith("last_res_"):
            continue

        for r in value or []:
            price = _safe_int(r.get("price") or r.get("precio"), 0)
            if price <= 0:
                continue

            score = float(r.get("_score") or 0)
            title = (r.get("title") or r.get("titulo") or "").strip()
            url = (r.get("url") or r.get("link") or "").strip()
            source = (r.get("source") or "-").strip() or "-"

            if not title:
                continue

            live_ops.append(
                {
                    "title": title,
                    "current_price": price,
                    "opportunity_score": score,
                    "url": url,
                    "source": source,
                }
            )

    uniq = []
    seen = set()
    for op in sorted(
        live_ops,
        key=lambda x: (
            -float(x.get("opportunity_score") or 0),
            _safe_int(x.get("current_price"), 999999999),
        ),
    ):
        key = (
            op.get("title", "").strip().lower(),
            _safe_int(op.get("current_price"), 0),
            op.get("url", "").strip(),
        )
        if key in seen:
            continue
        seen.add(key)
        uniq.append(op)

    return uniq

def es_plan_business(plan: str) -> bool:
    return normalize_plan_family(plan) in {"business_reseller", "business_monitor"}



def _fmt_money(value):
    try:
        return f"${float(value):,.0f}".replace(",", ".")
    except Exception:
        return "-"


def _fmt_pct(value):
    try:
        return f"{float(value):.2f}%"
    except Exception:
        return "-"


def _safe_int(value, default=0):
    try:
        return int(float(value))
    except Exception:
        return default

def contar_cazas_activas(user_id: str) -> int:
    if not user_id:
        return 0

    for attempt in range(2):
        try:
            res = (
                supabase.table("cazas")
                .select("id", count="exact")
                .eq("user_id", user_id)
                .eq("estado", "activa")
                .execute()
            )
            return int(res.count or 0)
        except Exception as e:
            if attempt == 0:
                time.sleep(0.5)
                continue
            logger.error("[contar_cazas_activas] error:", e)
            return 0


def get_user_profile(user_id: str | None):
    if not user_id:
        return {}

    try:
        res = (
            supabase.table("profiles")
            .select("plan, role, username, email, whatsapp_number")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        return rows[0] if rows else {}
    except Exception as e:
        logger.error("[get_user_profile] error:", e)
        return {}


def save_user_whatsapp(user_id: str, whatsapp_number: str) -> bool:
    if not user_id:
        return False

    numero = normalize_phone(whatsapp_number)
    if not numero:
        return False

    try:
        supabase.table("profiles").update(
            {"whatsapp_number": numero}
        ).eq("user_id", user_id).execute()
        return True
    except Exception as e:
        logger.error("[save_user_whatsapp] error:", e)
        return False
def password_strength(password: str):
    score = 0

    if len(password) >= 8:
        score += 1
    if re.search(r"[A-Z]", password):
        score += 1
    if re.search(r"[a-z]", password):
        score += 1
    if re.search(r"\d", password):
        score += 1
    if re.search(r"[^A-Za-z0-9]", password):
        score += 1

    if score <= 2:
        return "Débil", "🔴"
    if score <= 4:
        return "Media", "🟠"
    return "Fuerte", "🟢"


def normalize_phone(number: str) -> str:
    return re.sub(r"\D", "", str(number or "").strip())


def get_base64_logo(path: str) -> str:
    try:
        with open(path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except Exception:
        return ""


def play_wolf_sound():
    try:
        with open(WOLF_PATH, "rb") as f:
            audio_bytes = f.read()
        b64 = base64.b64encode(audio_bytes).decode()
        tick = int(st.session_state.get("sound_tick", 0))
        components.html(
            f"""
            <audio autoplay="true" style="display:none" id="wolf_{tick}">
              <source src="data:audio/mp3;base64,{b64}" type="audio/mp3" />
            </audio>
            """,
            height=0,
        )
    except Exception:
        pass
def calc_result_score(item: dict, min_price: int, avg_price: float) -> float:
    """
    Score relativo al lote actual:
    - más score si está cerca del mínimo
    - más score si está bastante por debajo del promedio
    - pequeño bonus por título más limpio/corto
    """
    try:
        price = int(item.get("price") or item.get("precio") or 999999999)
    except Exception:
        price = 999999999

    title = str(item.get("title") or item.get("titulo") or "").strip()

    title_len_bonus = 0
    if title:
        if len(title) <= 55:
            title_len_bonus = 10
        elif len(title) <= 85:
            title_len_bonus = 5

    if price <= 0 or avg_price <= 0 or min_price <= 0:
        return round(title_len_bonus, 2)

    # qué tan cerca está del mínimo
    min_component = max(0, (min_price / price) * 40)

    # qué tan por debajo del promedio está
    diff_vs_avg_pct = ((avg_price - price) / avg_price) * 100
    avg_component = max(0, diff_vs_avg_pct * 2.2)

    return round(min_component + avg_component + title_len_bonus, 2)


def get_result_badge(item: dict, min_price: int, avg_price: float) -> tuple[str, str]:
    """
    Badge dinámico según el lote actual.
    """
    try:
        price = int(item.get("price") or item.get("precio") or 0)
    except Exception:
        price = 0

    if price <= 0 or avg_price <= 0:
        return ("📦", "Sin precio claro")

    diff_vs_avg_pct = ((avg_price - price) / avg_price) * 100

    if price == min_price:
        return ("🏆", "Más barato del lote")
    if diff_vs_avg_pct >= 20:
        return ("🔥", "Oportunidad")
    if diff_vs_avg_pct >= 10:
        return ("💰", "Buen precio")
    if diff_vs_avg_pct >= 0:
        return ("👀", "Para seguir")
    return ("📌", "Por encima del promedio")


def sort_results_intelligent(results: list[dict]) -> list[dict]:
    cleaned = []
    seen = set()

    for item in results or []:
        title = str(item.get("title") or item.get("titulo") or "").strip()
        link = str(item.get("url") or item.get("link") or "").strip()

        try:
            price = int(item.get("price") or item.get("precio") or 999999999)
        except Exception:
            price = 999999999

        key = (title.lower(), price, link)
        if key in seen:
            continue
        seen.add(key)

        cleaned.append(item)

    valid_prices = []
    for item in cleaned:
        try:
            p = int(item.get("price") or item.get("precio") or 0)
            if p > 0 and p < 999999999:
                valid_prices.append(p)
        except Exception:
            pass

    min_price = min(valid_prices) if valid_prices else 0
    avg_price = sum(valid_prices) / len(valid_prices) if valid_prices else 0

    for item in cleaned:
        item["_score"] = calc_result_score(item, min_price, avg_price)
        item["_min_price"] = min_price
        item["_avg_price"] = avg_price

    cleaned.sort(
        key=lambda x: (
            -(x.get("_score") or 0),
            int(x.get("price") or x.get("precio") or 999999999),
        )
    )
