# Phase 08: Unified Python Backend (FastAPI on Port 8000\)

## Detailed Implementation Guide for AI / Antigravity

**Track ID:** PS03 | **Module:** FastAPI Application & Single-Command Deployment

---

## 1\. Objective & Scope

The Nexus Tiq24 submission guidelines state:

- *One command to run: `pip install -r requirements.txt`, then `python app.py` starts backend and frontend together serving at `http://localhost:8000`.*  
- *Startup within 90 seconds, single request timeout within 60 seconds.* Phase 08 packages the database, analytical kernels, Gemini agent, and static UI into a production-grade FastAPI application mounted directly at `app.py`.

---

## 2\. Root Entry Point Architecture (`app.py`)

import os

import sys

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from fastapi.staticfiles import StaticFiles

from fastapi.responses import FileResponse, JSONResponse

from pydantic import BaseModel

from src.data.generator import generate\_retail\_dataset

from src.analytics.kernel import AnalyticsKernel

from src.analytics.inventory\_physics import evaluate\_all\_stockouts

from src.analytics.rebalance import ArbitrageEngine

from src.analytics.triage import generate\_morning\_triage

from src.analytics.simulator import simulate\_intervention

from src.agent.copilot import CopilotAgent

@asynccontextmanager

async def lifespan(app: FastAPI):

    \# 1\. Check if SQLite DB exists; if not, generate in \< 3s

    db\_path \= "data/retail\_inventory.db"

    if not os.path.exists(db\_path):

        print("\[BOOTSTRAP\] Seeding multi-store retail database...")

        generate\_retail\_dataset(db\_path)

    

    \# 2\. Warm up analytical cache

    app.state.kernel \= AnalyticsKernel(db\_path)

    app.state.rebalance \= ArbitrageEngine(db\_path)

    app.state.copilot \= CopilotAgent(app.state.kernel, app.state.rebalance)

    print("\[BOOTSTRAP\] KinetiQ Engine ready on port 8000.")

    yield

app \= FastAPI(title="KinetiQ Retail Copilot", lifespan=lifespan)

\# API Endpoints

@app.get("/api/health")

async def health\_check():

    return {"status": "healthy", "track\_id": "PS03"}

@app.get("/api/triage/today")

async def get\_triage(store\_id: str \= "STORE\_01"):

    return generate\_morning\_triage(store\_id)

class ChatRequest(BaseModel):

    message: str

    store\_id: str \= "STORE\_01"

@app.post("/api/chat")

async def chat\_handler(req: ChatRequest):

    response \= app.state.copilot.ask(req.message, req.store\_id)

    return response

\# Serve Built Frontend

if os.path.exists("frontend/dist"):

    app.mount("/static", StaticFiles(directory="frontend/dist"), name="static")

    @app.get("/")

    async def serve\_index():

        return FileResponse("frontend/dist/index.html")

if \_\_name\_\_ \== "\_\_main\_\_":

    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)

---

## 3\. Minimal, Robust `requirements.txt`

fastapi\>=0.110.0

uvicorn\>=0.28.0

pydantic\>=2.6.0

google-genai\>=0.1.1

numpy\>=1.26.0

pandas\>=2.2.0

python-multipart\>=0.0.9

*Note: Zero external cloud database dependencies; zero PyTorch/TensorFlow weight downloads.*

---

## 4\. Antigravity AI Implementation Prompt

@Antigravity: Implement \`app.py\` and \`requirements.txt\`.

Ensure \`python app.py\` starts cleanly and prints \`Serving at http://localhost:8000\`.

Ensure startup time from cold start is less than 5 seconds.

Validate that all static frontend assets are served correctly from \`frontend/dist/\` or \`src/static/\`.

Write integration tests in \`tests/test\_api.py\` verifying \`/api/health\`, \`/api/triage/today\`, and \`/api/chat\`.  
