#!/usr/bin/env python3
"""Live AWS verification suite for FreshKeep.

Proves the three optional AWS seams against real services:
  1. DynamoDB store roundtrip (creates the table if missing, on-demand).
  2. Bedrock router: utterance -> validated tool call.
  3. Textract: receipt photo -> LINE text -> parsed items (needs --receipt-image).

Usage:
  python scripts/verify_aws.py [--cleanup] [--receipt-image PATH]

Reads freshkeep/.env automatically. Exits non-zero on any hard failure.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import freshkeep.config  # noqa: E402  (loads .env)

RESULTS: list[tuple[str, str, str]] = []


def record(name: str, status: str, detail: str = "") -> None:
    RESULTS.append((name, status, detail))
    print(f"{status:5} {name}" + (f" — {detail}" if detail else ""))


def verify_dynamodb(cleanup: bool) -> None:
    name = "dynamodb-roundtrip"
    try:
        import boto3

        from freshkeep.config import settings
        from freshkeep.storage import DynamoStore, empty_household

        ddb = boto3.resource("dynamodb", region_name=settings.dynamo_region)
        table_name = settings.dynamo_table
        try:
            ddb.Table(table_name).table_status
        except Exception:
            ddb.create_table(
                TableName=table_name,
                KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST",
            )
            ddb.Table(table_name).wait_until_exists()
            record(name, "INFO", f"created table {table_name} (on-demand)")

        store = DynamoStore(table_name, settings.dynamo_region, "verify-hh", "Verify kitchen")
        doc = empty_household("verify-hh", "Verify kitchen")
        doc["items"] = [{"id": "spinach", "name": "spinach", "display_name": "Spinach",
                         "quantity": 1, "unit": "bunch", "category": "produce",
                         "storage": "fridge", "added_at": "2026-01-01T00:00:00+00:00",
                         "expires_on": "2026-01-05"}]
        store.save(doc)
        loaded = store.load()
        assert loaded["items"][0]["name"] == "spinach", "roundtrip mismatch"
        record(name, "PASS", f"save+load ok on table {table_name}")

        if cleanup:
            ddb.Table(table_name).delete()
            record(name, "INFO", "table deleted (--cleanup)")
    except Exception as exc:
        record(name, "FAIL", f"{exc.__class__.__name__}: {exc}")


def verify_bedrock() -> None:
    name = "bedrock-router"
    try:
        from freshkeep.bedrock import BedrockUnavailable, route_with_bedrock
        from freshkeep.config import settings

        utterance = "We just bought spinach, 500 g of yogurt, and chicken that expires in 2 days"
        route = route_with_bedrock(utterance, settings.bedrock_model_id, settings.bedrock_region)
        assert route.tool == "track_food", f"expected track_food, got {route.tool}"
        assert route.args.get("items"), "no items extracted by the model"
        record(name, "PASS", f"{settings.bedrock_model_id} -> {route.tool}({len(route.args['items'])} items)")
    except BedrockUnavailable as exc:
        record(name, "FAIL", f"BedrockUnavailable: {exc}")
    except Exception as exc:
        record(name, "FAIL", f"{exc.__class__.__name__}: {exc}")


def verify_textract(image_path: str) -> None:
    name = "textract-receipt"
    if not image_path:
        record(name, "SKIP", "pass --receipt-image PATH to test")
        return
    try:
        from freshkeep.receipts import extract_lines_with_textract, parse_receipt_text

        with open(image_path, "rb") as fh:
            data = fh.read()
        region = os.environ.get("FRESHKEEP_TEXTRACT_REGION", os.environ.get("AWS_REGION", "us-east-1"))
        lines = extract_lines_with_textract(data, region)
        parsed = parse_receipt_text("\n".join(lines))
        record(name, "PASS" if parsed["items"] else "FAIL",
               f"{len(lines)} lines -> {len(parsed['items'])} items: "
               + ", ".join(i['name'] for i in parsed['items'][:6]))
    except Exception as exc:
        record(name, "FAIL", f"{exc.__class__.__name__}: {exc}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cleanup", action="store_true", help="delete the DynamoDB table when done")
    ap.add_argument("--receipt-image", default="", help="path to a receipt photo for Textract")
    args = ap.parse_args()

    if not os.environ.get("AWS_ACCESS_KEY_ID") and not os.path.isfile(
            os.path.expanduser("~/.aws/credentials")):
        print("No AWS credentials found. See docs/AWS_SETUP.md (step 2).")
        return 2

    verify_dynamodb(args.cleanup)
    if os.environ.get("FRESHKEEP_BEDROCK", "1") == "1":
        verify_bedrock()
    else:
        record("bedrock-router", "SKIP", "FRESHKEEP_BEDROCK != 1")
    verify_textract(args.receipt_image)

    hard_failures = [r for r in RESULTS if r[1] == "FAIL"]
    print()
    print(f"{len(RESULTS) - len(hard_failures)}/{len(RESULTS)} checks passed.")
    return 1 if hard_failures else 0


if __name__ == "__main__":
    sys.exit(main())
