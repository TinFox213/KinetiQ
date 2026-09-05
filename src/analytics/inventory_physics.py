"""
KinetiQ Inventory Physics Engine
Deterministic supply chain models for Days of Inventory (DOI), Safety Stock (SS),
Reorder Points (ROP), Stockout Date Projections, and Recommended Order Quantities.
"""

import math
from dataclasses import dataclass, asdict
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from src.analytics.kernel import AnalyticsKernel, SkuMetrics


@dataclass
class StockoutAlert:
    sku_id: str
    product_name: str
    category: str
    store_id: str
    store_name: str
    on_hand: int
    velocity_7d: float
    unconstrained_velocity_7d: float
    doi_days: float
    lead_time_days: int
    min_order_qty: int
    projected_stockout_date: str
    urgency_level: str  # 'CRITICAL', 'WARNING', 'HEALTHY'
    deficit_units: int
    recommended_order_qty: int
    unit_cost: float
    unit_retail: float
    potential_revenue_loss: float
    assumptions: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def calculate_doi(on_hand: int, velocity: float) -> float:
    """
    Calculate Days of Inventory (Runway) until stock is exhausted.
    Strict edge-case handling:
      - on_hand <= 0 -> 0.0
      - velocity <= 0 and on_hand > 0 -> 999.0 (indefinite runway / dead stock)
    """
    if on_hand <= 0:
        return 0.0
    if velocity <= 0.0:
        return 999.0
    return round(on_hand / velocity, 1)


def calculate_safety_stock(
    lead_time_days: int,
    std_dev_demand: float,
    service_level_z: float = 1.645,
) -> float:
    """
    Calculate Safety Stock buffer: SS = Z * sigma_demand * sqrt(L).
    Default Z = 1.645 corresponds to a 95% cycle service level.
    """
    if lead_time_days <= 0 or std_dev_demand <= 0:
        return 0.0
    return round(service_level_z * std_dev_demand * math.sqrt(lead_time_days), 1)


def calculate_rop(velocity: float, lead_time_days: int, safety_stock: float) -> float:
    """
    Calculate Reorder Point: ROP = (Velocity * Lead_Time) + Safety_Stock.
    """
    lead_time_demand = max(0.0, velocity) * max(0, lead_time_days)
    return round(lead_time_demand + safety_stock, 1)


def evaluate_stockout(
    metrics: SkuMetrics,
    review_period_days: int = 7,
    service_level: float = 0.95,
) -> StockoutAlert:
    """
    Evaluate inventory physics for a single SKU and generate a deterministic StockoutAlert
    with a fully transparent assumption ledger.
    """
    # Service level Z-score mapping
    z_map = {0.90: 1.282, 0.95: 1.645, 0.98: 2.054, 0.99: 2.326}
    z_val = z_map.get(service_level, 1.645)

    effective_velocity = (
        metrics.unconstrained_velocity_7d
        if metrics.unconstrained_velocity_7d > 0
        else metrics.velocity_7d
    )

    doi = calculate_doi(metrics.on_hand, effective_velocity)
    lead_time = metrics.lead_time_days

    safety_stock = calculate_safety_stock(
        lead_time_days=lead_time,
        std_dev_demand=metrics.std_dev_demand,
        service_level_z=z_val,
    )
    rop = calculate_rop(effective_velocity, lead_time, safety_stock)

    # Determine Urgency Level
    # CRITICAL: DOI <= lead time (stockout is inevitable before supplier delivery) or on_hand == 0
    # WARNING: on_hand <= ROP (time to order now to maintain safety buffer)
    # HEALTHY: on_hand > ROP
    if metrics.on_hand == 0:
        urgency = "CRITICAL"
    elif doi <= lead_time:
        urgency = "CRITICAL"
    elif metrics.on_hand <= rop or doi <= (lead_time + 3.0):
        urgency = "WARNING"
    else:
        urgency = "HEALTHY"

    # Stockout Date Projection
    try:
        base_date = date.fromisoformat(metrics.latest_date)
    except (ValueError, TypeError):
        base_date = date.today()

    if metrics.on_hand == 0:
        projected_date_str = "Already Out of Stock"
    elif doi >= 999.0:
        projected_date_str = "No Stockout Projected (Zero Velocity)"
    else:
        proj_date = base_date + timedelta(days=doi)
        projected_date_str = proj_date.isoformat()

    # Shortfall / Deficit calculation before delivery
    if doi < lead_time and effective_velocity > 0:
        deficit = int(math.ceil((lead_time - doi) * effective_velocity))
    else:
        deficit = 0

    # Recommended Order Quantity (Target Par Level logic)
    # Par Level = Velocity * (Lead_Time + Review_Period) + Safety_Stock
    par_level = (effective_velocity * (lead_time + review_period_days)) + safety_stock
    needed_qty = int(math.ceil(max(0.0, par_level - metrics.on_hand)))
    if urgency in ("CRITICAL", "WARNING") and needed_qty > 0:
        recommended_order_qty = max(metrics.min_order_qty, needed_qty)
    elif needed_qty > 0 and metrics.on_hand <= rop:
        recommended_order_qty = max(metrics.min_order_qty, needed_qty)
    else:
        recommended_order_qty = 0

    # Potential revenue loss if deficit is not addressed
    potential_revenue_loss = round(deficit * metrics.retail_price, 2)

    assumptions = {
        "lead_time_days": lead_time,
        "velocity_basis": "7-day unconstrained average",
        "service_level_target": f"{int(service_level * 100)}%",
        "service_level_z": z_val,
        "demand_std_dev": metrics.std_dev_demand,
        "safety_stock_buffer_units": safety_stock,
        "reorder_point_units": rop,
        "target_par_level_units": round(par_level, 1),
        "review_period_days": review_period_days,
        "min_order_qty": metrics.min_order_qty,
    }

    return StockoutAlert(
        sku_id=metrics.sku_id,
        product_name=metrics.product_name,
        category=metrics.category,
        store_id=metrics.store_id,
        store_name=metrics.store_name,
        on_hand=metrics.on_hand,
        velocity_7d=metrics.velocity_7d,
        unconstrained_velocity_7d=effective_velocity,
        doi_days=doi,
        lead_time_days=lead_time,
        min_order_qty=metrics.min_order_qty,
        projected_stockout_date=projected_date_str,
        urgency_level=urgency,
        deficit_units=deficit,
        recommended_order_qty=recommended_order_qty,
        unit_cost=metrics.cost_price,
        unit_retail=metrics.retail_price,
        potential_revenue_loss=potential_revenue_loss,
        assumptions=assumptions,
    )


