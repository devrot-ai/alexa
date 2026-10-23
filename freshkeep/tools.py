"""FreshKeep tool implementations — the single source of truth.

These pure functions are called by:
1. the MCP server (freshkeep/mcpserver.py), and
2. the optional Bedrock router (via the same schemas).

Every function returns a JSON-serializable dict with {"ok": bool, ...}.
"""
from __future__ import annotations

import re
import threading
from typing import Any

from . import rescue
from .models import (
    CATEGORIES,
    STORAGE_LOCATIONS,
    days_until_expiry,
    new_item,
    normalize_name,
    parse_iso_date,
    today,
    utc_now_iso,
    valid_item_name,
    with_freshness,
)
from .safety import MAX_ITEMS_PER_CALL, MAX_LIST_ITEMS, ValidationError, audit, clean_note
from .storage import Store, empty_household

_lock = threading.RLock()

DELETE_PHRASE = "delete all freshkeep data"


# ---------------------------------------------------------------- helpers
def _find_item(doc: dict[str, Any], name: str) -> dict[str, Any] | None:
    n = normalize_name(name)
    for it in doc["items"]:
        if it["name"] == n:
            return it
    for it in doc["items"]:
        if n in it["name"] or it["name"] in n:
            return it
    return None


def _err(user_msg: str, code: str = "error") -> dict[str, Any]:
    return {"ok": False, "error": code, "message": user_msg}


# ---------------------------------------------------------------- tools
def track_food(store: Store, items: list[dict[str, Any]], note: str = "") -> dict[str, Any]:
    """Add (or merge) groceries into the household memory."""
    if not isinstance(items, list) or not items:
        return _err("Tell me what you bought, e.g. 'spinach and 500 g of yogurt'.", "no_items")
    if len(items) > MAX_ITEMS_PER_CALL:
        return _err(f"Please add at most {MAX_ITEMS_PER_CALL} items at a time.", "too_many_items")

    added, updated, rejected = [], [], []
    with _lock:
        doc = store.load()
        for raw in items:
            if not isinstance(raw, dict):
                rejected.append({"input": str(raw)[:40], "reason": "not_an_object"})
                continue
            name = str(raw.get("name", "")).strip()
            if not valid_item_name(name):
                rejected.append({"input": name[:40], "reason": "invalid_name"})
                continue

            qty = raw.get("quantity", 1)
            try:
                qty = max(0.1, min(float(qty), 10000))
            except (TypeError, ValueError):
                qty = 1.0
            unit = str(raw.get("unit", "unit"))[:12].strip().lower() or "unit"
            category = str(raw.get("category", "other")).strip().lower()
            if category not in CATEGORIES:
                category = "other"
            storage = str(raw.get("storage", "fridge")).strip().lower()
            if storage not in STORAGE_LOCATIONS:
                storage = "fridge"

            from .models import DEFAULT_SHELF_DAYS, infer_category

            if category == "other":
                category = infer_category(name)

            expires_on = None
            expiry_estimated = False
            if raw.get("expires_on"):
                if parse_iso_date(str(raw["expires_on"])):
                    expires_on = str(raw["expires_on"])
            elif raw.get("expires_in_days") is not None:
                try:
                    d = int(raw["expires_in_days"])
                    if 0 <= d <= 730:
                        from datetime import timedelta

                        expires_on = (today() + timedelta(days=d)).isoformat()
                except (TypeError, ValueError):
                    pass
            if expires_on is None:
                # No date given: apply category-based shelf-life estimate and
                # flag it as an estimate in the response (never claimed as fact).
                from datetime import timedelta

                expires_on = (today() + timedelta(days=DEFAULT_SHELF_DAYS.get(category, 7))).isoformat()
                expiry_estimated = True

            existing = _find_item(doc, name)
            if existing:
                # Unit-aware merge: only add quantities when units are
                # comparable; a generic mention refreshes the existing item.
                old_unit = existing.get("unit", "unit")
                if unit == old_unit:
                    existing["quantity"] = round(existing["quantity"] + qty, 2)
                elif unit != "unit" and old_unit == "unit":
                    existing["quantity"] = round(qty, 2)
                    existing["unit"] = unit
                # else: keep existing quantity/unit (mention without measure)
                if expires_on:
                    existing["expires_on"] = expires_on
                existing["category"] = category
                existing["storage"] = storage
                enriched = with_freshness(existing)
                enriched["expiry_estimated"] = expiry_estimated
                updated.append(enriched)
            else:
                it = new_item(name, qty, unit, category, storage, expires_on)
                doc["items"].append(it)
                enriched = with_freshness(it)
                enriched["expiry_estimated"] = expiry_estimated
                added.append(enriched)
        store.save(doc)

    audit.record("track_food", added=len(added), updated=len(updated), rejected=len(rejected))
    return {
        "ok": True,
        "added": added,
        "updated": updated,
        "rejected": rejected,
        "note": clean_note(note),
        "reply_hint": f"Tracked {len(added)} new item(s), updated {len(updated)}.",
    }


