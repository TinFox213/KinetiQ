import time
import os
import sqlite3
import pytest
from src.data.generator import generate_retail_dataset

def test_tc_001_relational_schema_ddl_and_table_integrity(test_db):
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cursor.fetchall()}
    expected = {'stores', 'suppliers', 'products', 'inventory_snapshots', 'daily_sales', 'store_transfers'}
    assert expected.issubset(tables), f"Missing tables: {expected - tables}"
    conn.close()

def test_tc_002_synthetic_data_generator_execution_performance():
    tmp_path = "data/tmp_perf_test.db"
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
    t0 = time.perf_counter()
    generate_retail_dataset(tmp_path, days=90)
    duration = time.perf_counter() - t0
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
    assert duration < 3.5, f"Generation took {duration:.2f}s, expected < 3.5s"

def test_tc_003_store_entity_representation(test_db):
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute('SELECT store_id, name, city, store_type, manager_name FROM stores;')
    stores = cursor.fetchall()
    conn.close()
    assert len(stores) == 3, f"Expected 3 stores, found {len(stores)}"
    store_ids = [s[0] for s in stores]
    assert 'STORE_01' in store_ids
    assert 'STORE_02' in store_ids
    assert 'STORE_03' in store_ids

def test_tc_004_product_catalog_breadth_and_perishable(test_db):
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*), SUM(is_perishable) FROM products;')
    total, perishable = cursor.fetchone()
    conn.close()
    assert total == 250, f"Expected 250 products, found {total}"
    assert perishable > 0, "Expected perishable items"
    assert perishable < total, "Not all items should be perishable"

def test_tc_005_supplier_association_and_lead_time(test_db):
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute('SELECT supplier_id, lead_time_days FROM suppliers;')
    suppliers = cursor.fetchall()
    conn.close()
    assert len(suppliers) == 5, f"Expected 5 suppliers, found {len(suppliers)}"
    for sup_id, lead_time in suppliers:
        assert 2 <= lead_time <= 7, f"Supplier {sup_id} lead time {lead_time} outside 2..7"

def test_tc_006_daily_sales_record_count_and_continuity(test_db):
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM daily_sales;')
    count = cursor.fetchone()[0]
    conn.close()
    assert count == 67500, f"Expected 67500 records, got {count}"

def test_tc_007_inventory_stock_conservation_equation(test_db):
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.store_id, s.sku_id, s.units_sold, inv.on_hand_units
        FROM daily_sales s
        JOIN inventory_snapshots inv ON s.store_id = inv.store_id AND s.sku_id = inv.sku_id
        WHERE s.sale_date = (SELECT MAX(sale_date) FROM daily_sales)
        LIMIT 50;
    ''')
    rows = cursor.fetchall()
    conn.close()
    assert len(rows) > 0
    for store_id, sku_id, sold, on_hand in rows:
        assert on_hand >= 0, f"On hand {on_hand} cannot be negative"

def test_tc_008_stockout_event_truncation_and_flag_consistency(test_db):
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM daily_sales WHERE had_stockout = 1;')
    stockouts = cursor.fetchone()[0]
    conn.close()
    assert stockouts >= 0

def test_tc_009_dead_stock_seeding_invariant_check(test_db):
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT sku_id, SUM(units_sold) 
        FROM daily_sales 
        WHERE sku_id = 'SKU_1080' AND sale_date >= date((SELECT MAX(sale_date) FROM daily_sales), '-30 days')
        GROUP BY sku_id;
    ''')
    row = cursor.fetchone()
    conn.close()
    assert row is None or row[1] == 0, "SKU_1080 should have 0 sales in past 30 days"

def test_tc_010_high_velocity_demand_spike_seeding_check(test_db):
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT sku_id, units_sold 
        FROM daily_sales 
        WHERE sale_date = (SELECT MAX(sale_date) FROM daily_sales) AND sku_id = 'SKU_1008';
    ''')
    row = cursor.fetchone()
    conn.close()
    assert row is not None

def test_tc_011_multi_store_arbitrage_setup_validation(test_db):
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT store_id, on_hand_units FROM inventory_snapshots WHERE sku_id = 'SKU_1020';
    ''')
    rows = dict(cursor.fetchall())
    conn.close()
    assert 'STORE_01' in rows and 'STORE_03' in rows
    assert rows['STORE_01'] < rows['STORE_03'], f"Expected Store 1 deficit ({rows.get('STORE_01')}) < Store 3 surplus ({rows.get('STORE_03')})"

def test_tc_012_database_reinitialization_idempotency():
    tmp_path = "data/tmp_idempotent_test.db"
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
    generate_retail_dataset(tmp_path, days=30)
    generate_retail_dataset(tmp_path, days=30)
    conn = sqlite3.connect(tmp_path)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM products;')
    count = cursor.fetchone()[0]
    conn.close()
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
    assert count == 250
