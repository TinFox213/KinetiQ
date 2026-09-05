# Product Requirements Document (PRD)

## Project Name: KinetiQ — Retail Sales & Inventory Copilot

**Track ID:** PS03 (Nexus Tiq24 Hackathon)  
**Target Persona:** Multi-Store Retail Store Manager / Regional Inventory Supervisor  
**Execution Environment:** Python 3.11, Single Port (8000), Gemini API (LLM \+ Embeddings)

---

## 1\. Executive Summary & Problem Context

Small-to-midsize retail operations (3–5 stores, 200–500 SKUs spanning perishables, FMCG, and packaged goods) generate massive transaction logs, daily register tallies, and periodic stock-take spreadsheets. However, store managers operate under extreme time poverty: they spend the majority of their shift on the sales floor, resolving customer escalations, and directing store staff.

When operational decisions are made, they are hurried. Critical signals are buried across multi-tab CSV exports, disparate POS databases, and supplier invoices:

1. **Hidden Runways:** A SKU with 25 units in stock appears healthy on a snapshot report, but a sudden 7-day velocity surge to 10 units/day means stockout in 2.5 days—well inside a 4-day supplier delivery window.  
2. **Dead Capital Accumulation:** Non-moving inventory sits on prime shelving for 45+ days, silently incurring holding costs and causing cash-flow drag without alerting the manager.  
3. **Multi-Store Imbalance (The Arbitrage Blindspot):** Store 1 suffers stockouts while Store 3 (just 8 km away) holds 60 units of unmoving stock for the exact same item. Store managers reorder from suppliers at full cost rather than executing inter-store transfers.  
4. **Hallucination & Intuition Trap:** Generic AI tools invent numbers or offer vague advice ("consider ordering more"), while manual spreadsheet inspection takes hours.

### The KinetiQ Core Value Proposition

KinetiQ is a **Neuro-Symbolic Retail Copilot** that unifies deterministic inventory physics with conversational intelligence. It acts as an autonomous operational co-pilot that answers any natural-language query with **strict mathematical grounding** (every figure cited to deterministic calculation), generates a daily **3-Minute Morning Triage Queue** (stockouts, dead stock, velocity anomalies), recommends prescriptive actions with fully transparent assumptions, orchestrates **Inter-Store Inventory Arbitrage**, and enforces **Epistemic Refusal** whenever data is absent or insufficient.

---

## 2\. Product Objectives & Success Criteria

### 2.1 Objectives

- **Zero-Friction Morning Briefing:** Compress the store manager’s morning inventory analysis from 45 minutes of spreadsheet filtering down to a 3-minute glance at the prioritized Daily Action Queue.  
- **100% Grounded Intelligence:** Eliminate all LLM numerical fabrication. The LLM performs zero arithmetic; it only synthesizes verified data emitted by the deterministic analytics kernel.  
- **Inter-Store Arbitrage:** Prevent unnecessary supplier reorders by surfacing intra-network stock transfers between nearby stores.  
- **Disciplined Epistemic Boundaries:** Transparently decline or request clarification on questions that cannot be resolved from the loaded data (e.g., footfall, competitor pricing, unrecorded stores, missing supplier SLAs).  
- **Single-Command Hackathon Turnkey:** Deployable with `pip install -r requirements.txt && python app.py` on port 8000 in under 90 seconds.

### 2.2 Quantitative Target Metrics

- **Startup Latency:** \< 20 seconds from cold boot to healthy HTTP 200 on port 8000 (well within 90s hackathon limit).  
- **Query Response Latency:** \< 3.5 seconds end-to-end for complex analytical questions (well within 60s hackathon limit).  
- **Numerical Fidelity:** 100% match between emitted response numbers and SQLite/DuckDB ground truth.  
- **Refusal Precision:** 100% disciplined refusal rate on unanswerable out-of-domain queries.

---

## 3\. User Personas & User Journeys

### 3.1 Primary Persona: "Rajesh", Multi-Store Manager

- **Context:** Manages 3 physical convenience/grocery stores in an urban cluster.  
- **Pain Points:** Arrives at 7:30 AM before store opening. Has 15 minutes to review yesterday's sales, decide what purchase orders to place with FMCG distributors, and plan shelf restocking.  
- **Mental Model:** Needs direct, actionable answers: *"What do I need to order right now before the distributor deadline at 9:00 AM?"* and *"Why did sales drop yesterday in Store 2?"*

### 3.2 User Journey

1. **07:30 AM — Triage Inspection:** Rajesh opens `http://localhost:8000`. The **Daily Action Queue** is pre-calculated:  
   - 2 Imminent Stockouts flagged (one eligible for local store transfer).  
   - 1 Critical Dead-Stock SKU (suggested markdown bundle).  
   - 1 Negative Sales Velocity Spike (suspected stockout or barcode issue).  
2. **07:33 AM — Plain Language Exploration:** Rajesh types: *"What's running out at Store 1 this week?"*  
   - KinetiQ returns a grounded table with current on-hand, 7-day average velocity, projected days of inventory (DOI), supplier lead time, and exact reorder recommendation.  
