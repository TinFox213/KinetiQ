# Phase 07: Daily 3-Minute Cockpit & What-If Simulator

## Detailed Implementation Guide for AI / Antigravity

**Track ID:** PS03 | **Module:** Store Manager Cockpit & Scenario Simulation

---

## 1\. Objective & Scope

Store managers are rushed. They do not have time to explore multi-level menus. Phase 07 builds:

1. **The Morning 3-Minute Triage Cockpit (`src/analytics/triage.py`):** Pre-assembles the top 3 critical stockouts, top 3 dead stock SKUs, and top 3 demand velocity spikes into an actionable executive dashboard.  
2. **Interactive What-If Simulation Sandbox (`src/analytics/simulator.py`):** Models price discounts, promotional lifts, and lead-time delays deterministically.

---

## 2\. Morning Triage Schema (`src/analytics/triage.py`)

@dataclass

class DailyTriageBriefing:

    date: str

    store\_id: str

    store\_name: str

    health\_score: int \# 0 to 100

    imminent\_stockouts: list\[dict\] \# Top 3 items running out \< lead time

    stagnant\_dead\_stock: list\[dict\] \# Top 3 items with highest locked capital

    velocity\_anomalies: list\[dict\] \# Top 3 spikes/drops

    action\_items\_count: int

    potential\_revenue\_loss\_avoided: float

    total\_dead\_capital\_locked: float

def generate\_morning\_triage(store\_id: str) \-\> DailyTriageBriefing:

    \# Orchestrate calls to kernel, inventory\_physics, anomalies, and rebalance

    pass

---

## 3\. What-If Price Elasticity & Demand Lift Simulation

### Mathematical Model:

Given base price $P\_0$, base velocity $V\_0$, category price elasticity $E$ (typically $-1.2$ to $-2.5$ for retail food/beverage): $$\\Delta P % \= \\frac{P\_{\\text{new}} \- P\_0}{P\_0}$$ $$\\text{Expected Demand Lift } \\Delta V % \= \\Delta P % \\times E$$ $$\\text{Projected Velocity } V\_{\\text{new}} \= V\_0 \\times (1 \+ \\Delta V %)$$ $$\\text{Projected Days to Clear Inventory} \= \\frac{\\text{On\_Hand}}{V\_{\\text{new}}}$$ $$\\text{Gross Profit Comparison}:$$ $$\\text{Baseline Profit} \= (\\text{On\_Hand} \\times V\_0 \\times 14\) \\times (P\_0 \- C)$$ $$\\text{Discounted Profit} \= \\min(\\text{On\_Hand}, V\_{\\text{new}} \\times 14\) \\times (P\_{\\text{new}} \- C)$$

---

## 4\. Antigravity AI Implementation Prompt

@Antigravity: Build \`src/analytics/triage.py\` and \`src/analytics/simulator.py\`.

The triage generator must run in under 200ms by querying pre-aggregated tables or fast SQLite views.

The simulator should accept:

\`simulate\_intervention(sku\_id, store\_id, discount\_percent, duration\_days)\`

and return:

\- old\_velocity, new\_velocity

\- old\_days\_to\_clear, new\_days\_to\_clear

\- gross\_profit\_delta

\- inventory\_exhaustion\_risk

Write unit tests in \`tests/test\_triage.py\` and \`tests/test\_simulator.py\`.  
