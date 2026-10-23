# 🥬 FreshKeep — your kitchen's memory, built for Alexa+

> **FreshKeep gives Alexa+ persistent, structured memory of your kitchen — it knows
> what you bought, warns you before food spoils, and turns expiring ingredients
> into tonight's dinner.**

Built for **Build, Ship, Shape: The Amazon Developer Hackathon 2026**.

- **Primary track:** Alexa+ — self-hosted **MCP server** (Streamable HTTP,
  MCP spec 2026-07-28 via the official SDK; requirement was 2025-11-25+),
  an **Agent Skill** definition, and a **simulated Alexa+ experience** web app
  that acts as a real MCP client.
- **Mini-challenges:** AWS Builder (Bedrock router + DynamoDB adapter seams) · Open Source (MIT).

---

## The problem

The average household throws away roughly **$1,500 of food per year**
(USDA estimates 30–40% of the food supply is wasted). The reason is not lack
of caring — it's lack of *memory*: nobody maintains a pantry app when their
hands are full of groceries. Voice is the natural fix, but before MCP, Alexa
had no persistent, structured kitchen memory to reason over.

## The 60-second wow

1. *"We just bought spinach, 500 g of yogurt, and chicken that expires in 2 days"* → FreshKeep tracks them with structured MCP tool calls (visible in judge mode).
2. *"What needs rescuing?"* → 4 at-risk items, most urgent first, with money-at-risk.
3. *"Plan a rescue meal"* → **Everything-Left Veggie Omelette**, rescuing 3 items, ≈$9.60 saved (estimate), and it notices you're missing bread.
4. *"Add bread to the shopping list"* → write-back action completes the loop.
5. *"Waste report"* → rescued vs wasted, in dollars.
6. **🧾 Bonus:** paste a receipt → FreshKeep proposes the items (noise like totals/tax filtered) → confirm → tracked via the same MCP path. With `FRESHKEEP_TEXTRACT=1`, receipt *photos* are read by **Amazon Textract**.

Everything runs **deterministically** — the demo never depends on an LLM
behaving. Optional Bedrock mode enhances natural-language routing with strict
schema validation and automatic fallback.

## Quickstart (2 terminals, no cloud account needed)

```bash
git clone <this-repo> && cd freshkeep
pip install -r requirements.txt          # add pytest via requirements-dev.txt for tests

# Terminal 1 — the MCP server (Streamable HTTP on :8811)
python -m freshkeep.mcpserver

# Terminal 2 — the simulated Alexa+ experience (:8800)
python -m freshkeep.simulator.app
```

Open **http://localhost:8800**, accept the consent prompt, press
**Seed demo kitchen**, then use the quick-action chips (①–⑤) or type/speak:

- *"What needs rescuing?"*
- *"Plan a rescue meal"*
- *"Add soy sauce to the shopping list"*
- *"Waste report"*
- *"Delete my data"* (two-step confirmation)
- **🧾 button** next to the mic: paste a receipt → review parsed items → track

**Judge mode** (right panel) shows every live MCP tool call with arguments,
structured JSON results, latency, and which router answered.

### Verify the MCP endpoint directly

```bash
curl -s -X POST http://127.0.0.1:8811/mcp \
  -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}'
```

### Tests

```bash
pip install -r requirements-dev.txt
pytest -q          # 34 tests: tools, router, receipts, API, and a real MCP wire loop
```

## Architecture (summary)

```
Browser (simulated Alexa+ experience, judge mode)
        │  /api/utterance
        ▼
FastAPI simulator ── deterministic router (default)
        │              └── optional Bedrock Converse router (schema-validated, fallback-safe)
        │  MCP: initialize → tools/call  (Streamable HTTP)
        ▼
FreshKeep MCP server (official Python SDK, spec 2026-07-28)
        │
        ├── tool layer (validation, unit-aware merge, waste ledger)
        ├── deterministic rescue-meal engine (curated templates, zero hallucination)
        └── storage: JsonFileStore (default) | DynamoStore (FRESHKEEP_STORE=dynamodb)
```

Full diagram + AWS service justification: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Environment

Copy `.env.example` → `.env` (or export vars). Everything has a safe local
default; **no AWS account is required** for the core experience.

