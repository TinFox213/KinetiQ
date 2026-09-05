"""
KinetiQ Interactive What-If Simulation Sandbox
Deterministically models price discounts, price elasticity, promotional lifts,
and inventory runway impacts for store managers.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Optional, Any
from src.analytics.kernel import AnalyticsKernel, SkuMetrics


CATEGORY_PRICE_ELASTICITY = {
    "Pantry": -1.4,
    "Bakery": -1.8,
    "Dairy & Eggs": -1.5,
    "Snacks": -2.0,
    "Beverages": -2.2,
}


@dataclass
class SimulationResult:
    sku_id: str
    product_name: str
    category: str
    store_id: str
    on_hand: int
    base_retail_price: float
    discounted_price: float
    discount_percent: float
    cost_price: float
    price_elasticity: float
    base_velocity: float
    projected_velocity: float
    velocity_lift_percent: float
    base_clearance_days: float
    projected_clearance_days: float
    simulation_duration_days: int
    base_units_sold: int
    projected_units_sold: int
    base_revenue: float
    projected_revenue: float
    base_gross_profit: float
    projected_gross_profit: float
    gross_profit_delta: float
    revenue_delta: float
    inventory_exhaustion_risk: str
    assumptions: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def simulate_intervention(
    sku_id: str,
    store_id: str = "STORE_01",
    discount_percent: float = 15.0,
    duration_days: int = 14,
    kernel: Optional[AnalyticsKernel] = None,
) -> Optional[SimulationResult]:
    """
    Execute a deterministic price elasticity simulation for a given SKU and discount percentage.
    """
    k = kernel or AnalyticsKernel("data/retail_inventory.db")
    metrics = k.get_sku_metrics(sku_id, store_id)
    if not metrics:
        return None

    # 1. Price Elasticity Parameter
    elasticity = CATEGORY_PRICE_ELASTICITY.get(metrics.category, -1.6)

    # 2. Price and Demand Lift
    disc_pct = max(0.0, min(80.0, discount_percent))
    p0 = metrics.retail_price
    cost = metrics.cost_price
    new_price = round(p0 * (1.0 - (disc_pct / 100.0)), 2)

    v0 = metrics.velocity_7d
    delta_p_ratio = disc_pct / 100.0

    # Demand lift % = |Elasticity| * Delta P %
    demand_lift_pct = round(abs(elasticity) * delta_p_ratio * 100, 1)

    if v0 > 0:
        new_v = round(v0 * (1.0 + (demand_lift_pct / 100.0)), 2)
        base_days_to_clear = round(metrics.on_hand / v0, 1)
    else:
        # Non-moving dead stock: awakening factor based on discount depth
        awakened_rate = max(0.2, round(0.5 * (1.0 + (disc_pct / 25.0)), 2))
        new_v = awakened_rate
        base_days_to_clear = 999.0

    new_days_to_clear = round(metrics.on_hand / max(0.01, new_v), 1)

    # 3. Volume and Financial Projections over Simulation Duration
    on_hand = metrics.on_hand
    base_units = min(on_hand, int(round(v0 * duration_days)))
    new_units = min(on_hand, int(round(new_v * duration_days)))

    base_rev = round(base_units * p0, 2)
    new_rev = round(new_units * new_price, 2)

    base_profit = round(base_units * (p0 - cost), 2)
    new_profit = round(new_units * (new_price - cost), 2)

    profit_delta = round(new_profit - base_profit, 2)
    rev_delta = round(new_rev - base_rev, 2)

    # 4. Supply Chain Exhaustion Risk
    if new_days_to_clear <= metrics.lead_time_days:
        exhaustion_risk = (
            f"HIGH RISK: Stockout in {new_days_to_clear} days, faster than supplier lead time "
            f"of {metrics.lead_time_days} days. Place an advance replenishment order immediately."
        )
    elif new_days_to_clear <= (metrics.lead_time_days + 3):
        exhaustion_risk = f"MODERATE: Inventory will reach reorder point in {new_days_to_clear} days."
    else:
        exhaustion_risk = f"LOW: Stock runway ({new_days_to_clear} days) comfortably absorbs demand lift."

    return SimulationResult(
        sku_id=sku_id,
        product_name=metrics.product_name,
        category=metrics.category,
        store_id=store_id,
        on_hand=on_hand,
        base_retail_price=p0,
        discounted_price=new_price,
        discount_percent=disc_pct,
        cost_price=cost,
        price_elasticity=elasticity,
        base_velocity=v0,
        projected_velocity=new_v,
        velocity_lift_percent=demand_lift_pct,
        base_clearance_days=base_days_to_clear,
        projected_clearance_days=new_days_to_clear,
        simulation_duration_days=duration_days,
        base_units_sold=base_units,
        projected_units_sold=new_units,
        base_revenue=base_rev,
        projected_revenue=new_rev,
        base_gross_profit=base_profit,
        projected_gross_profit=new_profit,
        gross_profit_delta=profit_delta,
        revenue_delta=rev_delta,
        inventory_exhaustion_risk=exhaustion_risk,
        assumptions={
            "price_elasticity_coefficient": elasticity,
            "demand_lift_formula": f"|E| * (Discount %) = {abs(elasticity)} * {disc_pct}%",
            "supplier_lead_time_days": metrics.lead_time_days,
            "simulation_window_days": duration_days,
        },
    )
