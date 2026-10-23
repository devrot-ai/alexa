"""Deterministic utterance -> tool router.

This router keeps the core demo 100% reliable: no LLM needed.
When Bedrock mode is enabled, bedrock.py is tried first and this router is
the automatic fallback (and is also what judges can switch to explicitly).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Route:
    intent: str
    tool: str | None
    args: dict[str, Any] = field(default_factory=dict)
    needs_confirmation: bool = False
    reply: str | None = None  # set when no tool call is needed
    mode: str = "deterministic"
    confidence: float = 1.0


_QTY_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(kg|kgs|g|grams?|l|liters?|litres?|pcs|pieces?|packs?|bunch(?:es)?|bags?|cans?|bottles?|boxes?|cartons?|dozen|cups?|jars?)?\s*(?:of\s+)?(.*)$", re.IGNORECASE)
_A_RE = re.compile(r"^\s*(?:a|an|some|one|1)\s+(bag|bunch|pack|box|can|bottle|carton|dozen|jar|cup)\s+of\s+(.*)$", re.IGNORECASE)
_SPLIT_RE = re.compile(r"\s*(?:,| and |\+|;)\s*", re.IGNORECASE)
_BUY_RE = re.compile(r"\b(?:i|we)\s+(?:just\s+)?(?:bought|got|picked\s+up|purchased|added)|\bjust\s+bought|\btrack(?:ing)?\b|\bwe\s+have\s+(?:some\s+)?|\bwe'?ve\s+got\b|\badd(?:ing)?\s+(?:some\s+)?(?:to\s+)?(?:the\s+)?(?:fridge|pantry)\b", re.IGNORECASE)
_EXPIRY_RE = re.compile(r"\b(?:expires?|use\s+by|good\s+(?:for|until|till)|lasts?)\s+(?:in\s+)?(\d{1,3})\s*(?:days?|d)\b|\bin\s+(\d{1,3})\s+days\b", re.IGNORECASE)

HELP_REPLY = (
    "I'm FreshKeep, your kitchen's memory. Try: 'We just bought spinach, 500 g of yogurt, "
    "and chicken that expires in 2 days' • 'What needs rescuing?' • 'Plan a rescue meal' • "
    "'Add soy sauce to the shopping list' • 'Waste report' • 'Delete my data'."
)


def _parse_items_from_text(text: str) -> tuple[list[dict[str, Any]], int | None]:
    """Parse 'spinach, 500 g yogurt and chicken that expires in 2 days'."""
    expires_default: int | None = None
    m = _EXPIRY_RE.search(text)
    if m:
        expires_default = int(m.group(1) or m.group(2))
        text = text[: m.start()] + text[m.end():]

    items: list[dict[str, Any]] = []
    for chunk in _SPLIT_RE.split(text):
        chunk = chunk.strip(" \t-")
        if not chunk or len(chunk) > 60:
            continue
        qty, unit, name = 1.0, "unit", chunk
        m = _QTY_RE.match(chunk)
        if m and m.group(3):
            qty = float(m.group(1))
            unit = (m.group(2) or "unit").lower()
            name = m.group(3)
        else:
            m2 = _A_RE.match(chunk)
            if m2:
                unit = m2.group(1).lower()
                name = m2.group(2)
        name = name.strip(" .,")
        if name and not re.fullmatch(r"[\w\s''\-.,/()]+", name, re.UNICODE):
            continue
        if name.lower() in {"some", "the", "and", "of"}:
            continue
        entry: dict[str, Any] = {"name": name[:60], "quantity": qty, "unit": unit}
        if expires_default is not None:
            entry["expires_in_days"] = expires_default
        items.append(entry)
    return items[:12], expires_default


def route(utterance: str) -> Route:
    text = (utterance or "").strip()
    low = text.lower()

    if not low:
        return Route("empty", None, reply="I didn't catch that. Try 'What needs rescuing?'")

    if any(w in low for w in ("help", "what can you do", "how do you work")):
        return Route("help", None, reply=HELP_REPLY)

    # --- deletion (two-step confirmation handled by the caller) ---
    if re.search(r"\b(delete|erase|wipe|forget)\b.*\b(data|everything|all)\b|\bdelete\s+my\s+data\b", low):
        return Route("delete", "delete_all_my_data", needs_confirmation=True)

    # --- consent withdrawal ---
    if re.search(r"\bwithdraw\b.*\bconsent\b|\brevoke\b.*\bconsent\b", low):
        return Route("consent", "set_consent", args={"consent": False})

    # --- waste report ---
    if re.search(r"\bwaste\s+report\b|\bhow\s+much\b.*\b(wasted|saved)\b|\bstats\b|\bmy\s+impact\b", low):
        return Route("report", "waste_report")

    # --- tracking groceries (checked early: an utterance like "we bought X
    # that expires in 2 days" states a date, it is not a rescue question) ---
    if _BUY_RE.search(low) and not re.search(r"\bwhat\b|\bwhich\b|\?", low):
        remainder = _BUY_RE.sub(" ", text, count=1).strip(" :,")
        items, _ = _parse_items_from_text(remainder or text)
        if items:
            return Route("track", "track_food", args={"items": items})

    # --- rescue meal planning ---
    if re.search(r"\b(plan|suggest|what\s+(?:should|can)\s+(?:i|we)\s+(?:cook|make|eat))\b.*\b(rescue|meal|dinner|lunch|food)\b|\brescue\s+(?:meal|dinner|recipe|plan)\b|\bplan\s+a\s+rescue\b|\bwhat's\s+for\s+dinner\b|\bcook(?:ing)?\s+suggestion\b", low):
        return Route("plan", "plan_rescue_meal", args={"max_missing": 2})

    # --- rescue queue ---
    if re.search(r"\brescu(e|ing)\b|\bexpir\w*\b|\bgoing\s+bad\b|\babout\s+to\s+spoil\b|\buse\s+(?:it\s+)?up\b|\bwhat\s+should\s+i\s+save\b|\bdying\b|\bspoil\w*\b", low):
        return Route("rescue_queue", "rescue_queue", args={"within_days": 2})

    # --- shopping list read/write ---
    if re.search(r"\bshopping\s+list\b|\bgrocery\s+list\b", low):
        if re.search(r"\b(clear|empty|reset)\b", low):
            return Route("shopping_clear", "clear_shopping_list")
        m = re.search(r"\badd\s+(.+?)\s+to\s+(?:the\s+)?(?:shopping\s+|grocery\s+)?list\b", low)
        if m:
            names = [p.strip() for p in re.split(r",| and ", m.group(1)) if p.strip()][:12]
            return Route("shopping_add", "add_to_shopping_list", args={"items": names})
        return Route("shopping_get", "get_shopping_list")
    m = re.search(r"\badd\s+(.+)\s+to\s+(?:the\s+)?list\b", low)
    if m and "shopping" not in low:
        names = [p.strip() for p in re.split(r",| and ", m.group(1)) if p.strip()][:12]
        if names:
            return Route("shopping_add", "add_to_shopping_list", args={"items": names})

    # --- mark used / thrown ---
    m = re.search(r"\b(?:used\s+up|finished|ate|cooked|we\s+had)\s+(?:the\s+|my\s+|our\s+)?(.+)$", low)
    if m:
        return Route("used", "mark_used", args={"name": m.group(1).strip(".")[:60]})
    m = re.search(r"\b(?:threw\s+away|thrown\s+away|tossed|trashed|wasted)\s+(?:the\s+)?(.+)$", low)
    if m:
        return Route("thrown", "mark_thrown", args={"name": m.group(1).strip(".")[:60], "reason": "spoiled"})
    if re.search(r"\bwent\s+bad\b|\bspoiled\b", low):
        m = re.search(r"\b(the\s+)?(.+?)\s+(?:went\s+bad|spoiled)\b", low)
        if m:
            return Route("thrown", "mark_thrown", args={"name": m.group(2)[:60], "reason": "spoiled"})

    # --- pantry listing ---
    if re.search(r"\bwhat\s+do\s+(?:i|we)\s+have\b|\bin\s+the\s+(?:fridge|pantry|kitchen)\b|\bpantry\b|\binventory\b|\bwhat'?s\s+in\s+the\b", low):
        status = "all"
        if re.search(r"\burgent\b|\bexpir\w*\b", low):
            status = "urgent"
        return Route("pantry", "list_pantry", args={"status": status})

    if re.search(r"\b(summary|status|how\s+is\s+the\s+kitchen)\b", low):
        return Route("summary", "household_summary")

    return Route(
        "fallback",
        None,
        reply=(
            "I can track groceries, find food about to expire, and plan rescue meals. "
            "Try 'We just bought spinach and yogurt' or 'What needs rescuing?'"
        ),
        confidence=0.0,
    )
