"""
Integration Tests for Phase 08: Unified Python Backend (FastAPI on Port 8000)
Validates all REST endpoints, lifespan database bootstrapper, error handling,
and ensures complete absence of track ID strings.
"""

import os
import pytest
from fastapi.testclient import TestClient
from app import app


@pytest.fixture(scope="module")
def client():
    """Create FastAPI TestClient which triggers the lifespan bootstrapper."""
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client):
    """Verify health endpoint returns 200 and does NOT contain any track IDs."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "KinetiQ Retail Copilot"
    assert "track_id" not in data
    assert "PS03" not in str(data)


def test_get_stores_endpoint(client):
    """Verify listing of all stores in the network."""
    response = client.get("/api/stores")
    assert response.status_code == 200
    stores = response.json()
    assert len(stores) == 3
    store_ids = {s["store_id"] for s in stores}
    assert store_ids == {"STORE_01", "STORE_02", "STORE_03"}


def test_triage_today_endpoint(client):
    """Verify daily morning triage endpoint returns complete briefing."""
    response = client.get("/api/triage/today?store_id=STORE_01")
    assert response.status_code == 200
    triage = response.json()

    assert triage["store_id"] == "STORE_01"
    assert "health_score" in triage
    assert triage["total_active_skus"] == 250
    assert "top_imminent_stockouts" in triage
    assert "top_dead_stock_items" in triage
    assert "top_velocity_anomalies" in triage


def test_chat_endpoint_valid_query(client):
    """Verify conversational chat endpoint responds to valid retail question."""
    payload = {"message": "What is running out at Store 1 this week?", "store_id": "STORE_01"}
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "response" in data
    assert len(data["response"]) > 0
    assert len(data["tools_executed"]) > 0
    assert "imminent_stockouts" in data["grounded_facts"]


def test_chat_endpoint_epistemic_refusal(client):
    """Verify conversational chat endpoint rejects unanswerable footfall query."""
    payload = {"message": "Why did customer footfall drop yesterday?", "store_id": "STORE_01"}
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["source"] == "epistemic-refusal"
    assert "Data Boundary Notice" in data["response"]
    assert len(data["tools_executed"]) == 0


def test_simulate_endpoint(client):
    """Verify interactive price simulation endpoint."""
    payload = {
        "sku_id": "SKU_1080",
        "store_id": "STORE_01",
        "discount_percent": 25.0,
        "duration_days": 14,
    }
    response = client.post("/api/simulate", json=payload)
    assert response.status_code == 200
    sim = response.json()

    assert sim["sku_id"] == "SKU_1080"
    assert sim["discount_percent"] == 25.0
    assert sim["discounted_price"] < sim["base_retail_price"]
    assert sim["projected_velocity"] > sim["base_velocity"]


def test_sku_endpoint(client):
    """Verify detailed SKU performance endpoint."""
    response = client.get("/api/sku/SKU_1001?store_id=STORE_01")
    assert response.status_code == 200
    sku = response.json()

    assert sku["sku_id"] == "SKU_1001"
    assert "Classic White Bread" in sku["product_name"]
    assert sku["velocity_7d"] >= 0
    assert sku["retail_price"] == 2.49


def test_commit_transfer_endpoint(client):
    """Verify approving and committing an inter-store transfer note."""
    import uuid
    test_id = f"STN_API_{uuid.uuid4().hex[:6]}"
    payload = {
        "manifest_id": test_id,
        "from_store_id": "STORE_03",
        "to_store_id": "STORE_01",
        "sku_id": "SKU_1020",
        "quantity": 15,
    }
    response = client.post("/api/actions/transfer", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["manifest_id"] == test_id


def test_serve_frontend_index_and_static_assets(client):
    """Verify embedded frontend index and static assets are served properly."""
    # Index HTML
    res_index = client.get("/")
    assert res_index.status_code == 200
    assert "KinetiQ" in res_index.text
    assert "Daily Action Queue" in res_index.text
    assert "PS03" not in res_index.text

    # Stylesheet
    res_css = client.get("/static/styles.css")
    assert res_css.status_code == 200
    assert "--bg-primary" in res_css.text

    # JavaScript Client
    res_js = client.get("/static/app.js")
    assert res_js.status_code == 200
    assert "handleUserMessage" in res_js.text
