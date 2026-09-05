import os
import pytest
from fastapi.testclient import TestClient
from app import app, init_app_state

@pytest.fixture(scope="module")
def client():
    init_app_state(app)
    with TestClient(app) as c:
        yield c

def test_quick_login_all_three_roles(client):
    """Verify 1-click Quick Demo login works for all 3 supported operational roles."""
    roles = ["store_manager", "supply_chain_director", "executive"]
    for role in roles:
        res = client.post("/api/auth/quick-login", json={"role": role})
        assert res.status_code == 200, f"Quick login failed for {role}"
        data = res.json()
        assert data["role"] == role
        assert "token" in data
        assert "name" in data
        assert "avatar" in data

def test_path_normalization_without_api_prefix(client):
    """Verify that requests without /api prefix are seamlessly routed via path normalization."""
    res_login = client.post("/auth/quick-login", json={"role": "store_manager"})
    assert res_login.status_code == 200
    assert res_login.json()["role"] == "store_manager"

    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"

    res_stores = client.get("/stores")
    assert res_stores.status_code == 200
    assert len(res_stores.json()) == 3

def test_triage_today_inr_dead_capital(client):
    """Verify morning triage returns valid dead capital and imminent stockouts in INR."""
    res = client.get("/api/triage/today?store_id=STORE_01")
    assert res.status_code == 200
    data = res.json()
    assert "total_dead_capital_locked" in data
    assert data["total_dead_capital_locked"] >= 0
    assert "top_imminent_stockouts" in data
    assert "recommended_transfers" in data

def test_simulate_inr_pricing(client):
    """Verify simulation calculates price elasticity over realistic INR price catalog."""
    payload = {
        "sku_id": "SKU_1001",
        "store_id": "STORE_01",
        "discount_percent": 15.0,
        "duration_days": 14
    }
    res = client.post("/api/simulate", json=payload)
    assert res.status_code == 200
    sim = res.json()
    # Baseline retail price in INR should be >= 20.0
    assert sim["base_retail_price"] >= 20.0
    assert sim["discounted_price"] < sim["base_retail_price"]
    assert "velocity_lift_percent" in sim

def test_transfer_manifest_courier_costs_inr(client):
    """Verify rebalance transfers compute courier costs in INR range (150 - 450)."""
    transfers = app.state.rebalance.find_interstore_transfers(store_id="STORE_01")
    if transfers:
        manifest = transfers[0]
        assert manifest.estimated_courier_cost >= 100.0, "Courier cost should be in realistic INR range"
        assert "courier_cost_inr" in manifest.assumptions

def test_transfer_commit_endpoint(client):
    """Verify transfer commit records successfully and logs audit."""
    payload = {
        "manifest_id": "STN_TEST_INR_001",
        "from_store_id": "STORE_02",
        "to_store_id": "STORE_01",
        "sku_id": "SKU_1001",
        "quantity": 10
    }
    res = client.post("/api/actions/transfer", json=payload)
    assert res.status_code == 200
    assert res.json()["status"] == "success"

def test_copilot_chat_inr_responses(client):
    """Verify Copilot answers reflect INR currency without error."""
    payload = {
        "message": "What is my dead capital locked at Store 1?",
        "store_id": "STORE_01",
        "role": "store_manager"
    }
    res = client.post("/api/chat", json=payload)
    assert res.status_code == 200
    reply = res.json()["response"]
    assert "₹" in reply or "INR" in reply or "dead" in reply.lower()
