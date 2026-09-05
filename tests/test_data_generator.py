"""
Tests for Phase 01: Domain Data Engineering & Synthetic Ground-Truth Engine
Validates schema initialization, execution speed, row counts, data integrity, and retail patterns.
"""

import os
import sqlite3
import pytest
from src.data.generator import generate_retail_dataset, get_db_connection


TEST_DB_PATH = "data/test_retail_inventory.db"


@pytest.fixture(scope="module")
def seeded_db():
    """Seed a test database once for the test module."""
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except OSError:
            pass

    result = generate_retail_dataset(db_path=TEST_DB_PATH, days=90)
    yield result, TEST_DB_PATH

    # Cleanup after test suite
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except OSError:
            pass


def test_generation_performance(seeded_db):
    """Ensure dataset generation takes less than 5 seconds (target < 3s)."""
    result, _ = seeded_db
    assert result["status"] == "success"
    assert result["elapsed_seconds"] < 5.0, f"Generation took {result['elapsed_seconds']}s, exceeding 5.0s SLA."


def test_entity_counts(seeded_db):
    """Verify exact expected counts for stores, suppliers, products, and 90-day transactions."""
    result, db_path = seeded_db
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Stores
    cur.execute("SELECT COUNT(*) FROM stores;")
    stores_count = cur.fetchone()[0]
    assert stores_count == 3, f"Expected 3 stores, got {stores_count}"

    # Suppliers
    cur.execute("SELECT COUNT(*) FROM suppliers;")
    suppliers_count = cur.fetchone()[0]
    assert suppliers_count == 5, f"Expected 5 suppliers, got {suppliers_count}"

    # Products
    cur.execute("SELECT COUNT(*) FROM products;")
    products_count = cur.fetchone()[0]
    assert products_count == 250, f"Expected 250 products, got {products_count}"

    # Daily Sales: 90 days * 3 stores * 250 SKUs = 67,500
    cur.execute("SELECT COUNT(*) FROM daily_sales;")
    sales_count = cur.fetchone()[0]
    assert sales_count == 90 * 3 * 250, f"Expected 67,500 sales rows, got {sales_count}"

    # Inventory Snapshots: 90 days * 3 stores * 250 SKUs = 67,500
    cur.execute("SELECT COUNT(*) FROM inventory_snapshots;")
    inventory_count = cur.fetchone()[0]
    assert inventory_count == 90 * 3 * 250, f"Expected 67,500 inventory rows, got {inventory_count}"

    conn.close()


def test_data_integrity_and_null_constraints(seeded_db):
    """Verify zero NULL values across primary keys, foreign keys, and metrics."""
    _, db_path = seeded_db
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Null checks on products
    cur.execute("""
        SELECT COUNT(*) FROM products 
        WHERE sku_id IS NULL OR product_name IS NULL OR cost_price IS NULL 
           OR retail_price IS NULL OR supplier_id IS NULL;
    """)
    assert cur.fetchone()[0] == 0

    # Null checks on daily sales
    cur.execute("""
        SELECT COUNT(*) FROM daily_sales 
        WHERE sale_date IS NULL OR store_id IS NULL OR sku_id IS NULL 
           OR units_sold IS NULL OR gross_revenue IS NULL;
    """)
    assert cur.fetchone()[0] == 0

    # Foreign key integrity check
    cur.execute("""
        SELECT COUNT(*) FROM daily_sales s
        LEFT JOIN products p ON s.sku_id = p.sku_id
        WHERE p.sku_id IS NULL;
    """)
    assert cur.fetchone()[0] == 0

    cur.execute("""
        SELECT COUNT(*) FROM daily_sales s
        LEFT JOIN stores st ON s.store_id = st.store_id
        WHERE st.store_id IS NULL;
    """)
    assert cur.fetchone()[0] == 0

    conn.close()


def test_retail_patterns_and_scenarios(seeded_db):
    """Verify ground truth retail patterns exist for core PRD scenarios."""
    _, db_path = seeded_db
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1. Arbitrage pair: SKU_1020 on the latest date
    # Store 1 should have low stock (deficit), Store 3 should have surplus
    cur.execute("""
        SELECT store_id, on_hand_units FROM inventory_snapshots
        WHERE sku_id = 'SKU_1020' 
        ORDER BY snapshot_date DESC LIMIT 3;
    """)
    latest_milk = dict(cur.fetchall())
    assert latest_milk["STORE_01"] <= 15, "STORE_01 should have low stock of SKU_1020 for arbitrage test"
    assert latest_milk["STORE_03"] >= 50, "STORE_03 should have surplus stock of SKU_1020 for arbitrage test"

    # 2. Dead stock candidate: SKU_1080 at STORE_01
    cur.execute("""
        SELECT on_hand_units, days_since_last_sale FROM inventory_snapshots
        WHERE sku_id = 'SKU_1080' AND store_id = 'STORE_01'
        ORDER BY snapshot_date DESC LIMIT 1;
    """)
    truffle_row = cur.fetchone()
    assert truffle_row is not None
    on_hand, idle_days = truffle_row
    assert on_hand >= 30, "STORE_01 should hold significant on-hand units for dead stock SKU_1080"
    assert idle_days >= 30, f"STORE_01 should have >= 30 idle days for dead stock SKU_1080, got {idle_days}"

    # 3. Stockout events should exist in the dataset
    cur.execute("SELECT COUNT(*) FROM daily_sales WHERE had_stockout = 1;")
    stockout_count = cur.fetchone()[0]
    assert stockout_count > 0, "Dataset must contain realistic stockout occurrences"

    # 4. Anomaly candidate: SKU_1008 on latest date at STORE_01 has 0 sales despite stock > 0
    cur.execute("""
        SELECT s.units_sold, i.on_hand_units 
        FROM daily_sales s
        JOIN inventory_snapshots i ON s.sale_date = i.snapshot_date AND s.store_id = i.store_id AND s.sku_id = i.sku_id
        WHERE s.sku_id = 'SKU_1008' AND s.store_id = 'STORE_01'
        ORDER BY s.sale_date DESC LIMIT 1;
    """)
    sourdough_row = cur.fetchone()
    assert sourdough_row is not None
    sold, on_hand = sourdough_row
    assert sold == 0 and on_hand > 0, "SKU_1008 should exhibit phantom inventory (0 sales despite on_hand > 0) on final day"

    conn.close()
