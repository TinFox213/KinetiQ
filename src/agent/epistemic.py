import re
from typing import Tuple, Optional


UNANSWERABLE_INTENTS = [
    (
        [
            r"\bfootfall\b",
            r"\bdoor counter\b",
            r"\bpedestrian\b",
            r"\bfoot traffic\b",
            r"\bvisitor counter\b",
            r"\bvisited\b",
        ],
        "customer footfall, door counters, or store visitor tracking sensors",
    ),
    (
        [
            r"\bweather\b",
            r"\brain\b",
            r"\brainfall\b",
            r"\bmonsoon\b",
            r"\btemperature\b",
            r"\bstorm\b",
            r"\bmeteorological\b",
        ],
        "meteorological conditions, weather forecasting, or rainfall telemetry",
    ),
    (
        [
            r"\bcompetitor\b",
            r"\bcompetitors\b",
            r"\brival\b",
            r"\brivals\b",
            r"\bmarket share\b",
            r"\bexternal pricing\b",
            r"\bother supermarkets\b",
        ],
        "competitor pricing benchmarks, external market share, or third-party store data",
    ),
    (
        [
            r"\bdemographic\b",
            r"\bdemographics\b",
            r"\bage\b",
            r"\bgender\b",
            r"\bteenager\b",
            r"\bteenagers\b",
            r"\bincome bracket\b",
        ],
        "customer personal identity, demographic age profiles, or loyalty club personal data",
    ),
    (
        [
            r"\bwholesale\b",
            r"\bcommodity\b",
            r"\bcommodities\b",
            r"\bfutures\b",
            r"\bmandi\b",
            r"\bmandi price\b",
        ],
        "external commodity exchange trading rates or wholesale raw material market feeds",
    ),
    (
        [
            r"\binflation\b",
            r"\bmacroeconomic\b",
            r"\bgdp\b",
            r"\binterest rate\b",
            r"\beconomic forecast\b",
        ],
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

    for pattern_list, missing_description in UNANSWERABLE_INTENTS:
        for pat in pattern_list:
            if re.search(pat, query_lower):
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