3. **07:35 AM — Action Execution:** For the imminent stockout of Organic A2 Milk, Rajesh clicks **"Generate Inter-Store Transfer Manifest"**, transferring 15 units from Store 3 (where velocity is near zero) instead of paying expedited distributor fees.  
4. **07:37 AM — Edge Case Query:** Rajesh asks: *"Did footfall decrease yesterday because of the rain?"*  
   - KinetiQ responds: *"Our system tracks POS transaction timestamps, units sold, and stock balances across Stores 1–3, but does not capture customer footfall counters or external weather conditions. Based purely on transaction records, Store 1 processed 142 transactions yesterday (-18% vs 7-day average)."*

---

## 4\. Functional Requirements (FR)

### FR-1: Natural Language Query & Deterministic Grounding

- **FR-1.1:** Support free-form natural language questions regarding stock levels, sales history, SKU performance, comparisons across stores, and supplier terms.  
- **FR-1.2:** Enforce the **Zero-Math LLM Rule**: The LLM prompt must never ask the model to divide, multiply, or project numbers. All calculations (rolling averages, runway days, Z-scores, margins) are executed deterministically in Python/SQL and passed as structured JSON context.  
- **FR-1.3:** Every claim in the LLM response must quote the exact figure and source data point (e.g., *"Store 1 has 14 units remaining with an average consumption of 4.2 units/day, giving a 3.3-day runway"*).

### FR-2: Daily Morning Triage (The 3x3 Attention Matrix)

- **FR-2.1: Imminent Stock-Out Predictor:** Flag all SKUs where $\\text{Days of Inventory (DOI)} \\le \\text{Supplier Lead Time} \+ \\text{Safety Stock Buffer}$.  
- **FR-2.2: Stagnant & Dead Capital Identifier:** Flag all SKUs where on-hand inventory has had zero sales for $\\ge 30$ consecutive days or where DOI exceeds 90 days.  
- **FR-2.3: Demand Velocity Anomalies:** Detect statistically significant velocity shifts ($|Z\\text{-score}| \\ge 2.0$ over rolling 14-day window).

### FR-3: Prescriptive Recommendations & Assumption Ledger

- **FR-3.1:** For every flagged alert, the copilot must recommend an operational action:  
  - **Supplier Reorder:** Calculated via Economic Order Quantity (EOQ) or Target Par Level.  
  - **Inter-Store Transfer:** When another network store has excess DOI (\> 30 days).  
  - **Dynamic Clearance / Markdown:** For dead stock or near-expiry perishables.  
  - **Shelf Audit:** When sales unexpectedly collapse to zero despite non-zero inventory.  
- **FR-3.2:** Provide a transparent **Assumption Ledger** stating: lead time used (days), unit cost, holding cost percentage, target service level, and average daily consumption.

### FR-4: Inter-Store Inventory Arbitrage Engine

- **FR-4.1:** When an imminent stockout is detected at Store $A$, scan Stores $B, C, \\dots$ for surplus inventory ($\\text{DOI} \> 30\\text{ days}$ and stock $\> \\text{Safety Stock}$).  
- **FR-4.2:** Compute net transfer feasibility taking into account transit delay (e.g., 0.5 days local courier) vs. supplier lead time (3–7 days).  
- **FR-4.3:** Output a formatted, downloadable/printable **Stock Transfer Note (STN)** with source, destination, SKU, quantity, and batch number.

### FR-5: Epistemic Refusal & Honesty Guardrail

- **FR-5.1:** If a user query refers to non-existent SKUs, non-existent stores, future unmodelled external events, or metrics not present in the database (e.g., customer demographics, footfall, wholesale prices not recorded), the system must explicitly decline to speculate.  
- **FR-5.2:** Refusal output must state:  
  1. What was asked.  
  2. Exactly what data is absent.  
  3. What related data *is* available in the system.

### FR-6: Interactive "What-If" Simulation Sandbox

- **FR-6.1:** Allow store managers to test operational interventions (e.g., *"What happens to our inventory runway if we run a 15% discount on Greek Yogurt at Store 2?"*).  
- **FR-6.2:** Execute a deterministic price-elasticity calculation and display projected demand lift, updated run-out date, and revenue/margin impact.

---

## 5\. Non-Functional Requirements (NFR)

- **NFR-1 (Runtime Stack):** Pure Python 3.11 backend. Embedded web server using FastAPI / Uvicorn.  
- **NFR-2 (Single Command Bootstrap):** The entire system (data seeding, database initialization, analytical precomputation, API server, and web frontend) must start via:  
    
  pip install \-r requirements.txt  
    
  python app.py  
    
- **NFR-3 (Startup Time):** Boot up and serve HTTP 200 at `http://localhost:8000` in $\\le 30$ seconds on standard hardware.  
- **NFR-4 (Gemini Compliance):** Strictly use Google Gemini (`gemini-2.5-flash` or `gemini-1.5-flash` via `google-genai` / `google-generativeai` SDK) using the `GEMINI_API_KEY` environment variable. Embeddings via `text-embedding-004` or `gemini-embedding-001`.  
- **NFR-5 (Network Isolation):** Zero calls to any third-party external services or vector DB clouds (no Pinecone, no Weaviate, no OpenAI). Storage is 100% local (SQLite / DuckDB / NumPy).  
- **NFR-6 (Repository Structure):** Must comply with Nexus Tiq24 requirements:  
  - Line 1 of README.md: `TRACK_ID=PS03`  
  - Root contains `app.py`, `requirements.txt`, `README.md`, `src/`, `data/`, `frontend/dist/`.

