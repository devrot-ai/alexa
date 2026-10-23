"""Simulated Alexa+ experience for FreshKeep (officially permitted track path).

The web app is a real MCP *client*: every chat turn calls the FreshKeep
MCP server over Streamable HTTP. Judge mode shows the exact tool calls,
arguments, and structured results for every turn.

Run:  python -m freshkeep.simulator.app
"""
from __future__ import annotations

import logging
import os
import re
import time
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from ..config import settings
from ..mcpclient import LocalInvoker, McpInvoker
from ..router import route as deterministic_route, Route
from ..safety import RateLimiter, ValidationError, clean_utterance, audit
from ..seed import seed_household_doc
from ..storage import make_store
from ..tools import DELETE_PHRASE

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("freshkeep.simulator")

app = FastAPI(title="FreshKeep — simulated Alexa+ experience", version="0.1.0")

_static_dir = os.path.join(os.path.dirname(__file__), "static")
_limiter = RateLimiter(settings.rate_limit_per_minute)
_pending: dict[str, dict[str, Any]] = {}  # client_id -> pending action

USE_LOCAL = os.environ.get("FRESHKEEP_SIM_LOCAL") == "1"
BEDROCK_MODE = settings.bedrock_enabled


def make_invoker():
    if USE_LOCAL:
        return LocalInvoker()
    return McpInvoker(os.environ.get("FRESHKEEP_MCP_URL", settings.mcp_url))


invoker = make_invoker()
store = make_store()  # only for demo seed/reset controls, never for agent calls


# ------------------------------------------------------------------ replies
def _days_phrase(d: int | None) -> str:
    if d is None:
        return "no date set"
    if d < 0:
        return f"expired {-d} day(s) ago"
    if d == 0:
        return "expires today"
    if d == 1:
        return "expires tomorrow"
    return f"{d} days left"


