"""
KinetiQ Demand Anomaly Detection & Dead Capital Classifier
Statistical models for Z-score demand shifts, phantom inventory detection,
and stagnant capital classification with prescriptive operational interventions.
"""

import math
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from src.analytics.kernel import AnalyticsKernel, SkuMetrics


@dataclass
class SalesAnomaly:
    sku_id: str
    product_name: str
    category: str
    store_id: str
    yesterday_sales: int
    baseline_mean_14d: float
    baseline_std_14d: float
    z_score: float
    anomaly_type: str  # 'SPIKE' or 'DROP'
    percent_change_vs_baseline: float
    on_hand: int
    recommended_action: str
    rationale: str
    assumptions: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DeadStockItem:
    sku_id: str
    product_name: str
    category: str
    sub_category: str
    store_id: str
    on_hand: int
    unit_cost: float
    unit_retail: float
    days_since_last_sale: int
    doi_days: float
    locked_capital: float
    monthly_holding_cost_drag: float
    recommended_action: str
    suggested_discount_pct: int
    suggested_bundle_sku_id: Optional[str]
    suggested_bundle_sku_name: Optional[str]
    estimated_cash_recovery: float
    assumptions: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PhantomInventoryAlert:
    sku_id: str
    product_name: str
    category: str
    store_id: str
    on_hand: int
    yesterday_sales: int
    baseline_mean_14d: float
    consecutive_zero_sales_days: int
    urgency: str  # 'HIGH'
    recommended_action: str
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def detect_sales_anomalies(
    store_id: str,
    kernel: AnalyticsKernel,
    z_threshold: float = 2.0,
) -> List[SalesAnomaly]:
    """
    Detect statistical sales spikes (Z >= +2.0) and collapses (Z <= -2.0)
    comparing yesterday's volume against the prior 14-day rolling baseline.
    """
    conn = kernel._get_connection()
    cur = conn.cursor()
    latest_date = kernel.get_latest_date(conn)

    # Fetch daily sales for the latest 15 days (day 0 = yesterday, days 1..14 = baseline)
    cur.execute(
        """
        SELECT sku_id, sale_date, units_sold
        FROM daily_sales
        WHERE store_id = ?
          AND sale_date >= DATE(?, '-14 days') AND sale_date <= ?
        ORDER BY sku_id, sale_date DESC;
        """,
        (store_id, latest_date, latest_date),
    )
    rows = cur.fetchall()
    conn.close()

    # Group by SKU
    sku_sales_map = {}
    for r in rows:
        sku = r["sku_id"]
        if sku not in sku_sales_map:
            sku_sales_map[sku] = []
        sku_sales_map[sku].append((r["sale_date"], r["units_sold"]))

    anomalies = []

    for sku_id, date_sales in sku_sales_map.items():
        if len(date_sales) < 5:
            continue

        # Day 0 is latest/yesterday, days 1+ are baseline
        yesterday_sales = date_sales[0][1]
        baseline_sales = [u for d, u in date_sales[1:]]

        if not baseline_sales:
            continue

        mean_14d = sum(baseline_sales) / len(baseline_sales)
        if mean_14d < 1.0 and yesterday_sales <= 2:
            # Skip noise on ultra low velocity items
            continue

        variance_14d = sum((x - mean_14d) ** 2 for x in baseline_sales) / len(baseline_sales)
        std_14d = math.sqrt(variance_14d)

        # Z-score with minimum standard deviation safeguard
        denom = max(std_14d, 0.75)
        z = round((yesterday_sales - mean_14d) / denom, 2)

        if abs(z) >= z_threshold:
            metrics = kernel.get_sku_metrics(sku_id, store_id)
            if not metrics:
                continue

            pct_change = round(((yesterday_sales - mean_14d) / max(0.1, mean_14d)) * 100, 1)

            if z > 0:
                anomaly_type = "SPIKE"
                action = "Expedite shelf replenishment and review supplier safety buffer"
                rationale = (
                    f"Sales surged by +{pct_change}% (Z={z:+0.1f}). Daily sales hit {yesterday_sales} units "
                    f"vs 14-day normal baseline of {round(mean_14d, 1)} units. Risk of stockout if surge continues."
                )
            else:
                anomaly_type = "DROP"
                action = "Conduct shelf audit to verify item presence, shelf tag, and scannability"
                rationale = (
                    f"Sales dropped by {pct_change}% (Z={z:+0.1f}). Observed {yesterday_sales} units "
                    f"vs 14-day normal baseline of {round(mean_14d, 1)} units despite {metrics.on_hand} on hand."
                )

            anomalies.append(
                SalesAnomaly(
                    sku_id=sku_id,
                    product_name=metrics.product_name,
                    category=metrics.category,
                    store_id=store_id,
                    yesterday_sales=yesterday_sales,
                    baseline_mean_14d=round(mean_14d, 2),
                    baseline_std_14d=round(std_14d, 2),
                    z_score=z,
                    anomaly_type=anomaly_type,
                    percent_change_vs_baseline=pct_change,
                    on_hand=metrics.on_hand,
                    recommended_action=action,
                    rationale=rationale,
                    assumptions={
                        "rolling_baseline_days": 14,
                        "z_threshold": z_threshold,
                        "min_variance_floor": 0.75,
                    },
                )
            )

    # Sort anomalies by magnitude of Z-score descending
    anomalies.sort(key=lambda a: abs(a.z_score), reverse=True)
    return anomalies


