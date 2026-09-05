import time
import pytest
from src.analytics.simulator import simulate_intervention, CATEGORY_PRICE_ELASTICITY

def test_tc_085_negative_price_elasticity_application(kernel):
    res = simulate_intervention("SKU_1001", "STORE_01", discount_percent=20.0, kernel=kernel)
    assert res is not None
    assert res.price_elasticity < 0.0
    assert res.velocity_lift_percent > 0.0
    assert res.projected_velocity > res.base_velocity

def test_tc_086_projected_days_to_clear_calculation(kernel):
    res = simulate_intervention("SKU_1080", "STORE_01", discount_percent=35.0, kernel=kernel)
    assert res is not None
    assert res.projected_clearance_days < res.base_clearance_days

def test_tc_087_gross_profit_delta_calculation(kernel):
    res = simulate_intervention("SKU_1001", "STORE_01", discount_percent=15.0, duration_days=14, kernel=kernel)
    assert res is not None
    expected_delta = round(res.projected_gross_profit - res.base_gross_profit, 2)
    assert abs(res.gross_profit_delta - expected_delta) <= 0.05

def test_tc_088_zero_discount_identity_boundary(kernel):
    res = simulate_intervention("SKU_1001", "STORE_01", discount_percent=0.0, kernel=kernel)
    assert res is not None
    assert res.discounted_price == res.base_retail_price
    assert res.velocity_lift_percent == 0.0

def test_tc_089_high_clearance_discount_boundary(kernel):
    res = simulate_intervention("SKU_1080", "STORE_01", discount_percent=80.0, kernel=kernel)
    assert res is not None
    assert res.discounted_price < res.base_retail_price
    assert res.projected_velocity > 0

def test_tc_090_negative_discount_clamped(kernel):
    # Clamped to minimum 0.0
    res = simulate_intervention("SKU_1001", "STORE_01", discount_percent=-10.0, kernel=kernel)
    assert res is not None
    assert res.discount_percent >= 0.0

def test_tc_091_stockout_capped_at_on_hand(kernel):
    res = simulate_intervention("SKU_1020", "STORE_01", discount_percent=40.0, duration_days=30, kernel=kernel)
    assert res is not None
    assert res.projected_units_sold <= res.on_hand

def test_tc_092_category_specific_elasticity(kernel):
    assert CATEGORY_PRICE_ELASTICITY["Bakery"] != CATEGORY_PRICE_ELASTICITY["Pantry"]

def test_tc_093_simulator_non_existent_sku(kernel):
    res = simulate_intervention("SKU_INVALID_9999", "STORE_01", kernel=kernel)
    assert res is None

def test_tc_094_simulator_speed_benchmark(kernel):
    t0 = time.perf_counter()
    for _ in range(50):
        simulate_intervention("SKU_1080", "STORE_01", discount_percent=25.0, kernel=kernel)
    elapsed = time.perf_counter() - t0
    avg_ms = (elapsed / 50) * 1000
    assert avg_ms < 15.0, f"Average simulation time {avg_ms:.2f}ms, expected < 15ms"
