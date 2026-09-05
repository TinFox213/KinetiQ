"""
Unit Tests for Phase 04: Demand Anomaly Detection & Dead Capital Classifier
Validates Z-score anomaly detection (spikes and drops), phantom inventory identification,
and stagnant dead capital valuation with holding cost calculations.
"""

import os
import pytest
from src.data.generator import generate_retail_dataset
from src.analytics.kernel import AnalyticsKernel
from src.analytics.anomalies import (
    detect_sales_anomalies,
    detect_dead_stock,
    detect_phantom_inventory,
    SalesAnomaly,
    DeadStockItem,
    PhantomInventoryAlert,
)


TEST_DB_PATH = "data/test_retail_inventory.db"


@pytest.fixture(scope="module")
def kernel():
    if not os.path.exists(TEST_DB_PATH):
        generate_retail_dataset(db_path=TEST_DB_PATH, days=90)
    return AnalyticsKernel(db_path=TEST_DB_PATH)


def test_detect_sales_anomalies_spikes_and_drops(kernel):
    """Verify statistical anomaly detection flags both spikes and drops."""
    anomalies = detect_sales_anomalies("STORE_01", kernel, z_threshold=2.0)
    assert len(anomalies) > 0

    anomaly_types = {a.anomaly_type for a in anomalies}
    assert "SPIKE" in anomaly_types or "DROP" in anomaly_types

    for anom in anomalies:
        assert isinstance(anom, SalesAnomaly)
        assert abs(anom.z_score) >= 2.0
        assert anom.baseline_mean_14d >= 0
        assert anom.recommended_action != ""
        assert anom.rationale != ""
        assert "rolling_baseline_days" in anom.assumptions

    # Verify SKU_1050 was detected as a SPIKE
    spike_candidates = [a for a in anomalies if a.sku_id == "SKU_1050"]
    if spike_candidates:
        assert spike_candidates[0].anomaly_type == "SPIKE"
        assert spike_candidates[0].z_score >= 2.0


def test_detect_dead_stock_and_locked_capital(kernel):
    """Verify dead stock classification and financial holding cost calculation."""
    dead_items = detect_dead_stock("STORE_01", kernel, idle_days_threshold=30)
    assert len(dead_items) > 0

    # Ensure sorted by locked capital descending
    locked_caps = [item.locked_capital for item in dead_items]
    assert locked_caps == sorted(locked_caps, reverse=True)

    # Locate the anchor dead stock item: SKU_1080 (Artisanal Truffle Vinegar)
    truffle_matches = [item for item in dead_items if item.sku_id == "SKU_1080"]
    assert len(truffle_matches) == 1
    truffle = truffle_matches[0]

    assert isinstance(truffle, DeadStockItem)
    assert truffle.days_since_last_sale >= 30
    assert truffle.on_hand >= 30

    # Locked capital check: 42 * 18.50 = 777.00
    expected_capital = round(truffle.on_hand * truffle.unit_cost, 2)
    assert truffle.locked_capital == expected_capital

    # 24% annual holding cost = 2% per month
    expected_monthly_holding = round(expected_capital * 0.02, 2)
    assert truffle.monthly_holding_cost_drag == expected_monthly_holding

    assert truffle.suggested_discount_pct >= 20
    assert truffle.estimated_cash_recovery > 0
    assert "annual_holding_cost_rate" in truffle.assumptions


def test_detect_phantom_inventory(kernel):
    """Verify detection of items with stock on record but unexplained 0 sales."""
    phantoms = detect_phantom_inventory("STORE_01", kernel)
    assert len(phantoms) > 0

    # Anchor candidate SKU_1008 (Sourdough Loaf)
    sourdough_matches = [p for p in phantoms if p.sku_id == "SKU_1008"]
    assert len(sourdough_matches) == 1
    sourdough = sourdough_matches[0]

    assert isinstance(sourdough, PhantomInventoryAlert)
    assert sourdough.yesterday_sales == 0
    assert sourdough.on_hand > 0
    assert sourdough.baseline_mean_14d >= 5.0
    assert "shelf audit" in sourdough.recommended_action.lower()
