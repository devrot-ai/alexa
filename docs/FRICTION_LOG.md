# Friction log (real entries only)

Format per official rules: task attempted · tool/SDK · expected vs actual ·
severity · workaround · outcome · actionable suggestion.

---

## F-1 · `FastMCP` import fails on current SDK

- **Task:** bootstrap the MCP server from the pattern used in virtually all public samples (`from mcp.server.fastmcp import FastMCP`).
- **Tool:** MCP Python SDK 2.2.0.
- **Expected:** import succeeds.
- **Actual:** `ModuleNotFoundError: No module named 'mcp.server.fastmcp'` with a migration notice (renamed to `MCPServer`).
- **Severity:** Medium (blocks every tutorial; clear error text softens it).
- **Workaround:** migrate to `from mcp.server.mcpserver import MCPServer` and re-derive the run API.
- **Outcome:** resolved; ~30 minutes re-mapping APIs.
- **Suggestion:** ship a compatibility alias (`FastMCP = MCPServer`) for at least one major version, and pin sample repos to SDK major versions.

## F-2 · `@server.tool` must be called

- **Task:** register tools with the bare decorator `@server.tool` (v1-style).
- **Tool:** MCP Python SDK 2.2.0.
- **Expected:** tools registered.
- **Actual:** `TypeError: The @tool decorator was used incorrectly… Use @tool()`.
- **Severity:** Low-Medium (import-time crash, but the message tells you the fix).
- **Workaround:** `@server.tool()` everywhere.
- **Outcome:** resolved.
- **Suggestion:** accept both forms; many frameworks do.

## F-3 · Client transport renamed AND re-shaped

- **Task:** write the simulator's MCP client using the documented v1 pattern `streamablehttp_client(url) → (read, write, get_session_id)`.
- **Tool:** MCP Python SDK 2.2.0 (`mcp.client.streamable_http`).
- **Expected:** 3-tuple unpack works.
- **Actual:** function renamed to `streamable_http_client` and now yields a 2-tuple `(read_stream, write_stream)` → `ValueError: not enough values to unpack`.
- **Severity:** Medium (silent between releases; samples lag).
- **Workaround:** index-based unpack with a version-tolerant comment.
- **Outcome:** resolved.
- **Suggestion:** put the v1→v2 client migration table at the top of the transport docs, and keep the old name as a deprecated alias.

## F-4 · No timeout knob on the client transport

- **Task:** bound MCP call latency for a voice-like UX (`streamable_http_client(url, timeout=15)`).
- **Tool:** MCP Python SDK 2.2.0.
- **Expected:** a `timeout` parameter.
- **Actual:** `TypeError: unexpected keyword argument 'timeout'` at runtime; timeouts only possible by injecting an `httpx.AsyncClient`.
- **Severity:** Low-Medium (works, but undiscoverable without reading source).
- **Workaround:** construct `httpx.AsyncClient(timeout=…)` and pass via `http_client=`.
- **Outcome:** resolved; documented in `mcpclient.py`.
- **Suggestion:** add a first-class `timeout` kwarg that wires through to the default client.

## F-5 · SDK version not introspectable

- **Task:** programmatically confirm which SDK version/protocol is in use.
- **Tool:** MCP Python SDK 2.2.0.
- **Expected:** `mcp.__version__`.
- **Actual:** attribute missing; must use `pip show mcp` (protocol version is exposed via `mcp.types.LATEST_PROTOCOL_VERSION`, which *is* great).
- **Severity:** Low.
- **Workaround:** shell out / metadata read.
- **Outcome:** worked around.
- **Suggestion:** expose `__version__`.

---

*No friction was fabricated. Bedrock/DynamoDB live-call friction could not be
recorded honestly because no AWS credentials were used in this sandbox; the
adapters are implemented with conservative defaults and the deterministic
fallback covers any runtime failure.*