| Variable | Default | Purpose |
|---|---|---|
| `FRESHKEEP_MCP_HOST/PORT` | `0.0.0.0:8811` | MCP server bind |
| `FRESHKEEP_SIM_HOST/PORT` | `0.0.0.0:8800` | simulator bind |
| `FRESHKEEP_STORE` | `json` | `json` or `dynamodb` |
| `FRESHKEEP_JSON_PATH` | `data/household.json` | local store file |
| `FRESHKEEP_DYNAMO_TABLE` | `FreshKeepHousehold` | DynamoDB table |
| `FRESHKEEP_BEDROCK` | `0` | `1` enables the Bedrock NL router |
| `FRESHKEEP_BEDROCK_MODEL` | `amazon.nova-lite-v1:0` | router model |
| `FRESHKEEP_RATE_LIMIT` | `30` | utterances/min per client |
| `FRESHKEEP_REQUIRE_CONSENT` | `1` | consent gate before any storage |
| `FRESHKEEP_TEXTRACT` | `0` | `1` enables receipt-photo extraction via Amazon Textract |
| `FRESHKEEP_TEXTRACT_REGION` | `AWS_REGION` | Textract region |

## Privacy & safety (short version)

- **Consent before storage** — nothing persists until granted; withdrawal supported.
- **Two-step deletion** — "delete my data" then explicit confirmation; nothing is model-callable.
- **Prompt-injection hardening** — user text is data only; router can only emit schema-validated calls to known tools; destructive tools unreachable from the model path.
- **Audit log excludes utterance text** — tool names and counts only.
- **Deterministic core** — AI never controls actions; savings figures are always labeled estimates.

Details + full threat model: [`docs/SECURITY.md`](docs/SECURITY.md).

## Honest status (what is verified)

| Capability | Status |
|---|---|
| MCP server over Streamable HTTP (spec ≥ 2025-11-25) | ✅ tested end-to-end (`tests/test_mcp_wire.py`) |
| Simulated Alexa+ experience as real MCP client | ✅ tested incl. rate-limit, consent, 2-step delete |
| Deterministic router + rescue engine | ✅ unit-tested |
| JSON file storage | ✅ exercised by all tests |
| DynamoDB adapter (`DynamoStore`) | 🔧 implemented behind the same interface; live-verify with `python scripts/verify_aws.py` (setup: [`docs/AWS_SETUP.md`](docs/AWS_SETUP.md)) |
| Bedrock NL router (`bedrock.py`) | 🔧 implemented with strict validation + fallback; live-verify with the same script |
| Receipt ingestion (`receipts.py`) | ✅ text path tested end-to-end; Textract photo adapter implemented, live-verifiable with the same script |
| Agent Skill definition | 📄 follows public Agent Skills conventions; final format to be re-verified against Alexa+ docs before submission |

## Repository map

```
freshkeep/               Python package
├── mcpserver.py         MCP server entry (Streamable HTTP) — 13 tools
├── mcpclient.py         Real MCP client used by the simulator + test harness
├── tools.py             Tool logic + shared JSON schemas (single source of truth)
├── router.py            Deterministic utterance → tool router
├── bedrock.py           Optional Bedrock Converse router (guarded)
├── rescue.py            Deterministic rescue-meal engine
├── receipts.py          Receipt parsing (deterministic) + Amazon Textract adapter
├── storage.py           JsonFileStore | DynamoStore
├── models.py            Freshness math, validation helpers
├── safety.py            Validation, rate limiter, PII-light audit log
├── seed.py              Seeded demo kitchen (relative dates → always demo-ready)
└── simulator/           FastAPI simulated Alexa+ experience + single-file UI
skill/SKILL.md           Agent Skill definition for Alexa+
tests/                   29 tests incl. real MCP wire loop
docs/                    Architecture, security, demo script, judge guide,
                         submission draft, product feedback, friction log,
                         rules compliance
```

## Deadline (verified against the official page)

**Oct 23, 2026 — 12:00 PM Pacific (PDT) · 3:00 PM EDT · = Oct 24, 2026, 00:30 IST (Asia/Kolkata).**
Re-check before submitting: https://amazonappdev2026.devpost.com/

## License

MIT — see [LICENSE](LICENSE).