def format_reply(intent: str, result: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """(spoken-style text, structured payload for UI cards)."""
    if not result.get("ok"):
        return result.get("message", "Something went wrong — please try again."), {}

    if intent == "track":
        lines = []
        for it in result.get("added", []) + result.get("updated", []):
            est = " (estimate)" if it.get("expiry_estimated") else ""
            lines.append(f"{it['display_name']} — {_days_phrase(it.get('days_left'))}{est}")
        reply = f"Got it. Tracking {len(result.get('added', []))} new item(s)."
        if result.get("updated"):
            reply += f" Updated {len(result['updated'])} already in the kitchen."
        if lines:
            reply += " " + " · ".join(lines[:6])
        if result.get("rejected"):
            reply += f" (Skipped {len(result['rejected'])} unparseable item(s).)"
        return reply, {"tracked": result.get("added", []) + result.get("updated", [])}

    if intent == "rescue_queue":
        if result.get("count", 0) == 0:
            return "Nothing is close to expiring — your kitchen is in great shape!", {}
        lines = [f"{it['display_name']} ({_days_phrase(it.get('days_left'))})" for it in result["items"]]
        return (
            f"{result['count']} thing(s) need rescuing: " + ", ".join(lines) +
            f". Roughly ${result.get('value_at_risk_usd', 0)} at risk. Say 'plan a rescue meal' and I'll turn them into dinner.",
            {"queue": result["items"], "value_at_risk_usd": result.get("value_at_risk_usd")},
        )

    if intent == "plan":
        plan = result.get("plan", {})
        if not plan.get("has_plan"):
            return plan.get("message", "Nothing needs rescuing right now."), {}
        missing = f" You're missing: {', '.join(plan['missing'])} — say 'add them to the shopping list'." if plan.get("missing") else " You have everything you need."
        return (
            f"Tonight: {plan['recipe_name']} (~{plan['minutes']} min). It uses up: "
            + ", ".join(r["name"] for r in plan["rescued_items"])
            + f". Estimated ${plan.get('estimated_savings_usd', 0)} saved.{missing}",
            {"plan": plan},
        )

    if intent == "shopping_add":
        added = result.get("added", [])
        if not added:
            return "Those are already on the shopping list.", {}
        return f"Added to the shopping list: {', '.join(added)}.", {"shopping_list_added": added}

    if intent == "shopping_get":
        items = result.get("items", [])
        if not items:
            return "Your shopping list is empty.", {}
        return "Shopping list: " + ", ".join(i["name"] for i in items), {"shopping_list": items}

    if intent == "shopping_clear":
        return f"Cleared {result.get('cleared', 0)} item(s) from the shopping list.", {}

    if intent == "used":
        return result.get("reply_hint", "Done."), {}

    if intent == "thrown":
        return result.get("reply_hint", "Noted."), {}

    if intent == "report":
        return (
            f"Waste report: about ${result.get('wasted_usd_estimate', 0)} thrown away "
            f"({result.get('wasted_items', 0)} items) vs ${result.get('rescued_usd_estimate', 0)} rescued "
            f"across {result.get('rescue_meals_planned', 0)} rescue meals. "
            f"Currently ${result.get('value_at_risk_usd', 0)} sitting at risk in your kitchen. (Estimates for demo.)",
            {"report": result},
        )

    if intent == "summary":
        return (
            f"{result.get('household', 'This kitchen')}: {result.get('item_count', 0)} items tracked, "
            f"{result.get('shopping_list_count', 0)} on the shopping list.",
            {"summary": result},
        )

    if intent == "consent":
        state = "granted" if result.get("consent") else "withdrawn"
        return f"Consent {state}.", {}

    return result.get("reply_hint", "Done."), {}


# ------------------------------------------------------------------ endpoints
@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    with open(os.path.join(_static_dir, "index.html"), encoding="utf-8") as fh:
        return fh.read()


@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    return {
        "ok": True,
        "invoker": invoker.describe(),
        "bedrock_enabled": settings.bedrock_enabled,
        "store": settings.store_backend,
        "textract_enabled": os.environ.get("FRESHKEEP_TEXTRACT") == "1",
    }


@app.post("/api/receipt")
async def receipt(req: Request) -> JSONResponse:
    """Parse a receipt (pasted text, or photo via Textract when enabled).

    Only *proposes* items — the user confirms before anything is tracked.
    """
    from ..receipts import (
        ReceiptExtractionUnavailable,
        extract_lines_with_textract,
        parse_receipt_text,
    )

    try:
        body = await req.json()
    except Exception:
        return JSONResponse({"ok": False, "message": "Invalid request body."}, status_code=400)

    client_id = str(body.get("client_id", "anonymous"))[:64]
    if not _limiter.allow(client_id):
        return JSONResponse({"ok": False, "message": "Slow down a little — too many requests this minute."}, status_code=429)

    lines: list[str] = []
    image_b64 = body.get("image_b64")
    text = body.get("text", "")

    if image_b64:
        if os.environ.get("FRESHKEEP_TEXTRACT") != "1":
            return JSONResponse({
                "ok": False,
                "message": "Photo extraction needs FRESHKEEP_TEXTRACT=1 (Amazon Textract). Paste the receipt text instead.",
            }, status_code=400)
        import base64

        try:
            raw = base64.b64decode(str(image_b64)[:5_600_000], validate=True)
        except Exception:
            return JSONResponse({"ok": False, "message": "That image could not be read."}, status_code=400)
        try:
            lines = extract_lines_with_textract(
                raw, os.environ.get("FRESHKEEP_TEXTRACT_REGION", os.environ.get("AWS_REGION", "us-east-1"))
            )
        except ReceiptExtractionUnavailable as exc:
            return JSONResponse({"ok": False, "message": f"Receipt photo extraction failed ({exc}). Paste the text instead."}, status_code=422)
        audit.record("receipt_textract", lines=len(lines))
    else:
        try:
            text = clean_utterance(text)[:4000]
        except ValidationError as exc:
            return JSONResponse({"ok": False, "message": str(exc)}, status_code=400)
        lines = text.splitlines()
        audit.record("receipt_text", lines=len(lines))

    parsed = parse_receipt_text("\n".join(lines))
    if not parsed["items"]:
        return JSONResponse({
            "ok": False,
            "message": "I couldn't find any grocery lines in that receipt. Try pasting the item lines.",
        }, status_code=422)
    return JSONResponse({"ok": True, **parsed})


@app.post("/api/consent")
async def set_consent(req: Request) -> JSONResponse:
    body = await req.json()
    consent = bool(body.get("consent"))
    result = await invoker.call("set_consent", {"consent": consent})
    audit.record("consent_endpoint", granted=consent)
    return JSONResponse({"ok": result.get("ok", False), "consent": consent})


@app.post("/api/seed")
async def seed_demo() -> dict[str, Any]:
    """Demo control (not part of the agent surface): load the seeded kitchen."""
    store.save(seed_household_doc(settings.household_id, "The demo kitchen"))
    audit.record("seed_demo")
    return {"ok": True, "message": "Seeded demo kitchen loaded."}


@app.post("/api/reset")
async def reset_demo() -> dict[str, Any]:
    """Demo control: wipe + reseed."""
    store.save(seed_household_doc(settings.household_id, "The demo kitchen"))
    audit.record("reset_demo")
    return {"ok": True, "message": "Demo reset to seeded state."}


@app.post("/api/utterance")
async def utterance(req: Request) -> JSONResponse:
    started = time.perf_counter()
    try:
        body = await req.json()
    except Exception:
        return JSONResponse({"ok": False, "message": "Invalid request body."}, status_code=400)

    client_id = str(body.get("client_id", "anonymous"))[:64]
    text_raw = body.get("text", "")
    try:
        text = clean_utterance(text_raw)
    except ValidationError as exc:
        return JSONResponse({"ok": False, "message": str(exc)}, status_code=400)

    if not _limiter.allow(client_id):
        audit.record("rate_limited")
        return JSONResponse(
            {"ok": False, "message": "Slow down a little — too many requests this minute."},
            status_code=429,
        )

    # Consent gate: nothing is stored until consent is granted.
    doc = store.load()
    consented = bool(doc.get("consent"))
    pre_route = deterministic_route(text)
    if settings.require_consent and not consented and pre_route.intent not in {
        "help", "consent", "delete", "fallback",
    }:
        return JSONResponse({
            "ok": True,
            "reply": "Before I remember anything, I need your consent to store kitchen data on this server. Use the consent button — nothing is saved until you do.",
            "intent": "consent_required",
            "consent": False,
            "trace": None,
        })

    trace: dict[str, Any] | None = None

    # Pending two-step delete confirmation.
    pend = _pending.get(client_id)
    if pend and pend.get("intent") == "delete":
        if re.search(r"\b(yes|yeah|yep|confirm|do it|proceed|sure)\b", text.lower()):
            _pending.pop(client_id, None)
            result, elapsed = await _call("delete_all_my_data", {"confirm_phrase": DELETE_PHRASE}, started)
            reply, payload = format_reply("delete", result)
            return _ok("delete", reply, payload, result, elapsed, consented)
        _pending.pop(client_id, None)
        return JSONResponse({
            "ok": True,
            "reply": "Deletion cancelled. Nothing was removed.",
            "intent": "delete_cancelled",
            "consent": consented,
            "trace": None,
            "payload": {},
        })

    # Route: deterministic by default; Bedrock optional with safe fallback.
    rt: Route = pre_route
    mode = "deterministic"
    if BEDROCK_MODE and pre_route.intent not in {"help", "fallback", "delete"}:
        try:
            from ..bedrock import route_with_bedrock

            rt = route_with_bedrock(text, settings.bedrock_model_id, settings.bedrock_region)
            mode = "bedrock"
        except Exception:
            rt = pre_route
            mode = "deterministic-fallback"
    rt.mode = mode

    if rt.tool is None:
        return JSONResponse({
            "ok": True,
            "reply": rt.reply or "I'm not sure how to help with that yet.",
            "intent": rt.intent,
            "mode": mode,
            "consent": consented,
            "trace": None,
            "payload": {},
        })

    if rt.needs_confirmation:
        _pending[client_id] = {"intent": "delete", "at": time.time()}
        return JSONResponse({
            "ok": True,
            "reply": "To be safe I need explicit confirmation: reply 'yes, delete everything' and I will permanently erase all FreshKeep data. Anything else cancels.",
            "intent": "delete_confirm_requested",
            "mode": mode,
            "consent": consented,
            "trace": None,
            "payload": {},
        })

    result, elapsed = await _call(rt.tool, rt.args, started)
    reply, payload = format_reply(rt.intent, result)
    trace = {
        "tool": rt.tool,
        "args": rt.args,
        "result_ok": result.get("ok"),
        "result": result,
        "latency_ms": elapsed,
        "invoker": invoker.describe(),
        "router": mode,
        "intent": rt.intent,
    }
    audit.record("utterance", intent=rt.intent, tool=rt.tool, mode=mode)
    return JSONResponse({
        "ok": True,
        "reply": reply,
        "intent": rt.intent,
        "mode": mode,
        "consent": consented,
        "trace": trace,
        "payload": payload,
    })


async def _call(tool: str, args: dict[str, Any], started: float) -> tuple[dict[str, Any], int]:
    result = await invoker.call(tool, args)
    return result, int((time.perf_counter() - started) * 1000)


def _ok(intent, reply, payload, result, elapsed, consented):
    return JSONResponse({
        "ok": result.get("ok", False),
        "reply": reply,
        "intent": intent,
        "consent": consented,
        "trace": {"tool": "delete_all_my_data", "args": {"confirm_phrase": "<sent>"}, "result_ok": result.get("ok"), "result": result, "latency_ms": elapsed, "invoker": invoker.describe(), "router": "two-step-confirm", "intent": intent},
        "payload": payload,
    })


def main() -> None:
    import uvicorn

    logger.info("FreshKeep simulator on http://%s:%s (backend: %s)", settings.sim_host, settings.sim_port, invoker.describe())
    uvicorn.run(app, host=settings.sim_host, port=settings.sim_port, log_level="info")


if __name__ == "__main__":
    main()
