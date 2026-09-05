# KinetiQ — 2-3 Minute Live Demonstration Script

## Overview
This walkthrough script is designed for live evaluation of KinetiQ: demonstrating the 3-minute morning triage, zero-math conversational grounding, inter-store inventory arbitrage, and disciplined epistemic refusal.

---

## Demonstration Timeline & Narration

| Timestamp | Screen Action | Narration & Key Points |
| :--- | :--- | :--- |
| **0:00 – 0:30** | Launch terminal: `python app.py`. Open browser at `http://localhost:8000`. Show executive scorecard. | *"Retail store managers spend 45 minutes every morning filtering through spreadsheets. With KinetiQ, bootup takes under 4 seconds. The dashboard instantly displays the 3-Minute Morning Triage: Store Health at 88/100, 12 imminent stockouts, and $4,120 locked in dead capital."* |
| **0:30 – 1:00** | Click on **Imminent Stockouts** tab. Highlight `SKU_1020` (Organic A2 Milk). Click **"Approve Transfer"** button. | *"Here, Organic A2 Milk has only 2.3 days of inventory remaining, but distributor delivery takes 4 days—meaning an inevitable stockout. However, KinetiQ's Inter-Store Arbitrage Engine detected that Store 3 (8 km away) holds 58 idle units. With one click, the manager approves an Inter-Store Stock Transfer Note, saving $85 in gross profit with a 1-hour courier dispatch."* |
| **1:00 – 1:35** | Type in chat: *"What is running out at Store 1 this week?"* Review grounded response. | *"Let's test conversational exploration. When asked what's running out, KinetiQ enforces the Zero-Math Rule: the LLM never guesses numbers. It cites deterministic calculations directly—exact on-hand units, unconstrained 7-day velocity, and supplier lead times."* |
| **1:35 – 2:05** | Click chip: *"Show dead capital & holding costs"*. Click **"Simulate -35%"** on Truffle Vinegar (`SKU_1080`). Show slider in What-If sandbox. | *"Non-moving inventory silently incurs holding costs. SKU_1080 (Artisanal Truffle Vinegar) has been idle for 40 days, tying up $666 in locked cash. One click sends it to our What-If Simulation Sandbox: applying a 35% clearance markdown models price elasticity, projecting clearance in 18 days while recovering $505 in cash."* |
| **2:05 – 2:35** | Type in chat: *"Why did customer footfall drop yesterday due to the rain?"* Show refusal response. | *"Finally, disciplined epistemic boundaries: generic AI hallucinates answers to unanswerable questions. When asked about footfall or weather, KinetiQ declines to speculate because external footfall counters and meteorological sensors are unrecorded—while politely confirming what verified POS transaction data is available."* |
| **2:35 – 3:00** | Point out single-command architecture, full test suite passing in seconds, and conclusion. | *"KinetiQ bridges mathematical truth with conversational intelligence: zero hallucinations, automated multi-store arbitrage, and turnkey single-command deployment on port 8000."* |