def list_pantry(store: Store, status: str = "all", category: str = "") -> dict[str, Any]:
    doc = store.load()
    items = [with_freshness(it) for it in doc["items"]]
    if status and status != "all":
        items = [it for it in items if it["status"] == status]
    if category:
        items = [it for it in items if it["category"] == category.lower()]
    order = {"expired": 0, "urgent": 1, "use_soon": 2, "fresh": 3, "no_date": 4}
    items.sort(key=lambda x: (order.get(x["status"], 5), x["days_left"] if x["days_left"] is not None else 999))
    audit.record("list_pantry", count=len(items))
    return {"ok": True, "count": len(items), "items": items}


def rescue_queue(store: Store, within_days: int = 2) -> dict[str, Any]:
    try:
        window = max(0, min(int(within_days), 14))
    except (TypeError, ValueError):
        window = 2
    doc = store.load()
    items = [with_freshness(it) for it in rescue.at_risk_items(doc["items"], window)]
    total_at_risk = round(sum(it["est_value_usd"] for it in items), 2)
    audit.record("rescue_queue", count=len(items), window=window)
    return {
        "ok": True,
        "within_days": window,
        "count": len(items),
        "items": items,
        "value_at_risk_usd": total_at_risk,
    }


def plan_rescue_meal(store: Store, max_missing: int = 2) -> dict[str, Any]:
    try:
        mm = max(0, min(int(max_missing), 4))
    except (TypeError, ValueError):
        mm = 2
    doc = store.load()
    plan = rescue.plan_rescue(doc["items"], within_days=2, max_missing=mm)
    if plan.get("has_plan"):
        with _lock:
            doc = store.load()
            # De-dupe: asking for the same plan twice must not double-count.
            last = doc["rescue_log"][-1] if doc["rescue_log"] else None
            same_as_last = bool(
                last
                and last.get("recipe") == plan["recipe_key"]
                and sorted(last.get("items", [])) == sorted(r["name"] for r in plan["rescued_items"])
            )
            if same_as_last:
                return {"ok": True, "plan": plan, "already_logged": True}
            doc["rescue_log"].append(
                {
                    "at": utc_now_iso(),
                    "recipe": plan["recipe_key"],
                    "items": [r["name"] for r in plan["rescued_items"]],
                    "est_saved_usd": plan["estimated_savings_usd"],
                }
            )
            doc["rescue_log"] = doc["rescue_log"][-50:]
            store.save(doc)
        audit.record("plan_rescue_meal", recipe=plan["recipe_key"], missing=len(plan["missing"]))
    return {"ok": True, "plan": plan}


def add_to_shopping_list(store: Store, items: list[str]) -> dict[str, Any]:
    if not isinstance(items, list) or not items:
        return _err("Tell me what to add to the shopping list.", "no_items")
    if len(items) > MAX_ITEMS_PER_CALL:
        return _err(f"Please add at most {MAX_ITEMS_PER_CALL} items at a time.", "too_many_items")
    from .safety import clean_shopping_item

    try:
        cleaned = [clean_shopping_item(str(i)) for i in items]
    except ValidationError as exc:
        return _err(str(exc), "invalid_item")
    added = []
    with _lock:
        doc = store.load()
        existing = {normalize_name(e["name"]) for e in doc["shopping_list"]}
        for name in cleaned:
            if normalize_name(name) in existing:
                continue
            if len(doc["shopping_list"]) >= MAX_LIST_ITEMS:
                return _err("Shopping list is full (60 items). Clear it first.", "list_full")
            entry = {"name": name, "added_at": utc_now_iso(), "source": "freshkeep"}
            doc["shopping_list"].append(entry)
            existing.add(normalize_name(name))
            added.append(name)
        store.save(doc)
    audit.record("add_to_shopping_list", added=len(added))
    return {"ok": True, "added": added, "reply_hint": f"Added {len(added)} item(s) to the shopping list."}


