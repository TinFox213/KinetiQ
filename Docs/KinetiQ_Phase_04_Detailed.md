# Phase 04: Demand Anomaly Detection & Dead Capital Classifier

## Detailed Implementation Guide for AI / Antigravity

**Track ID:** PS03 | **Module:** Statistical Anomalies & Stagnant Inventory

---

## 1\. Objective & Scope

The problem statement mandates: *"It flags what needs attention today: stock that is not moving, and sales spikes or drops worth a look and recommends an action for each, showing data and assumptions."* Phase 04 implements:

1. **Z-Score Sales Spike / Drop Detector:** Surfaces sudden demand surges or unexpected drops.  
2. **Phantom Inventory Detector:** Stock $\> 0$, expected sales $\> 5$ units/day, but 3 consecutive days of 0 sales $\\rightarrow$ flags misplacement, shrinkage, or scanning error.  
3. **Dead Capital & Stagnancy Classifier:** Identifies frozen liquidity tied up in zero-velocity products.

---

## 2\. Statistical Formulations

### 2.1 Demand Velocity Z-Score

For yesterday's sales $y\_t$ evaluated against the prior 14-day rolling baseline ($\\mu\_{14}, \\sigma\_{14}$): $$Z \= \\frac{y\_t \- \\mu\_{14}}{\\max(\\sigma\_{14}, 0.5)}$$

- **Positive Spike ($Z \\ge \+2.5$):** Demand surge (viral product, local event, competitor stockout). Action: Check shelf replenishment to avoid stockout.  
- **Negative Drop ($Z \\le \-2.0$):** Unexplained demand collapse. Action: Check shelf presentation or price tag accuracy.

### 2.2 Dead Capital Index (DCI)

$$\\text{Dead Capital ($) } \= \\text{On\_Hand} \\times \\text{Cost Price}$$ $$\\text{Holding Cost Drag ($/month)} \= \\text{Dead Capital} \\times \\frac{0.24}{12} \\quad (24% \\text{ annual holding cost})$$ Criteria for **Dead Stock**:

1. $\\text{Days Since Last Sale} \\ge 30 \\text{ days}$, OR  
2. $\\text{DOI} \> 90 \\text{ days}$ with at least 15 units on hand.

---

## 3\. Prescriptive Actions for Stagnant Inventory

1. **Dynamic Markdown Recommendation:**  
   - Markdown 20% if $30 \\le \\text{DOI} \\le 60$.  
   - Markdown 40% if $\\text{DOI} \> 60$ or near expiry.  
2. **Bundle Suggestion:**  
   - Automatically pair the dead SKU with the highest-velocity compatible SKU in the same category.  
3. **Shelf Space Reallocation:**  
   - Recommend moving from prime eye-level shelves to endcap or clearance bin.

---

## 4\. Antigravity AI Implementation Prompt

@Antigravity: Create \`src/analytics/anomalies.py\`.

Implement:

1\. \`detect\_sales\_anomalies(store\_id: str, z\_threshold: float \= 2.0) \-\> list\[dict\]\`

2\. \`detect\_dead\_stock(store\_id: str, idle\_days\_threshold: int \= 30\) \-\> list\[dict\]\`

3\. \`detect\_phantom\_inventory(store\_id: str) \-\> list\[dict\]\`

Ensure every return payload provides complete figures: cost locked, holding cost estimate, baseline mean, actual observed sales, and recommended action with reasoning.  
