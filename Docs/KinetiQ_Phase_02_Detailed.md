# Phase 02: High-Performance Deterministic Analytical Kernel

## Detailed Implementation Guide for AI / Antigravity

**Track ID:** PS03 | **Module:** Deterministic Analytics & In-Memory SQL

---

## 1\. Objective & Scope

The core tenet of KinetiQ is **Zero-Math in the LLM**: the language model is strictly prohibited from calculating numbers, aggregations, ratios, or projections. Phase 02 builds the high-performance analytical kernel (`src/analytics/kernel.py`) that queries SQLite/DuckDB and outputs verified, strongly-typed JSON data structures for:

1. Multi-window rolling sales velocities (7-day, 14-day, 30-day moving averages).  
2. Store-level performance aggregation (revenue, units, margins, transaction volume).  
3. Product-level comparative metrics across stores.  
4. Historical demand standard deviation ($\\sigma$) for safety stock modeling.

---

## 2\. Core Mathematical Formulations

### 2.1 Rolling Sales Velocity

For any date $T$ and window $W \\in {7, 14, 30}$: $$\\text{Velocity}*W(s, k) \= \\frac{1}{W} \\sum*{i=1}^{W} \\text{units\_sold}(T \- i, s, k)$$ *Crucial Retail Adjustment:* If an item had a recorded stockout on day $t$ ($\\text{had\_stockout} \= 1$), calculate **Unconstrained Velocity** by normalizing for active in-stock days only: $$\\text{ActiveDays} \= W \- \\sum\_{i=1}^{W} \\mathbb{I}(\\text{Stock}*i \= 0)$$ $$\\text{Velocity}*{\\text{unconstrained}} \= \\frac{\\sum\_{i=1}^{W} \\text{units\_sold}\_i}{\\max(1, \\text{ActiveDays})}$$

### 2.2 Gross Profit Margin

$$\\text{Gross Margin %} \= \\frac{\\text{Retail Price} \- \\text{Cost Price}}{\\text{Retail Price}} \\times 100$$ $$\\text{Total Gross Profit} \= \\sum (\\text{Retail Price} \- \\text{Cost Price}) \\times \\text{Units Sold}$$

---

## 3\. High-Performance SQL Aggregates (`src/analytics/kernel.py`)

from dataclasses import dataclass

from typing import Dict, List, Optional

import sqlite3

@dataclass

class SkuMetrics:

    sku\_id: str

    product\_name: str

    category: str

    store\_id: str

    on\_hand: int

    velocity\_7d: float

    velocity\_30d: float

    std\_dev\_demand: float

    units\_sold\_30d: int

    revenue\_30d: float

    gross\_margin\_pct: float

    cost\_price: float

    retail\_price: float

class AnalyticsKernel:

    def \_\_init\_\_(self, db\_path: str \= "data/retail\_inventory.db"):

        self.db\_path \= db\_path

    def get\_sku\_metrics(self, sku\_id: str, store\_id: str) \-\> Optional\[SkuMetrics\]:

        conn \= sqlite3.connect(self.db\_path)

        cur \= conn.cursor()

        \# Query product details, latest on\_hand, and 30-day aggregate metrics

        query \= """

        SELECT 

            p.sku\_id, p.product\_name, p.category, i.store\_id, i.on\_hand\_units,

            p.cost\_price, p.retail\_price,

            COALESCE(AVG(CASE WHEN s.sale\_date \>= DATE('now', '-7 days') THEN s.units\_sold END), 0\) as v\_7d,

            COALESCE(AVG(s.units\_sold), 0\) as v\_30d,

            COALESCE(SUM(s.units\_sold), 0\) as total\_units\_30d,

            COALESCE(SUM(s.gross\_revenue), 0\) as total\_rev\_30d

        FROM products p

        JOIN inventory\_snapshots i ON p.sku\_id \= i.sku\_id

        LEFT JOIN daily\_sales s ON p.sku\_id \= s.sku\_id AND i.store\_id \= s.store\_id

        WHERE p.sku\_id \= ? AND i.store\_id \= ?

        GROUP BY p.sku\_id, i.store\_id

        """

        \# Return strongly typed SkuMetrics object

        pass

---

## 4\. Antigravity AI Implementation Prompt

@Antigravity: Implement \`src/analytics/kernel.py\`.

Provide comprehensive methods:

\- \`get\_sku\_metrics(sku\_id, store\_id)\`

\- \`get\_store\_overview(store\_id, window\_days=30)\`

\- \`compare\_skus(sku\_ids: list\[str\], store\_id: str)\`

\- \`get\_category\_summary(category: str, store\_id: str)\`

All calculations must be deterministic. Include unit tests in \`tests/test\_kernel.py\` validating that rolling averages handle 0-sale days gracefully without division-by-zero errors.  
