import json
import os
import pytest
import requests

def test_mcp_configuration_file_integrity():
    mcp_path = "mcp.json"
    assert os.path.exists(mcp_path), "mcp.json not found in project root"
    with open(mcp_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    assert "mcpServers" in config
    assert "devfolio" in config["mcpServers"]
    devfolio_cfg = config["mcpServers"]["devfolio"]
    assert "https://mcp.devfolio.co/mcp" in (devfolio_cfg.get("url"), devfolio_cfg.get("serverUrl"))

def test_devfolio_mcp_endpoint_live_and_responsive():
    url = "https://mcp.devfolio.co/mcp"
    res = requests.get(url, headers={"Accept": "text/event-stream"}, timeout=10)
    # Devfolio MCP server enforces OAuth2 Bearer token: 401 Unauthorized indicates active server
    assert res.status_code == 401
    assert "invalid_token" in res.headers.get("www-authenticate", "")
    assert "oauth-protected-resource" in res.headers.get("www-authenticate", "")

def test_devfolio_mcp_oauth_protected_resource_metadata():
    url = "https://mcp.devfolio.co/.well-known/oauth-protected-resource/mcp"
    res = requests.get(url, timeout=10)
    assert res.status_code == 200
    meta = res.json()
    assert meta.get("resource_name") == "Devfolio MCP Server"
    assert meta.get("resource") == "https://mcp.devfolio.co/mcp"
    assert "https://platform.devfolio.co" in meta.get("authorization_servers", [])
    expected_scopes = {"profile.read", "hackathons.read", "projects.read", "projects.write"}
    assert expected_scopes.issubset(set(meta.get("scopes_supported", [])))

def test_devfolio_authorization_server_discovery():
    auth_url = "https://platform.devfolio.co/.well-known/oauth-authorization-server"
    res = requests.get(auth_url, timeout=10)
    assert res.status_code == 200
    data = res.json()
    assert "https://platform.devfolio.co/authorize" in data.get("authorization_endpoint", "")
