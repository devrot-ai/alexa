"""Receipt ingestion — a zero-effort entry path into track_food.

Two extraction paths, both honest about what they are:

1. `parse_receipt_text` — deterministic line parser for pasted receipt text.
   Always available; used for tests and the offline demo.
2. `extract_lines_with_textract` — real Amazon Textract adapter (env-gated,
   FRESHKEEP_TEXTRACT=1). Extracts LINE blocks from a receipt photo.

In both cases the parser only *proposes* items; the user confirms before
anything is tracked, and tracking itself flows through the same MCP
`track_food` tool as voice entry (visible in judge mode).
"""
from __future__ import annotations

import re
from typing import Any

MAX_LINES = 120
MAX_ITEMS = 12  # matches tools.MAX_ITEMS_PER_CALL

_NOISE = {
    "total", "subtotal", "sub total", "tax", "cash", "change", "card", "visa",
    "mastercard", "maestro", "rupay", "upi", "paytm", "gpay", "thank", "thanks",
    "receipt", "invoice", "inv", "date", "time", "bill", "amount", "paid", "balance",
    "gst", "cgst", "sgst", "igst", "vat", "round off", "roundoff", "discount",
    "savings", "you saved", "items", "item", "store", "welcome", "net", "net amt",
    "grand total", "cashier", "counter", "phone", "ph", "gstin", "fssai",
}

_UNITS = {"g", "kg", "l", "ml", "pcs", "pc", "pack", "packs", "bunch", "bag", "dozen", "can", "bottle", "box", "cup", "cups", "jar"}

_PRICE_TAIL = re.compile(r"^(.*?)\s+((?:rs\.?|₹|\$|€|£|inr|usd)?\s?\d{1,6}(?:\.\d{1,2})?)\s*$", re.IGNORECASE)
_QTY_HEAD = re.compile(r"^(\d+(?:\.\d+)?)\s*(?:x|\*|×)\s+(.+)$")
_UNIT_ALT = r"(?:g|kg|ml|l|pcs|pc|pack|packs|bunch|bag|dozen|can|bottle|box|cup|cups|jar)"
_QTY_UNIT = re.compile(rf"^(.*?)\s+(\d+(?:\.\d+)?)\s*({_UNIT_ALT})\.?$", re.IGNORECASE)
_QTY_UNIT_PRICE = re.compile(rf"^(.*?)\s+(\d+(?:\.\d+)?)\s*({_UNIT_ALT})\.?\s+((?:rs\.?|₹|\$|€|£)?\s?\d{{1,6}}(?:\.\d{{1,2}})?)$", re.IGNORECASE)


class ReceiptExtractionUnavailable(Exception):
    pass


def _is_noise(line: str) -> bool:
    low = line.lower().strip(" :-")
    if not low:
        return True
    if any(n == low or low.startswith(n) for n in _NOISE):
        return True
    # any standalone noise word ("BIG BAZAAR INV 8891")
    words = re.split(r"\W+", low)
    if any(w in _NOISE for w in words):
        return True
    # pure numbers, dates, times, barcodes
    if re.fullmatch(r"[\d\s.:\/\-#*]+", low):
        return True
    return False


_DATE_LIKE = re.compile(r"\d{1,2}\s*[\/.-]\s*\d{1,2}\s*[\/.-]\s*\d{2,4}|\d{1,2}:\d{2}")


def parse_receipt_text(text: str) -> dict[str, Any]:
    """Deterministic line parser. Returns proposed items + skip counts."""
    items: list[dict[str, Any]] = []
    skipped_noise = 0
    skipped_cap = 0

    lines = (text or "").splitlines()[:MAX_LINES]
    # Receipt header heuristic: everything before the first date/time line is
    # store branding, not merchandise.
    header_until = 0
    for idx, ln in enumerate(lines):
        if _DATE_LIKE.search(ln):
            header_until = idx
            break

    for pos, raw_line in enumerate(lines):
        line = raw_line.strip()
        if not line:
            continue
        if pos < header_until:
            skipped_noise += 1
            continue
        if len(items) >= MAX_ITEMS:
            skipped_cap += 1
            continue
        if _is_noise(line) or len(line) > 80:
            skipped_noise += 1
            continue

        name_part, qty, unit, price = line, 1.0, "unit", None

        m = _QTY_HEAD.match(line)
        if m:
            qty = float(m.group(1))
            name_part = m.group(2)

        # quantity+unit+price ("milk 1 l 70", "rice 5 kg ₹480")
        m = _QTY_UNIT_PRICE.match(name_part)
        if m and m.group(1).strip():
            name_part, qty, unit = m.group(1).strip(), float(m.group(2)), m.group(3).lower()
            try:
                price = float(re.sub(r"[^\d.]", "", m.group(4)) or 0) or None
            except ValueError:
                price = None
        else:
            # trailing quantity+unit without price ("milk 1 l")
            m = _QTY_UNIT.match(name_part)
            if m and m.group(1).strip():
                name_part, qty, unit = m.group(1).strip(), float(m.group(2)), m.group(3).lower()

            # trailing price ("spinach 25.00", "eggs ₹60")
            m = _PRICE_TAIL.match(name_part)
            if m:
                head = m.group(1).strip()
                tail = m.group(2).strip()
                head_last = head.split()[-1].lower().rstrip(".") if head.split() else ""
                if head and head_last not in _UNITS and not re.fullmatch(r"[\d.]+", head):
                    try:
                        price = float(re.sub(r"[^\d.]", "", tail) or 0) or None
                    except ValueError:
                        price = None
                    name_part = head

        # sanitize name for downstream validation
        name = re.sub(r"[^ \w''\-.,/()]", "", name_part, flags=re.UNICODE).strip()
        name = re.sub(r"\s+", " ", name)
        if not name or len(name) > 60 or _is_noise(name):
            skipped_noise += 1
            continue

        entry: dict[str, Any] = {"name": name[:60], "quantity": qty, "unit": unit}
        if price:
            entry["price_seen"] = round(price, 2)
        items.append(entry)

    return {"items": items, "skipped_noise": skipped_noise, "skipped_over_cap": skipped_cap}


def extract_lines_with_textract(image_bytes: bytes, region: str) -> list[str]:
    """Real Amazon Textract LINE extraction (opt-in, FRESHKEEP_TEXTRACT=1)."""
    if not image_bytes or len(image_bytes) > 4_000_000:
        raise ReceiptExtractionUnavailable("Image missing or larger than 4 MB.")
    try:
        import boto3
    except ImportError as exc:
        raise ReceiptExtractionUnavailable("boto3 not installed") from exc
    client = boto3.client("textract", region_name=region)
    try:
        resp = client.detect_document_text(Document={"Bytes": image_bytes})
    except Exception as exc:
        raise ReceiptExtractionUnavailable(exc.__class__.__name__) from exc
    return [b["Text"] for b in resp.get("Blocks", []) if b.get("BlockType") == "LINE"]
