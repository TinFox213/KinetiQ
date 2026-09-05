"""
KinetiQ Synthetic Ground-Truth Data Generator
Generates realistic multi-store retail data with high performance (< 3 seconds)
for 3 stores, 5 suppliers, 250 SKUs over a 90-day window.
"""

import os
import sqlite3
import random
import time
from datetime import date, timedelta
from typing import Optional


# Fixed random seed for deterministic consistency
RANDOM_SEED = 42


def get_db_connection(db_path: str = "data/retail_inventory.db") -> sqlite3.Connection:
    """Create directory if needed and return an optimized SQLite connection."""
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_schema(conn: sqlite3.Connection, schema_path: Optional[str] = None):
    """Execute schema.sql to initialize database tables and indexes."""
    if schema_path is None:
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)


def generate_retail_dataset(
    db_path: str = "data/retail_inventory.db",
    days: int = 90,
    schema_path: Optional[str] = None,
    seed: int = RANDOM_SEED,
) -> dict:
    """
    Synthesize 90 days of realistic sales, inventory snapshots, stores, and products.
    Executes in < 3 seconds using batch executemany.
    """
    random.seed(seed)
    start_time = time.time()

    conn = get_db_connection(db_path)
    init_schema(conn, schema_path)
    cur = conn.cursor()

    # Clear existing data in correct FK order
    cur.execute("DELETE FROM store_transfers;")
    cur.execute("DELETE FROM daily_sales;")
    cur.execute("DELETE FROM inventory_snapshots;")
    cur.execute("DELETE FROM products;")
    cur.execute("DELETE FROM suppliers;")
    cur.execute("DELETE FROM stores;")

    # 1. Seed Stores
    stores_data = [
        ("STORE_01", "Downtown Metro Express", "Metro Central", "Urban Express", 2500, "Rajesh Sharma"),
        ("STORE_02", "Westside Suburban Supercenter", "Westside Suburb", "Suburban Super", 8500, "Anita Desai"),
        ("STORE_03", "North Corridor Highway Hub", "North Corridor", "Highway Transit", 3500, "Vikram Patel"),
    ]
    cur.executemany(
        "INSERT INTO stores (store_id, name, city, store_type, sq_ft, manager_name) VALUES (?, ?, ?, ?, ?, ?);",
        stores_data,
    )

    # 2. Seed Suppliers
    suppliers_data = [
        ("SUP_01", "FreshFarm Dairies & Bakery Co", 2, 15, 0.96),
        ("SUP_02", "Apex FMCG & Snacks Distributors", 4, 25, 0.94),
        ("SUP_03", "PureHarvest Organic Staples", 5, 20, 0.92),
        ("SUP_04", "QuickBite Beverage & Refreshment Corp", 3, 30, 0.98),
        ("SUP_05", "Heritage Gourmet & Fine Condiments", 6, 10, 0.90),
    ]
    cur.executemany(
        "INSERT INTO suppliers (supplier_id, supplier_name, lead_time_days, min_order_qty, reliability_score) VALUES (?, ?, ?, ?, ?);",
        suppliers_data,
    )

    # 3. Seed Products (Exactly 250 SKUs: SKU_1001 to SKU_1250)
    categories = [
        ("Dairy & Eggs", ["Milk", "Yogurt", "Cheese", "Butter", "Eggs"], "SUP_01", True, 7),
        ("Bakery", ["Bread", "Buns", "Bagels", "Croissants", "Muffins"], "SUP_01", True, 4),
        ("Beverages", ["Soda", "Juice", "Cold Brew", "Iced Tea", "Energy Drink"], "SUP_04", False, 180),
        ("Snacks", ["Chips", "Pretzels", "Crackers", "Popcorn", "Nuts"], "SUP_02", False, 120),
        ("Pantry", ["Pasta", "Rice", "Canned Beans", "Cooking Oil", "Sauce"], "SUP_03", False, 365),
    ]

    item_prefixes = {
        "Dairy & Eggs": ["Pasture Raised", "Farm Fresh", "Organic", "Lactose Free", "Homestead"],
        "Bakery": ["Artisan", "Golden", "Rustic", "Country", "Morning Harvest"],
        "Beverages": ["Sparkling", "Pure", "Hydra", "Botanical", "Mountain Stream"],
        "Snacks": ["Crispy", "Crunchy", "Gourmet", "Toasted", "Savory"],
        "Pantry": ["Heritage", "Chef Selection", "Sun-Ripened", "Natural", "Stone-Ground"],
    }

    # Explicit anchor definitions
    anchors = {
        1001: {
            "name": "Classic White Bread 400g", "cat": "Bakery", "subcat": "Bread",
            "cost": 1.20, "retail": 2.49, "perish": 1, "shelf": 4, "sup": "SUP_01",
            "type": "staple_perishable", "base_demand": 18
        },
        1002: {
            "name": "Whole Wheat Loaf 400g", "cat": "Bakery", "subcat": "Bread",
            "cost": 1.50, "retail": 3.29, "perish": 1, "shelf": 5, "sup": "SUP_01",
            "type": "staple_perishable", "base_demand": 14
        },
        1008: {
            "name": "Artisanal Sourdough Loaf 500g", "cat": "Bakery", "subcat": "Bread",
            "cost": 2.20, "retail": 4.99, "perish": 1, "shelf": 3, "sup": "SUP_01",
            "type": "sourdough_anomaly", "base_demand": 16
        },
        1012: {
            "name": "Cold Pressed Extra Virgin Olive Oil 500ml", "cat": "Pantry", "subcat": "Cooking Oil",
            "cost": 5.50, "retail": 11.99, "perish": 0, "shelf": 365, "sup": "SUP_03",
            "type": "staple_fmcg", "base_demand": 9
        },
        1020: {
            "name": "Organic A2 Fresh Whole Milk 1L", "cat": "Dairy & Eggs", "subcat": "Milk",
            "cost": 1.80, "retail": 3.89, "perish": 1, "shelf": 4, "sup": "SUP_01",
            "type": "arbitrage_milk", "base_demand": 15
        },
        1042: {
            "name": "Organic Plain Greek Yogurt 500g", "cat": "Dairy & Eggs", "subcat": "Yogurt",
            "cost": 2.10, "retail": 4.49, "perish": 1, "shelf": 6, "sup": "SUP_01",
            "type": "stockout_yogurt", "base_demand": 12
        },
        1050: {
            "name": "Roasted Himalayan Pink Salt Makhana 100g", "cat": "Snacks", "subcat": "Nuts",
            "cost": 1.40, "retail": 3.49, "perish": 0, "shelf": 150, "sup": "SUP_02",
            "type": "velocity_spike", "base_demand": 8
        },
        1080: {
            "name": "Artisanal White Truffle Glaze & Vinegar 250ml", "cat": "Pantry", "subcat": "Sauce",
            "cost": 18.50, "retail": 29.99, "perish": 0, "shelf": 365, "sup": "SUP_05",
            "type": "dead_stock_vinegar", "base_demand": 0
        },
    }

    products_data = []
    sku_configs = {}

    for sku_num in range(1001, 1251):
        sku_id = f"SKU_{sku_num}"
        if sku_num in anchors:
            a = anchors[sku_num]
            products_data.append((
                sku_id, a["name"], a["cat"], a["subcat"],
                a["cost"], a["retail"], a["perish"], a["shelf"], a["sup"]
            ))
            sku_configs[sku_id] = {"type": a["type"], "base_demand": a["base_demand"]}
        else:
            cat_tuple = categories[(sku_num % len(categories))]
            cat_name, subcats, sup_id, is_perish, shelf_life = cat_tuple
            subcat = subcats[(sku_num % len(subcats))]
            prefix = item_prefixes[cat_name][(sku_num % len(item_prefixes[cat_name]))]

            cost = round(random.uniform(1.20, 18.00), 2)
            margin = random.uniform(1.35, 1.85)
            retail = round(cost * margin, 2)
            product_name = f"{prefix} {subcat} {sku_num % 100 + 100}g"

            if sku_num <= 1030:
                behavior = "fast_perishable" if is_perish else "fast_fmcg"
                base_dem = random.randint(12, 22)
            elif 1031 <= sku_num <= 1060:
                behavior = "fmcg_occasional_stockout"
                base_dem = random.randint(10, 18)
            elif 1061 <= sku_num <= 1090:
                behavior = "dead_stock_candidate"
                base_dem = random.choice([0, 1])
            else:
                behavior = "standard_moving"
                base_dem = random.randint(3, 9)

            products_data.append((
                sku_id, product_name, cat_name, subcat,
                cost, retail, 1 if is_perish else 0, shelf_life, sup_id
            ))
            sku_configs[sku_id] = {"type": behavior, "base_demand": base_dem}

    cur.executemany(
        "INSERT INTO products (sku_id, product_name, category, sub_category, cost_price, retail_price, is_perishable, shelf_life_days, supplier_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);",
        products_data,
    )

    # 4. Simulate 90 Days of Sales & Daily Inventory Snapshots
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)

    daily_sales_records = []
    inventory_snapshot_records = []

    store_multiplier = {
        "STORE_01": {"perishable": 1.25, "snack": 1.0, "specialty": 0.35, "general": 1.0},
        "STORE_02": {"perishable": 1.10, "snack": 1.35, "specialty": 0.8, "general": 1.2},
        "STORE_03": {"perishable": 0.40, "snack": 1.20, "specialty": 0.1, "general": 0.75},
    }

    # Track on_hand and orders per (store_id, sku_id)
    state = {}
    for store_tuple in stores_data:
        store_id = store_tuple[0]
        for prod in products_data:
            sku_id = prod[0]
            cfg = sku_configs[sku_id]
            base_d = cfg["base_demand"]

            # Initial stock buffer
            init_stock = base_d * random.randint(8, 16)
            if cfg["type"] == "dead_stock_vinegar" and store_id == "STORE_01":
                init_stock = 42
            elif cfg["type"] == "dead_stock_candidate" and store_id == "STORE_01":
                init_stock = random.randint(25, 50)
            elif cfg["type"] == "arbitrage_milk":
                if store_id == "STORE_01":
                    init_stock = 30
                elif store_id == "STORE_03":
                    init_stock = 65

            state[(store_id, sku_id)] = {
                "on_hand": max(init_stock, 10),
                "pending_orders": [],  # list of (arrival_day_index, qty)
                "days_since_last_sale": 0,
            }

    products_dict = {p[0]: {"cost": p[4], "retail": p[5], "sup_id": p[8], "is_perish": p[6]} for p in products_data}
    suppliers_dict = {s[0]: {"lead_time": s[2], "min_order": s[3]} for s in suppliers_data}

    for day_idx in range(days):
        current_date = start_date + timedelta(days=day_idx)
        is_final_day = (day_idx == days - 1)
        is_past_35_days = (day_idx >= days - 35)

        for store_tuple in stores_data:
            store_id = store_tuple[0]
            mults = store_multiplier[store_id]

            for prod in products_data:
                sku_id = prod[0]
                p_info = products_dict[sku_id]
                cfg = sku_configs[sku_id]
                st = state[(store_id, sku_id)]

                # 1. Receive pending shipments due today
                new_pending = []
                for arr_idx, qty in st["pending_orders"]:
                    if arr_idx == day_idx:
                        st["on_hand"] += qty
                    else:
                        new_pending.append((arr_idx, qty))
                st["pending_orders"] = new_pending

                # 2. Determine demand for today
                c_type = cfg["type"]
                base_d = cfg["base_demand"]

                # Tailored behavioral overrides
                if c_type == "dead_stock_vinegar":
                    if store_id == "STORE_01":
                        demand = 0 if is_past_35_days else (1 if random.random() < 0.1 else 0)
                    else:
                        demand = 1 if random.random() < 0.2 else 0

                elif c_type == "dead_stock_candidate":
                    if store_id == "STORE_01" and is_past_35_days:
                        demand = 0
                    else:
                        demand = 1 if random.random() < 0.15 else 0

                elif c_type == "sourdough_anomaly":
                    if store_id == "STORE_01" and is_final_day:
                        demand = 0
                    else:
                        demand = max(0, int(random.gauss(base_d, 2.5)))

                elif c_type == "velocity_spike":
                    if store_id == "STORE_01" and is_final_day:
                        demand = int(base_d * 2.8)
                    else:
                        demand = max(0, int(random.gauss(base_d, 1.8)))

                elif c_type == "arbitrage_milk":
                    if store_id == "STORE_01":
                        demand = max(0, int(random.gauss(12, 2.0)))
                        if is_final_day:
                            st["on_hand"] = 14  # 14 units on hand, runway 2.3 days
                    elif store_id == "STORE_03":
                        demand = 1 if random.random() < 0.3 else 0
                        if is_final_day:
                            st["on_hand"] = 58  # Store 3 holds 58 units idle
                    else:
                        demand = max(0, int(random.gauss(8, 1.5)))

                elif c_type == "stockout_yogurt":
                    if store_id == "STORE_01" and is_final_day:
                        demand = 6
                        st["on_hand"] = 14  # 14 units remaining, 5.6 units/day velocity
                    else:
                        demand = max(0, int(random.gauss(base_d, 1.8)))

                elif c_type == "fmcg_occasional_stockout":
                    if day_idx in (30, 60) and store_id == "STORE_01":
                        st["on_hand"] = 2
                        demand = 15
                    else:
                        demand = max(0, int(random.gauss(base_d, 2.0)))

                else:
                    cat = prod[2]
                    cat_mult = mults["perishable"] if p_info["is_perish"] else mults["general"]
                    mean_demand = max(0.5, base_d * cat_mult)
                    demand = max(0, int(random.gauss(mean_demand, max(0.8, mean_demand * 0.25))))

                # 3. Fulfill sales from on-hand stock
                current_on_hand = st["on_hand"]
                if current_on_hand <= 0:
                    units_sold = 0
                    had_stockout = 1 if demand > 0 else 0
                elif current_on_hand < demand:
                    units_sold = current_on_hand
                    st["on_hand"] = 0
                    had_stockout = 1
                else:
                    units_sold = demand
                    st["on_hand"] -= units_sold
                    had_stockout = 0

                # 4. Update sales streak & revenue
                if units_sold > 0:
                    st["days_since_last_sale"] = 0
                else:
                    st["days_since_last_sale"] += 1

                gross_rev = round(units_sold * p_info["retail"], 2)

                daily_sales_records.append((
                    current_date.isoformat(),
                    store_id,
                    sku_id,
                    units_sold,
                    gross_rev,
                    had_stockout,
                ))

                inventory_snapshot_records.append((
                    current_date.isoformat(),
                    store_id,
                    sku_id,
                    st["on_hand"],
                    0,  # reserved units
                    st["days_since_last_sale"],
                ))

                # 5. Replenishment logic
                sup = suppliers_dict[p_info["sup_id"]]
                lead_time = sup["lead_time"]
                min_order = sup["min_order"]
                reorder_threshold = max(min_order // 2, int(base_d * lead_time * 1.2))

                if (
                    c_type not in ("dead_stock_vinegar", "dead_stock_candidate")
                    and st["on_hand"] <= reorder_threshold
                    and len(st["pending_orders"]) == 0
                    and not is_final_day
                ):
                    order_qty = max(min_order, int(base_d * (lead_time + 7)))
                    arrival_day = day_idx + lead_time
                    st["pending_orders"].append((arrival_day, order_qty))

    # Fast batch insertions
    cur.executemany(
        "INSERT INTO daily_sales (sale_date, store_id, sku_id, units_sold, gross_revenue, had_stockout) VALUES (?, ?, ?, ?, ?, ?);",
        daily_sales_records,
    )
    cur.executemany(
        "INSERT INTO inventory_snapshots (snapshot_date, store_id, sku_id, on_hand_units, reserved_units, days_since_last_sale) VALUES (?, ?, ?, ?, ?, ?);",
        inventory_snapshot_records,
    )

    # Initial sample transfer record
    cur.execute(
        """
        INSERT INTO store_transfers (transfer_id, created_at, from_store_id, to_store_id, sku_id, units, status)
        VALUES (?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?);
        """,
        ("TR_INIT_001", "STORE_03", "STORE_01", "SKU_1020", 25, "COMPLETED")
    )

    conn.commit()
    conn.close()

    elapsed = time.time() - start_time
    return {
        "status": "success",
        "elapsed_seconds": round(elapsed, 3),
        "stores_count": len(stores_data),
        "suppliers_count": len(suppliers_data),
        "products_count": len(products_data),
        "sales_records": len(daily_sales_records),
        "inventory_records": len(inventory_snapshot_records),
    }


if __name__ == "__main__":
    db_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "retail_inventory.db")
    res = generate_retail_dataset(db_file)
    print(f"Data generation complete: {res}")
