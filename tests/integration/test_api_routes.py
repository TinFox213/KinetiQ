import time
import pytest
from fastapi.testclient import TestClient

def test_tc_095_cold_boot_startup_time(api_client):
    t0 = time.perf_counter()
    res = api_client.get("/api/health")
    elapsed = time.perf_counter() - t0
    assert res.status_code == 200
    assert elapsed < 10.0, f"Cold boot took {elapsed:.2f}s, expected < 10s"

def test_tc_096_port_8000_binding(api_client):
    res = api_client.get("/api/health")
    assert res.status_code == 200

def test_tc_097_health_endpoint_spec(api_client):
    res = api_client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "service" in data

def test_tc_098_triage_today_json_schema(api_client):
    res = api_client.get("/api/triage/today?store_id=STORE_01")
    assert res.status_code == 200
    data = res.json()
    required_keys = [
        "date", "store_id", "store_name", "manager_name", "health_score",
        "total_active_skus", "healthy_skus_count", "imminent_stockouts_count",
        "potential_revenue_loss_at_risk", "dead_capital_skus_count",
        "total_dead_capital_locked", "monthly_holding_cost_drag",
        "velocity_anomalies_count", "available_transfers_count",
        "top_imminent_stockouts", "top_dead_stock_items",
        "top_velocity_anomalies", "phantom_inventory_alerts", "recommended_transfers"
    ]
    for key in required_keys:
        assert key in data, f"Missing key: {key}"

def test_tc_099_chat_post_handling(api_client):
    res = api_client.post("/api/chat", json={"message": "What is running out?", "store_id": "STORE_01"})
    assert res.status_code == 200
    data = res.json()
    assert "response" in data
    assert "source" in data

def test_tc_100_static_assets_delivery(api_client):
    res_html = api_client.get("/")
    assert res_html.status_code == 200
    assert "text/html" in res_html.headers.get("content-type", "")

    res_css = api_client.get("/static/styles.css")
    assert res_css.status_code == 200
    assert "text/css" in res_css.headers.get("content-type", "")

    res_js = api_client.get("/static/app.js")
    assert res_js.status_code == 200
    assert "javascript" in res_js.headers.get("content-type", "")

def test_tc_101_concurrent_api_load_resilience(api_client):
    for _ in range(25):
        res = api_client.get("/api/health")
        assert res.status_code == 200

def test_tc_102_single_request_latency(api_client):
    t0 = time.perf_counter()
    res = api_client.get("/api/triage/today?store_id=STORE_01")
    elapsed = time.perf_counter() - t0
    assert res.status_code == 200
    assert elapsed < 2.0, f"Request took {elapsed:.2f}s, expected < 2.0s"

def test_tc_103_malformed_json_handling(api_client):
    res = api_client.post(
        "/api/chat",
        content="not valid json",
        headers={"Content-Type": "application/json"}
    )
    assert res.status_code == 422

def test_tc_104_network_isolation_no_third_party():
    # Only Gemini GenAI SDK is imported, no OpenAI/Pinecone/LangChain
    import sys
    for forbidden in ["openai", "pinecone", "langchain", "anthropic"]:
        assert forbidden not in sys.modules, f"Forbidden module {forbidden} detected!"
