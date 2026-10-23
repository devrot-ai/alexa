"""Real MCP wire test: boot the actual MCP server (Streamable HTTP) in a
background thread and drive it with the real MCP client. This is the exact
path Alexa+/any MCP client would use at runtime."""
import asyncio
import socket
import threading
import time

import pytest
import uvicorn


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def mcp_url():
    from freshkeep.mcpserver import server

    port = _free_port()
    app = server.streamable_http_app(streamable_http_path="/mcp", stateless_http=True)
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    srv = uvicorn.Server(config)
    thread = threading.Thread(target=srv.run, daemon=True)
    thread.start()
    for _ in range(60):
        if srv.started:
            break
        time.sleep(0.1)
    assert srv.started, "MCP server did not start"
    yield f"http://127.0.0.1:{port}/mcp"
    srv.should_exit = True
    thread.join(timeout=5)


def test_mcp_wire_full_loop(mcp_url):
    from freshkeep.mcpclient import McpInvoker
    from freshkeep.seed import seed_household_doc
    from freshkeep.mcpserver import store
    from freshkeep.config import settings

    store.save(seed_household_doc(settings.household_id, "The demo kitchen"))

    async def run():
        inv = McpInvoker(mcp_url)
        try:
            q = await inv.call("rescue_queue", {"within_days": 2})
            assert q["ok"] and q["count"] >= 3

            plan = await inv.call("plan_rescue_meal", {"max_missing": 2})
            assert plan["ok"] and plan["plan"]["has_plan"]

            added = await inv.call("add_to_shopping_list", {"items": ["soy sauce"]})
            assert added["ok"]

            lst = await inv.call("get_shopping_list", {})
            assert any("soy sauce" in i["name"] for i in lst["items"])

            summary = await inv.call("household_summary", {})
            assert summary["ok"] and summary["item_count"] > 5

            # unknown tool must return a safe structured error
            bad = await inv.call("does_not_exist", {})
            assert not bad["ok"]
        finally:
            await inv.close()

    asyncio.run(run())
