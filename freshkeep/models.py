"""Data model + freshness logic for FreshKeep.

All dates are plain YYYY-MM-DD strings (calendar-day precision is the right
granularity for food). All timestamps are UTC ISO-8601.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, timezone
from typing import Any

CATEGORIES = [
    "produce",
    "fruit",
    "dairy",
    "protein",
    "grains",
    "leftovers",
    "frozen",
    "condiments",
    "beverages",
    "other",
]

STORAGE_LOCATIONS = ["fridge", "freezer", "pantry"]

# Rough USD value per typical retail unit, used ONLY to estimate money
# saved/wasted. These are estimates, never presented as actual prices.
EST_VALUE_PER_UNIT: dict[str, float] = {
    "produce": 2.2,
    "fruit": 2.5,
    "dairy": 3.0,
    "protein": 5.5,
    "grains": 1.8,
    "leftovers": 4.0,
    "frozen": 3.5,
    "condiments": 1.0,
    "beverages": 2.0,
    "other": 2.0,
}

_NAME_OK = re.compile(r"^[\w\s''\-.,/()]+$", re.UNICODE)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def today() -> date:
    return datetime.now(timezone.utc).date()


def normalize_name(raw: str) -> str:
    """Normalize an item name for matching ('Greek Yogurt' -> 'greek yogurt')."""
    s = unicodedata.normalize("NFKC", raw or "")
    s = s.strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def valid_item_name(raw: str) -> bool:
    s = (raw or "").strip()
    if not (1 <= len(s) <= 60):
        return False
    if any(unicodedata.category(ch) == "Cc" for ch in s):
        return False
    return bool(_NAME_OK.match(s))


_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "dairy": ("milk", "yogurt", "curd", "cheese", "paneer", "butter", "cream", "ghee"),
    "protein": ("chicken", "eggs", "egg", "fish", "prawn", "tofu", "mutton", "lamb", "beef", "dal", "lentil"),
    "produce": ("spinach", "tomato", "onion", "potato", "carrot", "beans", "greens", "kale", "lettuce", "cucumber", "capsicum", "broccoli", "cauliflower", "ginger", "garlic", "coriander", "pepper"),
    "fruit": ("banana", "apple", "mango", "berries", "berry", "grapes", "orange", "papaya", "watermelon", "pineapple", "guava"),
    "grains": ("rice", "bread", "pasta", "atta", "flour", "oats", "noodles", "tortilla", "chapati"),
    "leftovers": ("leftover", "cooked", "biryani", "curry", "dal makhani"),
    "frozen": ("frozen", "peas", "corn", "ice cream"),
    "condiments": ("sauce", "ketchup", "pickle", "masala", "spice", "oil", "soy", "honey", "jam"),
    "beverages": ("juice", "coffee", "tea", "soda", "water"),
}

# Sensible default shelf life (days) per category, used only when the user
# gives no date. Responses flag these as estimates.
DEFAULT_SHELF_DAYS: dict[str, int] = {
    "produce": 4,
    "fruit": 5,
    "dairy": 7,
    "protein": 3,
    "grains": 7,
    "leftovers": 3,
    "frozen": 90,
    "condiments": 180,
    "beverages": 14,
    "other": 7,
}


def infer_category(name: str) -> str:
    n = normalize_name(name)
    for cat, kws in _CATEGORY_KEYWORDS.items():
        if any(kw in n for kw in kws):
            if "leftover" in n or "cooked" in n:
                return "leftovers"
            return cat
    return "other"


def parse_iso_date(s: str) -> date | None:
    try:
        return date.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def days_until_expiry(item: dict[str, Any], ref: date | None = None) -> int | None:
    exp = item.get("expires_on")
    if not exp:
        return None
    d = parse_iso_date(exp)
    if d is None:
        return None
    return (d - (ref or today())).days


def freshness_status(days_left: int | None) -> str:
    """fresh | use_soon | urgent | expired | no_date."""
    if days_left is None:
        return "no_date"
    if days_left < 0:
        return "expired"
    if days_left <= 1:
        return "urgent"
    if days_left <= 3:
        return "use_soon"
    return "fresh"


def estimate_value(item: dict[str, Any]) -> float:
    """Rough USD value of an item, for waste/savings estimates only."""
    qty = float(item.get("quantity") or 1.0)
    per_unit = EST_VALUE_PER_UNIT.get(item.get("category", "other"), 2.0)
    unit = (item.get("unit") or "unit").lower()
    # Bulk weights are worth more than a single "unit".
    if unit in {"g", "grams", "kg"}:
        grams = qty * (1000 if unit == "kg" else 1)
        return round(per_unit * max(grams, 100) / 500, 2)
    if unit in {"l", "liter", "liters", "litre"}:
        return round(per_unit * max(qty, 0.25), 2)
    return round(per_unit * max(qty, 0.5), 2)


def new_item(
    name: str,
    quantity: float = 1.0,
    unit: str = "unit",
    category: str = "other",
    storage: str = "fridge",
    expires_on: str | None = None,
) -> dict[str, Any]:
    norm = normalize_name(name)
    return {
        "id": re.sub(r"[^a-z0-9]+", "-", norm).strip("-")[:40] or "item",
        "name": norm,
        "display_name": name.strip().title()[:80],
        "quantity": round(float(quantity), 2),
        "unit": unit.strip().lower()[:12] or "unit",
        "category": category if category in CATEGORIES else "other",
        "storage": storage if storage in STORAGE_LOCATIONS else "fridge",
        "added_at": utc_now_iso(),
        "expires_on": expires_on,
    }


def with_freshness(item: dict[str, Any], ref: date | None = None) -> dict[str, Any]:
    dl = days_until_expiry(item, ref)
    out = dict(item)
    out["days_left"] = dl
    out["status"] = freshness_status(dl)
    out["est_value_usd"] = estimate_value(item)
    return out
