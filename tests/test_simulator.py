"""
Unit Tests for Phase 07: Interactive What-If Simulation Sandbox
Validates price elasticity demand lift, clearance runway shortening,
profit delta calculations, and stockout exhaustion warnings.
"""

import os
import pytest
from src.data.generator import generate_retail_dataset
from src.analytics.kernel import AnalyticsKernel
from src.analytics.simulator import simulate_intervention, SimulationResult


TEST_DB_PATH = "data/test_retail_inventory.db"


@pytest.fixture(scope="module")
def kernel():
    if not os.path.exists(TEST_DB_PATH):
        generate_retail_dataset(db_path=TEST_DB_PATH, days=90)
    return AnalyticsKernel(db_path=TEST_DB_PATH)


def test_simulate_dead_stock_markdown(kernel):
    """
    Test 30% markdown on dead stock SKU_1080 (Artisanal Truffle Vinegar).
    Verifies that clearance runway drops from 999 days down to an active timeframe.
    """
    sim = simulate_intervention("SKU_1080", store_id="STORE_01", discount_percent=30.0, kernel=kernel)
    assert sim is not None
    assert isinstance(sim, SimulationResult)

    assert sim.sku_id == "SKU_1080"
    assert sim.discount_percent == 30.0
    assert sim.discounted_price < sim.base_retail_price
    assert sim.discounted_price == round(sim.base_retail_price * 0.70, 2)

    # Velocity must increase, days to clear must decrease
    assert sim.projected_velocity > sim.base_velocity
    assert sim.projected_clearance_days < sim.base_clearance_days

    # Units sold in 14 days must increase
    assert sim.projected_units_sold >= sim.base_units_sold
    assert "price_elasticity_coefficient" in sim.assumptions


def test_simulate_fast_moving_item_exhaustion_warning(kernel):
    """
    Test discounting a fast-moving item with limited runway.
    Verifies that high demand lift flags inventory exhaustion risk if it cuts into lead time.
    """
    # SKU_1020 has 14 units on hand and 4-day lead time
    sim = simulate_intervention("SKU_1020", store_id="STORE_01", discount_percent=25.0, kernel=kernel)
    assert sim is not None

    assert sim.velocity_lift_percent > 0
    assert sim.projected_velocity > sim.base_velocity

    # If projected clearance days is less than or close to lead time, exhaustion risk must be flagged
    if sim.projected_clearance_days <= 4.0:
        assert "HIGH RISK" in sim.inventory_exhaustion_risk


def test_simulate_non_existent_sku(kernel):
    """Ensure invalid SKU returns None."""
    res = simulate_intervention("SKU_INVALID_999", store_id="STORE_01", discount_percent=15.0, kernel=kernel)
    assert res is None
