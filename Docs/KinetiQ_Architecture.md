# System Architecture Document

## Project Name: KinetiQ — Retail Sales & Inventory Copilot

**Track ID:** PS03  
**Architecture Pattern:** Neuro-Symbolic Dual-Brain (Deterministic Engine \+ Gemini LLM Orchestrator)

---

## 1\. High-Level Architecture Overview

KinetiQ is architected on a **strict separation of concerns**:

1. **Symbolic Deterministic Brain (Mathematical Truth):** In-memory DuckDB/SQLite database \+ Python analytical kernel. Executes arithmetic, aggregate statistics, days of inventory, rolling velocities, Z-scores, economic order quantities, and inter-store rebalancing math.  
2. **Neural Cognitive Brain (Linguistic & Semantic Synthesis):** Gemini API (`gemini-2.5-flash`). Handles query decomposition, semantic routing, natural language synthesis, and explaining recommendations using the structured JSON output provided by the symbolic brain.

\+-----------------------------------------------------------------------------------+

|                              KinetiQ User Interface                                |

|             (Embedded SPA: Modern Tailwind CSS / Vanilla ES6 / Charts.js)          |

\+----------------------------------------+------------------------------------------+

                                         | HTTP / REST (Port 8000\)

                                         v

\+-----------------------------------------------------------------------------------+

|                           FastAPI Gateway (app.py)                                |

|  \- Static Asset Mounter (/static, / \-\> index.html)                                |

|  \- REST Endpoints (/api/chat, /api/triage/today, /api/sku/{id}, /api/rebalance)   |

|  \- Lifespan Bootstrapper (Auto-seeds DB, compiles analytics in \< 5s)             |

\+----------------------------------------+------------------------------------------+

                                         |

     \+-----------------------------------+------------------------------------+

     |                                                                        |

     v                                                                        v

\+------------------------------------+   \+------------------------------------+

|   Neuro-Symbolic Copilot Engine    |   |   Deterministic Analytical Core    |

|   (src/agent/copilot.py)           |   |   (src/analytics/kernel.py)        |

|                                    |   |                                    |

| 1\. Query Intent Classifier         |   | 1\. High-Performance In-Memory DB   |

| 2\. Epistemic Refusal Guardrail     |   |    (DuckDB / SQLite WAL Mode)      |

| 3\. Tool Dispatcher & Schema Val    |\<--+ 2\. Inventory Physics Engine:       |

