import os
import pytest
import sqlite3
from fastapi.testclient import TestClient
from app import app
from src.data.generator import generate_retail_dataset
from src.analytics.kernel import AnalyticsKernel
from src.analytics.rebalance import ArbitrageEngine
from src.agent.copilot import CopilotAgent

TEST_DB_PATH = "data/test_retail_inventory.db"

@pytest.fixture(scope="session")
def test_db():
    os.makedirs("data", exist_ok=True)
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass
    generate_retail_dataset(TEST_DB_PATH, days=90)
    yield TEST_DB_PATH
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass

@pytest.fixture
def kernel(test_db):
    return AnalyticsKernel(test_db)

@pytest.fixture
def arbitrage_engine(test_db, kernel):
    return ArbitrageEngine(test_db, kernel)

@pytest.fixture
def agent(kernel, arbitrage_engine):
    return CopilotAgent(kernel, arbitrage_engine)

@pytest.fixture
def api_client(test_db, kernel, arbitrage_engine):
    app.state.kernel = kernel
    app.state.rebalance = arbitrage_engine
    app.state.copilot = CopilotAgent(kernel, arbitrage_engine)
    client = TestClient(app)
    return client
