"""Storage backends for FreshKeep.

Two backends share one interface:
- JsonFileStore  : zero-dependency local file (default; great for demos/tests)
- DynamoStore    : Amazon DynamoDB via boto3 (opt-in with FRESHKEEP_STORE=dynamodb)

Both store one document per household: items, shopping list, waste log,
rescue log, consent state.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
from typing import Any, Protocol

from .config import settings
from .models import utc_now_iso


def empty_household(household_id: str, name: str) -> dict[str, Any]:
    return {
        "household_id": household_id,
        "name": name,
        "consent": False,
        "consented_at": None,
        "created_at": utc_now_iso(),
        "items": [],
        "shopping_list": [],
        "waste_log": [],
        "rescue_log": [],
    }


class Store(Protocol):
    def load(self) -> dict[str, Any]: ...
    def save(self, doc: dict[str, Any]) -> None: ...
    def backend_name(self) -> str: ...


class JsonFileStore:
    """Atomic JSON-file store. Fine for a single household; DynamoDB for scale."""

    def __init__(self, path: str, household_id: str, household_name: str) -> None:
        self.path = path
        self.household_id = household_id
        self.household_name = household_name
        self._lock = threading.RLock()

    def load(self) -> dict[str, Any]:
        with self._lock:
            try:
                with open(self.path, encoding="utf-8") as fh:
                    return json.load(fh)
            except (FileNotFoundError, json.JSONDecodeError):
                return empty_household(self.household_id, self.household_name)

    def save(self, doc: dict[str, Any]) -> None:
        with self._lock:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=os.path.dirname(self.path) or ".", suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    json.dump(doc, fh, ensure_ascii=False, indent=1)
                os.replace(tmp, self.path)
            finally:
                if os.path.exists(tmp):
                    os.remove(tmp)

    def backend_name(self) -> str:
        return "json-file"


class DynamoStore:
    """DynamoDB single-table-document store (item pk = household id)."""

    def __init__(self, table: str, region: str, household_id: str, household_name: str) -> None:
        import boto3  # lazy: not needed for the default local demo

        self._table_name = table
        self.household_id = household_id
        self.household_name = household_name
        self._table = boto3.resource("dynamodb", region_name=region).Table(table)
        self._lock = threading.RLock()

    def load(self) -> dict[str, Any]:
        from boto3.dynamodb.types import TypeDeserializer

        resp = self._table.get_item(Key={"pk": self.household_id})
        if "Item" not in resp:
            return empty_household(self.household_id, self.household_name)
        item = resp["Item"]
        doc_raw = item.get("doc")
        if isinstance(doc_raw, str):
            return json.loads(doc_raw)
        return TypeDeserializer().deserialize({"M": doc_raw})

    def save(self, doc: dict[str, Any]) -> None:
        with self._lock:
            self._table.put_item(
                Item={"pk": self.household_id, "doc": json.dumps(doc, ensure_ascii=False)}
            )

    def backend_name(self) -> str:
        return f"dynamodb:{self._table_name}"


def make_store() -> Store:
    if settings.store_backend == "dynamodb":
        return DynamoStore(
            settings.dynamo_table,
            settings.dynamo_region,
            settings.household_id,
            settings.household_name,
        )
    return JsonFileStore(settings.json_path, settings.household_id, settings.household_name)
