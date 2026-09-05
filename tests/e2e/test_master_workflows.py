import time
import pytest
from fastapi.testclient import TestClient

def test_tc_105_e2e_scenario_1_morning_triage_to_transfer(api_client, kernel):
    # 1. Fetch morning triage
    res = api_client.get("/api/triage/today?store_id=STORE_01")
    assert res.status_code == 200
    triage = res.json()
    assert triage["health_score"] >= 0
    assert len(triage["top_imminent_stockouts"]) > 0

    # 2. Pick candidate transfer
    transfers = triage.get("recommended_transfers", [])
    assert len(transfers) > 0
    candidate = transfers[0]
    assert candidate["net_savings"] > 0

    # 3. Commit transfer
    commit_res = api_client.post("/api/actions/transfer", json={
        "manifest_id": candidate["manifest_id"],
        "from_store_id": candidate["from_store_id"],
        "to_store_id": candidate["to_store_id"],
        "sku_id": candidate["sku_id"],
        "quantity": candidate["quantity"]
    })
    assert commit_res.status_code == 200
    res_data = commit_res.json()
    assert res_data["status"] == "success"

def test_tc_106_e2e_scenario_2_conversational_grounding(api_client, kernel):
    # Ask about stockouts
    res = api_client.post("/api/chat", json={
        "message": "What is running out at Store 1 this week?",
        "store_id": "STORE_01"
    })
    assert res.status_code == 200
    data = res.json()
    assert len(data["tools_executed"]) > 0
    assert "stockouts" in str(data["grounded_facts"]).lower()
    # Check that numbers in response match ground truth
    metrics = kernel.get_sku_metrics("SKU_1020", "STORE_01")
    if metrics:
        assert str(metrics.on_hand) in data["response"] or "runway" in data["response"].lower()

def test_tc_107_e2e_scenario_3_dead_capital_to_simulation(api_client):
    # 1. Fetch triage to find dead stock
    res = api_client.get("/api/triage/today?store_id=STORE_01")
    triage = res.json()
    dead_items = triage.get("top_dead_stock_items", [])
    assert len(dead_items) > 0
    target_sku = dead_items[0]["sku_id"]

    # 2. Run simulation
    sim_res = api_client.post("/api/simulate", json={
        "sku_id": target_sku,
        "store_id": "STORE_01",
        "discount_percent": 35.0,
        "duration_days": 14
    })
    assert sim_res.status_code == 200
    sim = sim_res.json()
    assert sim["discounted_price"] < sim["base_retail_price"]
    assert sim["projected_velocity"] > 0
    assert sim["projected_clearance_days"] < sim["base_clearance_days"]

def test_tc_108_e2e_scenario_4_phantom_inventory_to_audit(api_client):
    res = api_client.get("/api/triage/today?store_id=STORE_01")
    triage = res.json()
    phantoms = triage.get("phantom_inventory_alerts", [])
    assert len(phantoms) > 0
    p = phantoms[0]
    assert p["on_hand"] > 0
    assert p["yesterday_sales"] == 0
    assert "audit" in p["recommended_action"].lower()

def test_tc_109_e2e_scenario_5_disciplined_epistemic_refusal(api_client):
    res = api_client.post("/api/chat", json={
        "message": "Why did customer footfall drop yesterday due to the rain?",
        "store_id": "STORE_01"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["source"] == "epistemic-refusal"
    assert "Data Boundary Notice" in data["response"]
    assert "What the verified data can confirm" in data["response"]
    assert len(data["tools_executed"]) == 0

def test_tc_110_e2e_scenario_6_clean_machine_turnkey():
    # Verify core dependencies are clean and available
    import sqlite3
    import fastapi
    import uvicorn
    assert sqlite3.sqlite_version is not None
    assert fastapi.__version__ is not None
    assert uvicorn.__version__ is not None
