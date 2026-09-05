"""
KinetiQ Epistemic Boundary Guardrail
Enforces disciplined refusal whenever a user query seeks information absent from
or out-of-domain for the retail POS and inventory database.
"""

from typing import Tuple, Optional


UNANSWERABLE_INTENTS = [
    (
        ["footfall", "door counter", "pedestrian", "foot traffic", "visitor counter"],
        "customer footfall, door counters, or store visitor tracking sensors",
    ),
    (
        ["weather", "rain", "rainfall", "monsoon", "temperature", "storm", "meteorological"],
        "meteorological conditions, weather forecasting, or rainfall telemetry",
    ),
    (
        ["competitor", "rival", "market share", "external pricing", "other supermarkets"],
        "competitor pricing benchmarks, external market share, or third-party store data",
    ),
    (
        ["demographic", "age", "gender", "teenager", "income bracket", "customer age"],
        "customer personal identity, demographic age profiles, or loyalty club personal data",
    ),
    (
        ["wholesale market", "commodity exchange", "mandi price", "futures market", "commodity", "futures"],
        "external commodity exchange trading rates or wholesale raw material market feeds",
    ),
    (
        ["inflation", "macroeconomic", "gdp", "interest rate", "economic forecast"],
        "macroeconomic indicators, national inflation forecasts, or economic policy data",
    ),
]


def check_epistemic_boundary(query: str) -> Tuple[bool, str]:
    """
    Check if a query violates epistemic boundaries by requesting unrecorded or out-of-domain data.
    Returns:
        (is_in_scope: bool, refusal_response: str)
    """
    query_lower = query.lower().strip()

    for keywords, missing_description in UNANSWERABLE_INTENTS:
        if any(kw in query_lower for kw in keywords):
            refusal = (
                f"**Data Boundary Notice:**\n"
                f"Our system does not collect or track {missing_description}.\n\n"
                f"**What the verified data can confirm:**\n"
                f"- Daily POS transaction sales and revenue across Stores 1, 2, and 3.\n"
                f"- Current on-hand inventory balances and days of inventory (DOI).\n"
                f"- Supplier reorder points, lead times (2–6 days), and minimum order quantities.\n"
                f"- Inter-store stock transfer availability across our local retail network."
            )
            return False, refusal

    return True, ""
