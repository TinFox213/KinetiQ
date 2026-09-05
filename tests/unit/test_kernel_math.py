import time
import pytest
from src.analytics.kernel import AnalyticsKernel

def test_tc_013_rolling_velocity_7d_accuracy(kernel):
    metrics = kernel.get_sku_metrics("SKU_1001", "STORE_01")
    assert metrics is not None
    assert metrics.velocity_7d >= 0.0
    expected_v7 = round(metrics.units_sold_7d / 7.0, 2)
    assert abs(metrics.velocity_7d - expected_v7) <= 0.05

def test_tc_014_unconstrained_sales_velocity(kernel):
    metrics = kernel.get_sku_metrics("SKU_1020", "STORE_01")
    assert metrics is not None
    assert metrics.unconstrained_velocity_7d >= metrics.velocity_7d

def test_tc_015_revenue_and_gross_profit_30d(kernel):
    metrics = kernel.get_sku_metrics("SKU_1001", "STORE_01")
    assert metrics is not None
    assert metrics.revenue_30d >= 0.0
    assert metrics.gross_profit_30d == round(metrics.revenue_30d - (metrics.units_sold_30d * metrics.cost_price), 2)
    if metrics.revenue_30d > 0:
        expected_margin = round((metrics.gross_profit_30d / metrics.revenue_30d) * 100, 2)
        assert abs(metrics.gross_margin_pct - expected_margin) <= 0.1

def test_tc_016_zero_division_safeguard(kernel):
    metrics = kernel.get_sku_metrics("SKU_1080", "STORE_01")
    assert metrics is not None
    assert metrics.velocity_30d == 0.0
    assert metrics.gross_margin_pct >= 0.0

def test_tc_017_multi_store_comparison_aggregation(kernel):
    m1 = kernel.get_sku_metrics("SKU_1020", "STORE_01")
    m2 = kernel.get_sku_metrics("SKU_1020", "STORE_02")
    m3 = kernel.get_sku_metrics("SKU_1020", "STORE_03")
    assert m1 is not None and m2 is not None and m3 is not None
    assert m1.store_id == "STORE_01"
    assert m2.store_id == "STORE_02"
    assert m3.store_id == "STORE_03"

def test_tc_018_category_level_rollup_integrity(kernel):
    categories = ['Dairy & Eggs', 'Bakery', 'Beverages', 'Snacks', 'Pantry']
    total_cat_rev = 0.0
    for cat in categories:
        summary = kernel.get_category_summary(cat, "STORE_01")
        assert summary is not None
        assert summary.sku_count > 0
        assert summary.total_revenue_30d >= 0
        total_cat_rev += summary.total_revenue_30d
    overview = kernel.get_store_overview("STORE_01", window_days=30)
    assert abs(total_cat_rev - overview.total_revenue) < 10.0

def test_tc_019_store_overview_kpi_rollup(kernel):
    overview = kernel.get_store_overview("STORE_01", window_days=30)
    assert overview.total_revenue > 0
    assert overview.total_gross_profit > 0
    assert 0 < overview.gross_margin_pct < 100
    assert overview.active_skus_count == 250

def test_tc_020_demand_variance_sigma_calculation(kernel):
    metrics = kernel.get_sku_metrics("SKU_1001", "STORE_01")
    assert metrics is not None
    assert metrics.std_dev_demand >= 0.0

def test_tc_021_non_existent_sku_handling(kernel):
    res = kernel.get_sku_metrics("SKU_NON_EXISTENT_9999", "STORE_01")
    assert res is None

def test_tc_022_non_existent_store_handling(kernel):
    res = kernel.get_sku_metrics("SKU_1001", "STORE_INVALID_99")
    assert res is None

def test_tc_023_historical_lookback_boundary(kernel):
    latest_date = kernel.get_latest_date()
    assert latest_date is not None
    assert len(latest_date.split("-")) == 3

def test_tc_024_high_concurrency_query_benchmark(kernel):
    t0 = time.perf_counter()
    for _ in range(50):
        kernel.get_sku_metrics("SKU_1001", "STORE_01")
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.5, f"50 queries took {elapsed:.3f}s, expected < 0.5s"
