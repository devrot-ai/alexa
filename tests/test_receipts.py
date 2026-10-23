from freshkeep.receipts import parse_receipt_text

SAMPLE = """
BIG BAZAAR          INV 8891
04/09/2026  18:32
spinach 25.00
2 x eggs 120
milk 1 l 70
greek yogurt 500 g 95.50
basmati rice 5 kg 480
TOTAL 790.50
GST 12.00
CASH 800.00
CHANGE 9.50
THANK YOU VISIT AGAIN
"""


def test_parses_items_skips_noise():
    r = parse_receipt_text(SAMPLE)
    names = [i["name"] for i in r["items"]]
    assert names == ["spinach", "eggs", "milk", "greek yogurt", "basmati rice"]
    eggs = r["items"][1]
    assert eggs["quantity"] == 2.0
    milk = r["items"][2]
    assert milk["quantity"] == 1.0 and milk["unit"] == "l"
    yogurt = r["items"][3]
    assert yogurt["quantity"] == 500 and yogurt["unit"] == "g"
    assert r["items"][0].get("price_seen") == 25.0
    assert r["skipped_noise"] > 0


def test_store_header_before_date_is_skipped():
    r = parse_receipt_text("SPENCERS DAILY\n12-09-2026 19:04\npalak 30.00\nTOTAL 30.00")
    assert [i["name"] for i in r["items"]] == ["palak"]


def test_cap_at_twelve_items():
    text = "\n".join(f"apples batch{i} {i}.00" for i in range(20))
    r = parse_receipt_text(text)
    assert len(r["items"]) == 12
    assert r["skipped_over_cap"] == 8


def test_empty_or_garbage():
    assert parse_receipt_text("")["items"] == []
    r = parse_receipt_text("TOTAL 12.00\n\n12345\n##--##")
    assert r["items"] == []


def test_api_receipt_text_path():
    import os

    os.environ["FRESHKEEP_SIM_LOCAL"] = "1"
    from fastapi.testclient import TestClient
    from freshkeep.simulator import app as sim

    client = TestClient(sim.app)
    r = client.post("/api/receipt", json={"text": SAMPLE, "client_id": "t"})
    assert r.status_code == 200
    assert len(r.json()["items"]) == 5
    # photo path without Textract enabled is refused politely
    r = client.post("/api/receipt", json={"image_b64": "aGVsbG8=", "client_id": "t"})
    assert r.status_code == 400
