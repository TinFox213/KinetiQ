# KinetiQ: Master Test Suite & Verification Matrix (102 Detailed Test Cases)

## Retail Sales & Inventory Copilot (TRACK\_ID=PS03)

**Execution Framework:** Pytest 8.x, SQLite/DuckDB In-Memory Engine, FastAPI TestClient, Gemini Evaluation Harness  
**Target Platform:** Python 3.11, Ubuntu 22.04 / Debian 12, Clean Machine Standard

---

## 1\. Test Suite Architecture & Verification Taxonomy

This document specifies **102 exhaustive test cases** covering every functional requirement, edge case, mathematical invariant, epistemic guardrail, and end-to-end user journey for the KinetiQ Retail Sales and Inventory Copilot.

### Test Categories Overview

- **Category A (TC-001 to TC-012):** Data Engineering & Synthetic Ground-Truth Integrity (12 Test Cases)  
- **Category B (TC-013 to TC-024):** High-Performance Deterministic Analytical Kernel (12 Test Cases)  
- **Category C (TC-025 to TC-036):** Inventory Physics Engine & Stockout Forecasting (12 Test Cases)  
- **Category D (TC-037 to TC-048):** Demand Anomaly Detection & Dead Capital Classifier (12 Test Cases)  
- **Category E (TC-049 to TC-060):** Inter-Store Inventory Arbitrage & Rebalancing Matrix (12 Test Cases)  
- **Category F (TC-061 to TC-072):** Gemini Neuro-Symbolic Agent & Numerical Grounding (12 Test Cases)  
- **Category G (TC-073 to TC-084):** Epistemic Refusal & Boundary Enforcement (12 Test Cases)  
- **Category H (TC-085 to TC-094):** Interactive What-If Simulation Sandbox (10 Test Cases)  
- **Category I (TC-095 to TC-104):** Unified FastAPI Backend & Non-Functional Requirements (10 Test Cases)  
- **Category J (TC-105 to TC-110):** Master End-to-End Workflow & Turnkey Validation (6 Test Cases)

---

## Summary of All 102 Detailed Test Cases

### Category A: Data Engineering & Synthetic Ground-Truth Integrity

- **TC-001:** Relational Schema DDL & Table Integrity (stores, suppliers, products, inventory\_snapshots, daily\_sales, store\_transfers).  
- **TC-002:** Synthetic Data Generator Execution Performance (\< 3.0s for 90 days across 3 stores and 250 SKUs).  
- **TC-003:** Store Entity Representation & Geographic Distance Matrix.  
- **TC-004:** Product Catalog Breadth & Perishable vs. Non-Perishable Flagging.  
- **TC-005:** Supplier Association & Lead Time Reality Check (2 to 7 days).  
- **TC-006:** Daily Sales Record Count & Temporal Continuity (67,500 daily sales records).  
- **TC-007:** Inventory Stock Conservation Equation Verification (Stock\_t \>= max(0, Stock\_{t-1} \- Sales\_t)).  
- **TC-008:** Stockout Event Truncation & Flag Consistency (had\_stockout \= 1 iff stock \= 0).  
- **TC-009:** Dead Stock Seeding Invariant Check (SKU\_1061-1075 zero sales for 35+ days).  
- **TC-010:** High-Velocity Demand Spike Seeding Check (sales \>= 3x baseline on T-1).  
- **TC-011:** Multi-Store Arbitrage Setup Validation (Store 1 deficit with Store 3 surplus).  
- **TC-012:** Database Re-initialization Idempotency without duplicate key corruption.

### Category B: High-Performance Deterministic Analytical Kernel

- **TC-013:** 7-Day Rolling Velocity Computation Accuracy vs. manual average.  
- **TC-014:** Unconstrained Sales Velocity during Stockout Days (normalizing for active days).  
- **TC-015:** 30-Day Total Revenue & Gross Profit Calculation.  
- **TC-016:** Zero Division Safeguard for Completely New / Inactive Products.  
- **TC-017:** Multi-Store Comparison Aggregation across Stores 1, 2, and 3\.  
- **TC-018:** Category-Level Rollup Integrity (category sum equals SKU sum).  
- **TC-019:** Store Overview Executive KPI Rollup (revenue, profit, margin %).  
- **TC-020:** Demand Variance (Sigma) Calculation for Safety Stock.  
- **TC-021:** Non-Existent SKU Handling in Kernel (returns None cleanly).  
- **TC-022:** Non-Existent Store ID Handling in Kernel.  
- **TC-023:** Historical Lookback Date Boundary Accuracy.  
- **TC-024:** High-Concurrency In-Memory Query Benchmark (50 queries in \< 500ms).