def get_shopping_list(store: Store) -> dict[str, Any]:
    doc = store.load()
    audit.record("get_shopping_list", count=len(doc["shopping_list"]))
    return {"ok": True, "count": len(doc["shopping_list"]), "items": doc["shopping_list"]}


def clear_shopping_list(store: Store) -> dict[str, Any]:
    with _lock:
        doc = store.load()
        n = len(doc["shopping_list"])
        doc["shopping_list"] = []
        store.save(doc)
    audit.record("clear_shopping_list", cleared=n)
    return {"ok": True, "cleared": n}


def mark_used(store: Store, name: str) -> dict[str, Any]:
    with _lock:
        doc = store.load()
        it = _find_item(doc, name or "")
        if not it:
            return _err(f"I couldn't find '{(name or '')[:40]}' in your kitchen.", "not_found")
        doc["items"].remove(it)
        store.save(doc)
    audit.record("mark_used")
    return {"ok": True, "removed": with_freshness(it), "reply_hint": f"Used up {it['display_name']}."}


def mark_thrown(store: Store, name: str, reason: str = "") -> dict[str, Any]:
    with _lock:
        doc = store.load()
        it = _find_item(doc, name or "")
        if not it:
            return _err(f"I couldn't find '{(name or '')[:40]}' in your kitchen.", "not_found")
        doc["items"].remove(it)
        doc["waste_log"].append(
            {
                "at": utc_now_iso(),
                "name": it["display_name"],
                "est_value_usd": round(with_freshness(it)["est_value_usd"], 2),
                "reason": clean_note(reason)[:80],
            }
        )
        doc["waste_log"] = doc["waste_log"][-100:]
        store.save(doc)
    audit.record("mark_thrown")
    return {"ok": True, "thrown": it["display_name"], "reply_hint": f"Noted. {it['display_name']} is gone — I'll count it in the waste report."}


def waste_report(store: Store) -> dict[str, Any]:
    doc = store.load()
    wasted = round(sum(w["est_value_usd"] for w in doc["waste_log"]), 2)
    rescued = round(sum(r.get("est_saved_usd", 0) for r in doc["rescue_log"]), 2)
    at_risk = rescue.at_risk_items(doc["items"], 2)
    value_at_risk = round(sum(with_freshness(it)["est_value_usd"] for it in at_risk), 2)
    audit.record("waste_report")
    return {
        "ok": True,
        "wasted_usd_estimate": wasted,
        "wasted_items": len(doc["waste_log"]),
        "rescued_usd_estimate": rescued,
        "rescue_meals_planned": len(doc["rescue_log"]),
        "value_at_risk_usd": value_at_risk,
        "note": "All amounts are rough demo estimates, not store prices.",
    }


def household_summary(store: Store) -> dict[str, Any]:
    doc = store.load()
    items = [with_freshness(it) for it in doc["items"]]
    by_status: dict[str, int] = {}
    for it in items:
        by_status[it["status"]] = by_status.get(it["status"], 0) + 1
    return {
        "ok": True,
        "household": doc.get("name"),
        "item_count": len(items),
        "by_status": by_status,
        "shopping_list_count": len(doc["shopping_list"]),
        "consent": doc.get("consent"),
        "backend": store.backend_name(),
    }