def evaluate_all_stockouts(
    store_id: str,
    kernel: AnalyticsKernel,
    urgency_filter: Optional[List[str]] = None,
) -> List[StockoutAlert]:
    """
    Scan all SKUs in a store and return stockout alerts, sorted by urgency and shortest DOI.
    """
    conn = kernel._get_connection()
    cur = conn.cursor()
    cur.execute("SELECT sku_id FROM products ORDER BY sku_id;")
    sku_rows = cur.fetchall()
    conn.close()

    alerts = []
    for row in sku_rows:
        sku_id = row["sku_id"]
        metrics = kernel.get_sku_metrics(sku_id, store_id)
        if not metrics:
            continue
        alert = evaluate_stockout(metrics)
        if urgency_filter is None or alert.urgency_level in urgency_filter:
            alerts.append(alert)

    # Sort by urgency: CRITICAL first, then WARNING, then by ascending DOI
    urgency_rank = {"CRITICAL": 0, "WARNING": 1, "HEALTHY": 2}
    alerts.sort(key=lambda a: (urgency_rank.get(a.urgency_level, 3), a.doi_days))
    return alerts


def get_imminent_stockouts(
    store_id: str,
    kernel: AnalyticsKernel,
    threshold_days: float = 5.0,
) -> List[StockoutAlert]:
    """
    Get top priority stockout alerts where remaining DOI is less than threshold days.
    Optimized to pre-filter candidate low-stock SKUs in < 50ms.
    """
    conn = kernel._get_connection()
    cur = conn.cursor()
    latest_date = kernel.get_latest_date(conn)

    # Candidate pre-filter: items with on_hand <= 25 or projected DOI <= threshold + 1
    cur.execute(
        """
        SELECT i.sku_id
        FROM inventory_snapshots i
        LEFT JOIN (
            SELECT sku_id, SUM(units_sold) as units_7d
            FROM daily_sales
            WHERE store_id = ? AND sale_date >= DATE(?, '-6 days') AND sale_date <= ?
            GROUP BY sku_id
        ) s ON i.sku_id = s.sku_id
        WHERE i.store_id = ? AND i.snapshot_date = ?
          AND (i.on_hand_units <= 20 OR (i.on_hand_units / MAX(0.1, COALESCE(s.units_7d, 0) / 7.0)) <= ?)
        ORDER BY (i.on_hand_units / MAX(0.1, COALESCE(s.units_7d, 0) / 7.0)) ASC
        LIMIT 20;
        """,
        (store_id, latest_date, latest_date, store_id, latest_date, threshold_days + 1.5),
    )
    candidates = [r["sku_id"] for r in cur.fetchall()]
    conn.close()

    alerts = []
    for sku_id in candidates:
        metrics = kernel.get_sku_metrics(sku_id, store_id)
        if not metrics:
            continue
        alert = evaluate_stockout(metrics)
        if alert.urgency_level in ("CRITICAL", "WARNING") and (alert.doi_days <= threshold_days or alert.on_hand == 0):
            alerts.append(alert)

    urgency_rank = {"CRITICAL": 0, "WARNING": 1, "HEALTHY": 2}
    alerts.sort(key=lambda a: (urgency_rank.get(a.urgency_level, 3), a.doi_days))
    return alerts