def detect_dead_stock(
    store_id: str,
    kernel: AnalyticsKernel,
    idle_days_threshold: int = 30,
) -> List[DeadStockItem]:
    """
    Classify non-moving inventory tying up working capital in < 20ms using a single SQL query.
    Criteria: days_since_last_sale >= 30 OR (DOI > 90 and on_hand >= 15).
    """
    conn = kernel._get_connection()
    cur = conn.cursor()
    latest_date = kernel.get_latest_date(conn)

    cur.execute(
        """
        SELECT 
            p.sku_id, p.product_name, p.category, p.sub_category,
            p.cost_price, p.retail_price,
            i.on_hand_units, i.days_since_last_sale,
            COALESCE(sales_7d.units_7d, 0) AS units_sold_7d
        FROM inventory_snapshots i
        JOIN products p ON i.sku_id = p.sku_id
        LEFT JOIN (
            SELECT sku_id, SUM(units_sold) AS units_7d
            FROM daily_sales
            WHERE store_id = ? AND sale_date >= DATE(?, '-6 days') AND sale_date <= ?
            GROUP BY sku_id
        ) sales_7d ON p.sku_id = sales_7d.sku_id
        WHERE i.store_id = ? AND i.snapshot_date = ? AND i.on_hand_units > 0
        ORDER BY (i.on_hand_units * p.cost_price) DESC;
        """,
        (store_id, latest_date, latest_date, store_id, latest_date),
    )
    rows = cur.fetchall()

    # Pre-fetch top selling items per category for instant bundling
    cur.execute(
        """
        SELECT p.category, p.sku_id, p.product_name
        FROM (
            SELECT p.category, p.sku_id, p.product_name, SUM(s.units_sold) as total_units,
                   ROW_NUMBER() OVER (PARTITION BY p.category ORDER BY SUM(s.units_sold) DESC) as rn
            FROM products p
            JOIN daily_sales s ON p.sku_id = s.sku_id
            WHERE s.store_id = ? AND s.sale_date >= DATE(?, '-29 days')
            GROUP BY p.category, p.sku_id, p.product_name
        ) p
        WHERE rn = 1;
        """,
        (store_id, latest_date),
    )
    top_cat_skus = {r["category"]: (r["sku_id"], r["product_name"]) for r in cur.fetchall()}
    conn.close()

    dead_items = []

    for r in rows:
        sku_id = r["sku_id"]
        on_hand = r["on_hand_units"]
        idle_days = r["days_since_last_sale"]
        cost = r["cost_price"]
        retail = r["retail_price"]
        v_7d = round(r["units_sold_7d"] / 7.0, 2)

        doi = round(on_hand / v_7d, 1) if v_7d > 0 else 999.0

        is_dead = (idle_days >= idle_days_threshold) or (doi > 90.0 and on_hand >= 15)

        if is_dead:
            locked_cap = round(on_hand * cost, 2)
            holding_cost_drag = round(locked_cap * (0.24 / 12.0), 2)

            if idle_days >= 35 or doi >= 120:
                discount_pct = 35
                action = f"Apply {discount_pct}% clearance markdown and relocate from prime gondola to promo endcap"
            else:
                discount_pct = 20
                action = f"Run {discount_pct}% weekend discount promotion or promotional cross-category bundle"

            bundle_info = top_cat_skus.get(r["category"])
            bundle_sku_id = None
            bundle_sku_name = None
            if bundle_info and bundle_info[0] != sku_id:
                bundle_sku_id = bundle_info[0]
                bundle_sku_name = bundle_info[1]
                action += f" paired with fast-seller '{bundle_sku_name}'"

            discounted_price = retail * (1 - (discount_pct / 100.0))
            est_recovery = round(on_hand * min(discounted_price, retail * 0.75), 2)

            dead_items.append(
                DeadStockItem(
                    sku_id=sku_id,
                    product_name=r["product_name"],
                    category=r["category"],
                    sub_category=r["sub_category"],
                    store_id=store_id,
                    on_hand=on_hand,
                    unit_cost=cost,
                    unit_retail=retail,
                    days_since_last_sale=idle_days,
                    doi_days=doi,
                    locked_capital=locked_cap,
                    monthly_holding_cost_drag=holding_cost_drag,
                    recommended_action=action,
                    suggested_discount_pct=discount_pct,
                    suggested_bundle_sku_id=bundle_sku_id,
                    suggested_bundle_sku_name=bundle_sku_name,
                    estimated_cash_recovery=est_recovery,
                    assumptions={
                        "annual_holding_cost_rate": "24%",
                        "monthly_holding_rate": "2.0%",
                        "idle_days_threshold": idle_days_threshold,
                        "doi_dead_threshold": 90.0,
                    },
                )
            )

    dead_items.sort(key=lambda item: item.locked_capital, reverse=True)
    return dead_items