### Category C: Inventory Physics Engine & Stockout Forecasting

- **TC-025:** Days of Inventory (DOI) Calculation with Non-Zero Velocity (On-Hand / Velocity).  
- **TC-026:** DOI Calculation with Zero Inventory (Immediate Stockout, DOI \= 0.0).  
- **TC-027:** DOI Calculation with Zero Velocity (Infinite Runway, DOI \= 999.0 sentinel).  
- **TC-028:** Safety Stock (SS) Calculation at 95% Service Level (Z=1.645).  
- **TC-029:** Reorder Point (ROP) Invariant Verification (ROP \= Velocity \* L \+ SS).  
- **TC-030:** Imminent Stockout Classification (Critical vs Warning vs Healthy).  
- **TC-031:** Exact Calendar Stockout Date Forecasting (Current Date \+ floor(DOI)).  
- **TC-032:** Recommended Order Quantity (Target Max Par Level Formulation).  
- **TC-033:** Perishable Expiry vs. Stockout Race Condition.  
- **TC-034:** Full Store Stockout Scanner sorted by DOI ascending.  
- **TC-035:** Negative Stock Calibration (clamped to 0 with audit warning).  
- **TC-036:** Complete Assumptions Ledger Transparency (lead time, velocity window, buffer).

### Category D: Demand Anomaly Detection & Dead Capital Classifier

- **TC-037:** Z-Score Demand Spike Detection (Z \>= \+2.5).  
- **TC-038:** Z-Score Demand Drop Detection (Z \<= \-2.0).  
- **TC-039:** Low Baseline Variance Safeguard (Standard deviation denominator \>= 0.5).  
- **TC-040:** Phantom Inventory / Zero-Sales Anomaly Detection.  
- **TC-041:** Dead Stock 30-Day Idle Identification (units\_sold\_30d \= 0).  
- **TC-042:** Dead Capital Dollar Valuation Accuracy (On-Hand \* Cost Price).  
- **TC-043:** Monthly Inventory Holding Cost Drag Calculation (24% annual / 2% monthly).  
- **TC-044:** Prescriptive Dynamic Markdown Tiering (20% for DOI 30-60, 35% for DOI \> 60).  
- **TC-045:** Fast-Moving Companion Bundling Recommendation.  
- **TC-046:** Store-Wide Dead Capital Aggregation.  
- **TC-047:** False Positive Suppression on Low-Volume SKUs (baseline \< 2.0).  
- **TC-048:** Anomaly Engine Execution Speed Benchmark (\< 150ms for 250 SKUs).

### Category E: Inter-Store Inventory Arbitrage & Rebalancing Matrix

