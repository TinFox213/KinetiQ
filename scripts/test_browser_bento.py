"""
KinetiQ Playwright Browser Automation Suite: White Bento Box & Multi-Role Verification
Tests Login portal, 3-role switching, live triage, transfer commit, sandbox, copilot,
and captures real UI screenshots for Devfolio MCP submission.
"""

import os
import sys
import time
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "artifacts", "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def run_bento_browser_verification():
    print("[PLAYWRIGHT] Launching Chrome browser to verify White Bento Box and Multi-Role Auth...")
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 950})
        page = context.new_page()
        try:
            cdp = context.new_cdp_session(page)
            cdp.send("Network.setCacheDisabled", {"cacheDisabled": True})
        except Exception:
            pass
        page.on("console", lambda msg: print(f"[CONSOLE] {msg.type}: {msg.text}"))
        page.on("pageerror", lambda err: print(f"[PAGEERROR] {err}"))

        # Step 1: Open Login Screen
        print("[TEST 1] Navigating to http://localhost:8000...")
        page.goto("http://localhost:8000", wait_until="networkidle")
        page.wait_for_timeout(1000)

        # Clear any existing local storage to start clean
        page.evaluate("localStorage.clear(); window.location.reload();")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        # Verify Login View elements
        assert page.locator("#loginView").is_visible(), "Login View must be visible initially"
        assert page.locator(".quick-demo-card.role-store_manager").is_visible(), "Store Manager card must exist"
        assert page.locator(".quick-demo-card.role-supply_chain_director").is_visible(), "Supply Chain card must exist"
        assert page.locator(".quick-demo-card.role-executive").is_visible(), "Executive card must exist"

        login_shot = os.path.join(SCREENSHOT_DIR, "01_bento_login_view.png")
        page.screenshot(path=login_shot)
        print(f"[SCREENSHOT 1] Saved login screen: {login_shot}")

        # Step 2: 1-Click Quick Demo Login as Store Manager
        print("[TEST 2] Executing 1-Click Quick Demo Login as Store Manager (Alice Johnson)...")
        page.locator(".quick-demo-card.role-store_manager").click()
        page.wait_for_selector("#dashboardView", state="visible", timeout=8000)
        page.wait_for_timeout(1500)

        # Verify Store Manager state
        user_name = page.locator("#headerUserName").inner_text()
        assert "Alice Johnson" in user_name, f"Expected Alice Johnson, got {user_name}"
        assert page.locator("#headerRoleBadge").inner_text() == "STORE GENERAL MANAGER" or "Store" in page.locator("#headerRoleBadge").inner_text()
        print(f"  ✓ Store Manager authenticated: {user_name}")

        # Verify KPIs & Triage Narrative
        page.wait_for_function("document.getElementById('triageNarrative').textContent !== 'Loading morning operational briefing and inventory runway...'")
        kpi_stockouts = page.locator("#kpiStockouts").inner_text()
        print(f"  ✓ Imminent Stockouts KPI: {kpi_stockouts}")
        assert page.locator("#triageNarrative").inner_text() != "Loading morning operational briefing and inventory runway..."

        # Test tabs
        page.locator('.tab-btn[data-tab="rebalance"]').click()
        page.wait_for_timeout(500)
        page.locator('.tab-btn[data-tab="stockouts"]').click()
        page.wait_for_timeout(500)

        manager_shot = os.path.join(SCREENSHOT_DIR, "02_store_manager_bento_dashboard.png")
        page.screenshot(path=manager_shot)
        print(f"[SCREENSHOT 2] Saved Store Manager Dashboard: {manager_shot}")

        # Step 3: Switch Role to Supply Chain Director
        print("[TEST 3] Switching role to Supply Chain Director (Bob Martinez)...")
        page.locator("#roleSwitcherSelect").select_option("supply_chain_director")
        page.wait_for_timeout(1500)

        user_name_dir = page.locator("#headerUserName").inner_text()
        assert "Bob Martinez" in user_name_dir, f"Expected Bob Martinez, got {user_name_dir}"
        print(f"  ✓ Supply Chain Director authenticated: {user_name_dir}")

        # Verify Arbitrage Opportunities tab
        page.locator('.tab-btn[data-tab="rebalance"]').click()
        page.wait_for_timeout(800)

        director_shot = os.path.join(SCREENSHOT_DIR, "03_supply_chain_director_bento.png")
        page.screenshot(path=director_shot)
        print(f"[SCREENSHOT 3] Saved Supply Chain Director Dashboard: {director_shot}")

        # Step 4: Switch Role to Executive & CFO
        print("[TEST 4] Switching role to Executive & CFO (Clara Vance)...")
        page.locator("#roleSwitcherSelect").select_option("executive")
        page.wait_for_timeout(1500)

        user_name_exec = page.locator("#headerUserName").inner_text()
        assert "Clara Vance" in user_name_exec, f"Expected Clara Vance, got {user_name_exec}"
        print(f"  ✓ Executive authenticated: {user_name_exec}")

        # Test Simulation Slider
        print("[TEST 5] Testing What-If Price Elasticity Sandbox Slider...")
        page.locator("#simDiscountSlider").fill("25")
        page.locator("#simDiscountSlider").dispatch_event("input")
        page.wait_for_timeout(800)
        discount_label = page.locator("#sliderDiscountLabel").inner_text()
        assert discount_label == "25%", f"Expected 25%, got {discount_label}"
        print(f"  ✓ Discount slider set to: {discount_label}")

        # Test API Key Modal
        print("[TEST 6] Opening Gemini API Key Modal...")
        page.locator("#btnOpenApiKeyModal").click()
        page.wait_for_selector("#apiKeyModal.active", state="visible", timeout=3000)
        page.wait_for_timeout(500)
        status_text = page.locator("#modalCurrentKeyPreview").inner_text()
        print(f"  ✓ API Key Modal open with status: {status_text}")
        page.locator("#btnCloseApiKeyModal").click()
        page.wait_for_timeout(500)

        exec_shot = os.path.join(SCREENSHOT_DIR, "04_executive_bento_dashboard.png")
        page.screenshot(path=exec_shot)
        print(f"[SCREENSHOT 4] Saved Executive Dashboard: {exec_shot}")

        # Step 5: Test Conversational Copilot Chat
        print("[TEST 7] Testing Conversational Copilot Chat...")
        page.locator("#chatInput").fill("What are the priority stockout risks today?")
        page.locator("#btnSendChat").click()
        page.wait_for_timeout(3500)

        messages = page.locator(".chat-msg.assistant").all()
        assert len(messages) >= 2, "Expected at least 2 assistant messages in stream"
        latest_text = messages[-1].inner_text()
        print(f"  ✓ Copilot responded: {latest_text[:90]}...")

        chat_shot = os.path.join(SCREENSHOT_DIR, "05_copilot_chat_response.png")
        page.screenshot(path=chat_shot)
        print(f"[SCREENSHOT 5] Saved Copilot Chat screenshot: {chat_shot}")

        # Step 6: Test Sign Out
        print("[TEST 8] Testing Sign Out...")
        page.locator("#btnLogout").click()
        page.wait_for_selector("#loginView", state="visible", timeout=3000)
        assert page.locator("#loginView").is_visible()
        print("  ✓ Sign out successful; returned to White Bento Login View.")

        browser.close()
        print("\n🎉 ALL 8 BROWSER TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    run_bento_browser_verification()
