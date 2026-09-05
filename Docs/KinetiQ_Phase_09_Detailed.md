# Phase 09: Single-Command Front-End & Executive UI Dashboard

## Detailed Implementation Guide for AI / Antigravity

**Track ID:** PS03 | **Module:** Responsive UI & Interactive Manager Dashboard

---

## 1\. Objective & Scope

The frontend must provide an intuitive, high-density dashboard for the store manager. To strictly respect the hackathon evaluation rule (*"commit the built files and serve them from your Python app; a judge will not run a second command"*), the frontend is built using standard Vanilla JavaScript (ES6), Tailwind CSS (via CDN or compiled static bundle), and Chart.js, pre-committed in `frontend/dist/`.

---

## 2\. Dashboard UI Layout & Component Hierarchy

\+-----------------------------------------------------------------------------------+

|  \[Logo\] KINETIQ | Store: \[STORE\_01 \- Downtown v\] | Date: Today | API Status: Live |

\+-----------------------------------------------------------------------------------+

| TOP BAR: 3-MINUTE MORNING TRIAGE SCORECARD                                        |

| \[250 Active SKUs\] | \[12 Imminent Stockouts\] | \[15 Dead Capital\] | \[$4,120 At Risk\]|

\+------------------------------------+----------------------------------------------+

| LEFT PANE: DAILY ACTION QUEUE      | RIGHT PANE: CONVERSATIONAL COPILOT           |

|                                    |                                              |

| \[ALERT 1: Stockout in 2.1 Days\]    | Rajesh: "What is running out this week?"     |

| Organic A2 Milk (14 units left)    |                                              |

| \- Velocity: 6.2 units/day          | KinetiQ:                                     |

| \- Action: \[Transfer 20 from St 3\]  | "Here are the top 3 items facing imminent    |

|   or \[Order from Supplier\]         | stockout at Store 1 before supplier restock: |

|                                    | 1\. Organic A2 Milk: 14 on hand, 6.2 units/day|

| \[ALERT 2: Dead Capital Detected\]   |    Runway: 2.3 days vs 4-day lead time.      |

| Truffle Vinegar (0 sales in 35d)   | 2\. Sourdough Loaf: 8 on hand, 5.0 units/day  |

| \- Value: $777.00                   |    Runway: 1.6 days vs 2-day lead time.      |

| \- Action: \[Apply 30% Clearance\]    |                                              |

|                                    | Action Recommended: Inter-Store Transfer     |

| \[ALERT 3: Velocity Spike \+280%\]    | available from Store 3 for A2 Milk."         |

| Roasted Makhana Snack              |                                              |

| \- Action: \[Restock Shelf\]          | \[Type question or select quick prompt...\]    |

\+------------------------------------+----------------------------------------------+

| BOTTOM PANEL: INTERACTIVE WHAT-IF SIMULATOR & INTER-STORE TRANSFER MANIFESTS      |

| SKU: \[Truffle Vinegar\] | Discount Slider: \[ \-25% \] | Projected Clearance: 18 Days|

\+-----------------------------------------------------------------------------------+

---

## 3\. Implementation Assets (`frontend/dist/`)

- `frontend/dist/index.html`: Modern semantic markup with clean typography.  
- `frontend/dist/app.js`: Connects to `/api/triage/today` and `/api/chat` using asynchronous `fetch()`. Formats markdown responses cleanly using a lightweight parser.  
- `frontend/dist/styles.css`: Dark/light mode slate theme optimized for high contrast.

---

## 4\. Antigravity AI Implementation Prompt

@Antigravity: Generate \`frontend/dist/index.html\`, \`frontend/dist/app.js\`, and \`frontend/dist/styles.css\`.

Ensure the frontend renders cleanly without requiring any Node.js/npm commands.

Implement:

1\. Auto-refreshing Morning Triage action cards with one-click "Approve Transfer" and "Simulate Markdown" buttons.

2\. Interactive chat box with quick-prompt chips ("What's running out?", "What's overstocked?", "Compare bread sales").

3\. Verification that all data displayed connects to the live backend on port 8000\.  
