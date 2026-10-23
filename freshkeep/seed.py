"""Seeded demo data — a realistic week in a demo kitchen.

Expiry dates are set relative to "today" so the rescue queue is always
interesting for judges, whenever they run the demo.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from .models import new_item, today


def _d(days: int) -> str:
    return (today() + timedelta(days=days)).isoformat()


def seed_items() -> list[dict[str, Any]]:
    return [
        new_item("spinach", 1, "bunch", "produce", "fridge", _d(1)),
        new_item("cooked rice (leftover)", 2, "cups", "leftovers", "fridge", _d(1)),
        new_item("greek yogurt", 500, "g", "dairy", "fridge", _d(2)),
        new_item("chicken breast", 400, "g", "protein", "fridge", _d(2)),
        new_item("tomatoes", 4, "pcs", "produce", "fridge", _d(4)),
        new_item("milk", 1, "l", "dairy", "fridge", _d(6)),
        new_item("eggs", 6, "pcs", "protein", "fridge", _d(12)),
        new_item("basmati rice", 5, "kg", "grains", "pantry", _d(180)),
        new_item("frozen peas", 1, "kg", "frozen", "freezer", _d(90)),
        new_item("eggs", 6, "pcs", "protein", "fridge", _d(12)),  # dup removed by loader
    ]


def seed_shopping_list() -> list[dict[str, Any]]:
    return []


def seed_household_doc(household_id: str, name: str) -> dict[str, Any]:
    from .storage import empty_household
    from .models import utc_now_iso

    doc = empty_household(household_id, name)
    doc["consent"] = True
    doc["consented_at"] = utc_now_iso()
    # de-dupe by id
    seen: set[str] = set()
    for it in seed_items():
        if it["id"] in seen:
            continue
        seen.add(it["id"])
        doc["items"].append(it)
    return doc
