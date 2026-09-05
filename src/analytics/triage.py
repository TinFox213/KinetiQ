"""
KinetiQ Daily 3-Minute Cockpit & Morning Triage Generator
Pre-assembles the 3x3 Daily Action Queue (Stockouts, Dead Stock, Anomalies)
and computes executive scorecard metrics in < 200ms.
"""

import math
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from src.analytics.kernel import AnalyticsKernel
from src.analytics.inventory_physics import get_imminent_stockouts, evaluate_all_stockouts
from src.analytics.anomalies import detect_sales_anomalies, detect_dead_stock, detect_phantom_inventory
from src.analytics.rebalance import ArbitrageEngine


@dataclass
class DailyTriageBriefing:
    date: str
    store_id: str
    store_name: str
    city: str
    store_type: str
    manager_name: str
    health_score: int  # 0 to 100
    total_active_skus: int
    healthy_skus_count: int
    imminent_stockouts_count: int
    dead_capital_skus_count: int
    velocity_anomalies_count: int
    available_transfers_count: int
    potential_revenue_loss_at_risk: float
    total_dead_capital_locked: float
    monthly_holding_cost_drag: float
    top_imminent_stockouts: List[Dict[str, Any]]  # Top 3
    top_dead_stock_items: List[Dict[str, Any]]    # Top 3
    top_velocity_anomalies: List[Dict[str, Any]]  # Top 3
    recommended_transfers: List[Dict[str, Any]]   # Top 2
    phantom_inventory_alerts: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def calculate_store_health_score(
    total_skus: int,
    stockout_count: int,
    dead_stock_count: int,
    anomaly_count: int,
) -> int:
    """
    Compute a composite operational health index (0 - 100).
    Penalties:
      - Stockouts: -2.5 points per critical SKU
      - Dead stock: -1.5 points per stagnant SKU
      - Velocity anomalies: -1.0 points per anomaly
    """
    if total_skus <= 0:
        return 100

    deductions = (stockout_count * 2.5) + (dead_stock_count * 1.5) + (anomaly_count * 1.0)
    score = max(20, min(100, int(100 - deductions)))
    return score


def generate_morning_triage(
    store_id: str = "STORE_01",
    kernel: Optional[AnalyticsKernel] = None,
    arbitrage: Optional[ArbitrageEngine] = None,
) -> DailyTriageBriefing:
    """
    Generate the high-density morning briefing for store managers.
    Executes in < 200ms using optimized analytical kernels.
    """
    k = kernel or AnalyticsKernel("data/retail_inventory.db")
    arb = arbitrage or ArbitrageEngine(k.db_path, k)

    conn = k._get_connection()
    cur = conn.cursor()
    latest_date = k.get_latest_date(conn)

    # 1. Fetch Store Details
    cur.execute("SELECT * FROM stores WHERE store_id = ?;", (store_id,))
    store_row = cur.fetchone()
    conn.close()

    store_name = store_row["name"] if store_row else f"Store {store_id}"
    city = store_row["city"] if store_row else "Metro"
    store_type = store_row["store_type"] if store_row else "Retail"
    manager_name = store_row["manager_name"] if store_row else "Store Manager"

    # 2. Gather Critical Signals
    imminent_stockouts = get_imminent_stockouts(store_id, k, threshold_days=5.0)
    dead_stock_items = detect_dead_stock(store_id, k, idle_days_threshold=30)
    anomalies = detect_sales_anomalies(store_id, k, z_threshold=2.0)
    phantoms = detect_phantom_inventory(store_id, k)
    transfers = arb.find_interstore_transfers(
        store_id,
        candidate_sku_ids=[s.sku_id for s in imminent_stockouts],
    )

    # 3. Aggregate Financial Impact
    potential_revenue_risk = round(sum(s.potential_revenue_loss for s in imminent_stockouts), 2)
    total_dead_capital = round(sum(d.locked_capital for d in dead_stock_items), 2)
    monthly_holding_drag = round(sum(d.monthly_holding_cost_drag for d in dead_stock_items), 2)

    total_skus = 250
    problem_skus = len({s.sku_id for s in imminent_stockouts} | {d.sku_id for d in dead_stock_items})
    healthy_count = max(0, total_skus - problem_skus)

    health_score = calculate_store_health_score(
        total_skus=total_skus,
        stockout_count=len(imminent_stockouts),
        dead_stock_count=len(dead_stock_items),
        anomaly_count=len(anomalies),
    )

    # 4. Extract Top 3 for Attention Queue
    top_stockouts = [s.to_dict() for s in imminent_stockouts[:3]]
    top_dead = [d.to_dict() for d in dead_stock_items[:3]]
    top_anomalies = [a.to_dict() for a in anomalies[:3]]
    rec_transfers = [t.to_dict() for t in transfers[:2]]
    phantom_alerts = [p.to_dict() for p in phantoms[:2]]

    return DailyTriageBriefing(
        date=latest_date,
        store_id=store_id,
        store_name=store_name,
        city=city,
        store_type=store_type,
        manager_name=manager_name,
        health_score=health_score,
        total_active_skus=total_skus,
        healthy_skus_count=healthy_count,
        imminent_stockouts_count=len(imminent_stockouts),
        dead_capital_skus_count=len(dead_stock_items),
        velocity_anomalies_count=len(anomalies),
        available_transfers_count=len(transfers),
        potential_revenue_loss_at_risk=potential_revenue_risk,
        total_dead_capital_locked=total_dead_capital,
        monthly_holding_cost_drag=monthly_holding_drag,
        top_imminent_stockouts=top_stockouts,
        top_dead_stock_items=top_dead,
        top_velocity_anomalies=top_anomalies,
        recommended_transfers=rec_transfers,
        phantom_inventory_alerts=phantom_alerts,
    )
