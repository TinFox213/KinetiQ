import time
import pytest
from src.analytics.rebalance import ArbitrageEngine, STORE_DISTANCE_MATRIX, TransferManifest

def test_tc_049_stockout_deficit_quantification(arbitrage_engine):
    manifest = arbitrage_engine.evaluate_transfer_for_sku("SKU_1020", "STORE_01")
    assert manifest is not None
    assert manifest.quantity > 0
    assert manifest.to_store_id == "STORE_01"

def test_tc_050_safe_surplus_calculation(arbitrage_engine):
    manifest = arbitrage_engine.evaluate_transfer_for_sku("SKU_1020", "STORE_01")
    assert manifest is not None
    assert manifest.source_remaining_runway_days >= 7.0

def test_tc_051_donor_store_depletion_protection(arbitrage_engine):
    manifest = arbitrage_engine.evaluate_transfer_for_sku("SKU_1020", "STORE_01")
    assert manifest is not None
    assert manifest.source_remaining_runway_days >= 5.0

def test_tc_052_courier_cost_vs_margin_tradeoff(arbitrage_engine):
    manifest = arbitrage_engine.evaluate_transfer_for_sku("SKU_1020", "STORE_01")
    assert manifest is not None
    assert manifest.net_savings > 0.0
    assert manifest.net_savings == round(manifest.gross_profit_protected - manifest.estimated_courier_cost, 2)

def test_tc_053_stn_manifest_schema(arbitrage_engine):
    manifest = arbitrage_engine.evaluate_transfer_for_sku("SKU_1020", "STORE_01")
    assert manifest is not None
    assert manifest.manifest_id.startswith("STN")
    assert manifest.sku_id == "SKU_1020"
    assert manifest.from_store_id != manifest.to_store_id
    assert "courier_cost_usd" in manifest.assumptions

def test_tc_054_multi_donor_tie_breaking(arbitrage_engine):
    manifest = arbitrage_engine.evaluate_transfer_for_sku("SKU_1020", "STORE_01")
    assert manifest is not None
    assert manifest.from_store_id == "STORE_03"

def test_tc_055_fallback_when_no_surplus(arbitrage_engine):
    manifest = arbitrage_engine.evaluate_transfer_for_sku("SKU_1020", "STORE_03")
    assert manifest is None

def test_tc_056_circular_transfer_prevention(arbitrage_engine):
    transfers = arbitrage_engine.find_interstore_transfers("STORE_01")
    for t in transfers:
        assert t.from_store_id != t.to_store_id

def test_tc_057_distance_matrix_feasibility_filter():
    for (s1, s2), meta in STORE_DISTANCE_MATRIX.items():
        assert meta["distance_km"] <= 50.0
        assert meta["transit_hours"] > 0
        assert meta["courier_cost"] > 0

def test_tc_058_in_transit_stock_accounting(arbitrage_engine):
    manifest = arbitrage_engine.evaluate_transfer_for_sku("SKU_1020", "STORE_01")
    assert manifest is not None
    assert manifest.destination_runway_after_days > 2.0

def test_tc_059_database_transaction_commit(arbitrage_engine):
    success = arbitrage_engine.commit_transfer(
        manifest_id="STN_TEST_9999",
        from_store_id="STORE_03",
        to_store_id="STORE_01",
        sku_id="SKU_1020",
        quantity=5
    )
    assert success is True

def test_tc_060_arbitrage_engine_speed_benchmark(arbitrage_engine):
    t0 = time.perf_counter()
    arbitrage_engine.find_interstore_transfers("STORE_01")
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.25, f"Arbitrage evaluation took {elapsed:.3f}s, expected < 0.25s"
