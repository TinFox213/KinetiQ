"""
KinetiQ Benchmark & Acceptance Test Suite
Comprehensive validation of all operational criteria:
- Deterministic zero-division protection
- Disciplined epistemic refusal
- Numerical grounding between DB and Copilot responses
- Cross-store inventory arbitrage economics
- What-If price elasticity simulation
- Single-command backend health
"""

import os
import pytest
from fastapi.testclient import TestClient
from app import app
from src.analytics.kernel import AnalyticsKernel
from src.analytics.inventory_physics import calculate_doi
from src.analytics.rebalance import ArbitrageEngine
from src.analytics.simulator import simulate_intervention
from src.agent.epistemic import check_epistemic_boundary


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_deterministic_zero_division():
    """Verify that zero division in DOI runway calculation is impossible."""
    assert calculate_doi(10, 0.0) == 999.0
    assert calculate_doi(0, 5.0) == 0.0
    assert calculate_doi(0, 0.0) == 0.0
    assert calculate_doi(-5, 2.0) == 0.0


def test_epistemic_refusal_discipline():
    """Verify out-of-domain queries trigger polite, structured refusal without hallucination."""
    out_of_domain_queries = [
        "Why did store footfall decrease yesterday?",
        "How will tomorrow's rain affect bakery sales?",
        "What are competitor supermarket prices for milk?",
        "What is the average age of customers purchasing snacks?",
    ]
    for q in out_of_domain_queries:
        is_in_scope, msg = check_epistemic_boundary(q)
        assert is_in_scope is False
        assert "Data Boundary Notice" in msg
        assert "What the verified data can confirm" in msg


def test_numerical_grounding_fidelity():
    """Verify that every number emitted in SKU metrics matches underlying database records."""
    kernel = AnalyticsKernel("data/retail_inventory.db")
    metrics = kernel.get_sku_metrics("SKU_1001", "STORE_01")
    assert metrics is not None

    # Exact mathematical relationships
    assert metrics.gross_profit_30d == round(metrics.revenue_30d - (metrics.units_sold_30d * metrics.cost_price), 2)
    expected_margin = round(((metrics.retail_price - metrics.cost_price) / metrics.retail_price) * 100, 1)
    assert metrics.gross_margin_pct == expected_margin
    assert metrics.velocity_7d == round(metrics.units_sold_7d / 7.0, 2)


def test_interstore_arbitrage_economics():
    """Verify arbitrage math: gross profit protected must exceed courier cost."""
    arb = ArbitrageEngine("data/retail_inventory.db")
    manifest = arb.evaluate_transfer_for_sku("SKU_1020", to_store_id="STORE_01")
    assert manifest is not None
    assert manifest.net_savings > 0
    assert manifest.net_savings == round(manifest.gross_profit_protected - manifest.estimated_courier_cost, 2)
    assert manifest.source_remaining_runway_days >= 14.0


def test_what_if_simulation_elasticity():
    """Verify that a 20% discount on pantry goods lifts volume and shortens clearance runway."""
    sim = simulate_intervention("SKU_1080", store_id="STORE_01", discount_percent=20.0)
    assert sim is not None
    assert sim.discounted_price < sim.base_retail_price
    assert sim.projected_velocity > sim.base_velocity
    assert sim.projected_clearance_days < sim.base_clearance_days


def test_zero_track_id_leakage(client):
    """Ensure no track ID string is present anywhere in API health or main pages."""
    res_health = client.get("/api/health")
    assert "track_id" not in res_health.json()
    assert "PS03" not in res_health.text

    res_index = client.get("/")
    assert "PS03" not in res_index.text
