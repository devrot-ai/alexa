"""Critical workflow tests: track -> rescue -> plan -> shopping list -> report -> delete."""
from freshkeep import tools as T


def test_track_adds_items_and_estimates_expiry(store):
    r = T.track_food(store, [{"name": "Spinach", "quantity": 1, "unit": "bunch"}])
    assert r["ok"] and len(r["added"]) == 1
    item = r["added"][0]
    assert item["category"] == "produce"          # inferred
    assert item["expiry_estimated"] is True       # flagged as estimate
    assert item["days_left"] is not None


def test_track_respects_explicit_expiry(store):
    r = T.track_food(store, [{"name": "chicken breast", "expires_in_days": 2}])
    assert r["added"][0]["days_left"] == 2
    assert r["added"][0]["expiry_estimated"] is False


def test_track_merges_duplicates(store):
    T.track_food(store, [{"name": "eggs", "quantity": 6}])
    r = T.track_food(store, [{"name": "Eggs", "quantity": 6}])
    assert r["updated"] and r["updated"][0]["quantity"] == 12
    assert len(T.list_pantry(store)["items"]) == 1


def test_track_merge_is_unit_aware(store):
    # Mentioning an item measured in grams without a quantity must not
    # corrupt its stored quantity ("400 g + 1 unit" bug).
    T.track_food(store, [{"name": "chicken breast", "quantity": 400, "unit": "g"}])
    r = T.track_food(store, [{"name": "chicken breast"}])
    assert r["updated"][0]["quantity"] == 400
    assert r["updated"][0]["unit"] == "g"
    assert r["updated"][0]["est_value_usd"] < 50  # sane estimate preserved


def test_track_rejects_invalid_names(store):
    r = T.track_food(store, [{"name": "<script>alert(1)</script>"}])
    assert r["rejected"] and not r["added"]


def test_track_caps_batch_size(store):
    items = [{"name": f"item {i}"} for i in range(20)]
    r = T.track_food(store, items)
    assert not r["ok"] and r["error"] == "too_many_items"


def test_rescue_queue_orders_by_urgency(seeded):
    q = T.rescue_queue(seeded, 2)
    assert q["ok"] and q["count"] >= 3
    days = [i["days_left"] for i in q["items"]]
    assert days == sorted(days)
    assert q["items"][0]["days_left"] <= 1


def test_plan_rescue_is_deterministic_and_covers_at_risk(seeded):
    p1 = T.plan_rescue_meal(seeded)
    p2 = T.plan_rescue_meal(seeded)
    assert p1["plan"]["has_plan"]
    assert p1["plan"]["recipe_key"] == p2["plan"]["recipe_key"]
    assert p1["plan"]["rescued_items"]
    assert len(p1["plan"]["missing"]) <= 2
    assert p1["plan"]["steps"]


def test_shopping_list_dedupes(store):
    T.add_to_shopping_list(store, ["soy sauce", "spring onion"])
    r = T.add_to_shopping_list(store, ["Soy Sauce", "lime"])
    assert r["added"] == ["lime"]
    assert T.get_shopping_list(store)["count"] == 3


def test_shopping_list_validation(store):
    bad = T.add_to_shopping_list(store, [""])
    assert not bad["ok"]
    bad2 = T.add_to_shopping_list(store, ["ok <b>item</b>"])
    assert not bad2["ok"]


def test_mark_used_and_thrown_feed_report(seeded):
    r = T.mark_used(seeded, "eggs")
    assert r["ok"]
    r = T.mark_thrown(seeded, "spinach", "went slimy")
    assert r["ok"]
    rep = T.waste_report(seeded)
    assert rep["wasted_items"] == 1
    assert rep["wasted_usd_estimate"] > 0


def test_delete_requires_explicit_phrase(seeded):
    r = T.delete_all_my_data(seeded, "yes")
    assert not r["ok"] and r["error"] == "confirmation_required"
    r = T.delete_all_my_data(seeded, T.DELETE_PHRASE)
    assert r["ok"]
    assert T.list_pantry(seeded)["count"] == 0
    assert T.household_summary(seeded)["consent"] is False


def test_consent_toggle(store):
    T.set_consent(store, False)
    assert T.household_summary(store)["consent"] is False
    T.set_consent(store, True)
    assert T.household_summary(store)["consent"] is True
