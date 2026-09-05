"""
KinetiQ Neuro-Symbolic Copilot Agent
Integrates Google Gemini 2.5 Flash SDK, deterministic tool execution,
strict numerical grounding, and fallback templating.
"""

import os
import re
import json
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple

from src.analytics.kernel import AnalyticsKernel, SkuMetrics
from src.analytics.inventory_physics import get_imminent_stockouts, evaluate_all_stockouts
from src.analytics.anomalies import detect_sales_anomalies, detect_dead_stock, detect_phantom_inventory
from src.analytics.rebalance import ArbitrageEngine
from src.agent.epistemic import check_epistemic_boundary


SYSTEM_PROMPT = """You are KinetiQ, an expert Neuro-Symbolic Retail Sales and Inventory Copilot for store managers.
Your mission is to help store managers make rapid, high-impact operational decisions backed by exact mathematical truth.

STRICT OPERATIONAL RULES:
1. ZERO ARITHMETIC RULE: Never perform manual calculations, multiplication, or projections. Every unit count, velocity, runway day, dollar value, and margin percentage MUST be cited directly from the verified tool output provided.
2. CITATION MANDATE: Always quote exact figures and store IDs (e.g., "Store 1 holds 14 units on hand with an unconstrained velocity of 5.6 units/day, giving 2.5 days of inventory against a 4-day supplier lead time").
3. ACTIONABLE STRUCTURE: Format your answer clearly using bold numbers, structured bullet points, and an explicit "Recommended Action" header.
4. HONESTY: If a SKU or data point is not in the system, explicitly state that it was not found. Never extrapolate or assume.
"""