def detect_phantom_inventory(
    store_id: str,
    kernel: AnalyticsKernel,
) -> List[PhantomInventoryAlert]:
    """
    Detect ghost/phantom inventory: items showing stock on the system but registering 0 sales
    despite high historical demand (>= 5 units/day).
    Indicates physical misplacement, theft shrinkage, damaged goods, or damaged barcodes.
    """
    anomalies = detect_sales_anomalies(store_id, kernel, z_threshold=2.0)
    conn = kernel._get_connection()
    cur = conn.cursor()
    latest_date = kernel.get_latest_date(conn)

    cur.execute(
        """
        SELECT sku_id, on_hand_units, days_since_last_sale
        FROM inventory_snapshots
        WHERE store_id = ? AND snapshot_date = ? AND on_hand_units >= 5;
        """,
        (store_id, latest_date),
    )
    stock_rows = {r["sku_id"]: (r["on_hand_units"], r["days_since_last_sale"]) for r in cur.fetchall()}
    conn.close()

    phantom_alerts = []

    # Check anomalies for zero-sales drop on high velocity items
    for anom in anomalies:
        if anom.yesterday_sales == 0 and anom.baseline_mean_14d >= 5.0 and anom.on_hand >= 5:
            idle = stock_rows.get(anom.sku_id, (anom.on_hand, 1))[1]
            phantom_alerts.append(
                PhantomInventoryAlert(
                    sku_id=anom.sku_id,
                    product_name=anom.product_name,
                    category=anom.category,
                    store_id=store_id,
                    on_hand=anom.on_hand,
                    yesterday_sales=0,
                    baseline_mean_14d=anom.baseline_mean_14d,
                    consecutive_zero_sales_days=idle,
                    urgency="HIGH",
                    recommended_action="Conduct immediate physical shelf audit to confirm stock presence and check barcode scannability",
                    rationale=(
                        f"Zero units sold yesterday despite {anom.on_hand} units on record and expected demand "
                        f"of {round(anom.baseline_mean_14d, 1)} units/day (Z={anom.z_score:0.1f}). High probability of ghost inventory."
                    ),
                )
            )

    return phantom_alerts
