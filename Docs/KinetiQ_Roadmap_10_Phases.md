# Phase-by-Phase Building Roadmap for AI Engineering (10 Phases)

## Project Name: KinetiQ — Retail Sales & Inventory Copilot

**Track ID:** PS03  
**Target Tooling:** Google Antigravity / Cursor / Claude Code  
**Duration:** Designed for rapid, high-integrity implementation within a 24-Hour Hackathon window

---

## Master 10-Phase Roadmap Summary

\+----------------------------------------------------------------------------------------------------+

|  Phase 01: Domain Data Engineering, Synthetic Data Generator & SQLite/DuckDB Schema                |

|  Phase 02: High-Performance Deterministic Analytical Kernel (Math & SQL Engine)                     |

|  Phase 03: Inventory Physics Engine (Runways, Days of Inventory, ROP, Stockout Predictor)          |

|  Phase 04: Demand Anomaly Detection & Dead Capital Classifier                                      |

|  Phase 05: Multi-Store Inventory Arbitrage & Peer Rebalancing Optimizer                            |

|  Phase 06: Gemini Neuro-Symbolic Agent Core & Epistemic Refusal Engine                             |

|  Phase 07: Daily 3-Minute Cockpit (Morning Action Queue & What-If Simulator)                       |

|  Phase 08: Unified Python Backend (FastAPI, Single Port 8000, 90s Startup Bootstrap)               |

|  Phase 09: Single-Command Front-End & Executive UI Dashboard (Tailwind/Charts.js)                  |

|  Phase 10: Hackathon Hardening, 24-Hr Commit Cadence, Benchmark Testing & Demo Script              |

\+----------------------------------------------------------------------------------------------------+

---

## Detailed Phase Breakdown & Antigravity Directives

### Phase 01: Domain Data Engineering & Schema Definition

- **Duration:** Hour 0 – 2 (Hackathon T+0 to T+2)  
- **Primary Focus:** Build the multi-store retail dataset generator. Real retail demands messy reality: stockouts, seasonal shifts, dead stock, perishables, and varying store profiles.  
- **Key Deliverables:**  
  - `src/data/schema.sql`: DDL for 6 core tables.  
  - `src/data/generator.py`: Generates 3 stores, 250 SKUs, 90 days of transactions (150,000 records) in \< 3s.  
  - Verification test: Zero missing values in primary keys; realistic normal/poisson distributions for sales.

### Phase 02: High-Performance Deterministic Analytical Kernel

- **Duration:** Hour 2 – 4 (Hackathon T+2 to T+4)  
- **Primary Focus:** Build the zero-math foundation. All numerical calculations must live in pure Python/SQL functions.  
- **Key Deliverables:**  
  - `src/analytics/kernel.py`: SQL aggregates, rolling window calculations (7d, 14d, 30d), revenue and margin calculators.  
  - Unit tests validating that SQL metrics match ground-truth math exactly.

### Phase 03: Inventory Physics Engine

- **Duration:** Hour 4 – 6 (Hackathon T+4 to T+6)  
- **Primary Focus:** Implement supply chain equations: Days of Inventory (DOI), Stockout Date Forecast, Safety Stock, Reorder Point (ROP).  
- **Key Deliverables:**  
  - `src/analytics/inventory_physics.py`:  
    - `calculate_doi(on_hand, velocity_7d)`  
    - `calculate_stockout_date(on_hand, velocity_7d)`  
    - `calculate_rop(velocity, lead_time, service_level_z, std_dev)`  
  - Edge cases handled: zero sales velocity (avoid div by zero), negative adjustments, batch expiries.

### Phase 04: Demand Anomaly Detection & Dead Capital Classifier

- **Duration:** Hour 6 – 8 (Hackathon T+6 to T+8)  
- **Primary Focus:** Automatically flag what needs attention today.  
- **Key Deliverables:**  
  - `src/analytics/anomalies.py`:  
    - Z-score anomaly detector for sudden sales spikes or drops.  
    - Zero-sales anomaly detector (detecting potential phantom inventory).  
    - Dead capital classifier: flags items with \>30 days without sale or \>90 days DOI, computing locked capital ($).

### Phase 05: Multi-Store Inventory Arbitrage Engine

- **Duration:** Hour 8 – 10 (Hackathon T+8 to T+10)  
- **Primary Focus:** The killer unique feature of KinetiQ. Cross-store rebalancing matching surplus stores with deficit stores.  
- **Key Deliverables:**  
  - `src/analytics/rebalance.py`:  
    - Multi-store matrix solver.  
    - Generates actionable Stock Transfer Notes (STNs) with transit delays and net financial savings.

### Phase 06: Gemini Neuro-Symbolic Agent Core & Epistemic Refusal

- **Duration:** Hour 10 – 13 (Hackathon T+10 to T+13)  
- **Primary Focus:** Integrate Google Gemini (`gemini-2.5-flash`) via the official SDK, implementing strict tool calling, citation enforcement, and disciplined refusal.  
- **Key Deliverables:**  
  - `src/agent/copilot.py`: Gemini client initialization with `GEMINI_API_KEY`.  
  - `src/agent/epistemic.py`: Boundary classifier that cleanly rejects out-of-domain queries without guessing.  
  - Grounded prompt templates with numerical citation verification.

### Phase 07: Daily 3-Minute Cockpit & What-If Simulator

- **Duration:** Hour 13 – 15 (Hackathon T+13 to T+15)  
- **Primary Focus:** The store manager's operational command center: pre-aggregated daily triage API and interactive scenario modeling.  
- **Key Deliverables:**  
  - `src/analytics/triage.py`: Prepares the 3x3 Daily Action Queue.  
  - `src/analytics/simulator.py`: What-If price elasticity and promotion impact simulator.

### Phase 08: Unified Python Backend (FastAPI on Port 8000\)

- **Duration:** Hour 15 – 17 (Hackathon T+15 to T+17)  
- **Primary Focus:** Packaging everything into `app.py` meeting the strict hackathon one-command execution rule.  
- **Key Deliverables:**  
  - `app.py`: FastAPI server mounted at `http://localhost:8000`.  
  - `requirements.txt`: Minimal, robust dependencies (fastapi, uvicorn, pydantic, google-genai, duckdb, pandas, numpy).  
  - Startup bootstrap in `< 10s` (well within 90s limit).

### Phase 09: Single-Command Front-End & Executive UI

- **Duration:** Hour 17 – 20 (Hackathon T+17 to T+20)  
- **Primary Focus:** Clean, responsive, dark/light modern UI served directly by the Python backend without a second terminal.  
- **Key Deliverables:**  
  - `frontend/dist/index.html`, `styles.css`, `app.js`:  
    - Morning Triage Action Queue cards with 1-click actions.  
    - Conversational chat interface with streaming grounded citations.  
    - Interactive What-If simulation slider.  
    - Inter-Store Transfer manifest viewer.

### Phase 10: Hackathon Hardening, Benchmark Testing & Demo

- **Duration:** Hour 20 – 24 (Hackathon T+20 to T+24)  
- **Primary Focus:** End-to-end stress testing, edge-case validation, 24-hr commit timeline staging, demo video script, and README preparation.  
- **Key Deliverables:**  
  - `README.md` with required first line: `TRACK_ID=PS03`.  
  - Automated test suite (`pytest tests/`) validating all normal and difficult cases.  
  - 2–3 minute winning demo video walk-through script.

