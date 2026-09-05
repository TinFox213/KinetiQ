# Phase 03: Inventory Physics Engine (Runways & Stockouts)

## Detailed Implementation Guide for AI / Antigravity

**Track ID:** PS03 | **Module:** Inventory Science & Stockout Predictor

---

## 1\. Objective & Scope

The store manager must know: *"What is running out before it happens?"* Phase 03 implements classical supply-chain operations research equations to calculate:

1. **Days of Inventory (DOI) / Runway:** Exact days until the shelf is empty.  
2. **Stockout Date:** Exact calendar date/hour of projected stock exhaustion.  
3. **Safety Stock (SS) & Reorder Point (ROP):** When to trigger a supplier reorder.  
4. **Order Quantity Recommendation:** Economic Order Quantity (EOQ) or Target Par Level.

---

## 2\. Supply Chain Mathematical Formulations

### 2.1 Days of Inventory (DOI)

$$\\text{DOI}(s, k) \= \\begin{cases} \\frac{\\text{On\_Hand}(s, k)}{\\text{Velocity}*{7d}(s, k)} & \\text{if } \\text{Velocity}*{7d} \> 0 \\ 999.0 & \\text{if } \\text{Velocity}\_{7d} \= 0 \\land \\text{On\_Hand} \> 0 \\ 0.0 & \\text{if } \\text{On\_Hand} \= 0 \\end{cases}$$

### 2.2 Safety Stock (SS) with 95% Service Level

Given lead time $L$ (days) and daily sales standard deviation $\\sigma\_D$: $$\\text{SS} \= Z \\times \\sigma\_D \\times \\sqrt{L} \\quad (Z \= 1.645 \\text{ for } 95% \\text{ service level})$$

### 2.3 Reorder Point (ROP)

$$\\text{ROP} \= (\\text{Velocity}\_{7d} \\times L) \+ \\text{SS}$$

- If $\\text{On\_Hand} \\le \\text{ROP}$, trigger a restock alert immediately.  
- If $\\text{DOI} \\le L$, mark as **CRITICAL: Stockout Inevitable before normal delivery**.

### 2.4 Recommended Reorder Quantity (Target Max Par Level)

$$\\text{Par Level} \= \\text{Velocity}\_{7d} \\times (L \+ \\text{Review Period Days}) \+ \\text{SS}$$ $$\\text{Recommended Order Qty} \= \\max(\\text{MinOrderQty}, \\lceil \\text{Par Level} \- \\text{On\_Hand} \\rceil)$$

---

## 3\. Implementation Specification (`src/analytics/inventory_physics.py`)

from dataclasses import dataclass

from datetime import date, timedelta

import math

@dataclass

class StockoutAlert:

    sku\_id: str

    product\_name: str

    store\_id: str

    on\_hand: int

    velocity\_7d: float

    doi\_days: float

    lead\_time\_days: int

    projected\_stockout\_date: str

    urgency\_level: str \-- 'CRITICAL', 'WARNING', 'HEALTHY'

    deficit\_units: int

    recommended\_order\_qty: int

    assumptions: dict

def evaluate\_stockouts(sku\_metrics: SkuMetrics, lead\_time: int, min\_order\_qty: int \= 10\) \-\> StockoutAlert:

    \# Deterministically calculate DOI, ROP, Deficit, and Order Qty

    pass

---

## 4\. Antigravity AI Implementation Prompt

@Antigravity: Build \`src/analytics/inventory\_physics.py\`.

Implement:

1\. \`calculate\_doi(on\_hand: int, velocity: float) \-\> float\`

2\. \`calculate\_rop(velocity: float, lead\_time: int, sigma: float, service\_level: float \= 0.95) \-\> int\`

3\. \`get\_imminent\_stockouts(store\_id: str, threshold\_days: int \= 5\) \-\> list\[StockoutAlert\]\`

Include full assumptions ledger in the output dictionary:

{

  "lead\_time\_days": 4,

  "velocity\_basis": "7-day rolling unconstrained average",

  "service\_level\_target": "95%",

  "safety\_stock\_buffer\_units": 6

}

Write unit tests covering edge cases: 0 on hand, 0 velocity, and high volatility.  
