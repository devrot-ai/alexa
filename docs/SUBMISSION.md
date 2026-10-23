# Devpost submission draft (text description)

> Paste-and-edit draft for the submission form. Re-check every requirement
> against https://amazonappdev2026.devpost.com/ before submitting.

**Project name:** FreshKeep

**Track:** Alexa+ (self-hosted MCP server + Agent Skill + simulated Alexa+ experience)
**Mini-challenges:** AWS Builder · Open Source

---

## What it does

FreshKeep gives Alexa+ a persistent memory for your kitchen. Tell it what you
bought — in one natural sentence — and it tracks every item with an expiry
date, warns you before food spoils, turns expiring ingredients into a concrete
rescue meal, and appends anything you're missing to the shopping list. A waste
report shows estimated dollars rescued vs thrown away.

## The problem

Households waste roughly $1,500 of food per year (USDA estimates 30–40% of the
food supply is wasted). Pantry apps fail because manual entry at the moment of
unpacking groceries never happens. Voice is the natural entry point — but
until MCP, Alexa had no persistent, structured kitchen memory to reason over.

## How it works

1. A self-hosted **MCP server** (official Python SDK, Streamable HTTP,
   protocol 2026-07-28 ≥ the required 2025-11-25) exposes 13 typed tools:
   track_food, rescue_queue, plan_rescue_meal, shopping-list read/write,
   mark_used/mark_thrown, waste_report, consent, and two-step data deletion.
2. A **simulated Alexa+ experience** (permitted by the rules) acts as a real
   MCP client: every chat turn is an actual `initialize` + `tools/call`
   round-trip, shown live in a judge-mode panel with arguments, structured
   JSON results, and latency.
3. A **deterministic rescue engine** plans meals from curated templates, so
   the core experience never depends on an LLM and can never hallucinate an
   action. An optional **Amazon Bedrock** router (Converse `tool_use`) handles
   messy phrasing; every model response is schema-validated, destructive tools
   are not model-callable, and any failure falls back to the deterministic path.
4. **Receipt ingestion** removes the last excuse for manual entry: paste a
   receipt and a deterministic parser proposes the items (totals, tax, and
   store headers filtered); with `FRESHKEEP_TEXTRACT=1`, receipt photos are
   read by **Amazon Textract**. Either way, items are only proposed — the
   user confirms, and tracking flows through the same MCP `track_food` tool.
5. Storage is swappable by env var: local atomic JSON (default) or **Amazon
   DynamoDB**. All monetary figures are labeled estimates.

## Amazon technology used

- **Alexa+ / MCP (track requirement):** self-hosted MCP server over Streamable
  HTTP + Agent Skill definition + simulated experience.
- **Amazon Bedrock** (optional router, AWS Builder mini-challenge).
- **Amazon DynamoDB** (optional durable store, AWS Builder mini-challenge).
- **Amazon Textract** (optional receipt-photo extraction, AWS Builder mini-challenge).

## Originality

Pantry apps exist but die from manual entry. FreshKeep is, to our knowledge,
the first agent-grade *kitchen memory* for Alexa+: structured, persistent,
household-shared, and action-oriented (it doesn't just list expiring food — it
plans the meal that saves it and updates the shopping list in the same breath).

## Privacy & safety

Consent before any storage; two-step deletion; prompt-injection hardening
(user text is data only; delete is not model-callable); PII-light audit log;
rate limiting; deterministic core; estimates always labeled.

## Impact & what's next

If a household rescues even two items a week, that's hundreds of dollars and
dozens of kilograms of avoided waste per year — measurable inside the app.
Next: receipt-photo ingestion (zero-effort entry), Alexa Lists API write-back,
multi-household via Cognito, and a Fire TV kitchen dashboard.

## Honest limitations

Single household per instance; recipe corpus is curated, not open-ended;
DynamoDB/Bedrock paths are implemented and unit-tested at the seam but were
not exercised against live AWS in the hackathon sandbox; no production auth.
