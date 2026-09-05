# Phase 06: Gemini Neuro-Symbolic Agent Core & Epistemic Refusal

## Detailed Implementation Guide for AI / Antigravity

**Track ID:** PS03 | **Module:** GenAI Reasoning, Prompt Engineering & Boundary Enforcement

---

## 1\. Objective & Scope

Phase 06 establishes the conversational AI interface using Google Gemini (`gemini-2.5-flash`). It bridges natural language user intent to deterministic analytical tools and enforces:

1. **The Grounding Rule:** Never emit a claim, trend, or recommendation without citing the exact data points and figures returned by the deterministic tools.  
2. **The Zero-Math Rule:** The LLM does not calculate sums, averages, or stockout dates; it receives precomputed figures from the deterministic kernel.  
3. **The Epistemic Refusal Engine:** If the user asks about data not present in the system (e.g. weather, footfall, competitor prices, unrecorded stores), gracefully decline and state what *is* available.

---

## 2\. Gemini API Client Initialization & Tool Definitions

import os

from google import genai

from google.genai import types

class CopilotAgent:

    def \_\_init\_\_(self, analytics\_kernel, rebalance\_engine):

        self.kernel \= analytics\_kernel

        self.rebalance \= rebalance\_engine

        api\_key \= os.environ.get("GEMINI\_API\_KEY")

        if api\_key:

            self.client \= genai.Client(api\_key=api\_key)

            self.model\_name \= "gemini-2.5-flash"

        else:

            self.client \= None \# Local template fallback

    def get\_tool\_declarations(self):

        \# Declare callable schema for kernel functions:

        \# \- get\_stockouts(store\_id)

        \# \- get\_dead\_stock(store\_id)

        \# \- get\_sales\_anomalies(store\_id)

        \# \- get\_sku\_performance(sku\_name\_or\_id, store\_id)

        \# \- check\_interstore\_transfers(store\_id)

        pass

---

## 3\. Epistemic Boundary Guardrail (`src/agent/epistemic.py`)

The prompt and boundary validator checks for common unanswerable questions:

UNANSWERABLE\_INTENTS \= \[

    ("footfall", "customer footfall or door counter sensors"),

    ("weather", "meteorological conditions or rainfall data"),

    ("competitor", "competitor pricing or market share benchmarks"),

    ("demographics", "customer age, gender, or income demographics"),

    ("wholesale\_market", "external commodity market trading prices")

\]

def check\_epistemic\_boundary(query: str) \-\> tuple\[bool, str\]:

    query\_lower \= query.lower()

    for keyword, missing\_data in UNANSWERABLE\_INTENTS:

        if keyword in query\_lower:

            refusal\_msg \= (

                f"\*\*Data Boundary Notice:\*\* Our system does not track {missing\_data}.\\\\n\\\\n"

                f"\*\*What is available:\*\* Daily POS sales transactions, on-hand store inventory, "

                f"supplier lead times, and inter-store rebalancing logs for Stores 1, 2, and 3."

            )

            return False, refusal\_msg

    return True, ""

---

## 4\. Grounded System Prompt Template

You are KinetiQ, an expert Retail Sales and Inventory Copilot for store managers.

Your mission is to help the manager make rapid, high-impact decisions backed by exact figures.

STRICT OPERATIONAL RULES:

1\. NEVER INVENT OR GUESS A NUMBER. Every number, unit count, currency value, velocity, and date must come directly from the verified tool outputs provided.

2\. ALWAYS SHOW YOUR WORKINGS: When recommending a purchase order or transfer, explicitly state the 7-day velocity, on-hand balance, supplier lead time, and safety buffer.

3\. STRUCTURE YOUR ANSWERS: Use bullet points, bold key metrics, and provide a clear "Recommended Action" header.

4\. HONESTY AND DISCIPLINED REFUSAL: If a product is not found in the database, or if the user asks a question that requires data you do not possess, say so directly. Never extrapolate or assume.

---

## 5\. Antigravity AI Implementation Prompt

@Antigravity: Implement \`src/agent/copilot.py\` and \`src/agent/epistemic.py\`.

Use \`google-genai\` SDK targeting \`gemini-2.5-flash\`.

Implement automatic tool execution:

1\. User prompt \-\> Epistemic pre-filter.

2\. If passed \-\> Send to Gemini with function calling declarations.

3\. Execute tool locally against AnalyticsKernel.

4\. Pass tool results back to Gemini for final grounded synthesis.

Add an automated verification test in \`tests/test\_agent.py\` confirming that asking about "customer age breakdown" returns a clean refusal without calling the database.  