def delete_all_my_data(store: Store, confirm_phrase: str) -> dict[str, Any]:
    if (confirm_phrase or "").strip().lower() != DELETE_PHRASE:
        return _err(
            "For safety, data deletion needs explicit confirmation. Say 'yes, delete everything' to FreshKeep.",
            "confirmation_required",
        )
    with _lock:
        doc = empty_household(store.load()["household_id"], store.load().get("name", ""))
        doc["consent"] = False  # consent must be re-given
        store.save(doc)
    audit.record("delete_all_my_data")
    return {"ok": True, "reply_hint": "All FreshKeep data for this household has been deleted."}


def set_consent(store: Store, consent: bool) -> dict[str, Any]:
    with _lock:
        doc = store.load()
        doc["consent"] = bool(consent)
        doc["consented_at"] = utc_now_iso() if consent else None
        store.save(doc)
    audit.record("consent", granted=bool(consent))
    return {"ok": True, "consent": bool(consent)}


# ---------------------------------------------------------------- schemas
# JSON Schemas shared by the MCP server and the (optional) Bedrock router.
_ITEM_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "minLength": 1, "maxLength": 60},
        "quantity": {"type": "number", "minimum": 0.1, "maximum": 10000},
        "unit": {"type": "string", "maxLength": 12},
        "category": {"type": "string", "enum": CATEGORIES},
        "storage": {"type": "string", "enum": STORAGE_LOCATIONS},
        "expires_in_days": {"type": "integer", "minimum": 0, "maximum": 730},
        "expires_on": {"type": "string", "description": "YYYY-MM-DD"},
    },
    "required": ["name"],
}

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "track_food",
        "description": "Record groceries the household just bought so FreshKeep can track freshness.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "items": {"type": "array", "items": _ITEM_INPUT_SCHEMA, "minItems": 1, "maxItems": 12},
                "note": {"type": "string", "maxLength": 200},
            },
            "required": ["items"],
        },
    },
    {
        "name": "list_pantry",
        "description": "List what is currently in the kitchen, optionally filtered by freshness status or category.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["all", "fresh", "use_soon", "urgent", "expired", "no_date"]},
                "category": {"type": "string"},
            },
        },
    },
    {
        "name": "rescue_queue",
        "description": "Show items close to expiring ('what needs rescuing'), most urgent first.",
        "inputSchema": {
            "type": "object",
            "properties": {"within_days": {"type": "integer", "minimum": 0, "maximum": 14}},
        },
    },
    {
        "name": "plan_rescue_meal",
        "description": "Produce a concrete meal plan that uses up the items closest to expiring, plus any missing ingredients.",
        "inputSchema": {
            "type": "object",
            "properties": {"max_missing": {"type": "integer", "minimum": 0, "maximum": 4}},
        },
    },
    {
        "name": "add_to_shopping_list",
        "description": "Append items to the household shopping list.",
        "inputSchema": {
            "type": "object",
            "properties": {"items": {"type": "array", "items": {"type": "string", "maxLength": 80}, "minItems": 1, "maxItems": 12}},
            "required": ["items"],
        },
    },
    {
        "name": "get_shopping_list",
        "description": "Read the current household shopping list.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "clear_shopping_list",
        "description": "Empty the shopping list (e.g. after shopping).",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "mark_used",
        "description": "Remove an item because it was cooked or eaten.",
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string", "minLength": 1, "maxLength": 60}},
            "required": ["name"],
        },
    },
    {
        "name": "mark_thrown",
        "description": "Remove an item because it was thrown away, and log it in the waste report.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "minLength": 1, "maxLength": 60},
                "reason": {"type": "string", "maxLength": 80},
            },
            "required": ["name"],
        },
    },
    {
        "name": "waste_report",
        "description": "Summarize estimated money wasted vs rescued.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "household_summary",
        "description": "Quick status of the kitchen memory.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "delete_all_my_data",
        "description": "Permanently delete all FreshKeep data. Requires the explicit confirmation phrase.",
        "inputSchema": {
            "type": "object",
            "properties": {"confirm_phrase": {"type": "string"}},
            "required": ["confirm_phrase"],
        },
    },
    {
        "name": "set_consent",
        "description": "Grant or withdraw consent to store household kitchen data.",
        "inputSchema": {
            "type": "object",
            "properties": {"consent": {"type": "boolean"}},
            "required": ["consent"],
        },
    },
]
