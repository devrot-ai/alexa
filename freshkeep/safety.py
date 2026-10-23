"""Safety primitives: input validation, rate limiting, audit logging.

Design rules:
- Audit log records tool names + counts, NEVER raw utterance text.
- Errors returned to users are generic; detail goes to the log.
- All user-supplied strings pass validation before touching storage.
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from collections import deque

from .models import utc_now_iso

logger = logging.getLogger("freshkeep")

MAX_UTTERANCE_LEN = 500
MAX_NOTE_LEN = 200
MAX_ITEMS_PER_CALL = 12
MAX_LIST_ITEMS = 60
MAX_SHOPPING_ITEM_LEN = 80

# Characters that have no business in a shopping-list line or note.
_TEXT_BLOCKLIST = re.compile(r"[<>{}\x00-\x08\x0b\x0c\x0e-\x1f]")


class ValidationError(Exception):
    """Raised when input fails validation; message is safe to show users."""


def clean_utterance(text: str) -> str:
    t = (text or "").strip()
    if len(t) > MAX_UTTERANCE_LEN:
        raise ValidationError("Please keep requests under 500 characters.")
    if _TEXT_BLOCKLIST.search(t):
        raise ValidationError("That message contains characters I can't process.")
    return t


def clean_note(text: str) -> str:
    t = (text or "").strip()[:MAX_NOTE_LEN]
    return _TEXT_BLOCKLIST.sub("", t)


def clean_shopping_item(text: str) -> str:
    t = (text or "").strip()
    if not t or len(t) > MAX_SHOPPING_ITEM_LEN:
        raise ValidationError("Shopping-list items must be 1-80 characters.")
    if _TEXT_BLOCKLIST.search(t):
        raise ValidationError("Shopping-list items contain invalid characters.")
    return t


class RateLimiter:
    """Sliding-window limiter, keyed by client id."""

    def __init__(self, per_minute: int = 30) -> None:
        self.per_minute = per_minute
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, client_id: str) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self._hits.setdefault(client_id or "anonymous", deque())
            while q and now - q[0] > 60:
                q.popleft()
            if len(q) >= self.per_minute:
                return False
            q.append(now)
            return True


class AuditLog:
    """Append-only JSONL log. Deliberately PII-light: no utterance text."""

    def __init__(self, path: str = "data/audit.log") -> None:
        self.path = path
        self._lock = threading.Lock()

    def record(self, event: str, **fields) -> None:
        entry = {"ts": utc_now_iso(), "event": event}
        entry.update({k: v for k, v in fields.items() if v is not None})
        try:
            with self._lock:
                os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
                with open(self.path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:  # audit failure must never break the product
            logger.warning("audit_write_failed", exc_info=True)


audit = AuditLog(os.environ.get("FRESHKEEP_AUDIT_PATH", "data/audit.log"))
