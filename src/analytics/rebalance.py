"""
KinetiQ Multi-Store Inventory Arbitrage Engine
Solves intra-network stock surpluses and deficits across peer stores,
calculates courier transfer economics, and generates Stock Transfer Notes (STNs).
"""

import math
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any
from src.analytics.kernel import AnalyticsKernel, SkuMetrics
from src.analytics.inventory_physics import calculate_doi, calculate_safety_stock, calculate_rop


# Inter-store distance matrix and courier cost estimates (in KM and INR)
STORE_DISTANCE_MATRIX = {
    ("STORE_01", "STORE_02"): {"distance_km": 12.5, "transit_hours": 1.5, "courier_cost": 250.00},
    ("STORE_01", "STORE_03"): {"distance_km": 8.2, "transit_hours": 1.0, "courier_cost": 180.00},
    ("STORE_02", "STORE_01"): {"distance_km": 12.5, "transit_hours": 1.5, "courier_cost": 250.00},
    ("STORE_02", "STORE_03"): {"distance_km": 18.0, "transit_hours": 2.0, "courier_cost": 320.00},
    ("STORE_03", "STORE_01"): {"distance_km": 8.2, "transit_hours": 1.0, "courier_cost": 180.00},
    ("STORE_03", "STORE_02"): {"distance_km": 18.0, "transit_hours": 2.0, "courier_cost": 320.00},
}