| 4\. Context Grounding Engine        |   |    \- Rolling Velocity (7d, 14d, 30d|

| 5\. Gemini 2.5 Flash Client         |   |    \- Days of Inventory (DOI)       |

|    (google-genai / SDK)            |   |    \- Stockout Date & ROP           |

| 6\. Numerical Verification Filter   |   | 3\. Anomaly & Dead Stock Classifier |

|                                    |   | 4\. Inter-Store Arbitrage Engine    |

\+------------------------------------+   \+------------------------------------+

                 |                                         |

                 v                                         v

\+------------------------------------+   \+------------------------------------+

|        Google Gemini API           |   |   Local Storage & Data Seed        |

|   (GEMINI\_API\_KEY from env)        |   |   (data/retail\_inventory.db)       |

|  \- gemini-2.5-flash                |   |   \- Stores, Products, DailySales   |

|  \- text-embedding-004              |   |   \- StockSnapshots, Suppliers      |

\+------------------------------------+   \+------------------------------------+

---

## 2\. Component Specifications

### 2.1 The Data Persistence & Analytical Layer (`src/data/`)

- **Technology:** In-memory DuckDB or local SQLite with `PRAGMA journal_mode = WAL;` and `PRAGMA synchronous = NORMAL;`.  
- **Database Schema:**  
  1. `stores`: `store_id` (PK, e.g., 'STORE\_01'), `name`, `city`, `location_type`, `distance_matrix_km`.  
  2. `products`: `sku_id` (PK, e.g., 'SKU\_1001'), `product_name`, `category`, `sub_category`, `unit_price`, `cost_price`, `shelf_life_days`, `is_perishable`.  
  3. `suppliers`: `supplier_id` (PK), `supplier_name`, `lead_time_days`, `min_order_qty`, `order_cutoff_time`.  
  4. `inventory_snapshots`: `snapshot_date`, `store_id`, `sku_id`, `on_hand_units`, `reserved_units`, `batch_expiry_date`.  
  5. `daily_sales`: `sale_date`, `store_id`, `sku_id`, `units_sold`, `revenue`, `stockout_flag`.  
  6. `transfer_manifests`: `transfer_id`, `timestamp`, `from_store_id`, `to_store_id`, `sku_id`, `qty`, `status`.

### 2.2 The Deterministic Analytical Kernel (`src/analytics/kernel.py`)

This module is strictly mathematical and deterministic with zero LLM involvement.

- **Velocity Calculation:** $$\\text{Velocity}*{7d} \= \\frac{\\sum*{i=1}^{7} \\text{units\_sold}\_{t-i}}{7}$$  
- **Days of Inventory (DOI) / Runway:** $$\\text{DOI} \= \\frac{\\text{on\_hand\_units}}{\\max(\\text{Velocity}\_{7d}, 0.01)}$$  
- **Reorder Point (ROP) & Safety Stock (SS):** $$\\text{SS} \= Z \\times \\sigma\_{\\text{demand}} \\times \\sqrt{L}$$ $$\\text{ROP} \= (\\text{Velocity}\_{7d} \\times L) \+ \\text{SS}$$ *(where $L$ is supplier lead time in days, $Z=1.65$ for 95% service level)*  
- **Imminent Stockout Condition:** $$\\text{Is\_Stockout\_Alert} \\iff \\text{DOI} \\le L \+ \\text{SafetyBufferDays}$$  
- **Dead Stock Condition:** $$\\text{Is\_Dead\_Stock} \\iff (\\text{Units Sold in last 30 days} \== 0 \\land \\text{on\_hand} \> 0\) \\lor (\\text{DOI} \> 90)$$  
- **Velocity Anomaly Detection:** $$Z \= \\frac{\\text{UnitsSold}*{\\text{yesterday}} \- \\mu*{\\text{sales, 14d}}}{\\sigma\_{\\text{sales, 14d}}}$$ Flag if $|Z| \\ge 2.0$.

### 2.3 Inter-Store Inventory Arbitrage Engine (`src/analytics/rebalance.py`)

- For every SKU with an imminent stockout at `Store_Deficit`:  
  - Calculate surplus across peer stores: $$\\text{Surplus}(S\_i) \= \\max(0, \\text{on\_hand}(S\_i) \- (\\text{Velocity}\_{7d}(S\_i) \\times (L \+ 7)))$$  
  - If $\\text{Surplus}(S\_i) \\ge \\text{Deficit}$, calculate transfer feasibility:  
    - Intra-network courier transit: $0.5\\text{ days}$.  
    - Cost of transfer: Flat local rate vs. lost gross margin if stocked out.  
    - Output: Feasible transfer pairs with exact quantities and net savings.

### 2.4 The Gemini Neuro-Symbolic Agent Core (`src/agent/`)

- **Query Classification & Epistemic Gate (`epistemic.py`):**  
  - Parses incoming user prompt.  
  - Checks if the user is asking about: a) In-scope retail analytics (SKU performance, stockouts, overstock, store comparison). b) Out-of-scope / missing information (weather, footfall sensors, unrecorded suppliers, external macroeconomic conditions).  
  - If out-of-scope, halts execution and routes to the **Epistemic Refusal Engine**.  
- **Deterministic Tool Calling:**  
  - Tools available: `get_imminent_stockouts()`, `get_dead_stock()`, `get_sku_metrics(sku_id, store_id)`, `get_store_overview(store_id)`, `simulate_price_markdown(sku_id, discount_pct)`, `calculate_store_transfer(sku_id, to_store)`.  
  - Tool execution occurs purely in Python.  
- **Response Synthesis Prompting:**  
  - Feeds the raw, verified JSON output of the tools into `gemini-2.5-flash` with a system prompt enforcing the **Strict Citation Mandate**: *Never state any number that does not appear in the tool output. Always explain the assumptions and business reasoning behind every recommendation.*  
- **Numerical Verification Post-Processor:**  
  - A deterministic regex scanner extracts numbers from the LLM output and asserts that they exist in the underlying tool payload. If an unregistered number is detected, the post-processor flags or corrects it.

### 2.5 API & Serving Layer (`app.py`)

- Single FastAPI application mounted on port 8000\.  
- `FastAPI.lifespan` hook:  
  - Generates synthetic 90-day multi-store dataset if `retail_inventory.db` does not exist (\< 2.5 seconds).  
  - Compiles DuckDB views and pre-caches the Daily Morning Triage Matrix (\< 1.0 second).  
- Serves endpoints:  
  - `GET /` $\\rightarrow$ Serves pre-built HTML/JS/CSS dashboard.  
  - `POST /api/chat` $\\rightarrow$ Handles streaming or structured conversational requests.  
  - `GET /api/triage/today` $\\rightarrow$ Returns the daily 3x3 attention matrix.  
  - `POST /api/actions/transfer` $\\rightarrow$ Commits an inter-store transfer manifest.  
  - `POST /api/simulate` $\\rightarrow$ Evaluates what-if discount/reorder scenarios.

