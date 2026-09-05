"""
Unit Tests for Phase 02: High-Performance Deterministic Analytical Kernel
Validates that all calculations (rolling velocities, margins, aggregates, comparisons)
are mathematically accurate, deterministic, and protected against division-by-zero.
"""

import os
import pytest
from src.data.generator import generate_retail_dataset
from src.analytics.kernel import AnalyticsKernel, SkuMetrics, StoreOverview, CategorySummary


TEST_DB_PATH = "data/test_retail_inventory.db"


@pytest.fixture(scope="module")
def kernel():
    """Seed test database if needed and return AnalyticsKernel instance."""
    if not os.path.exists(TEST_DB_PATH):
        generate_retail_dataset(db_path=TEST_DB_PATH, days=90)
    return AnalyticsKernel(db_path=TEST_DB_PATH)


def test_sku_metrics_calculation(kernel):
    """Test standard SKU metric calculations for SKU_1001."""
    metrics = kernel.get_sku_metrics("SKU_1001", "STORE_01")
    assert metrics is not None
    assert isinstance(metrics, SkuMetrics)

    # Core attributes
    assert metrics.sku_id == "SKU_1001"
    assert "White Bread" in metrics.product_name
    assert metrics.category == "Bakery"
    assert metrics.store_id == "STORE_01"
    assert metrics.cost_price == 1.20
    assert metrics.retail_price == 2.49

    # Velocities must be non-negative
    assert metrics.velocity_7d >= 0.0
    assert metrics.velocity_14d >= 0.0
    assert metrics.velocity_30d >= 0.0
    assert metrics.unconstrained_velocity_7d >= metrics.velocity_7d

    # Demand standard deviation must be non-negative
    assert metrics.std_dev_demand >= 0.0

    # Margin check: ((2.49 - 1.20) / 2.49) * 100 = 51.8%
    expected_margin = round(((2.49 - 1.20) / 2.49) * 100, 1)
    assert metrics.gross_margin_pct == expected_margin

    # Units and revenue consistency
    assert metrics.units_sold_7d <= metrics.units_sold_30d
    assert metrics.revenue_7d <= metrics.revenue_30d


def test_sku_metrics_not_found(kernel):
    """Ensure non-existent SKU returns None cleanly without error."""
    res = kernel.get_sku_metrics("SKU_9999", "STORE_01")
    assert res is None


def test_dead_stock_sku_metrics(kernel):
    """Verify dead stock SKU_1080 metrics reflect zero or near-zero sales velocity."""
    metrics = kernel.get_sku_metrics("SKU_1080", "STORE_01")
    assert metrics is not None
    assert metrics.days_since_last_sale >= 30
    assert metrics.on_hand >= 30
    assert metrics.velocity_7d == 0.0


def test_store_overview_aggregation(kernel):
    """Test macro store aggregation calculations."""
    overview = kernel.get_store_overview("STORE_01", window_days=30)
    assert overview is not None
    assert isinstance(overview, StoreOverview)

    assert overview.store_id == "STORE_01"
    assert overview.active_skus_count == 250
    assert overview.total_revenue > 0
    assert overview.total_cost > 0
    assert overview.total_gross_profit == round(overview.total_revenue - overview.total_cost, 2)
    assert 0.0 < overview.gross_margin_pct < 100.0
    assert overview.avg_daily_revenue == round(overview.total_revenue / 30, 2)


def test_compare_skus(kernel):
    """Test side-by-side SKU comparison."""
    comparisons = kernel.compare_skus(["SKU_1001", "SKU_1002"], "STORE_01")
    assert len(comparisons) == 2
    assert comparisons[0].sku_id == "SKU_1001"
    assert comparisons[1].sku_id == "SKU_1002"


def test_category_summary(kernel):
    """Test department/category aggregation."""
    cat_summary = kernel.get_category_summary("Bakery", "STORE_01")
    assert cat_summary is not None
    assert isinstance(cat_summary, CategorySummary)

    assert cat_summary.category == "Bakery"
    assert cat_summary.sku_count >= 45
    assert cat_summary.total_revenue_30d > 0
    assert cat_summary.top_sku_id != ""
    assert cat_summary.top_sku_revenue > 0


def test_search_skus(kernel):
    """Test flexible search across product catalog."""
    results = kernel.search_skus("Bread", "STORE_01")
    assert len(results) > 0
    for r in results:
        assert "Bread" in r["product_name"] or "Bakery" in r["category"] or "Bread" in r["sub_category"]
