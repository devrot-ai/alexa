"""End-to-end tests of the simulated Alexa+ experience API.

Uses the LocalInvoker (in-process tools) so tests are hermetic; the MCP
wire path is covered separately in test_mcp_wire.py.
"""
import os

os.environ["FRESHKEEP_SIM_LOCAL"] = "1"
os.environ["FRESHKEEP_JSON_PATH"] = "data/sim_test_household.json"

import pytest
from fastapi.testclient import TestClient

from freshkeep.simulator import app as sim
from freshkeep.config import settings
from freshkeep.seed import seed_household_doc


@pytest.fixture()
def client(tmp_path):
    from freshkeep.storage import JsonFileStore

    store = JsonFileStore(str(tmp_path / "sim.json"), settings.household_id, "The demo kitchen")
    store.save(seed_household_doc(settings.household_id, "The demo kitchen"))
    sim.store = store
    sim.invoker.store = store  # keep the (local) invoker pointed at the same data
    sim._pending.clear()
    return TestClient(sim.app)


def _say(client, text, cid="judge"):
    return client.post("/api/utterance", json={"text": text, "client_id": cid})


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200 and r.json()["ok"]


def test_full_judge_flow(client):
    # 1. rescue queue from seed
    r = _say(client, "What needs rescuing?")
    assert r.status_code == 200 and r.json()["intent"] == "rescue_queue"
    assert r.json()["trace"]["tool"] == "rescue_queue"

    # 2. plan a rescue meal
    r = _say(client, "Plan a rescue meal")
    assert r.json()["intent"] == "plan"
    assert r.json()["payload"]["plan"]["has_plan"]

    # 3. shopping list write-back
    r = _say(client, "Add soy sauce to the shopping list")
    assert "soy sauce" in r.json()["reply"]
    r = _say(client, "show my shopping list")
    assert r.json()["intent"] == "shopping_get"

    # 4. waste report
    r = _say(client, "waste report")
    assert r.json()["intent"] == "report"


def test_two_step_delete(client):
    r = _say(client, "delete my data")
    assert r.json()["intent"] == "delete_confirm_requested"
    r = _say(client, "actually nevermind")
    assert r.json()["intent"] == "delete_cancelled"
    r = _say(client, "delete my data")
    assert r.json()["intent"] == "delete_confirm_requested"
    r = _say(client, "yes, delete everything")
    assert r.json()["intent"] == "delete" and r.json()["trace"]["result_ok"]


def test_consent_gate_blocks_storage(client):
    sim.store.save({**seed_household_doc(settings.household_id, "x"), "consent": False, "items": []})
    r = _say(client, "we bought milk")
    assert r.json()["intent"] == "consent_required"
    r = client.post("/api/consent", json={"consent": True})
    assert r.json()["ok"]
    r = _say(client, "we bought milk")
    assert r.json()["intent"] == "track"


def test_invalid_input_is_rejected_safely(client):
    r = _say(client, "x" * 900)
    assert r.status_code == 400
    # markup in the utterance is rejected with a safe, generic message
    r = _say(client, "we bought <script>alert(1)</script>")
    assert r.status_code == 400
    assert "characters" in r.json()["message"]


def test_rate_limit(client):
    sim._limiter.per_minute = 5
    codes = [_say(client, "help", cid="flooder").status_code for _ in range(8)]
    sim._limiter.per_minute = settings.rate_limit_per_minute
    assert 429 in codes
