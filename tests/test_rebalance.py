"""
Unit Tests for Phase 05: Multi-Store Inventory Arbitrage Engine
Validates cross-store inventory rebalancing, safe surplus calculation, courier logistics economics,
Stock Transfer Note (STN) generation, and transfer commit tracking.
"""

import os
import sqlite3
import pytest
from src.data.generator import generate_retail_dataset
from src.analytics.kernel import AnalyticsKernel
from src.analytics.rebalance import ArbitrageEngine, TransferManifest


TEST_DB_PATH = "data/test_retail_inventory.db"


@pytest.fixture(scope="module")
def arbitrage():
    if not os.path.exists(TEST_DB_PATH):
        generate_retail_dataset(db_path=TEST_DB_PATH, days=90)
    kernel = AnalyticsKernel(db_path=TEST_DB_PATH)
    return ArbitrageEngine(db_path=TEST_DB_PATH, kernel=kernel)


def test_evaluate_transfer_for_arbitrage_candidate(arbitrage):
    """
    Test the anchor arbitrage pair:
    SKU_1020 (Organic A2 Milk) is in deficit at STORE_01, while STORE_03 holds idle surplus.
    """
    manifest = arbitrage.evaluate_transfer_for_sku("SKU_1020", to_store_id="STORE_01")
    assert manifest is not None
    assert isinstance(manifest, TransferManifest)

    assert manifest.sku_id == "SKU_1020"
    assert manifest.from_store_id == "STORE_03"
    assert manifest.to_store_id == "STORE_01"

    assert manifest.quantity > 0
    assert manifest.revenue_protected > 0
    assert manifest.gross_profit_protected > 0
    assert manifest.estimated_courier_cost > 0
    assert manifest.net_savings > 0

    # Source store must maintain safe reserve
    assert manifest.source_remaining_runway_days >= 14.0
    assert manifest.destination_runway_after_days > manifest.source_remaining_runway_days or manifest.destination_runway_after_days >= 3.0

    # Assumptions ledger completeness
    assert "courier_cost_usd" in manifest.assumptions
    assert "transit_time_hours" in manifest.assumptions
    assert "source_min_reserve_kept" in manifest.assumptions


def test_no_transfer_when_destination_healthy(arbitrage):
    """Ensure no transfer is generated for items where destination has adequate stock."""
    # Truffle vinegar SKU_1080 has 30+ units on hand at STORE_01 with 0 velocity
    manifest = arbitrage.evaluate_transfer_for_sku("SKU_1080", to_store_id="STORE_01")
    assert manifest is None


def test_find_interstore_transfers_list(arbitrage):
    """Verify scanning for all network rebalancing opportunities for STORE_01."""
    transfers = arbitrage.find_interstore_transfers("STORE_01")
    assert len(transfers) > 0

    for t in transfers:
        assert isinstance(t, TransferManifest)
        assert t.to_store_id == "STORE_01"
        assert t.from_store_id != "STORE_01"
        assert t.net_savings > 0
        assert t.quantity > 0

    # Verify sorting: net savings descending
    savings = [t.net_savings for t in transfers]
    assert savings == sorted(savings, reverse=True)


def test_commit_transfer_database_write(arbitrage):
    """Verify committing an approved transfer manifest records in store_transfers table."""
    test_id = "STN_TEST_999"
    success = arbitrage.commit_transfer(
        manifest_id=test_id,
        from_store_id="STORE_03",
        to_store_id="STORE_01",
        sku_id="SKU_1020",
        quantity=20,
    )
    assert success is True

    conn = sqlite3.connect(arbitrage.db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM store_transfers WHERE transfer_id = ?;", (test_id,))
    row = cur.fetchone()
    conn.close()

    assert row is not None
    assert row[0] == test_id
    assert row[2] == "STORE_03"
    assert row[3] == "STORE_01"
    assert row[4] == "SKU_1020"
    assert row[5] == 20
    assert row[6] == "PENDING"
