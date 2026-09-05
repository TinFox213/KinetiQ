"""
Integration Test Suite: Multi-Role Authentication & API Key Management
Validates MongoDB auth layer, 1-click quick logins, session retrieval, and key updates.
"""

import pytest
from fastapi.testclient import TestClient
from app import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_roles_overview_returns_three_seed_roles(client):
    res = client.get("/api/roles/overview")
    assert res.status_code == 200
    roles = res.json()
    assert len(roles) == 3
    role_names = [r["role"] for r in roles]
    assert "store_manager" in role_names
    assert "supply_chain_director" in role_names
    assert "executive" in role_names


def test_quick_login_store_manager(client):
    res = client.post("/api/auth/quick-login", json={"role": "store_manager"})
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "store_manager"
    assert data["assigned_store"] == "STORE_01"
    assert "token" in data
    assert len(data["token"]) >= 16


def test_quick_login_supply_chain_director(client):
    res = client.post("/api/auth/quick-login", json={"role": "supply_chain_director"})
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "supply_chain_director"
    assert data["assigned_store"] == "ALL"
    assert "token" in data


def test_quick_login_executive(client):
    res = client.post("/api/auth/quick-login", json={"role": "executive"})
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "executive"
    assert data["assigned_store"] == "ALL"


def test_quick_login_invalid_role(client):
    res = client.post("/api/auth/quick-login", json={"role": "invalid_super_admin"})
    assert res.status_code == 400


def test_password_login_success_and_failure(client):
    # Success
    res = client.post("/api/auth/login", json={"username": "manager@kinetiq.com", "password": "manager123"})
    assert res.status_code == 200
    assert res.json()["username"] == "manager@kinetiq.com"

    # Bad password
    res_bad = client.post("/api/auth/login", json={"username": "manager@kinetiq.com", "password": "wrongpassword"})
    assert res_bad.status_code == 401


def test_auth_me_session_lookup(client):
    login_res = client.post("/api/auth/quick-login", json={"role": "store_manager"})
    token = login_res.json()["token"]

    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["name"] == "Alice Johnson"

    # Unauthenticated
    bad_res = client.get("/api/auth/me", headers={"Authorization": "Bearer invalidtoken123"})
    assert bad_res.status_code == 401


def test_update_api_key_endpoint(client):
    login_res = client.post("/api/auth/quick-login", json={"role": "executive"})
    token = login_res.json()["token"]

    update_res = client.post(
        "/api/auth/api-key",
        json={"api_key": "AIzaSyFakeTestGeminiKey9988"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "success"
    assert update_res.json()["has_key"] is True
    assert update_res.json()["key_preview"] == "****9988"
