"""
KinetiQ — Retail Sales & Inventory Copilot
Unified FastAPI Application serving REST API and embedded frontend on Port 8000.
Supports standard local execution and Vercel serverless deployment.
"""

import os
import sys
import threading
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from src.data.generator import generate_retail_dataset
from src.analytics.kernel import AnalyticsKernel
from src.analytics.rebalance import ArbitrageEngine
from src.analytics.triage import generate_morning_triage
from src.analytics.simulator import simulate_intervention
from src.agent.copilot import CopilotAgent

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IS_VERCEL = bool(os.environ.get("VERCEL"))

if IS_VERCEL:
    DB_PATH = "/tmp/retail_inventory.db"
else:
    DB_PATH = os.path.join(BASE_DIR, "data", "retail_inventory.db")

FRONTEND_DIST_DIR = os.path.join(BASE_DIR, "frontend", "dist")
PUBLIC_DIR = os.path.join(BASE_DIR, "public")

_init_lock = threading.Lock()


def init_app_state(app_instance: FastAPI):
    """
    Idempotently initializes analytical engines, database seeding,
    and neuro-symbolic copilot state.
    Safe for local servers and serverless environments.
    """
    if getattr(app_instance.state, "kernel", None) is not None:
        return

    with _init_lock:
        if getattr(app_instance.state, "kernel", None) is not None:
            return

        db_dir = os.path.dirname(os.path.abspath(DB_PATH))
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        if not os.path.exists(DB_PATH):
            print(f"[BOOTSTRAP] Seeding initial multi-store retail database at {DB_PATH}...")
            generate_retail_dataset(db_path=DB_PATH, days=90)
            print("[BOOTSTRAP] Database generated successfully.")

        # Initialize shared components
        app_instance.state.kernel = AnalyticsKernel(db_path=DB_PATH)
        app_instance.state.rebalance = ArbitrageEngine(db_path=DB_PATH, kernel=app_instance.state.kernel)
        app_instance.state.copilot = CopilotAgent(
            kernel=app_instance.state.kernel,
            rebalance_engine=app_instance.state.rebalance,
        )
        print("[BOOTSTRAP] KinetiQ Copilot Engine initialized and ready.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan hook."""
    init_app_state(app)
    yield


app = FastAPI(
    title="KinetiQ — Retail Sales & Inventory Copilot",
    description="Neuro-Symbolic Retail Copilot with Deterministic Grounding",
    lifespan=lifespan,
)

# State initialization fallback middleware for serverless invocations
@app.middleware("http")
async def ensure_state_middleware(request: Request, call_next):
    if getattr(app.state, "kernel", None) is None:
        init_app_state(app)
    return await call_next(request)

# Allow CORS for local testing/development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request & Response Schemas
class ChatRequest(BaseModel):
    message: str = Field(..., description="User query or instruction")
    store_id: str = Field(default="STORE_01", description="Context store identifier")


class TransferCommitRequest(BaseModel):
    manifest_id: str
    from_store_id: str
    to_store_id: str
    sku_id: str
    quantity: int


class SimulationRequest(BaseModel):
    sku_id: str
    store_id: str = "STORE_01"
    discount_percent: float = 15.0
    duration_days: int = 14


# API Endpoints
@app.get("/api/health")
async def health_check():
    """Health check endpoint for container and uptime probes."""
    return {
        "status": "healthy",
        "service": "KinetiQ Retail Copilot",
        "gemini_connected": app.state.copilot.client is not None,
    }


@app.get("/api/stores")
async def get_stores():
    """Return list of all registered stores in the chain."""
    return app.state.kernel.get_all_stores()


@app.get("/api/triage/today")
async def get_triage(store_id: str = Query(default="STORE_01")):
    """Get the 3-minute morning triage briefing for a store."""
    briefing = generate_morning_triage(
        store_id=store_id,
        kernel=app.state.kernel,
        arbitrage=app.state.rebalance,
    )
    return briefing.to_dict()


@app.post("/api/chat")
async def chat_handler(req: ChatRequest):
    """Handle conversational natural language queries with deterministic grounding."""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Query message cannot be empty.")
    response = app.state.copilot.ask(query=req.message, store_id=req.store_id)
    return response.to_dict()


@app.post("/api/actions/transfer")
async def commit_transfer_endpoint(req: TransferCommitRequest):
    """Approve and commit an inter-store inventory transfer manifest."""
    success = app.state.rebalance.commit_transfer(
        manifest_id=req.manifest_id,
        from_store_id=req.from_store_id,
        to_store_id=req.to_store_id,
        sku_id=req.sku_id,
        quantity=req.quantity,
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to record transfer manifest.")
    return {
        "status": "success",
        "message": f"Transfer {req.manifest_id} committed successfully.",
        "manifest_id": req.manifest_id,
    }


@app.post("/api/simulate")
async def simulate_endpoint(req: SimulationRequest):
    """Run deterministic What-If price elasticity and demand lift simulation."""
    res = simulate_intervention(
        sku_id=req.sku_id,
        store_id=req.store_id,
        discount_percent=req.discount_percent,
        duration_days=req.duration_days,
        kernel=app.state.kernel,
    )
    if not res:
        raise HTTPException(status_code=404, detail=f"SKU {req.sku_id} not found in store {req.store_id}")
    return res.to_dict()


@app.get("/api/sku/{sku_id}")
async def get_sku_endpoint(sku_id: str, store_id: str = Query(default="STORE_01")):
    """Get detailed 7d/14d/30d metrics and rolling velocities for a single SKU."""
    metrics = app.state.kernel.get_sku_metrics(sku_id, store_id)
    if not metrics:
        raise HTTPException(status_code=404, detail=f"SKU {sku_id} not found.")
    return metrics.to_dict()


# Serve Embedded Static UI
static_dir = FRONTEND_DIST_DIR if os.path.exists(FRONTEND_DIST_DIR) else os.path.join(PUBLIC_DIR, "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def serve_index():
    candidates = [
        os.path.join(FRONTEND_DIST_DIR, "index.html"),
        os.path.join(PUBLIC_DIR, "index.html"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return FileResponse(path)
    return JSONResponse(
        {"status": "online", "message": "KinetiQ Retail Copilot API running."}
    )


@app.get("/healthz")
async def healthz():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    print("[SERVER] Starting KinetiQ on http://localhost:8000")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
