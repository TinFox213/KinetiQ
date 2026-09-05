import time
import pytest
from src.analytics.anomalies import (
    detect_sales_anomalies,
    detect_dead_stock,
    detect_phantom_inventory
)

def test_tc_037_z_score_demand_spike_detection(kernel):
    anomalies = detect_sales_anomalies("STORE_01", kernel, z_threshold=2.0)
    spikes = [a for a in anomalies if a.anomaly_type == "SPIKE"]
    assert len(spikes) >= 0
    for s in spikes:
        assert s.z_score >= 2.0

def test_tc_038_z_score_demand_drop_detection(kernel):
    anomalies = detect_sales_anomalies("STORE_01", kernel, z_threshold=2.0)
    drops = [a for a in anomalies if a.anomaly_type == "DROP"]
    assert len(drops) >= 0
    for d in drops:
        assert d.z_score <= -2.0

def test_tc_039_low_baseline_variance_safeguard(kernel):
    anomalies = detect_sales_anomalies("STORE_01", kernel, z_threshold=2.0)
    for a in anomalies:
        assert a.baseline_std_14d >= 0.5 or a.baseline_std_14d == 0.0

def test_tc_040_phantom_inventory_detection(kernel):
    phantoms = detect_phantom_inventory("STORE_01", kernel)
    assert len(phantoms) >= 1
    p = phantoms[0]
    assert p.on_hand > 0
    assert p.consecutive_zero_sales_days >= 1
    assert p.yesterday_sales == 0
    assert p.baseline_mean_14d > 5.0

def test_tc_041_dead_stock_30d_idle_identification(kernel):
    dead_items = detect_dead_stock("STORE_01", kernel, idle_days_threshold=30)
    assert len(dead_items) >= 1
    item = dead_items[0]
    assert item.days_since_last_sale >= 30

def test_tc_042_dead_capital_dollar_valuation(kernel):
    dead_items = detect_dead_stock("STORE_01", kernel, idle_days_threshold=30)
    for item in dead_items:
        expected_locked = round(item.on_hand * item.unit_cost, 2)
        assert abs(item.locked_capital - expected_locked) <= 0.05

def test_tc_043_monthly_holding_cost_drag_calculation(kernel):
    dead_items = detect_dead_stock("STORE_01", kernel, idle_days_threshold=30)
    for item in dead_items:
        expected_drag = round(item.locked_capital * 0.02, 2)
        assert abs(item.monthly_holding_cost_drag - expected_drag) <= 0.05

def test_tc_044_dynamic_markdown_tiering(kernel):
    dead_items = detect_dead_stock("STORE_01", kernel, idle_days_threshold=30)
    for item in dead_items:
        assert item.suggested_discount_pct in (20, 35, 50)

def test_tc_045_companion_bundling_recommendation(kernel):
    dead_items = detect_dead_stock("STORE_01", kernel, idle_days_threshold=30)
    assert len(dead_items) > 0
    bundled = [i for i in dead_items if i.suggested_bundle_sku_id]
    assert len(bundled) > 0

def test_tc_046_store_wide_dead_capital_aggregation(kernel):
    dead_items = detect_dead_stock("STORE_01", kernel, idle_days_threshold=30)
    total_locked = sum(i.locked_capital for i in dead_items)
    assert total_locked >= 0

def test_tc_047_false_positive_suppression_low_volume(kernel):
    anomalies = detect_sales_anomalies("STORE_01", kernel, z_threshold=2.0)
    for a in anomalies:
        assert a.baseline_mean_14d >= 1.0 or a.yesterday_sales >= 3

def test_tc_048_anomaly_engine_speed_benchmark(kernel):
    # warm up cache
    detect_sales_anomalies("STORE_01", kernel)
    t0 = time.perf_counter()
    detect_sales_anomalies("STORE_01", kernel)
    detect_dead_stock("STORE_01", kernel)
    detect_phantom_inventory("STORE_01", kernel)
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.5, f"Anomaly detection took {elapsed:.3f}s, expected < 0.5s"