- **TC-049:** Stockout Deficit Quantification at Target Store.  
- **TC-050:** Safe Surplus Calculation at Source Store (protecting donor store's reserve).  
- **TC-051:** Donor Store Depletion Protection Invariant (never transfer \> safe surplus).  
- **TC-052:** Inter-Store Courier Cost vs. Gross Margin Trade-off (only positive net benefit).  
- **TC-053:** Stock Transfer Note (STN) Manifest Data Schema.  
- **TC-054:** Multi-Donor Tie-Breaking Logic (distance ASC, surplus DESC).  
- **TC-055:** Fallback to Distributor PO when No Surplus Exists.  
- **TC-056:** Circular / Ping-Pong Transfer Prevention (7-day transfer cooldown).  
- **TC-057:** Distance Matrix Feasibility Filter (\<= 50km local radius).  
- **TC-058:** In-Transit Stock Accounting (effective runway accounts for incoming stock).  
- **TC-059:** Database Transaction Commit for Transfer Creation.  
- **TC-060:** Arbitrage Engine Execution Latency Benchmark (\< 250ms).

### Category F: Gemini Neuro-Symbolic Agent & Numerical Grounding

- **TC-061:** Tool Dispatching & Intent Mapping Accuracy (what is running out \-\> get\_stockouts).  
- **TC-062:** Dead Stock Query Intent Mapping (unmoving stock \-\> get\_dead\_stock).  
- **TC-063:** Single-Product Monthly Performance Intent Mapping (how did X do \-\> get\_sku\_performance).  
- **TC-064:** Strict Zero-Math Invariant (No LLM Calculation; routing to kernel).  
- **TC-065:** Exact Numerical Fidelity Regex Verification (100% quoted numbers match tool JSON).  
- **TC-066:** Multi-SKU Comparative Analysis Synthesis.  
- **TC-067:** Recommendation Assumption Transparency (explicit assumptions section).  
- **TC-068:** Arbitrage Suggestion Integration in Plain Language before distributor reorder.  
- **TC-069:** Prompt Injection & System Jailbreak Resistance.  
- **TC-070:** Markdown Table Formatting Consistency.  
- **TC-071:** End-to-End LLM Latency SLA (\< 4.0s).  
- **TC-072:** Offline Fallback when GEMINI\_API\_KEY is Unset.

### Category G: Epistemic Refusal & Boundary Enforcement

- **TC-073:** Footfall Sensor Data Refusal.  
- **TC-074:** Weather & Climate Data Refusal.  
- **TC-075:** Competitor Pricing & Market Share Refusal.  
- **TC-076:** Customer Demographics & Age Profile Refusal.  
- **TC-077:** Wholesale Commodity Market Speculation Refusal.  
- **TC-078:** Future Macroeconomic Inflation Prediction Refusal.  
- **TC-079:** Non-Existent Product Catalog Search Refusal.  
- **TC-080:** Non-Existent Store Location Refusal.  
- **TC-081:** Unrecorded Supplier SLA Refusal.  
- **TC-082:** Partial Information Graceful Refusal Protocol (answer feasible, refuse unrecorded).  
- **TC-083:** Tone and Structure Verification for Refusals (consistent 2-part format).  
- **TC-084:** Zero Hallucination during Forced Extrapolation.

### Category H: Interactive What-If Simulation Sandbox

- **TC-085:** Negative Price Elasticity Application (Delta V% \= Delta P% \* Elasticity).  
- **TC-086:** Projected Days to Clear Inventory Calculation (On-Hand / New Velocity).  
- **TC-087:** Gross Profit Delta Calculation Under Promotion.  
- **TC-088:** Zero Discount (Identity) Boundary Test.  
- **TC-089:** 100% Clearance Giveaway Boundary Test.  
- **TC-090:** Price Increase / Negative Discount Test.  
- **TC-091:** Stockout During Promotion Horizon (capped at on-hand stock).  
- **TC-092:** Category-Specific Elasticity Variation (perishable vs staple).  
- **TC-093:** Simulator Input Validation (-50% to 100%).  
- **TC-094:** Simulator Execution Speed Benchmark (\< 5ms per simulation).

### Category I: Unified FastAPI Backend & Non-Functional Requirements

- **TC-095:** Cold Boot Startup Time Verification (\< 10s vs. 90s hackathon limit).  
- **TC-096:** Port 8000 Single-Port Binding Verification.  
- **TC-097:** /api/health Endpoint Specification Check (200 OK, track\_id: PS03).  
- **TC-098:** /api/triage/today JSON Schema Validation.  
- **TC-099:** /api/chat POST Request Handling.  
- **TC-100:** Static Asset Mime-Type & Caching Headers.  
- **TC-101:** Concurrent API Load Resilience (50 simultaneous requests without database locking).  
- **TC-102:** Single Request Timeout Enforcement (\< 60s).  
- **TC-103:** Malformed JSON Request Handling (HTTP 422 Unprocessable Entity).  
- **TC-104:** Network Isolation Verification (Zero outbound calls except Google Gemini).

### Category J: Master End-to-End Workflow & Turnkey Validation

- **TC-105:** E2E Scenario 1 — Morning Triage to Inter-Store Arbitrage Execution.  
- **TC-106:** E2E Scenario 2 — Conversational Grounded Query with Exact Citations.  
- **TC-107:** E2E Scenario 3 — Dead Capital Detection to What-If Clearance Simulation.  
- **TC-108:** E2E Scenario 4 — Phantom Inventory Flag to Shelf Audit Directive.  
- **TC-109:** E2E Scenario 5 — Complex Hybrid Query with Disciplined Refusal.  
- **TC-110:** E2E Scenario 6 — Clean Machine Turnkey Startup & Evaluation Script.

---

*(Full 1,135-line comprehensive specification with complete setup fixtures, step-by-step code payloads, and remediation code blocks is cataloged in the master testing document).*  
