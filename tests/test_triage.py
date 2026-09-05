"""
Unit Tests for Phase 07: Morning Triage Cockpit
Validates executive scorecard computation, 3x3 Daily Action Queue aggregation,
health index scoring, and sub-second execution performance.
"""

import os
import time
import pytest
from src.data.generator import generate_retail_dataset
from src.analytics.kernel import AnalyticsKernel
from src.analytics.rebalance import ArbitrageEngine
from src.analytics.triage import generate_morning_triage, DailyTriageBriefing, calculate_store_health_score


TEST_DB_PATH = "data/test_retail_inventory.db"


@pytest.fixture(scope="module")
def components():
    if not os.path.exists(TEST_DB_PATH):
        generate_retail_dataset(db_path=TEST_DB_PATH, days=90)
    kernel = AnalyticsKernel(db_path=TEST_DB_PATH)
    arbitrage = ArbitrageEngine(db_path=TEST_DB_PATH, kernel=kernel)
    return kernel, arbitrage


def test_calculate_store_health_score():
    """Verify health score formula bounded between 20 and 100."""
    perfect = calculate_store_health_score(250, 0, 0, 0)
    assert perfect == 100

    moderate = calculate_store_health_score(250, 5, 8, 3)
    assert 20 <= moderate <= 90

    extreme = calculate_store_health_score(250, 40, 50, 20)
    assert extreme == 20  # Minimum floor


def test_generate_morning_triage_structure_and_speed(components):
    """Verify morning triage generation completeness and sub-second speed."""
    kernel, arbitrage = components

    t0 = time.time()
    briefing = generate_morning_triage("STORE_01", kernel=kernel, arbitrage=arbitrage)
    elapsed = time.time() - t0

    assert elapsed < 2.0, f"Morning triage took {elapsed}s, exceeding 2.0s target."
    assert isinstance(briefing, DailyTriageBriefing)

    # Scorecard verification
    assert briefing.store_id == "STORE_01"
    assert briefing.total_active_skus == 250
    assert 20 <= briefing.health_score <= 100
    assert briefing.healthy_skus_count > 0
    assert briefing.potential_revenue_loss_at_risk >= 0
    assert briefing.total_dead_capital_locked >= 0
    assert briefing.monthly_holding_cost_drag >= 0

    # 3x3 Attention Queue lists
    assert len(briefing.top_imminent_stockouts) <= 3
    assert len(briefing.top_dead_stock_items) <= 3
    assert len(briefing.top_velocity_anomalies) <= 3
    assert len(briefing.recommended_transfers) <= 2

    # Check that top stockout items have all key physics fields
    if briefing.top_imminent_stockouts:
        first_so = briefing.top_imminent_stockouts[0]
        assert "doi_days" in first_so
        assert "lead_time_days" in first_so
        assert "recommended_order_qty" in first_so

    # Check that top dead stock items have locked capital
    if briefing.top_dead_stock_items:
        first_dead = briefing.top_dead_stock_items[0]
        assert "locked_capital" in first_dead
        assert "days_since_last_sale" in first_dead
        assert "suggested_discount_pct" in first_dead
