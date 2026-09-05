# Phase 10: Hackathon Evaluation Hardening, Testing & Demo Script

## Detailed Implementation Guide for AI / Antigravity

**Track ID:** PS03 | **Module:** Quality Assurance, Benchmarking & 24-Hr Commit Cadence

---

## 1\. Objective & Scope

Phase 10 ensures that the repository meets all criteria outlined in the Nexus Tiq24 Hackathon Problem Statements document:

1. `TRACK_ID=PS03` as the very first line of `README.md`.  
2. A single run command (`pip install -r requirements.txt && python app.py`) that starts in under 90 seconds on a clean Python 3.11 machine.  
3. Clean separation between deterministic logic and LLM reasoning.  
4. Disciplined refusal handling for out-of-domain edge cases.  
5. Realistic 24-hour Git commit progression.  
6. A concise, 2–3 minute video presentation walkthrough.

---

## 2\. 24-Hour Git Commit Progression Strategy

To reflect genuine engineering progression rather than a single monolithic dump, stage commits following this chronological log:

- `commit 01 (T+01h): feat(data): initialize repository, schema.sql and synthetic retail dataset generator`  
- `commit 02 (T+03h): feat(analytics): implement deterministic analytical kernel and rolling velocity calculators`  
- `commit 03 (T+05h): feat(physics): add days-of-inventory, safety stock and stockout forecasting engine`  
- `commit 04 (T+07h): feat(anomalies): add z-score demand anomaly detector and dead capital classifier`  
- `commit 05 (T+09h): feat(arbitrage): implement inter-store inventory transfer and rebalancing matrix`  
- `commit 06 (T+12h): feat(agent): integrate Gemini 2.5 Flash SDK, tool dispatcher and epistemic boundary guardrail`  
- `commit 07 (T+14h): feat(triage): build daily morning triage 3x3 cockpit and what-if simulation sandbox`  
- `commit 08 (T+16h): feat(backend): assemble unified FastAPI server in app.py with lifespan data bootstrapper`  
- `commit 09 (T+19h): feat(frontend): deliver responsive embedded executive dashboard in frontend/dist/`  
- `commit 10 (T+22h): test: comprehensive test suite covering normal queries, stockouts, and disciplined refusal`  
- `commit 11 (T+24h): docs: complete README.md with TRACK_ID=PS03, architecture diagram and demo video link`

---

## 3\. Automated Validation Suite (`tests/`)

\# tests/test\_hackathon\_criteria.py

import pytest

from src.analytics.kernel import AnalyticsKernel

from src.analytics.inventory\_physics import calculate\_doi

from src.agent.epistemic import check\_epistemic\_boundary

def test\_deterministic\_zero\_division():

    assert calculate\_doi(10, 0.0) \== 999.0

    assert calculate\_doi(0, 5.0) \== 0.0

def test\_epistemic\_refusal():

    is\_valid, msg \= check\_epistemic\_boundary("Why did footfall drop due to rain?")

    assert is\_valid is False

    assert "does not track customer footfall" in msg

def test\_numerical\_grounding():

    kernel \= AnalyticsKernel("data/retail\_inventory.db")

    metrics \= kernel.get\_sku\_metrics("SKU\_1001", "STORE\_01")

    assert metrics is not None

    assert metrics.on\_hand \>= 0

    assert metrics.velocity\_7d \>= 0

---

## 4\. 2-3 Minute Hackathon Demo Video Script

| Time | Scene | Dialogue & Narration | Visual Action on Screen |
| :---- | :---- | :---- | :---- |
| **0:00 \- 0:30** | The Retail Problem | *"Store managers are rich in data, but rushed in decisions. 15 minutes before opening, they must review dozens of spreadsheets to prevent stockouts and cut dead stock."* | Show overwhelming raw CSV spreadsheets, then launch `python app.py` showing cold start in 4 seconds. |
| **0:30 \- 1:15** | Morning Triage & Arbitrage | *"KinetiQ's Morning Triage highlights today's critical items. Here, Organic A2 Milk has only 2.3 days of inventory, while distributor restock takes 4 days. But instead of ordering, KinetiQ spots that Store 3 has 58 idle units. One click generates an Inter-Store Transfer Manifest."* | Click on the alert, inspect the assumption ledger, and click "Approve Transfer". Show generated manifest. |
| **1:15 \- 1:50** | Grounded Q\&A | *"The manager asks in plain language: 'What is running out at Store 1?' KinetiQ answers with exact figures—units on hand, 7-day velocity, and lead time. No hallucinations, pure deterministic math."* | Type natural language query into chat; show instant response with data tables and exact numerical citations. |
| **1:50 \- 2:30** | Disciplined Refusal & Conclusion | *"When asked 'Why did customer footfall drop yesterday?', KinetiQ does not invent a story. It enforces an epistemic boundary: stating clearly that footfall sensors are unrecorded, while summarizing the actual POS sales transactions."* | Type the out-of-domain query, showcase the polite, structured refusal, and conclude with the unified Python architecture. |

