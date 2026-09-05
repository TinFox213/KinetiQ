"""
Unit Tests for Phase 06: Gemini Neuro-Symbolic Agent Core & Epistemic Refusal
Validates boundary refusal on unanswerable out-of-domain requests,
deterministic tool execution, grounded fact citation, and fallback synthesis.
"""

import os
import pytest
from src.data.generator import generate_retail_dataset
from src.analytics.kernel import AnalyticsKernel
from src.analytics.rebalance import ArbitrageEngine
from src.agent.epistemic import check_epistemic_boundary
from src.agent.copilot import CopilotAgent, CopilotResponse


TEST_DB_PATH = "data/test_retail_inventory.db"


@pytest.fixture(scope="module")
def agent():
    if not os.path.exists(TEST_DB_PATH):
        generate_retail_dataset(db_path=TEST_DB_PATH, days=90)
    kernel = AnalyticsKernel(db_path=TEST_DB_PATH)
    rebalance = ArbitrageEngine(db_path=TEST_DB_PATH, kernel=kernel)
    return CopilotAgent(kernel=kernel, rebalance_engine=rebalance)


def test_epistemic_boundary_refusals():
    """Verify clean refusals on unanswerable queries without accessing database."""
    # 1. Footfall
    ok1, msg1 = check_epistemic_boundary("Why did store footfall decrease yesterday?")
    assert ok1 is False
    assert "footfall" in msg1.lower()
    assert "What the verified data can confirm" in msg1

    # 2. Weather / Rain
    ok2, msg2 = check_epistemic_boundary("Will tomorrow's rain affect tomato sales?")
    assert ok2 is False
    assert "meteorological" in msg2.lower()

    # 3. Competitor benchmarking
    ok3, msg3 = check_epistemic_boundary("How are our competitor prices compared to rivals?")
    assert ok3 is False
    assert "competitor" in msg3.lower()

    # 4. Demographics / Age
    ok4, msg4 = check_epistemic_boundary("What is the average age of customers buying bread?")
    assert ok4 is False
    assert "demographic" in msg4.lower()

    # 5. Valid retail query must pass
    ok5, msg5 = check_epistemic_boundary("What is running out at Store 1 this week?")
    assert ok5 is True
    assert msg5 == ""


def test_agent_refuses_out_of_domain_query(agent):
    """Test full agent pipeline on out-of-domain query."""
    resp = agent.ask("What is the customer footfall at Store 1?")
    assert isinstance(resp, CopilotResponse)
    assert resp.source == "epistemic-refusal"
    assert len(resp.tools_executed) == 0
    assert "Data Boundary Notice" in resp.response


def test_agent_answers_stockout_query(agent):
    """Test conversational response for imminent stockout triage."""
    resp = agent.ask("What items are running out this week at Store 1?", store_id="STORE_01")
    assert isinstance(resp, CopilotResponse)
    assert "get_imminent_stockouts" in resp.tools_executed
    assert "imminent_stockouts" in resp.grounded_facts
    assert "On Hand" in resp.response or "Runway" in resp.response


def test_agent_answers_dead_stock_query(agent):
    """Test conversational response for dead stock and locked capital."""
    resp = agent.ask("What items are not moving and have locked capital?", store_id="STORE_01")
    assert isinstance(resp, CopilotResponse)
    assert "get_dead_stock" in resp.tools_executed
    assert "dead_stock" in resp.grounded_facts
    assert "Locked Capital" in resp.response or "holding" in resp.response.lower()


def test_agent_answers_sku_query(agent):
    """Test conversational response for a specific SKU."""
    resp = agent.ask("Tell me about SKU_1001", store_id="STORE_01")
    assert isinstance(resp, CopilotResponse)
    assert "get_sku_metrics" in resp.tools_executed
    assert "sku_metrics_SKU_1001" in resp.grounded_facts
    assert "Classic White Bread" in resp.response
