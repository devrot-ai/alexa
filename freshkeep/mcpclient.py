"""MCP client invokers.

McpInvoker talks to the FreshKeep MCP server over real Streamable HTTP —
the simulator uses this, so every chat turn exercises the actual MCP
protocol (initialize -> tools/call), not a shortcut.

LocalInvoker calls the same tool functions in-process; tests use it so
they stay hermetic, and it is also the documented offline fallback.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Protocol

logger = logging.getLogger("freshkeep.client")


class ToolInvoker(Protocol):
    async def call(self, tool: str, args: dict[str, Any]) -> dict[str, Any]: ...
    async def close(self) -> None: ...
    def describe(self) -> str: ...


class McpInvoker:
    """Real MCP Streamable-HTTP client with reconnect + bounded retries."""

    def __init__(self, url: str, timeout: float = 15.0) -> None:
        self.url = url
        self.timeout = timeout
        self._session = None
        self._streams = None
        self._cm = None
        self._http_client = None
        self._lock = asyncio.Lock()

    async def _ensure(self):
        import httpx
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client

        if self._session is not None:
            return
        async with self._lock:
            if self._session is not None:
                return
            # NB: SDK v2's streamable_http_client has no timeout kwarg;
            # timeouts are set on the underlying httpx client instead.
            self._http_client = httpx.AsyncClient(timeout=httpx.Timeout(self.timeout))
            self._cm = streamable_http_client(self.url, http_client=self._http_client)
            # MCP SDK v2 yields (read_stream, write_stream); v1 yielded a 3-tuple.
            streams = await self._cm.__aenter__()
            read, write = streams[0], streams[1]
            session = ClientSession(read, write)
            await session.__aenter__()
            await session.initialize()
            self._session = session
            logger.info("MCP session established with %s", self.url)

    async def call(self, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        last_err: Exception | None = None
        for attempt in range(3):
            try:
                await self._ensure()
                result = await asyncio.wait_for(
                    self._session.call_tool(tool, args), timeout=self.timeout
                )
                text = "".join(
                    c.text for c in result.content if getattr(c, "text", None)
                )
                return json.loads(text) if text else {"ok": False, "error": "empty_response"}
            except Exception as exc:  # reconnect + retry, then surface a safe error
                last_err = exc
                logger.warning("mcp_call_failed tool=%s attempt=%s err=%s", tool, attempt + 1, exc.__class__.__name__)
                await self._teardown()
                await asyncio.sleep(0.3 * (attempt + 1))
        return {
            "ok": False,
            "error": "mcp_unavailable",
            "message": "FreshKeep MCP server is unreachable. Is it running? (python -m freshkeep.mcpserver)",
        }

    async def _teardown(self):
        try:
            if self._session is not None:
                await self._session.__aexit__(None, None, None)
        except Exception:
            pass
        try:
            if self._cm is not None:
                await self._cm.__aexit__(None, None, None)
        except Exception:
            pass
        try:
            if self._http_client is not None:
                await self._http_client.aclose()
        except Exception:
            pass
        self._session = None
        self._cm = None
        self._http_client = None

    async def close(self) -> None:
        await self._teardown()

    def describe(self) -> str:
        return f"mcp-streamable-http {self.url}"


class LocalInvoker:
    """In-process invoker used by tests and as an offline fallback."""

    def __init__(self) -> None:
        from .storage import make_store
        from . import tools as T

        self.store = make_store()
        self._T = T

    async def call(self, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        T, store = self._T, self.store
        table = {
            "track_food": lambda a: T.track_food(store, a.get("items", []), a.get("note", "")),
            "list_pantry": lambda a: T.list_pantry(store, a.get("status", "all"), a.get("category", "")),
            "rescue_queue": lambda a: T.rescue_queue(store, a.get("within_days", 2)),
            "plan_rescue_meal": lambda a: T.plan_rescue_meal(store, a.get("max_missing", 2)),
            "add_to_shopping_list": lambda a: T.add_to_shopping_list(store, a.get("items", [])),
            "get_shopping_list": lambda a: T.get_shopping_list(store),
            "clear_shopping_list": lambda a: T.clear_shopping_list(store),
            "mark_used": lambda a: T.mark_used(store, a.get("name", "")),
            "mark_thrown": lambda a: T.mark_thrown(store, a.get("name", ""), a.get("reason", "")),
            "waste_report": lambda a: T.waste_report(store),
            "household_summary": lambda a: T.household_summary(store),
            "delete_all_my_data": lambda a: T.delete_all_my_data(store, a.get("confirm_phrase", "")),
            "set_consent": lambda a: T.set_consent(store, bool(a.get("consent"))),
        }
        fn = table.get(tool)
        if fn is None:
            return {"ok": False, "error": "unknown_tool", "message": f"Unknown tool: {tool}"}
        return fn(args)

    async def close(self) -> None:
        return None

    def describe(self) -> str:
        return "local-in-process"
