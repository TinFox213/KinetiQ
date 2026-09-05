# End-to-End Workflow Document

## Project Name: KinetiQ — Retail Sales & Inventory Copilot

**Track ID:** PS03  
**Scope:** Complete Operational and Data Workflows for Store Managers and Developers

---

## 1\. System Lifecycle & Startup Workflow (Under 90s SLA)

\[Start Command: python app.py\]

               |

               v

       (1. Environment Check)

       Is GEMINI\_API\_KEY present?

       ├── Yes \-\> Initialize Gemini Client

       └── No  \-\> Fallback to Local Deterministic Templating Engine

               |

               v

       (2. Database Bootstrap)

       Does data/retail\_inventory.db exist?

       ├── Yes \-\> Connect to SQLite / DuckDB

       └── No  \-\> Execute src/data/generator.py

                  \- Generate 3 Stores (Urban Downtown, Suburban Mall, Highway Hub)

                  \- Generate 250 Realistic SKUs (Perishables, Beverages, Staples, Snacks)

                  \- Generate 90 Days of Sales & Stock Transactions (150,000 rows)

                  \- Time taken: \~2.2 seconds

               |

               v

       (3. Analytical Precomputation)

       \- Compute 7-day, 14-day, and 30-day rolling velocities

       \- Calculate current on-hand stock and Days of Inventory (DOI)

       \- Build the Daily Morning Triage Matrix

       \- Time taken: \~0.8 seconds

               |

               v

       (4. Server Launch)

       \- Uvicorn binds to 0.0.0.0:8000

       \- Static files served from frontend/dist/ or src/static/

       \- Total cold start: \< 4.0 seconds (Passing 90s limit with 95% safety margin)

---

## 2\. Daily Morning Triage Workflow (The 3-Minute Store Manager Routine)

Every morning before opening, the store manager runs through this structured operational flow:

### Step 1: Automated Health Scorecard

- The UI displays an executive summary:  
  - Total Active SKUs: `250`  
  - Healthy SKUs: `218`  
  - Imminent Stockouts: `12`  
  - Dead Capital Items: `15`  
  - Velocity Anomalies: `5`  
  - Total Capital Tied in Dead Stock: `$4,120.50`

### Step 2: Imminent Stockout Resolution

- **Detection:** SKU `SKU_1042` (Organic Greek Yogurt, 500g)  
  - Current On Hand: `14 units`  
  - 7-Day Rolling Velocity: `5.6 units/day`  
  - Remaining Runway: `2.5 days`  
  - Supplier Lead Time: `4 days`  
  - Deficit Before Restock: $\\text{Shortfall} \= (4.0 \- 2.5) \\times 5.6 \= 8.4 \\text{ units}$  
- **Copilot Action Card:**  
  - *Option A (Inter-Store Transfer \- Recommended):* Store 3 holds `58 units` with velocity `0.4 units/day` (145 days DOI). Action: Transfer `25 units` from Store 3 to Store 1 today (Estimated transit: 3 hours, cost: $5.00).  
  - *Option B (Distributor Reorder):* Standard supplier reorder of 40 units at $2.20/unit; arrives in 4 days (Results in 1.5 days of out-of-stock revenue loss).  
- **Manager Interaction:** Clicks **"Approve Transfer Manifest"**. System records the transfer, decrements pending stock from Store 3, increments in-transit stock for Store 1, and prints a shipping manifest.

### Step 3: Stagnant Stock & Dead Capital Clearance

- **Detection:** SKU `SKU_1180` (Artisanal Truffle Vinegar)  
  - Current On Hand: `42 units`  
  - Cost Capital: `$18.50/unit` $\\rightarrow$ `$777.00` total locked cash  
  - Sales in Last 30 Days: `0 units` (DOI: $\\infty$)  
  - Shelf Space Occupancy: `Premium Front Gondola`  
- **Copilot Action Card:**  
  - *Recommended Action:* 35% Promotional Clearance Bundle with fast-moving Olive Oil (`SKU_1012`), moving shelf position to Endcap.  
  - *Assumptions:* Price elasticity factor $-1.8$; expected clearance velocity $1.4$ units/day; expected full liquidation in 30 days recovering $$505.00$ in cash.

