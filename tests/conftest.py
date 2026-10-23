import os
import sys

# Make the repo root importable and force hermetic test settings.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("FRESHKEEP_JSON_PATH", "data/test_household.json")
os.environ.setdefault("FRESHKEEP_AUDIT_PATH", "data/test_audit.log")

import pytest

from freshkeep.storage import JsonFileStore, empty_household
from freshkeep import tools as T


@pytest.fixture()
def store(tmp_path):
    s = JsonFileStore(str(tmp_path / "hh.json"), "test-hh", "Test kitchen")
    doc = empty_household("test-hh", "Test kitchen")
    doc["consent"] = True
    s.save(doc)
    return s


@pytest.fixture()
def seeded(store):
    from freshkeep.seed import seed_household_doc

    store.save(seed_household_doc("test-hh", "Test kitchen"))
    return store
