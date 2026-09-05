-- KinetiQ Database Schema
-- SQLite schema for multi-store retail sales & inventory copilot

-- 1. Stores Table
CREATE TABLE IF NOT EXISTS stores (
    store_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    store_type TEXT NOT NULL, -- 'Urban Express', 'Suburban Super', 'Highway Transit'
    sq_ft INTEGER NOT NULL,
    manager_name TEXT NOT NULL
);

-- 2. Suppliers Table
CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id TEXT PRIMARY KEY,
    supplier_name TEXT NOT NULL,
    lead_time_days INTEGER NOT NULL,
    min_order_qty INTEGER NOT NULL,
    reliability_score REAL NOT NULL -- e.g., 0.95
);

-- 3. Products Catalog Table
CREATE TABLE IF NOT EXISTS products (
    sku_id TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL, -- 'Dairy & Eggs', 'Bakery', 'Beverages', 'Snacks', 'Pantry'
    sub_category TEXT NOT NULL,
    cost_price REAL NOT NULL,
    retail_price REAL NOT NULL,
    is_perishable BOOLEAN NOT NULL,
    shelf_life_days INTEGER,
    supplier_id TEXT NOT NULL,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
);

-- 4. Inventory Snapshots Table (Daily record per store & SKU)
CREATE TABLE IF NOT EXISTS inventory_snapshots (
    snapshot_date DATE NOT NULL,
    store_id TEXT NOT NULL,
    sku_id TEXT NOT NULL,
    on_hand_units INTEGER NOT NULL,
    reserved_units INTEGER DEFAULT 0,
    days_since_last_sale INTEGER DEFAULT 0,
    PRIMARY KEY (snapshot_date, store_id, sku_id),
    FOREIGN KEY (store_id) REFERENCES stores(store_id),
    FOREIGN KEY (sku_id) REFERENCES products(sku_id)
);

-- 5. Daily Sales Table
CREATE TABLE IF NOT EXISTS daily_sales (
    sale_date DATE NOT NULL,
    store_id TEXT NOT NULL,
    sku_id TEXT NOT NULL,
    units_sold INTEGER NOT NULL,
    gross_revenue REAL NOT NULL,
    had_stockout BOOLEAN DEFAULT 0,
    PRIMARY KEY (sale_date, store_id, sku_id),
    FOREIGN KEY (store_id) REFERENCES stores(store_id),
    FOREIGN KEY (sku_id) REFERENCES products(sku_id)
);

-- 6. Inter-Store Transfers Log
CREATE TABLE IF NOT EXISTS store_transfers (
    transfer_id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    from_store_id TEXT NOT NULL,
    to_store_id TEXT NOT NULL,
    sku_id TEXT NOT NULL,
    units INTEGER NOT NULL,
    status TEXT NOT NULL -- 'PENDING', 'IN_TRANSIT', 'COMPLETED'
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_sales_date_store_sku ON daily_sales(sale_date, store_id, sku_id);
CREATE INDEX IF NOT EXISTS idx_sales_store_date ON daily_sales(store_id, sale_date);
CREATE INDEX IF NOT EXISTS idx_inventory_date_store ON inventory_snapshots(snapshot_date, store_id);
CREATE INDEX IF NOT EXISTS idx_inventory_store_sku ON inventory_snapshots(store_id, sku_id);
