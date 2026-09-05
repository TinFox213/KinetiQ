import pytest
from src.analytics.inventory_physics import (
    calculate_doi,
    calculate_safety_stock,
    calculate_rop,
    evaluate_stockout,
    get_imminent_stockouts
)

def test_tc_025_doi_calculation_nonzero():
    doi = calculate_doi(on_hand=50, velocity=10.0)
    assert doi == 5.0

def test_tc_026_doi_zero_inventory():
    doi = calculate_doi(on_hand=0, velocity=5.0)
    assert doi == 0.0

def test_tc_027_doi_zero_velocity_sentinel():
    doi = calculate_doi(on_hand=25, velocity=0.0)
    assert doi == 999.0

def test_tc_028_safety_stock_calculation():
    ss = calculate_safety_stock(lead_time_days=4, std_dev_demand=2.0, service_level_z=1.645)
    assert abs(ss - 6.6) <= 0.1

def test_tc_029_rop_invariant():
    rop = calculate_rop(velocity=5.0, lead_time_days=3, safety_stock=6.0)
    assert rop == 21.0

def test_tc_030_imminent_stockout_classification(kernel):
    metrics = kernel.get_sku_metrics("SKU_1020", "STORE_01")
    alert = evaluate_stockout(metrics)
    assert alert.urgency_level in ("CRITICAL", "WARNING", "HEALTHY")
    if alert.doi_days <= alert.lead_time_days:
        assert alert.urgency_level == "CRITICAL"

def test_tc_031_exact_calendar_stockout_forecasting(kernel):
    metrics = kernel.get_sku_metrics("SKU_1020", "STORE_01")
    alert = evaluate_stockout(metrics)
    assert alert.projected_stockout_date is not None
    assert len(alert.projected_stockout_date) > 0

def test_tc_032_recommended_order_quantity(kernel):
    metrics = kernel.get_sku_metrics("SKU_1020", "STORE_01")
    alert = evaluate_stockout(metrics)
    if alert.urgency_level == "CRITICAL":
        assert alert.recommended_order_qty >= metrics.min_order_qty

def test_tc_033_perishable_expiry_vs_stockout(kernel):
    metrics = kernel.get_sku_metrics("SKU_1020", "STORE_01")
    assert metrics.is_perishable is True
    assert metrics.shelf_life_days is not None
    alert = evaluate_stockout(metrics)
    assert alert.assumptions is not None

def test_tc_034_full_store_stockout_scanner(kernel):
    alerts = get_imminent_stockouts("STORE_01", kernel, threshold_days=14.0)
    assert len(alerts) > 0
    dois = [a.doi_days for a in alerts]
    assert dois == sorted(dois)

def test_tc_035_negative_stock_calibration():
    doi = calculate_doi(on_hand=-5, velocity=2.0)
    assert doi == 0.0

def test_tc_036_assumptions_ledger_transparency(kernel):
    metrics = kernel.get_sku_metrics("SKU_1020", "STORE_01")
    alert = evaluate_stockout(metrics)
    ledger = alert.assumptions
    assert "lead_time_days" in ledger
    assert "service_level_target" in ledger
    assert "safety_stock_buffer_units" in ledger
    assert "reorder_point_units" in ledger
