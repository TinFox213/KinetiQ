# KinetiQ: Testing Instructions & Execution Guide

## Comprehensive Quality Assurance & Verification Playbook

**Track ID:** PS03 | **Product:** Retail Sales & Inventory Copilot  
**Tools Supported:** Pytest, HTTPie/cURL, Playwright/Headless Chromium, Google Antigravity, Cursor

---

## 1\. Executive Summary & Verification Strategy

KinetiQ employs a **tri-layer verification pyramid** designed to guarantee zero mathematical hallucinations and flawless operational execution during hackathon evaluation:

1. **Layer 1: Deterministic Unit & Mathematical Invariant Tests (80% of test suite)**  
   Executed entirely in pure Python and SQLite in-memory mode. Validates equations for rolling velocity, Days of Inventory (DOI), Safety Stock, Reorder Points (ROP), Z-score demand anomalies, and multi-store inventory arbitrage without making any external API calls. Runs in $\< 2.5\\text{ seconds}$.  
2. **Layer 2: Fast Integration & API Contracts (15% of test suite)**  
   Validates FastAPI routes (`/api/health`, `/api/triage/today`, `/api/chat`, `/api/actions/transfer`, `/api/simulate`), lifespan database seeding, static asset delivery, and error handling. Runs in $\< 3.0\\text{ seconds}$.  
3. **Layer 3: Gemini Grounding & End-to-End Workflow Harness (5% of test suite)**  
   Tests conversational intelligence, tool dispatching, exact numerical regex citation verification, and disciplined epistemic refusals. Supports both live Gemini calls (`GEMINI_API_KEY`) and offline deterministic mock evaluation.

---

## 2\. Directory Structure for Test Artifacts

Organize your test repository cleanly under `tests/`:

your-project/

├── app.py

├── requirements.txt

├── README.md

├── src/

│   ├── data/

│   │   ├── generator.py

│   │   └── schema.sql

│   ├── analytics/

│   │   ├── kernel.py

│   │   ├── inventory\_physics.py

│   │   ├── anomalies.py

│   │   ├── rebalance.py

│   │   ├── triage.py

│   │   └── simulator.py

│   └── agent/

│       ├── copilot.py

│       └── epistemic.py

├── tests/

│   ├── \_\_init\_\_.py

│   ├── conftest.py                   \# Shared fixtures, in-memory DB, mock Gemini

│   ├── unit/

│   │   ├── test\_data\_integrity.py    \# Tests Category A (TC-001 to TC-012)

│   │   ├── test\_kernel\_math.py       \# Tests Category B (TC-013 to TC-024)

│   │   ├── test\_inventory\_physics.py \# Tests Category C (TC-025 to TC-036)

│   │   ├── test\_anomalies.py         \# Tests Category D (TC-037 to TC-048)

│   │   ├── test\_arbitrage.py         \# Tests Category E (TC-049 to TC-060)

│   │   └── test\_simulator.py         \# Tests Category H (TC-085 to TC-094)

│   ├── integration/

│   │   ├── test\_api\_routes.py        \# Tests Category I (TC-095 to TC-104)

│   │   └── test\_agent\_grounding.py   \# Tests Categories F & G (TC-061 to TC-084)

│   └── e2e/

│       └── test\_master\_workflows.py  \# Tests Category J (TC-105 to TC-110)

└── docs/

    ├── master\_test\_suite\_100\_testcases.md

    └── testing\_instructions\_and\_execution\_guide.md

---

## 3\. Environment Setup & Prerequisites

### 3.1 Python 3.11 Clean Environment

To guarantee that your test environment matches the judge's clean-machine standard:

\# 1\. Ensure Python 3.11 is active

python3 \--version

\# Expected output: Python 3.11.x

\# 2\. Create and activate a pristine virtual environment

python3.11 \-m venv venv\_test

source venv\_test/bin/activate

\# 3\. Upgrade pip and install all runtime and test dependencies

pip install \--upgrade pip

pip install \-r requirements.txt

pip install pytest pytest-asyncio pytest-cov httpx

### 3.2 Environment Variables

Set your Gemini API key for live model evaluation:

export GEMINI\_API\_KEY="AIzaSyYourActualKeyHere"

*(Note: If `GEMINI_API_KEY` is omitted, the test suite automatically runs against local deterministic template mocks).*

---

## 4\. Pytest Fixture Configuration (`tests/conftest.py`)

Create `tests/conftest.py` to provide standardized, isolated fixtures for all test runs:

import os

import pytest

import sqlite3

from fastapi.testclient import TestClient

from app import app

from src.data.generator import generate\_retail\_dataset

from src.analytics.kernel import AnalyticsKernel

from src.analytics.rebalance import ArbitrageEngine

TEST\_DB\_PATH \= "data/test\_retail\_inventory.db"

@pytest.fixture(scope="session")