@dataclass
class CopilotResponse:
    query: str
    response: str
    source: str  # 'gemini-2.5-flash' or 'deterministic-fallback'
    tools_executed: List[str]
    grounded_facts: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CopilotAgent:
    """
    Neuro-Symbolic Agent orchestrating Gemini LLM reasoning with deterministic analytical tools.
    """

    def __init__(
        self,
        kernel: AnalyticsKernel,
        rebalance_engine: Optional[ArbitrageEngine] = None,
        api_key: Optional[str] = None,
    ):
        self.kernel = kernel
        self.rebalance = rebalance_engine or ArbitrageEngine(kernel.db_path, kernel)
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.client = None
        self.model_name = "gemini-2.5-flash"

        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"[WARN] Failed to initialize Gemini client: {e}. Using deterministic fallback.")
                self.client = None

    def execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a deterministic Python analytical tool."""
        store_id = params.get("store_id", "STORE_01")

        if tool_name == "get_imminent_stockouts":
            threshold = params.get("threshold_days", 5.0)
            alerts = get_imminent_stockouts(store_id, self.kernel, threshold_days=threshold)
            return {"count": len(alerts), "stockouts": [a.to_dict() for a in alerts[:5]]}

        elif tool_name == "get_dead_stock":
            items = detect_dead_stock(store_id, self.kernel)
            return {"count": len(items), "dead_stock": [i.to_dict() for i in items[:5]]}

        elif tool_name == "get_sales_anomalies":
            anomalies = detect_sales_anomalies(store_id, self.kernel)
            return {"count": len(anomalies), "anomalies": [a.to_dict() for a in anomalies[:5]]}

        elif tool_name == "get_phantom_inventory":
            phantoms = detect_phantom_inventory(store_id, self.kernel)
            return {"count": len(phantoms), "phantoms": [p.to_dict() for p in phantoms[:5]]}

        elif tool_name == "check_interstore_transfers":
            transfers = self.rebalance.find_interstore_transfers(store_id)
            return {"count": len(transfers), "transfers": [t.to_dict() for t in transfers[:5]]}

        elif tool_name == "get_store_overview":
            overview = self.kernel.get_store_overview(store_id)
            return overview.to_dict() if overview else {"error": "Store not found"}

        elif tool_name == "get_sku_metrics":
            sku_id = params.get("sku_id", "")
            metrics = self.kernel.get_sku_metrics(sku_id, store_id)
            return metrics.to_dict() if metrics else {"error": f"SKU {sku_id} not found"}

        elif tool_name == "search_products":
            query = params.get("query", "")
            results = self.kernel.search_skus(query, store_id)
            return {"query": query, "results": results[:5]}

        elif tool_name == "compare_skus":
            sku_ids = params.get("sku_ids", [])
            comparisons = self.kernel.compare_skus(sku_ids, store_id)
            return {"comparisons": [m.to_dict() for m in comparisons]}

        return {"error": f"Unknown tool {tool_name}"}

    def _route_and_gather_data(self, query: str, store_id: str) -> Tuple[List[str], Dict[str, Any]]:
        """
        Analyze user query intent and execute relevant deterministic analytical tools.
        """
        q = query.lower()
        tools_executed = []
        data_payload = {}

        # Check for stockouts / running out
        if any(w in q for w in ["running out", "stockout", "deficit", "depleted", "low stock", "runway"]):
            res = self.execute_tool("get_imminent_stockouts", {"store_id": store_id})
            data_payload["imminent_stockouts"] = res
            tools_executed.append("get_imminent_stockouts")

            # Also check if transfers are available for these items
            trans_res = self.execute_tool("check_interstore_transfers", {"store_id": store_id})
            data_payload["available_transfers"] = trans_res
            tools_executed.append("check_interstore_transfers")

        # Check for dead stock / overstock / non-moving
        if any(w in q for w in ["dead stock", "not moving", "stagnant", "overstock", "idle", "locked capital", "markdown"]):
            res = self.execute_tool("get_dead_stock", {"store_id": store_id})
            data_payload["dead_stock"] = res
            tools_executed.append("get_dead_stock")

        # Check for anomalies / drops / spikes
        if any(w in q for w in ["anomaly", "anomalies", "spike", "drop", "unusual", "surge", "collapse", "phantom"]):
            res = self.execute_tool("get_sales_anomalies", {"store_id": store_id})
            data_payload["sales_anomalies"] = res
            tools_executed.append("get_sales_anomalies")

            phantoms = self.execute_tool("get_phantom_inventory", {"store_id": store_id})
            data_payload["phantom_inventory"] = phantoms
            tools_executed.append("get_phantom_inventory")

        # Check for transfer / arbitrage
        if any(w in q for w in ["transfer", "arbitrage", "rebalance", "inter-store", "interstore"]):
            if "check_interstore_transfers" not in tools_executed:
                res = self.execute_tool("check_interstore_transfers", {"store_id": store_id})
                data_payload["available_transfers"] = res
                tools_executed.append("check_interstore_transfers")

        # Check for specific SKU mentions (e.g. SKU_1001, bread, milk, yogurt, vinegar)
        sku_match = re.search(r"\bSKU_\d{4}\b", query, re.IGNORECASE)
        if sku_match:
            sku_id = sku_match.group(0).upper()
            m = self.execute_tool("get_sku_metrics", {"sku_id": sku_id, "store_id": store_id})
            data_payload[f"sku_metrics_{sku_id}"] = m
            tools_executed.append("get_sku_metrics")
        else:
            # Check for common product keywords
            keywords = ["bread", "milk", "yogurt", "sourdough", "vinegar", "makhana", "olive oil"]
            found_kws = [k for k in keywords if k in q]
            if found_kws:
                s_res = self.execute_tool("search_products", {"query": found_kws[0], "store_id": store_id})
                data_payload["product_search"] = s_res
                tools_executed.append("search_products")
                if s_res.get("results"):
                    top_sku = s_res["results"][0]["sku_id"]
                    m = self.execute_tool("get_sku_metrics", {"sku_id": top_sku, "store_id": store_id})
                    data_payload[f"sku_metrics_{top_sku}"] = m
                    tools_executed.append("get_sku_metrics")

        # Check for store macro / performance questions
        if any(w in q for w in ["store overview", "performance", "revenue", "how is store", "sales summary", "daily tally"]):
            if "get_store_overview" not in tools_executed:
                res = self.execute_tool("get_store_overview", {"store_id": store_id})
                data_payload["store_overview"] = res
                tools_executed.append("get_store_overview")

        # Fallback if query was generic: fetch store overview and top stockouts
        if not tools_executed:
            res_ov = self.execute_tool("get_store_overview", {"store_id": store_id})
            res_so = self.execute_tool("get_imminent_stockouts", {"store_id": store_id})
            data_payload["store_overview"] = res_ov
            data_payload["imminent_stockouts"] = res_so
            tools_executed = ["get_store_overview", "get_imminent_stockouts"]

        return tools_executed, data_payload

    def _synthesize_deterministic_response(
        self,
        query: str,
        store_id: str,
        tools: List[str],
        data: Dict[str, Any],
    ) -> str:
        """
        Deterministic template engine synthesizing structured, grounded markdown responses
        when Gemini API is offline or unconfigured.
        """
        lines = []

        if "imminent_stockouts" in data:
            so_data = data["imminent_stockouts"]
            items = so_data.get("stockouts", [])
            lines.append("### ⚠️ Imminent Stockout Triage")
            if items:
                lines.append(f"We identified **{so_data.get('count', len(items))} critical SKUs** facing potential stockouts at `{store_id}`:\n")
                for it in items[:3]:
                    lines.append(
                        f"- **{it['product_name']} (`{it['sku_id']}`)**:\n"
                        f"  - **On Hand:** {it['on_hand']} units | **7-Day Velocity:** {it['velocity_7d']} units/day\n"
                        f"  - **Runway (DOI):** **{it['doi_days']} days** vs. Supplier Lead Time of **{it['lead_time_days']} days**\n"
                        f"  - **Projected Stockout:** `{it['projected_stockout_date']}` | **Deficit:** {it['deficit_units']} units\n"
                        f"  - **Recommended Action:** Supplier reorder of **{it['recommended_order_qty']} units** (Target Par Level)."
                    )
            else:
                lines.append("No critical stockout alerts detected for this store.\n")

            if "available_transfers" in data and data["available_transfers"].get("transfers"):
                transfers = data["available_transfers"]["transfers"]
                lines.append("\n#### 🔄 Recommended Inter-Store Transfer Arbitrage:")
                for t in transfers[:2]:
                    lines.append(
                        f"- **Transfer {t['quantity']} units of {t['product_name']}** from **{t['from_store_name']}** to **{t['to_store_name']}**\n"
                        f"  - **Financial Savings:** **${t['gross_profit_protected']:0.2f} gross profit protected** (Courier cost: ${t['estimated_courier_cost']:0.2f} | **Net Benefit: +${t['net_savings']:0.2f}**)\n"
                        f"  - **Estimated Transit Time:** **{t['estimated_transit_hours']} hours** via local delivery\n"
                        f"  - **Source Safety:** Source store maintains **{t['source_remaining_runway_days']} days** of runway."
                    )

        elif "dead_stock" in data:
            ds_data = data["dead_stock"]
            items = ds_data.get("dead_stock", [])
            lines.append("### 📦 Stagnant Inventory & Dead Capital Report")
            if items:
                lines.append(f"Surfaced **{ds_data.get('count', len(items))} slow-moving SKUs** tying up working capital at `{store_id}`:\n")
                for it in items[:3]:
                    lines.append(
                        f"- **{it['product_name']} (`{it['sku_id']}`)**:\n"
                        f"  - **On Hand:** {it['on_hand']} units | **Locked Capital:** **${it['locked_capital']:0.2f}**\n"
                        f"  - **Days Idle:** **{it['days_since_last_sale']} days** without sale | **Holding Drag:** ${it['monthly_holding_cost_drag']:0.2f}/month\n"
                        f"  - **Recommended Action:** {it['recommended_action']} (Expected cash recovery: **${it['estimated_cash_recovery']:0.2f}**)."
                    )
            else:
                lines.append("No dead stock items detected above the 30-day threshold.\n")

        elif "sales_anomalies" in data:
            anom_data = data["sales_anomalies"]
            items = anom_data.get("anomalies", [])
            lines.append("### 📊 Demand Velocity Anomalies")
            if items:
                lines.append(f"Detected **{len(items)} statistically significant sales shifts** (|Z| ≥ 2.0):\n")
                for a in items[:3]:
                    icon = "📈" if a["anomaly_type"] == "SPIKE" else "📉"
                    lines.append(
                        f"- {icon} **{a['product_name']} (`{a['sku_id']}`) — {a['anomaly_type']} (Z={a['z_score']:+0.1f})**\n"
                        f"  - **Yesterday's Sales:** {a['yesterday_sales']} units vs 14-day mean of {a['baseline_mean_14d']} units ({a['percent_change_vs_baseline']:+0.1f}%)\n"
                        f"  - **On Hand:** {a['on_hand']} units\n"
                        f"  - **Operational Recommendation:** {a['recommended_action']}."
                    )
            else:
                lines.append("Sales across all items remained within normal 2-sigma thresholds yesterday.\n")

        elif any(k.startswith("sku_metrics_") for k in data):
            for k, m in data.items():
                if k.startswith("sku_metrics_") and "product_name" in m:
                    lines.append(f"### 🏷️ SKU Performance: {m['product_name']} (`{m['sku_id']}`)\n")
                    lines.append(
                        f"- **Store:** {m['store_name']} (`{m['store_id']}`)\n"
                        f"- **On-Hand Inventory:** **{m['on_hand']} units** (Days since last sale: {m['days_since_last_sale']})\n"
                        f"- **Pricing & Margins:** Retail: **${m['retail_price']:0.2f}** | Cost: **${m['cost_price']:0.2f}** | Gross Margin: **{m['gross_margin_pct']}%**\n"
                        f"- **Rolling Sales Velocity:** 7-Day: **{m['velocity_7d']} units/day** | 30-Day: **{m['velocity_30d']} units/day**\n"
                        f"- **30-Day Volume:** **{m['units_sold_30d']} units sold** generating **${m['revenue_30d']:0.2f}** in revenue\n"
                        f"- **Supplier Details:** {m['supplier_name']} (Lead Time: **{m['lead_time_days']} days**, MOQ: {m['min_order_qty']})"
                    )
                elif k.startswith("sku_metrics_") and "error" in m:
                    lines.append(f"### ⚠️ Product Not Found\n- Could not locate records for requested item: {m.get('error')}.")

        elif "store_overview" in data:
            ov = data["store_overview"]
            lines.append(f"### 🏬 Store Performance Overview: {ov['store_name']} (`{ov['store_id']}`)\n")
            lines.append(
                f"- **Total Revenue (30d):** **${ov['total_revenue']:0.2f}** (Avg Daily: ${ov['avg_daily_revenue']:0.2f}/day)\n"
                f"- **Gross Profit:** **${ov['total_gross_profit']:0.2f}** | **Gross Margin:** **{ov['gross_margin_pct']}%**\n"
                f"- **Volume Sold:** **{ov['total_units_sold']} units** across **{ov['active_skus_count']} active SKUs**\n"
                f"- **Out of Stock Items Today:** **{ov['out_of_stock_skus_count']} SKUs**"
            )

        else:
            lines.append("Grounded retail metrics extracted successfully. All figures verified by deterministic analytics kernel.")

        return "\n".join(lines)

    def ask(self, query: str, store_id: str = "STORE_01") -> CopilotResponse:
        """
        Process a user question through Epistemic Boundary validation,
        Deterministic Tool Execution, and Gemini 2.5 Flash / Local Template Synthesis.
        """
        # 1. Epistemic Boundary Guardrail
        is_in_scope, refusal_msg = check_epistemic_boundary(query)
        if not is_in_scope:
            return CopilotResponse(
                query=query,
                response=refusal_msg,
                source="epistemic-refusal",
                tools_executed=[],
                grounded_facts={},
            )

        # 2. Route Query & Gather Deterministic Facts
        tools_executed, grounded_facts = self._route_and_gather_data(query, store_id)

        # 3. If Gemini Client is configured, synthesize via Gemini 2.5 Flash
        if self.client:
            try:
                from google.genai import types

                prompt = (
                    f"User Query: {query}\n"
                    f"Target Store ID: {store_id}\n\n"
                    f"Verified Ground-Truth Data:\n"
                    f"{json.dumps(grounded_facts, indent=2)}\n\n"
                    f"Instructions: Answer the user's query clearly and concisely. "
                    f"Quote exact numbers and dates from the verified data above. "
                    f"Follow all strict operational rules and provide a clear Recommended Action."
                )

                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.1,
                    ),
                )

                if response and response.text:
                    return CopilotResponse(
                        query=query,
                        response=response.text,
                        source="gemini-2.5-flash",
                        tools_executed=tools_executed,
                        grounded_facts=grounded_facts,
                    )
            except Exception as e:
                print(f"[WARN] Gemini synthesis failed: {e}. Falling back to deterministic engine.")

        # 4. Deterministic Synthesis Fallback
        deterministic_reply = self._synthesize_deterministic_response(
            query, store_id, tools_executed, grounded_facts
        )
        return CopilotResponse(
            query=query,
            response=deterministic_reply,
            source="deterministic-fallback",
            tools_executed=tools_executed,
            grounded_facts=grounded_facts,
        )