@dataclass
class TransferManifest:
    manifest_id: str
    sku_id: str
    product_name: str
    category: str
    from_store_id: str
    from_store_name: str
    to_store_id: str
    to_store_name: str
    quantity: int
    revenue_protected: float
    gross_profit_protected: float
    estimated_transit_hours: float
    estimated_courier_cost: float
    net_savings: float
    source_remaining_runway_days: float
    destination_runway_after_days: float
    status: str  # 'RECOMMENDED', 'PENDING', 'COMPLETED'
    created_at: str
    assumptions: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ArbitrageEngine:
    """
    Evaluates multi-store rebalancing opportunities to satisfy stockout deficits
    using excess idle inventory from nearby network stores instead of placing supplier reorders.
    """

    def __init__(self, db_path: str = "data/retail_inventory.db", kernel: Optional[AnalyticsKernel] = None):
        self.db_path = db_path
        self.kernel = kernel or AnalyticsKernel(db_path)

    def evaluate_transfer_for_sku(
        self,
        sku_id: str,
        to_store_id: str,
    ) -> Optional[TransferManifest]:
        """
        Evaluate if any peer store can supply SKU to target store without compromising its own health.
        """
        dest_metrics = self.kernel.get_sku_metrics(sku_id, to_store_id)
        if not dest_metrics:
            return None

        lead_time = dest_metrics.lead_time_days
        dest_velocity = (
            dest_metrics.unconstrained_velocity_7d
            if dest_metrics.unconstrained_velocity_7d > 0
            else dest_metrics.velocity_7d
        )

        dest_doi = calculate_doi(dest_metrics.on_hand, dest_velocity)

        # Only search for arbitrage if destination is in deficit or imminent stockout (DOI <= Lead Time + 2)
        if dest_doi > (lead_time + 2.0) and dest_metrics.on_hand > 10:
            return None

        # Deficit calculation: Target Par Level - On Hand
        dest_safety = calculate_safety_stock(lead_time, dest_metrics.std_dev_demand)
        target_par = (dest_velocity * (lead_time + 7)) + dest_safety
        deficit = int(math.ceil(max(0.0, target_par - dest_metrics.on_hand)))
        if deficit <= 0:
            return None

        all_stores = self.kernel.get_all_stores()
        peer_stores = [s for s in all_stores if s["store_id"] != to_store_id]

        candidates = []

        for peer in peer_stores:
            peer_id = peer["store_id"]
            peer_metrics = self.kernel.get_sku_metrics(sku_id, peer_id)
            if not peer_metrics or peer_metrics.on_hand <= 0:
                continue

            peer_velocity = (
                peer_metrics.unconstrained_velocity_7d
                if peer_metrics.unconstrained_velocity_7d > 0
                else peer_metrics.velocity_7d
            )

            peer_safety = calculate_safety_stock(lead_time, peer_metrics.std_dev_demand)

            # Minimum safe reserve: keep enough stock for Lead Time + 14 days + Safety Stock
            min_reserve = int(math.ceil((peer_velocity * (lead_time + 14)) + peer_safety))
            surplus = max(0, peer_metrics.on_hand - min_reserve)

            if surplus > 0:
                transit_info = STORE_DISTANCE_MATRIX.get(
                    (peer_id, to_store_id),
                    {"distance_km": 15.0, "transit_hours": 2.0, "courier_cost": 10.00},
                )
                candidates.append({
                    "store_id": peer_id,
                    "store_name": peer["name"],
                    "peer_metrics": peer_metrics,
                    "surplus": surplus,
                    "peer_velocity": peer_velocity,
                    "transit_info": transit_info,
                })

        if not candidates:
            return None

        # Sort candidates by surplus descending, then courier cost ascending
        candidates.sort(key=lambda c: (-c["surplus"], c["transit_info"]["courier_cost"]))
        best_source = candidates[0]

        transfer_qty = min(deficit, best_source["surplus"])
        if transfer_qty <= 0:
            return None

        # Financial justification
        retail = dest_metrics.retail_price
        cost = dest_metrics.cost_price
        courier_cost = best_source["transit_info"]["courier_cost"]

        revenue_protected = round(transfer_qty * retail, 2)
        gross_profit_protected = round(transfer_qty * (retail - cost), 2)
        net_savings = round(gross_profit_protected - courier_cost, 2)

        # Post-transfer runways
        src_on_hand_after = best_source["peer_metrics"].on_hand - transfer_qty
        src_runway_after = calculate_doi(src_on_hand_after, best_source["peer_velocity"])

        dest_on_hand_after = dest_metrics.on_hand + transfer_qty
        dest_runway_after = calculate_doi(dest_on_hand_after, dest_velocity)

        manifest_id = f"STN_{uuid.uuid4().hex[:8].upper()}"

        return TransferManifest(
            manifest_id=manifest_id,
            sku_id=sku_id,
            product_name=dest_metrics.product_name,
            category=dest_metrics.category,
            from_store_id=best_source["store_id"],
            from_store_name=best_source["store_name"],
            to_store_id=to_store_id,
            to_store_name=dest_metrics.store_name,
            quantity=transfer_qty,
            revenue_protected=revenue_protected,
            gross_profit_protected=gross_profit_protected,
            estimated_transit_hours=best_source["transit_info"]["transit_hours"],
            estimated_courier_cost=courier_cost,
            net_savings=net_savings,
            source_remaining_runway_days=src_runway_after,
            destination_runway_after_days=dest_runway_after,
            status="RECOMMENDED",
            created_at=datetime.utcnow().isoformat(),
            assumptions={
                "courier_cost_usd": courier_cost,
                "courier_cost_inr": courier_cost,
                "transit_time_hours": best_source["transit_info"]["transit_hours"],
                "gross_margin_per_unit": round(retail - cost, 2),
                "source_min_reserve_kept": best_source["peer_metrics"].on_hand - best_source["surplus"],
                "alternative_supplier_lead_time_days": lead_time,
            },
        )

    def find_interstore_transfers(
        self,
        store_id: str,
        candidate_sku_ids: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[TransferManifest]:
        """
        Scan SKUs facing stockouts or low inventory at the given store
        and find peer rebalancing opportunities across the network.
        """
        if candidate_sku_ids:
            sku_list = candidate_sku_ids[:limit]
        else:
            conn = self.kernel._get_connection()
            cur = conn.cursor()
            latest_date = self.kernel.get_latest_date(conn)

            # Find SKUs with lowest on hand stock
            cur.execute(
                """
                SELECT p.sku_id
                FROM products p
                JOIN inventory_snapshots i ON p.sku_id = i.sku_id
                WHERE i.store_id = ? AND i.snapshot_date = ? AND i.on_hand_units <= 20
                ORDER BY i.on_hand_units ASC
                LIMIT ?;
                """,
                (store_id, latest_date, limit),
            )
            rows = cur.fetchall()
            conn.close()
            sku_list = [r["sku_id"] for r in rows]

        transfers = []
        for sku_id in sku_list:
            manifest = self.evaluate_transfer_for_sku(sku_id, store_id)
            if manifest and manifest.net_savings > 0:
                transfers.append(manifest)

        # Sort by net savings descending
        transfers.sort(key=lambda t: t.net_savings, reverse=True)
        return transfers

    def commit_transfer(
        self,
        manifest_id: str,
        from_store_id: str,
        to_store_id: str,
        sku_id: str,
        quantity: int,
    ) -> bool:
        """
        Record and commit a stock transfer note to the database.
        """
        conn = self.kernel._get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT OR REPLACE INTO store_transfers (transfer_id, created_at, from_store_id, to_store_id, sku_id, units, status)
            VALUES (?, CURRENT_TIMESTAMP, ?, ?, ?, ?, 'PENDING');
            """,
            (manifest_id, from_store_id, to_store_id, sku_id, quantity),
        )
        conn.commit()
        conn.close()
        return True
