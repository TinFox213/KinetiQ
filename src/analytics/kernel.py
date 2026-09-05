"""
KinetiQ Deterministic Analytical Kernel
Pure mathematical and SQL engine executing all aggregations, rolling velocities,
margins, and store-level metrics with Zero LLM Involvement.
"""

import os
import math
import sqlite3
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any


@dataclass
class SkuMetrics:
    sku_id: str
    product_name: str
    category: str
    sub_category: str
    store_id: str
    store_name: str
    on_hand: int
    days_since_last_sale: int
    cost_price: float
    retail_price: float
    is_perishable: bool
    shelf_life_days: Optional[int]
    supplier_id: str
    supplier_name: str
    lead_time_days: int
    min_order_qty: int
    velocity_7d: float
    velocity_14d: float
    velocity_30d: float
    unconstrained_velocity_7d: float
    std_dev_demand: float
    units_sold_7d: int
    units_sold_30d: int
    revenue_7d: float
    revenue_30d: float
    gross_profit_30d: float
    gross_margin_pct: float
    stockout_days_30d: int
    latest_date: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StoreOverview:
    store_id: str
    store_name: str
    city: str
    store_type: str
    sq_ft: int
    manager_name: str
    window_days: int
    total_revenue: float
    total_cost: float
    total_gross_profit: float
    gross_margin_pct: float
    total_units_sold: int
    active_skus_count: int
    out_of_stock_skus_count: int
    avg_daily_revenue: float
    latest_date: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CategorySummary:
    category: str
    store_id: str
    sku_count: int
    total_units_sold_30d: int
    total_revenue_30d: float
    total_gross_profit_30d: float
    avg_gross_margin_pct: float
    top_sku_id: str
    top_sku_name: str
    top_sku_revenue: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AnalyticsKernel:
    """
    High-performance analytical engine for retail sales and inventory calculations.
    Ensures mathematical fidelity, deterministic reproducibility, and zero hallucination.
    """

    def __init__(self, db_path: str = "data/retail_inventory.db"):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database file not found at: {self.db_path}")
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode = WAL;")
        except Exception:
            pass
        try:
            conn.execute("PRAGMA synchronous = NORMAL;")
        except Exception:
            pass
        return conn

    def get_latest_date(self, conn: Optional[sqlite3.Connection] = None) -> str:
        """Get the latest recorded date across transactions."""
        close_after = False
        if conn is None:
            conn = self._get_connection()
            close_after = True

        cur = conn.cursor()
        cur.execute("SELECT MAX(sale_date) FROM daily_sales;")
        row = cur.fetchone()
        latest = row[0] if row and row[0] else "2026-09-05"

        if close_after:
            conn.close()
        return latest

    def get_sku_metrics(self, sku_id: str, store_id: str = "STORE_01") -> Optional[SkuMetrics]:
        """
        Compute granular 7d, 14d, and 30d performance metrics for a specific SKU at a specific store.
        """
        conn = self._get_connection()
        cur = conn.cursor()

        latest_date = self.get_latest_date(conn)

        # 1. Fetch Product, Store, and Supplier details
        cur.execute(
            """
            SELECT 
                p.sku_id, p.product_name, p.category, p.sub_category,
                p.cost_price, p.retail_price, p.is_perishable, p.shelf_life_days,
                s.supplier_id, s.supplier_name, s.lead_time_days, s.min_order_qty,
                st.store_id, st.name AS store_name
            FROM products p
            JOIN suppliers s ON p.supplier_id = s.supplier_id
            CROSS JOIN stores st ON st.store_id = ?
            WHERE p.sku_id = ?;
            """,
            (store_id, sku_id),
        )
        base_info = cur.fetchone()
        if not base_info:
            conn.close()
            return None

        # 2. Fetch Latest Inventory Snapshot
        cur.execute(
            """
            SELECT on_hand_units, days_since_last_sale
            FROM inventory_snapshots
            WHERE sku_id = ? AND store_id = ? AND snapshot_date = ?;
            """,
            (sku_id, store_id, latest_date),
        )
        inv_row = cur.fetchone()
        on_hand = inv_row["on_hand_units"] if inv_row else 0
        days_since_last_sale = inv_row["days_since_last_sale"] if inv_row else 0

        # 3. Fetch past 30 days daily sales records
        cur.execute(
            """
            SELECT sale_date, units_sold, gross_revenue, had_stockout
            FROM daily_sales
            WHERE sku_id = ? AND store_id = ?
              AND sale_date >= DATE(?, '-29 days') AND sale_date <= ?
            ORDER BY sale_date DESC;
            """,
            (sku_id, store_id, latest_date, latest_date),
        )
        sales_rows = cur.fetchall()
        conn.close()

        # Deterministic window processing in Python
        units_30d = 0
        revenue_30d = 0.0
        stockout_days_30d = 0

        units_14d = 0
        units_7d = 0
        revenue_7d = 0.0
        stockout_days_7d = 0

        units_list_30d = []

        for idx, r in enumerate(sales_rows):
            u = r["units_sold"]
            rev = r["gross_revenue"]
            so = r["had_stockout"]

            units_30d += u
            revenue_30d += rev
            if so:
                stockout_days_30d += 1
            units_list_30d.append(u)

            if idx < 14:
                units_14d += u
            if idx < 7:
                units_7d += u
                revenue_7d += rev
                if so:
                    stockout_days_7d += 1

        days_count_30 = len(sales_rows) if len(sales_rows) > 0 else 30
        velocity_30d = round(units_30d / max(1, days_count_30), 2)
        velocity_14d = round(units_14d / 14.0, 2)
        velocity_7d = round(units_7d / 7.0, 2)

        # Unconstrained Velocity: exclude zero-sales stockout days
        active_days_7d = max(1, 7 - stockout_days_7d)
        unconstrained_velocity_7d = round(units_7d / active_days_7d, 2)

        # Standard deviation of demand (using 30-day series)
        if len(units_list_30d) > 1:
            mean_demand = sum(units_list_30d) / len(units_list_30d)
            variance = sum((x - mean_demand) ** 2 for x in units_list_30d) / len(units_list_30d)
            std_dev_demand = round(math.sqrt(variance), 2)
        else:
            std_dev_demand = 0.0

        # Margin calculations
        cost = base_info["cost_price"]
        retail = base_info["retail_price"]
        gross_profit_30d = round(revenue_30d - (units_30d * cost), 2)
        gross_margin_pct = round(((retail - cost) / max(0.01, retail)) * 100, 1)

        return SkuMetrics(
            sku_id=sku_id,
            product_name=base_info["product_name"],
            category=base_info["category"],
            sub_category=base_info["sub_category"],
            store_id=store_id,
            store_name=base_info["store_name"],
            on_hand=on_hand,
            days_since_last_sale=days_since_last_sale,
            cost_price=cost,
            retail_price=retail,
            is_perishable=bool(base_info["is_perishable"]),
            shelf_life_days=base_info["shelf_life_days"],
            supplier_id=base_info["supplier_id"],
            supplier_name=base_info["supplier_name"],
            lead_time_days=base_info["lead_time_days"],
            min_order_qty=base_info["min_order_qty"],
            velocity_7d=velocity_7d,
            velocity_14d=velocity_14d,
            velocity_30d=velocity_30d,
            unconstrained_velocity_7d=unconstrained_velocity_7d,
            std_dev_demand=std_dev_demand,
            units_sold_7d=units_7d,
            units_sold_30d=units_30d,
            revenue_7d=round(revenue_7d, 2),
            revenue_30d=round(revenue_30d, 2),
            gross_profit_30d=gross_profit_30d,
            gross_margin_pct=gross_margin_pct,
            stockout_days_30d=stockout_days_30d,
            latest_date=latest_date,
        )

    def get_store_overview(self, store_id: str = "STORE_01", window_days: int = 30) -> Optional[StoreOverview]:
        """
        Aggregate macro store performance metrics across all active SKUs.
        """
        conn = self._get_connection()
        cur = conn.cursor()

        latest_date = self.get_latest_date(conn)

        # Fetch Store Info
        cur.execute("SELECT * FROM stores WHERE store_id = ?;", (store_id,))
        store = cur.fetchone()
        if not store:
            conn.close()
            return None

        # Aggregate 30-day sales and costs
        cur.execute(
            """
            SELECT 
                COUNT(DISTINCT s.sku_id) AS active_skus,
                SUM(s.units_sold) AS total_units,
                SUM(s.gross_revenue) AS total_revenue,
                SUM(s.units_sold * p.cost_price) AS total_cost
            FROM daily_sales s
            JOIN products p ON s.sku_id = p.sku_id
            WHERE s.store_id = ?
              AND s.sale_date >= DATE(?, '-' || ? || ' days')
              AND s.sale_date <= ?;
            """,
            (store_id, latest_date, window_days - 1, latest_date),
        )
        agg = cur.fetchone()

        # Count out-of-stock SKUs on the latest day
        cur.execute(
            """
            SELECT COUNT(*) AS oos_count
            FROM inventory_snapshots
            WHERE store_id = ? AND snapshot_date = ? AND on_hand_units = 0;
            """,
            (store_id, latest_date),
        )
        oos_row = cur.fetchone()
        conn.close()

        total_rev = round(agg["total_revenue"] or 0.0, 2)
        total_cost = round(agg["total_cost"] or 0.0, 2)
        total_profit = round(total_rev - total_cost, 2)
        margin_pct = round((total_profit / max(0.01, total_rev)) * 100, 1)
        total_units = int(agg["total_units"] or 0)
        active_skus = int(agg["active_skus"] or 0)
        oos_count = int(oos_row["oos_count"] or 0)
        avg_daily_rev = round(total_rev / max(1, window_days), 2)

        return StoreOverview(
            store_id=store_id,
            store_name=store["name"],
            city=store["city"],
            store_type=store["store_type"],
            sq_ft=store["sq_ft"],
            manager_name=store["manager_name"],
            window_days=window_days,
            total_revenue=total_rev,
            total_cost=total_cost,
            total_gross_profit=total_profit,
            gross_margin_pct=margin_pct,
            total_units_sold=total_units,
            active_skus_count=active_skus,
            out_of_stock_skus_count=oos_count,
            avg_daily_revenue=avg_daily_rev,
            latest_date=latest_date,
        )

    def compare_skus(self, sku_ids: List[str], store_id: str = "STORE_01") -> List[SkuMetrics]:
        """
        Compare performance of multiple SKUs side-by-side at a given store.
        """
        results = []
        for sku_id in sku_ids:
            metrics = self.get_sku_metrics(sku_id, store_id)
            if metrics:
                results.append(metrics)
        return results

    def get_category_summary(self, category: str, store_id: str = "STORE_01") -> Optional[CategorySummary]:
        """
        Aggregate category performance and identify the top revenue contributor.
        """
        conn = self._get_connection()
        cur = conn.cursor()

        latest_date = self.get_latest_date(conn)

        cur.execute(
            """
            SELECT 
                COUNT(DISTINCT p.sku_id) AS sku_count,
                COALESCE(SUM(s.units_sold), 0) AS total_units,
                COALESCE(SUM(s.gross_revenue), 0) AS total_revenue,
                COALESCE(SUM(s.units_sold * p.cost_price), 0) AS total_cost
            FROM products p
            LEFT JOIN daily_sales s ON p.sku_id = s.sku_id AND s.store_id = ?
              AND s.sale_date >= DATE(?, '-29 days') AND s.sale_date <= ?
            WHERE p.category = ?;
            """,
            (store_id, latest_date, latest_date, category),
        )
        agg = cur.fetchone()
        if not agg or agg["sku_count"] == 0:
            conn.close()
            return None

        # Find top SKU by revenue in this category
        cur.execute(
            """
            SELECT p.sku_id, p.product_name, COALESCE(SUM(s.gross_revenue), 0) AS sku_rev
            FROM products p
            LEFT JOIN daily_sales s ON p.sku_id = s.sku_id AND s.store_id = ?
              AND s.sale_date >= DATE(?, '-29 days') AND s.sale_date <= ?
            WHERE p.category = ?
            GROUP BY p.sku_id
            ORDER BY sku_rev DESC
            LIMIT 1;
            """,
            (store_id, latest_date, latest_date, category),
        )
        top = cur.fetchone()
        conn.close()

        total_rev = round(agg["total_revenue"] or 0.0, 2)
        total_cost = round(agg["total_cost"] or 0.0, 2)
        gross_profit = round(total_rev - total_cost, 2)
        margin_pct = round((gross_profit / max(0.01, total_rev)) * 100, 1)

        return CategorySummary(
            category=category,
            store_id=store_id,
            sku_count=int(agg["sku_count"]),
            total_units_sold_30d=int(agg["total_units"]),
            total_revenue_30d=total_rev,
            total_gross_profit_30d=gross_profit,
            avg_gross_margin_pct=margin_pct,
            top_sku_id=top["sku_id"] if top else "",
            top_sku_name=top["product_name"] if top else "",
            top_sku_revenue=round(top["sku_rev"] if top else 0.0, 2),
        )

    def search_skus(self, query: str, store_id: str = "STORE_01", limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for SKUs by ID, name, category, or subcategory.
        """
        conn = self._get_connection()
        cur = conn.cursor()
        latest_date = self.get_latest_date(conn)

        search_param = f"%{query.strip()}%"
        cur.execute(
            """
            SELECT 
                p.sku_id, p.product_name, p.category, p.sub_category,
                p.retail_price, p.cost_price, p.is_perishable,
                COALESCE(i.on_hand_units, 0) AS on_hand
            FROM products p
            LEFT JOIN inventory_snapshots i ON p.sku_id = i.sku_id 
              AND i.store_id = ? AND i.snapshot_date = ?
            WHERE p.sku_id LIKE ? 
               OR p.product_name LIKE ? 
               OR p.category LIKE ? 
               OR p.sub_category LIKE ?
            LIMIT ?;
            """,
            (store_id, latest_date, search_param, search_param, search_param, search_param, limit),
        )
        rows = cur.fetchall()
        conn.close()

        return [dict(r) for r in rows]

    def get_all_stores(self) -> List[Dict[str, Any]]:
        """Return list of all registered stores in the retail network."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM stores ORDER BY store_id;")
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