### Step 4: Demand Velocity Anomalies Investigation

- **Detection:** SKU `SKU_1008` (Sourdough Loaf)  
  - Typical daily volume: $18 \\pm 3$ units  
  - Yesterday's sales: `0 units` ($Z \= \-3.8$)  
  - Recorded stock on hand: `15 units`  
- **Copilot Action Card:**  
  - *Alert:* Phantom inventory or scanning issue. System indicates stock exists, but zero sales occurred on a high-demand day.  
  - *Recommended Action:* Conduct physical shelf audit. (Item may be mislaid in backroom, damaged, or barcode unscannable).

---

## 3\. Conversational Query & Grounded Synthesis Workflow

\[User Input Query\]

"How did whole wheat bread perform this month compared to white bread in Store 2?"

                         |

                         v

       (1. Entity & Intent Extraction)

       \- Category / SKU Match: "Whole Wheat Bread" (SKU\_1002) vs "White Bread" (SKU\_1001)

       \- Scope: Store 2, Month: Last 30 Days

       \- Intent: Comparative Performance Analysis

                         |

                         v

       (2. Epistemic Validation)

       \- Are SKUs found in catalog? YES

       \- Is Store 2 valid? YES

       \- Are 30-day sales records available? YES

                         |

                         v

       (3. Deterministic Data Extraction)

       SQL Query against DuckDB/SQLite:

       SELECT sku\_id, SUM(units\_sold), SUM(revenue), AVG(units\_sold), COUNT(DISTINCT sale\_date)

       WHERE store\_id \= 'STORE\_02' AND sale\_date \>= CURRENT\_DATE \- 30;

                         |

                         v

       Structured Result:

       {

         "SKU\_1002": {"name": "Whole Wheat Bread", "units\_sold": 412, "revenue": 1236.00, "daily\_avg": 13.73, "stockouts": 0},

         "SKU\_1001": {"name": "Classic White Bread", "units\_sold": 598, "revenue": 1196.00, "daily\_avg": 19.93, "stockouts": 2}

       }

                         |

                         v

       (4. Grounded Prompt Formulation)

       System Prompt instructs Gemini 2.5 Flash:

       "Synthesize the comparative analysis strictly using the numbers above.

        Quote units sold, revenue, and daily average. Highlight that Classic White Bread

        experienced 2 stockout days which curtailed potential revenue."

                         |

                         v

       (5. LLM Generation & Output Display)

       Clean, structured response displayed to user with data tables,

       charts, and specific actionable takeaway.

---

## 4\. Disciplined Refusal Workflow (Epistemic Guardrails)

The hackathon guidelines require: *"When the data cannot answer a question, it says so rather than guessing."*

### Scenario A: Unrecorded Attribute

- **User:** *"Which brand of ice cream is preferred by teenage customers in Store 1?"*  
- **Epistemic Engine:**  
  - Data Available: SKU, product name, price, store\_id, sale\_timestamp, units\_sold.  
  - Data Missing: Customer demographic records, ages, loyalty club profile.  
- **System Output:**  
    
  \*\*Data Limitation Notice:\*\*  
    
  Our system does not collect or store customer demographic information or customer age profiles.   
    
  \*\*What the data can confirm:\*\*  
    
  Across all customers at Store 1 over the last 30 days:  
    
  \- Brand A (Belgian Chocolate): 340 units sold ($1,700.00 revenue)  
    
  \- Brand B (Vanilla Bean): 215 units sold ($860.00 revenue)  
    
  Total ice cream category revenue was $3,450.00 across 810 units.

### Scenario B: Hypothetical Unmodeled Macro Event

- **User:** *"How will next week's monsoon impact tomato sales in Store 3?"*  
- **System Output:**  
    
  \*\*Epistemic Boundary:\*\*  
    
  KinetiQ has no integrated meteorological forecasting API or weather-to-demand regression model.   
    
  \*\*Historical Baseline:\*\*  
    
  Over the past 90 days, Store 3 sells an average of 24.5 kg of tomatoes per day (std dev: 4.2 kg). Current inventory is 32.0 kg (1.3 days of inventory). If you anticipate delivery delays due to regional weather, placing an early replenishment order is advised, as supplier lead time is 2 days.

