# Product feedback (required submission field)

Feedback for every Amazon/AWS tool used — what we used it for, what worked,
what needs work, onboarding feel, and whether we'd build with it again.

## 1. MCP Python SDK (`mcp` v2.2.0) — Alexa+ track core

**Used for:** the self-hosted MCP server (Streamable HTTP) and the MCP client
inside the simulator.

- **Worked well:** `MCPServer` + typed `@server.tool()` functions generate
  correct JSON Schemas automatically; `streamable_http_app()` embeds cleanly
  in uvicorn for tests; stateless HTTP mode made test boot trivial; protocol
  version negotiation just worked (server advertises 2026-07-28).
- **Needs work:**
  - v1→v2 rename (`FastMCP` → `MCPServer`, `streamablehttp_client` →
    `streamable_http_client`) breaks nearly every public sample on the
    internet, and the Alexa+ hackathon docs still lean on older patterns.
    A deprecation shim for one release would save builders hours.
  - `@server.tool` vs `@server.tool()` trips people at import time — the
    error message is good, but accepting both forms would be friendlier.
  - The v2 client yields a 2-tuple where v1 yielded a 3-tuple; document the
    migration inline in the type stubs.
  - `streamable_http_client` has no `timeout` kwarg; you must construct and
    inject an `httpx.AsyncClient`. Discoverable only by reading source.
  - `mcp.__version__` isn't exposed; version checks need `pip show`.
- **Onboarding:** Fast once you're on v2 docs; confusing while samples/docs mix v1/v2.
- **Build again?** Yes — it's the right abstraction and the transport is solid.

## 2. MCP spec 2025-11-25 (Streamable HTTP)

- **Worked well:** one endpoint, SSE responses, trivial to probe with curl;
  `initialize` → `tools/call` is a clean, judge-demoable story.
- **Needs work:** a canonical "10-line client smoke test" snippet in the spec
  docs would help builders verify their server quickly.
- **Build again?** Yes.

## 3. Amazon Bedrock (Converse API design) — optional router

- **Used for:** schema-validated natural-language routing (`tool_use`).
- **Worked well:** `toolConfig` maps 1:1 from our shared JSON Schemas;
  structured output means we can validate before executing anything.
- **Needs work (from reading/SDK shape):** clearer guidance + samples for
  "router-only" usage (no chat memory) with tight token budgets; a documented
  timeout/retry recipe for latency-sensitive voice paths.
- **Build again?** Yes, with the deterministic fallback pattern we shipped.

## 4. Amazon DynamoDB — optional store

- **Used for:** durable household documents behind `DynamoStore`.
- **Worked well:** single-document-per-household maps perfectly to a
  single-partition-key table; boto3's credential chain keeps secrets out of code.
- **Needs work:** a tiny "document store" recipe in the hackathon resources
  (PK + JSON doc) would match how agent builders actually model state.
- **Build again?** Yes.

## 5. Amazon Textract — optional receipt photos

- **Used for:** `DetectDocumentText` LINE extraction behind `receipts.py`
  (adapter implemented; not live-called in the hackathon sandbox — no AWS
  credentials used; noted for honesty).
- **Worked well (from SDK shape):** `Bytes` in, LINE blocks out — a perfect
  fit for receipt line parsing; boto3 keeps credentials out of code.
- **Needs work:** a hackathon "receipt → structured items" recipe (even
  heuristic) would jump-start exactly this class of household apps.
- **Build again?** Yes.

## 6. Devpost hackathon page & track resources

- **Worked well:** track requirements were unusually precise (spec version
  called out; simulated path explicitly permitted); the resources page's
  per-track SDK list saved real time.
- **Needs work:** prize-list rendering mixed "Fire Track"/"Fire TV Track"
  labels and one Alexa+ entry was mislabeled "3rd Place" in the listing we
  saw — worth a proofread so builders trust the breakdown.
- **Build again?** Yes.