def test\_db():

    """Generates a fast synthetic test database once per session."""

    os.makedirs("data", exist\_ok=True)

    if os.path.exists(TEST\_DB\_PATH):

        os.remove(TEST\_DB\_PATH)

    generate\_retail\_dataset(TEST\_DB\_PATH, days=90)

    yield TEST\_DB\_PATH

    if os.path.exists(TEST\_DB\_PATH):

        os.remove(TEST\_DB\_PATH)

@pytest.fixture

def kernel(test\_db):

    """Provides an initialized AnalyticsKernel instance."""

    return AnalyticsKernel(test\_db)

@pytest.fixture

def arbitrage\_engine(test\_db):

    """Provides an initialized ArbitrageEngine instance."""

    return ArbitrageEngine(test\_db)

@pytest.fixture

def api\_client(test\_db):

    """Provides a FastAPI TestClient bound to the test database."""

    app.state.kernel \= AnalyticsKernel(test\_db)

    app.state.rebalance \= ArbitrageEngine(test\_db)

    client \= TestClient(app)

    return client

---

## 5\. Step-by-Step Test Execution Instructions

### 5.1 Run the Full Test Suite (All 102 Test Cases)

Execute all test cases with verbose output and summary reporting:

pytest tests/ \-v \--tb=short

### 5.2 Run with Code Coverage Measurement

Verify that test coverage exceeds 90% across all core analytical and data modules:

pytest tests/ \--cov=src \--cov-report=term-missing \--cov-report=html

### 5.3 Run by Category / Module Subsets

Target specific subsystems during active development:

\# 1\. Run only Data & Schema tests (TC-001 to TC-012)

pytest tests/unit/test\_data\_integrity.py \-v

\# 2\. Run only Mathematical Kernel tests (TC-013 to TC-024)

pytest tests/unit/test\_kernel\_math.py \-v

\# 3\. Run only Inventory Physics & Stockout tests (TC-025 to TC-036)

pytest tests/unit/test\_inventory\_physics.py \-v

\# 4\. Run only Anomalies & Dead Stock tests (TC-037 to TC-048)

pytest tests/unit/test\_anomalies.py \-v

\# 5\. Run only Inter-Store Arbitrage tests (TC-049 to TC-060)

pytest tests/unit/test\_arbitrage.py \-v

\# 6\. Run only Grounding & Epistemic Refusal tests (TC-061 to TC-084)

pytest tests/integration/test\_agent\_grounding.py \-v

\# 7\. Run only FastAPI routes and performance tests (TC-095 to TC-104)

pytest tests/integration/test\_api\_routes.py \-v

\# 8\. Run Master End-to-End Workflow tests (TC-105 to TC-110)

pytest tests/e2e/test\_master\_workflows.py \-v

---

## 6\. How to Run the Automated End-to-End Workflow Test

The end-to-end test (`tests/e2e/test_master_workflows.py`) simulates the complete store manager lifecycle and verifies system stability from initial cold start to operational decision execution:

\# Execute master E2E test

pytest tests/e2e/test\_master\_workflows.py \-s \-v

### What This Test Verifies Live:

1. **Cold Boot Bootstrapping:** Validates that `app.py` boots from an empty folder, generates all tables and seed records in under 3 seconds, and starts listening on port 8000\.  
2. **Morning Triage Aggregation:** Verifies that `/api/triage/today` emits prioritized stockouts, dead capital, and velocity anomalies with non-null metrics.  
3. **Inter-Store Transfer Execution:** Triggers an inter-store transfer for Organic A2 Milk from Store 3 to Store 1, verifies that the transfer record is written to `store_transfers`, and asserts that stock balances reflect the in-transit allocation.  
4. **Conversational Grounding Check:** Fires natural language queries to `/api/chat` and programmatically validates that every number in the LLM response matches the underlying SQL database.  
5. **Epistemic Refusal Check:** Sends queries regarding unrecorded customer footfall and weather, verifying that the model produces structured refusals without guessing.

---

## 7\. Error Diagnosis & Remediation Playbook

When a test fails, consult this diagnostic matrix for immediate code fixes:

### Issue 1: `ZeroDivisionError` in Rolling Velocity or DOI

- **Symptom:** TC-016 or TC-027 fails with `ZeroDivisionError: float division by zero`.  
- **Root Cause:** SKU had 0 units sold over the rolling window, or inventory snapshot recorded 0 on hand.  
- **Fix:** In `src/analytics/kernel.py` and `inventory_physics.py`, protect denominators:  
    
  def calculate\_doi(on\_hand: int, velocity: float) \-\> float:  
    
      if on\_hand \<= 0:  
    
          return 0.0  
    
      if velocity \<= 0.0:  
    
          return 999.0  \# Sentinel representing dormant / infinite runway  
    
      return round(on\_hand / velocity, 2\)

### Issue 2: Flaky Z-Score Demand Spike Alerts on Low-Volume SKUs

