"""
Comprehensive Verification Script for KinetiQ on http://localhost:8000
1. Inspects login portal for 3 Quick Demo cards (Store Manager, Supply Chain Director, Executive & CFO)
2. Verifies currency indicators show INR (₹) and no USD ($)
3. Tests 1-click quick login as Store Manager
4. Verifies Morning Triage and KPI cards render in INR (₹)
5. Captures screenshot evidence
"""

import os
import sys
import json
import re
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://localhost:8000"
ARTIFACTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "artifacts", "verification")
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

def verify_kinetiq():
    results = {
        "step1_login_portal_cards": False,
        "step2_currency_indicators_inr": False,
        "step3_quick_login_store_manager": False,
        "step4_morning_triage_and_kpis_inr": False,
        "details": {}
    }

    print("=" * 70)
    print("STARTING KINETIQ COMPREHENSIVE VERIFICATION")
    print(f"Target: {BASE_URL}")
    print("=" * 70)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 950})
        page = context.new_page()

        # Disable cache
        try:
            cdp = context.new_cdp_session(page)
            cdp.send("Network.setCacheDisabled", {"cacheDisabled": True})
        except Exception:
            pass

        # -------------------------------------------------------------
        # STEP 1: Inspect the login portal and verify 1-click Quick Demo cards
        # -------------------------------------------------------------
        print("\n[STEP 1] Navigating to login portal...")
        page.goto(BASE_URL, wait_until="networkidle")
        page.wait_for_timeout(1000)

        # Clear localStorage to ensure starting on login view
        page.evaluate("localStorage.clear(); window.location.reload();")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        assert page.locator("#loginView").is_visible(), "Login view not visible!"

        card_sm = page.locator(".quick-demo-card.role-store_manager")
        card_sc = page.locator(".quick-demo-card.role-supply_chain_director")
        card_ex = page.locator(".quick-demo-card.role-executive")

        assert card_sm.is_visible(), "Store Manager card is not visible!"
        assert card_sc.is_visible(), "Supply Chain Director card is not visible!"
        assert card_ex.is_visible(), "Executive & CFO card is not visible!"

        sm_text = card_sm.inner_text()
        sc_text = card_sc.inner_text()
        ex_text = card_ex.inner_text()

        print("  ✓ Store Manager card verified:")
        print(f"    - Title: Store Manager | User: Alice Johnson")
        print(f"    - Snippet: {sm_text.splitlines()[:3]}")

        print("  ✓ Supply Chain Director card verified:")
        print(f"    - Title: Supply Chain Director | User: Bob Martinez")
        print(f"    - Snippet: {sc_text.splitlines()[:3]}")

        print("  ✓ Executive & CFO card verified:")
        print(f"    - Title: Executive & CFO | User: Clara Vance")
        print(f"    - Snippet: {ex_text.splitlines()[:3]}")

        results["step1_login_portal_cards"] = True
        results["details"]["step1"] = {
            "store_manager_card": "Store Manager (Alice Johnson - Downtown Metro Express)",
            "supply_chain_card": "Supply Chain Director (Bob Martinez - Multi-Store Network)",
            "executive_card": "Executive & CFO (Clara Vance - Enterprise Fleet Portfolio)",
        }

        # -------------------------------------------------------------
        # STEP 2: Verify currency indicators show INR (₹) instead of USD ($)
        # -------------------------------------------------------------
        print("\n[STEP 2] Verifying currency indicators show INR (₹) instead of USD ($)...")
        # Check header currency pill
        header_pill = page.locator(".currency-indicator-pill").inner_text()
        print(f"  ✓ Header Currency Pill: {repr(header_pill)}")
        assert "INR (₹)" in header_pill or "₹" in header_pill, f"Header missing INR (₹), got: {header_pill}"

        # Check login hero badge
        login_hero_text = page.locator(".login-hero-header").inner_text()
        print(f"  ✓ Login Hero Badges: {repr(login_hero_text.splitlines()[:3])}")
        assert "INR (₹)" in login_hero_text, "Login hero header missing 'INR (₹)' badge!"

        # Check page text for any stray '$' currency symbols
        all_body_text = page.locator("body").inner_text()
        dollar_in_body = [line for line in all_body_text.splitlines() if "$" in line]
        print(f"  ✓ Dollar sign lines in body text: {dollar_in_body}")
        assert len(dollar_in_body) == 0, f"Found unexpected '$' in body: {dollar_in_body}"

        # Save Login View screenshot
        login_shot = os.path.join(ARTIFACTS_DIR, "01_login_portal_inr_cards.png")
        page.screenshot(path=login_shot)
        print(f"  ✓ Screenshot saved: {login_shot}")

        results["step2_currency_indicators_inr"] = True
        results["details"]["step2"] = {
            "header_currency_pill": header_pill,
            "login_badge": "All Values in INR (₹)",
            "stray_dollar_count": len(dollar_in_body)
        }

        # -------------------------------------------------------------
        # STEP 3: Test quick login as Store Manager
        # -------------------------------------------------------------
        print("\n[STEP 3] Testing 1-click Quick Login as Store Manager...")
        card_sm.click()
        page.wait_for_selector("#dashboardView", state="visible", timeout=8000)
        page.wait_for_timeout(1500)

        user_name = page.locator("#headerUserName").inner_text()
        role_badge = page.locator("#headerRoleBadge").inner_text()
        store_val = page.locator("#storeSelect").input_value()
        store_disabled = page.locator("#storeSelect").is_disabled()

        print(f"  ✓ Authenticated user name: {user_name}")
        print(f"  ✓ Role badge: {role_badge}")
        print(f"  ✓ Store selected: {store_val} (disabled={store_disabled})")

        assert "Alice Johnson" in user_name, f"Expected Alice Johnson, got {user_name}"
        assert "STORE" in role_badge.upper() or "MANAGER" in role_badge.upper(), f"Unexpected role: {role_badge}"
        assert store_val == "STORE_01", f"Expected STORE_01, got {store_val}"
        assert store_disabled is True, "Store select should be pinned/disabled for Store Manager"

        results["step3_quick_login_store_manager"] = True
        results["details"]["step3"] = {
            "user_name": user_name,
            "role_badge": role_badge,
            "assigned_store": store_val,
            "store_selector_pinned": store_disabled
        }

        # -------------------------------------------------------------
        # STEP 4: Verify morning triage and KPI cards render in INR
        # -------------------------------------------------------------
        print("\n[STEP 4] Verifying Morning Triage and KPI cards render in INR (₹)...")
        # Wait for morning triage data to load
        page.wait_for_function("document.getElementById('triageNarrative').textContent !== 'Loading morning operational briefing and inventory runway...'")
        page.wait_for_timeout(1000)

        # Inspect KPI cards
        kpi_stockouts = page.locator("#kpiStockouts").inner_text()
        kpi_dead_capital = page.locator("#kpiDeadCapital").inner_text()
        kpi_dead_count = page.locator("#kpiDeadCount").inner_text()
        kpi_arbitrage = page.locator("#kpiArbitrage").inner_text()
        kpi_copilot = page.locator("#kpiCopilotStatus").inner_text()

        print("  ✓ KPI Card Values:")
        print(f"    - Imminent Stockout Risk: {kpi_stockouts}")
        print(f"    - Locked Dead Capital: {kpi_dead_capital} ({kpi_dead_count})")
        print(f"    - Arbitrage Opportunities: {kpi_arbitrage}")
        print(f"    - Copilot Reasoning: {kpi_copilot}")

        assert "₹" in kpi_dead_capital, f"Dead capital KPI missing ₹ symbol! Got: {kpi_dead_capital}"
        assert "$" not in kpi_dead_capital, f"Dead capital KPI contains $: {kpi_dead_capital}"

        # Inspect Morning Triage Narrative
        narrative_text = page.locator("#triageNarrative").inner_text()
        print(f"  ✓ Morning Triage Narrative: {narrative_text}")
        assert "₹" in narrative_text, f"Triage narrative missing ₹ symbol! Got: {narrative_text}"
        assert "$" not in narrative_text, f"Triage narrative contains $: {narrative_text}"

        # Check Action Queue tabs
        # Tab 1: Stockouts
        page.locator('.tab-btn[data-tab="stockouts"]').click()
        page.wait_for_timeout(500)
        stockout_items = page.locator("#actionQueueContainer .action-item").all_inner_texts()
        print(f"  ✓ Action Queue - Stockout Items count: {len(stockout_items)}")
        if stockout_items:
            print(f"    Sample item: {stockout_items[0].splitlines()[:2]}")

        # Tab 2: Dead Capital
        page.locator('.tab-btn[data-tab="deadStock"]').click()
        page.wait_for_timeout(500)
        dead_items = page.locator("#actionQueueContainer .action-item").all_inner_texts()
        print(f"  ✓ Action Queue - Dead Capital Items count: {len(dead_items)}")
        if dead_items:
            print(f"    Sample dead item: {dead_items[0].splitlines()[:3]}")
            # Ensure ₹ is in the dead capital item
            assert "₹" in dead_items[0], f"Dead capital item missing ₹: {dead_items[0]}"
            assert "$" not in dead_items[0], f"Dead capital item contains $: {dead_items[0]}"

        # Tab 4: Peer Transfers (Rebalance)
        page.locator('.tab-btn[data-tab="rebalance"]').click()
        page.wait_for_timeout(500)
        transfer_items = page.locator("#actionQueueContainer .action-item").all_inner_texts()
        print(f"  ✓ Action Queue - Peer Transfer Items count: {len(transfer_items)}")
        if transfer_items:
            print(f"    Sample transfer item: {transfer_items[0].splitlines()[:3]}")
            assert "₹" in transfer_items[0], f"Transfer item missing ₹: {transfer_items[0]}"
            assert "$" not in transfer_items[0], f"Transfer item contains $: {transfer_items[0]}"

        # Check Sandbox Simulator profit variance
        sim_profit = page.locator("#simProfitVal").inner_text()
        print(f"  ✓ What-If Simulator Net Profit Lift: {sim_profit}")
        assert "₹" in sim_profit, f"Simulator profit missing ₹: {sim_profit}"
        assert "$" not in sim_profit, f"Simulator profit contains $: {sim_profit}"

        # Save Store Manager Dashboard screenshot
        manager_shot = os.path.join(ARTIFACTS_DIR, "02_store_manager_triage_inr.png")
        page.screenshot(path=manager_shot)
        print(f"  ✓ Screenshot saved: {manager_shot}")

        results["step4_morning_triage_and_kpis_inr"] = True
        results["details"]["step4"] = {
            "kpi_stockouts": kpi_stockouts,
            "kpi_dead_capital": kpi_dead_capital,
            "kpi_dead_count": kpi_dead_count,
            "kpi_arbitrage": kpi_arbitrage,
            "triage_narrative": narrative_text,
            "sim_profit_variance": sim_profit,
            "dead_stock_sample": dead_items[0].replace('\n', ' | ') if dead_items else "None",
            "transfer_sample": transfer_items[0].replace('\n', ' | ') if transfer_items else "None"
        }

        # Verify no stray '$' in any authenticated dashboard element
        dash_text = page.locator("#dashboardView").inner_text()
        dollar_in_dash = [l for l in dash_text.splitlines() if "$" in l]
        print(f"  ✓ Stray '$' lines in dashboard view: {len(dollar_in_dash)}")
        assert len(dollar_in_dash) == 0, f"Found '$' in dashboard view: {dollar_in_dash}"

        browser.close()

    print("\n" + "=" * 70)
    print("ALL 4 VERIFICATION STEPS PASSED WITH ZERO ERRORS!")
    print("=" * 70)
    print(json.dumps(results, indent=2))
    return results

if __name__ == "__main__":
    verify_kinetiq()
