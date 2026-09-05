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

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from src.data.generator import generate_retail_dataset
from src.data.mongodb import get_auth_service
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
    MongoDB auth services, and neuro-symbolic copilot state.
    Safe for local servers and serverless environments.
    """
    with _init_lock:
        if getattr(app_instance.state, "kernel", None) is None:
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

        if getattr(app_instance.state, "auth", None) is None:
            app_instance.state.auth = get_auth_service()
            print("[BOOTSTRAP] KinetiQ Copilot Engine & MongoDB Auth initialized.")


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

# Path normalization middleware for Vercel serverless rewrites and stripped prefixes
@app.middleware("http")
async def path_normalization_middleware(request: Request, call_next):
    # Check if request was rewritten to index.py by Vercel
    if request.scope.get("path", "").endswith("index.py"):
        matched = (
            request.headers.get("x-matched-path")
            or request.headers.get("x-vercel-matched-path")
            or request.headers.get("x-forwarded-uri")
        )
        if matched:
            request.scope["path"] = matched.split("?")[0]

    cur_path = request.scope.get("path", "")
    api_prefixes = (
        "/auth/",
        "/roles/",
        "/triage/",
        "/chat",
        "/simulate",
        "/stores",
        "/actions/",
        "/sku/",
        "/health",
    )
    if any(cur_path.startswith(p) for p in api_prefixes) and not cur_path.startswith("/api/"):
        request.scope["path"] = f"/api{cur_path}"

    return await call_next(request)


# State initialization fallback middleware for serverless invocations
@app.middleware("http")
async def ensure_state_middleware(request: Request, call_next):
    if getattr(app.state, "kernel", None) is None or getattr(app.state, "auth", None) is None:
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
class LoginRequest(BaseModel):
    username: str
    password: str


class QuickLoginRequest(BaseModel):
    role: str


class ApiKeyUpdateRequest(BaseModel):
    api_key: str


class ChatRequest(BaseModel):
    message: str = Field(..., description="User query or instruction")
    store_id: str = Field(default="STORE_01", description="Context store identifier")
    role: Optional[str] = Field(default=None, description="Active user role")


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


# Authentication & Role Endpoints
@app.get("/api/roles/overview")
async def get_roles_overview():
    """Return public demo roles and sample login presets for 1-click evaluation."""
    return app.state.auth.get_role_presets()


@app.post("/api/auth/login")
async def login_endpoint(req: LoginRequest):
    """Authenticate with username/email and password against MongoDB or fallback store."""
    sess = app.state.auth.authenticate(req.username, req.password)
    if not sess:
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    return sess


@app.post("/api/auth/quick-login")
async def quick_login_endpoint(req: QuickLoginRequest):
    """1-Click demo authentication for instant role-based exploration."""
    sess = app.state.auth.quick_login(req.role)
    if not sess:
        raise HTTPException(status_code=400, detail=f"Role '{req.role}' is not recognized.")
    return sess


@app.get("/api/auth/me")
async def get_current_user_profile(request: Request):
    """Get authenticated user profile and active role."""
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip() if auth_header.startswith("Bearer ") else request.query_params.get("token", "")
    sess = app.state.auth.get_session(token)
    if not sess:
        raise HTTPException(status_code=401, detail="Session expired or invalid.")
    return sess


@app.post("/api/auth/api-key")
async def update_api_key_endpoint(req: ApiKeyUpdateRequest, request: Request):
    """Update or test Gemini API key for current user/role."""
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip() if auth_header.startswith("Bearer ") else request.query_params.get("token", "")
    sess = app.state.auth.get_session(token)
    username = sess["username"] if sess else "guest"

    clean_key = req.api_key.strip()
    app.state.auth.update_custom_api_key(username, clean_key)

    if clean_key:
        app.state.copilot.api_key = clean_key
        try:
            from google import genai
            app.state.copilot.client = genai.Client(api_key=clean_key)
        except Exception:
            pass

    return {
        "status": "success",
        "message": "Gemini API key updated successfully.",
        "has_key": bool(clean_key),
        "key_preview": f"****{clean_key[-4:]}" if len(clean_key) >= 4 else "None",
    }


# API Endpoints
@app.get("/api/health")
async def health_check():
    """Health check endpoint for container, MongoDB Atlas, and uptime probes."""
    return {
        "status": "healthy",
        "service": "KinetiQ Retail Copilot",
        "mongodb_connected": getattr(app.state, "auth", None) is not None and app.state.auth.is_connected,
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
    """Handle conversational natural language queries with role-tailored deterministic grounding."""
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Query message cannot be empty.")
    
    # Append role-tailored operational context
    scoped_query = req.message
    if req.role == "store_manager":
        scoped_query = f"[Role: Store General Manager for {req.store_id}]: {req.message}"
    elif req.role == "supply_chain_director":
        scoped_query = f"[Role: Regional Supply Chain Director - Multi-Store]: {req.message}"
    elif req.role == "executive":
        scoped_query = f"[Role: Executive & Finance - Portfolio Overview]: {req.message}"

    response = app.state.copilot.ask(query=scoped_query, store_id=req.store_id)
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
    
    if getattr(app.state, "auth", None):
        app.state.auth.log_audit("system", "supply_chain_director", "TRANSFER_COMMITTED", {
            "manifest_id": req.manifest_id,
            "from_store_id": req.from_store_id,
            "to_store_id": req.to_store_id,
            "sku_id": req.sku_id,
            "quantity": req.quantity,
        })

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