- **Symptom:** TC-047 fails with false-positive anomaly alerts for items selling 1 unit every 3 days.  
- **Root Cause:** When baseline sales standard deviation is close to zero ($\\sigma \< 0.2$), a single sale creates an artificially inflated Z-score ($Z \> 5.0$).  
- **Fix:** Clamp the standard deviation denominator to a minimum threshold and ignore low-volume baselines:  
    
  def calculate\_z\_score(observed\_sales: float, baseline\_mean: float, baseline\_std: float) \-\> float:  
    
      if baseline\_mean \< 2.0:  
    
          return 0.0  \# Suppress anomaly detection on very low volume items  
    
      effective\_std \= max(baseline\_std, 0.5)  
    
      return (observed\_sales \- baseline\_mean) / effective\_std

### Issue 3: Arbitrage Engine Depleting Donor Store Reserve

- **Symptom:** TC-051 fails because the recommended transfer leaves Store 3 with fewer units than its own safety stock.  
- **Root Cause:** Surplus was calculated simply as $\\text{On\_Hand} \- \\text{Safety Stock}$ without accounting for consumption during supplier lead time.  
- **Fix:** Enforce the full lead-time buffer reservation in `src/analytics/rebalance.py`:  
    
  def calculate\_safe\_surplus(store\_id: str, sku\_id: str, lead\_time: int, velocity: float, safety\_stock: int, on\_hand: int) \-\> int:  
    
      min\_reserve \= math.ceil(velocity \* (lead\_time \+ 14)) \+ safety\_stock  
    
      surplus \= on\_hand \- min\_reserve  
    
      return max(0, surplus)

### Issue 4: Gemini LLM Emitting Numbers Not Found in Tool Outputs

- **Symptom:** TC-065 fails during numerical regex assertion.  
- **Root Cause:** Model is extrapolating or performing its own rounding/arithmetic.  
- **Fix:** Strengthen the system prompt in `src/agent/copilot.py`:  
    
  CRITICAL GROUNDING MANDATE:  
    
  You are strictly forbidden from doing arithmetic, calculating averages, or estimating numbers.  
    
  Every number you state in your response MUST be copied directly from the tool output JSON.  
    
  If the tool output says '14 units', write '14 units'. Never round, alter, or interpolate figures.

### Issue 5: Epistemic Refusal Filter Leaking Out-of-Domain Inquiries

- **Symptom:** TC-073 or TC-074 fails because the agent attempts to invent a reason for sales drops based on external rain or footfall.  
- **Root Cause:** The query bypassed the epistemic filter because the keyword was formatted differently.  
- **Fix:** Use normalized lowercase substring checking with word boundary regex in `src/agent/epistemic.py`.

### Issue 6: Cold Boot Exceeding 10 Seconds

- **Symptom:** TC-095 fails because database initialization takes $\> 10$ seconds.  
- **Root Cause:** Inserting 67,500 daily sales records using single `cursor.execute("INSERT ...")` statements.  
- **Fix:** Use SQLite transaction batching and `executemany()` with `PRAGMA synchronous = OFF;`.

---

## 8\. Hackathon Evaluation Checklist (Judge Pre-Flight Check)

| Check | Requirement | Verification Command | Pass Criteria |
| :---- | :---- | :---- | :---- |
| **1\. Track ID** | First line of `README.md` must be exactly `TRACK_ID=PS03` | `head -n 1 README.md` | Must output `TRACK_ID=PS03` (nothing else on that line) |
| **2\. One Command** | Single command starts backend & frontend on port 8000 | `python app.py` | Starts in $\< 10$s, serves `http://localhost:8000` |
| **3\. Clean Machine** | Runs on clean Python 3.11 with `pip install -r requirements.txt` | Fresh `venv` test | Zero compilation errors, zero external C++ toolchains |
| **4\. Gemini Only** | Gemini API is the sole external network call | Packet inspection / `grep` | Zero calls to OpenAI, Pinecone, LangChain Cloud, etc. |
| **5\. 24-Hr Commits** | Git history shows steady progression | `git log --oneline` | 8–12 progressive commits across 24 hours |
| **6\. Disciplined Refusal** | System refuses unanswerable queries rather than guessing | Run TC-073 to TC-084 | 100% disciplined refusal rate on untracked data |

---

## 9\. Antigravity & Cursor Prompt for Automated Test Execution

@Antigravity:

1\. Review \`docs/master\_test\_suite\_100\_testcases.md\` and \`docs/testing\_instructions\_and\_execution\_guide.md\`.

2\. Inspect the test suite under \`tests/\`.

3\. Execute \`pytest tests/ \-v \--tb=short\`.

4\. If any test case fails, identify the exact test ID (e.g., TC-027, TC-051), locate the root cause using the Error Diagnosis & Remediation Playbook, and apply the targeted fix in \`src/\`.

5\. Re-run \`pytest tests/\` until 100% of the 102 test cases pass.

6\. Verify code coverage meets or exceeds 90% via \`pytest tests/ \--cov=src\`.

7\. Generate a final test report summarizing execution results.  
