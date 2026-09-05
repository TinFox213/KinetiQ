"""
Unit Tests for Phase 03: Inventory Physics Engine
Validates classical supply-chain operations research formulas:
Days of Inventory (DOI), Safety Stock (SS), Reorder Points (ROP), Deficits, and Assumptions.
"""

import os
import pytest
from src.data.generator import generate_retail_dataset
from src.analytics.kernel import AnalyticsKernel
from src.analytics.inventory_physics import (
    calculate_doi,
    calculate_safety_stock,
    calculate_rop,
    evaluate_stockout,
    evaluate_all_stockouts,
    get_imminent_stockouts,
    StockoutAlert,
)


TEST_DB_PATH = "data/test_retail_inventory.db"


@pytest.fixture(scope="module")
def kernel():
    if not os.path.exists(TEST_DB_PATH):
        generate_retail_dataset(db_path=TEST_DB_PATH, days=90)
    return AnalyticsKernel(db_path=TEST_DB_PATH)


def test_calculate_doi_edge_cases():
    """Test standard and extreme boundary cases for Days of Inventory."""
    # Standard: 14 units at 5.6 units/day -> 2.5 days
    assert calculate_doi(14, 5.6) == 2.5

    # Zero stock on hand -> 0.0 days
    assert calculate_doi(0, 10.0) == 0.0
    assert calculate_doi(-2, 10.0) == 0.0

    # Non-moving inventory (velocity = 0) -> 999.0 days
    assert calculate_doi(50, 0.0) == 999.0
    assert calculate_doi(50, -1.0) == 999.0

    # Both zero stock and zero velocity -> 0.0
    assert calculate_doi(0, 0.0) == 0.0


def test_calculate_safety_stock():
    """Test safety stock formula: SS = Z * sigma * sqrt(L)."""
    # L=4, sqrt(L)=2.0, sigma=3.0, Z=1.645 -> 1.645 * 3 * 2 = 9.87 -> 9.9
    ss = calculate_safety_stock(lead_time_days=4, std_dev_demand=3.0, service_level_z=1.645)
    assert ss == 9.9

    # Zero lead time or zero sigma -> 0.0
    assert calculate_safety_stock(0, 3.0) == 0.0
    assert calculate_safety_stock(4, 0.0) == 0.0


def test_calculate_rop():
    """Test reorder point: ROP = (Velocity * L) + SS."""
    # Velocity=5.0, L=4, SS=10.0 -> (5 * 4) + 10 = 30.0
    assert calculate_rop(velocity=5.0, lead_time_days=4, safety_stock=10.0) == 30.0
    assert calculate_rop(velocity=0.0, lead_time_days=4, safety_stock=5.0) == 5.0


def test_evaluate_stockout_alert(kernel):
    """Test evaluation of a fast-moving perishable facing imminent stockout (SKU_1020)."""
    metrics = kernel.get_sku_metrics("SKU_1020", "STORE_01")
    assert metrics is not None

    alert = evaluate_stockout(metrics)
    assert isinstance(alert, StockoutAlert)
    assert alert.sku_id == "SKU_1020"
    assert alert.urgency_level in ("CRITICAL", "WARNING")
    assert alert.doi_days <= alert.lead_time_days + 3.0
    assert alert.projected_stockout_date != ""

    # Assumptions ledger completeness
    ledger = alert.assumptions
    assert "lead_time_days" in ledger
    assert "safety_stock_buffer_units" in ledger
    assert "reorder_point_units" in ledger
    assert "target_par_level_units" in ledger
    assert ledger["service_level_target"] == "95%"


def test_evaluate_dead_stock_alert(kernel):
    """Ensure dead stock SKU_1080 is marked HEALTHY from a stockout perspective."""
    metrics = kernel.get_sku_metrics("SKU_1080", "STORE_01")
    assert metrics is not None

    alert = evaluate_stockout(metrics)
    assert alert.urgency_level == "HEALTHY"
    assert alert.doi_days == 999.0
    assert alert.deficit_units == 0
    assert alert.recommended_order_qty == 0


def test_get_imminent_stockouts_list(kernel):
    """Test listing top imminent stockouts for STORE_01."""
    imminent = get_imminent_stockouts("STORE_01", kernel, threshold_days=5.0)
    assert len(imminent) > 0

    # Ensure all returned alerts are either under threshold DOI or 0 on hand
    for alert in imminent:
        assert alert.doi_days <= 5.0 or alert.on_hand == 0
        assert alert.urgency_level in ("CRITICAL", "WARNING")

    # Verify sorting: CRITICAL comes before WARNING
    urgency_ranks = [0 if a.urgency_level == "CRITICAL" else 1 for a in imminent]
    assert urgency_ranks == sorted(urgency_ranks)
