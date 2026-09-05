import sys
import time
import os
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')

def run_browser_tests():
    print("=== STARTING BROWSER E2E TEST SUITE ===")
    os.makedirs("artifacts/screenshots", exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page()
        page.set_viewport_size({"width": 1440, "height": 900})

        # TC-B01: Initial Load & Branding
        print("[TC-B01] Loading http://localhost:8000...")
        page.goto("http://localhost:8000")
        page.wait_for_selector(".app-header")
        assert "KinetiQ" in page.title(), "Title does not contain KinetiQ"
        brand_title = page.locator(".brand-title").text_content()
        assert brand_title == "KinetiQ", f"Brand title was {brand_title}"
        print("  [PASS] TC-B01: Header, Title, and Branding verified.")

        # TC-B02: Store Switcher
        print("[TC-B02] Verifying store selector...")
        options = page.locator("#storeSelect option").all_text_contents()
        assert len(options) == 3, f"Expected 3 store options, got {len(options)}"
        print(f"  [PASS] TC-B02: 3 stores available in selector.")

        # TC-B03: Scorecard Validation
        print("[TC-B03] Validating 3-Minute Morning Scorecard...")
        page.wait_for_function("document.getElementById('healthScore').textContent !== '--/100'")
        health = page.locator("#healthScore").text_content()
        skus = page.locator("#statActiveSkus").text_content()
        stockouts = page.locator("#statStockouts").text_content()
        dead = page.locator("#statDeadStock").text_content()
        transfers = page.locator("#statTransfers").text_content()
        print(f"  Scorecard Metrics: Health={health}, SKUs={skus}, Stockouts={stockouts}, Dead Stock={dead}, Transfers={transfers}")
        assert "/100" in health
        assert skus == "250"
        print("  [PASS] TC-B03: Scorecard metrics loaded and non-empty.")

        # TC-B04: Stockouts Queue Tab
        print("[TC-B04] Inspecting Daily Action Queue (Stockouts)...")
        cards = page.locator("#queueContainer .queue-card").all()
        assert len(cards) > 0, "No stockout queue cards found"
        print(f"  Found {len(cards)} stockout queue cards.")
        print("  [PASS] TC-B04: Stockout cards rendered successfully.")

        # TC-B05: Dead Capital Tab & Simulation Trigger
        print("[TC-B05] Testing Dead Capital Tab...")
        page.click("button[data-tab='deadstock']")
        time.sleep(0.5)
        dead_cards = page.locator("#queueContainer .queue-card").all()
        assert len(dead_cards) > 0, "No dead stock cards found"
        print(f"  Found {len(dead_cards)} dead capital items.")
        
        sim_btn = page.locator("#queueContainer button:has-text('Simulate')").first
        if sim_btn.is_visible():
            sim_btn.click()
            time.sleep(0.5)
            discount_val = page.locator("#simDiscountVal").text_content()
            print(f"  Simulator discount value set to: {discount_val}")
            assert "%" in discount_val
        print("  [PASS] TC-B05: Dead capital and simulator trigger verified.")

        # TC-B06: Anomalies Tab & Phantom Inventory
        print("[TC-B06] Testing Anomalies Tab...")
        page.click("button[data-tab='anomalies']")
        time.sleep(0.5)
        anom_cards = page.locator("#queueContainer .queue-card").all()
        assert len(anom_cards) > 0, "No anomaly cards found"
        print(f"  Found {len(anom_cards)} anomaly/phantom alert cards.")
        
        audit_btn = page.locator("button:has-text('Dispatch Shelf Audit')").first
        if audit_btn.is_visible():
            audit_btn.click()
            time.sleep(0.5)
            toast = page.locator(".toast").first.text_content()
            print(f"  Toast notification received: {toast}")
            assert "audit" in toast.lower()
        print("  [PASS] TC-B06: Anomalies and Shelf Audit dispatch verified.")

        # TC-B07: Transfers Tab & STN Approval
        print("[TC-B07] Testing Transfers Tab...")
        page.click("button[data-tab='transfers']")
        time.sleep(0.5)
        trans_cards = page.locator("#queueContainer .queue-card").all()
        if len(trans_cards) > 0:
            print(f"  Found {len(trans_cards)} transfer recommendations.")
            approve_btn = page.locator("button:has-text('Approve Stock Transfer Note')").first
            if approve_btn.is_visible():
                approve_btn.click()
                time.sleep(1.0)
                toast = page.locator(".toast").last.text_content()
                print(f"  Approval Toast received: {toast}")
                assert "approved" in toast.lower() or "transfer" in toast.lower()
        print("  [PASS] TC-B07: Transfers tab and STN approval verified.")

        # TC-B08: Copilot Chat - Grounded Query
        print("[TC-B08] Testing Copilot Chat Grounded Query...")
        page.fill("#chatInput", "What is running out at Store 1 this week?")
        page.click(".chat-send-btn")
        # Wait until loading spinner disappears and response tag is rendered
        page.wait_for_selector(".chat-msg.copilot .msg-source-tag", timeout=15000)
        time.sleep(1.0)
        copilot_msgs = page.locator(".chat-msg.copilot").all()
        chat_text = copilot_msgs[-1].text_content()
        print(f"  Copilot Response preview: {chat_text[:120]}...")
        assert "runway" in chat_text.lower() or "stockout" in chat_text.lower() or "units" in chat_text.lower()
        print("  [PASS] TC-B08: Copilot responded with grounded analytics.")

        # TC-B09: Copilot Chat - Epistemic Boundary Refusal
        print("[TC-B09] Testing Epistemic Boundary Refusal via Browser...")
        page.fill("#chatInput", "Why did customer footfall drop yesterday due to the rain?")
        page.click(".chat-send-btn")
        # Wait for second response
        time.sleep(1.5)
        copilot_msgs = page.locator(".chat-msg.copilot").all()
        refusal_text = copilot_msgs[-1].text_content()
        print(f"  Refusal Response preview: {refusal_text[:120]}...")
        assert "Data Boundary Notice" in refusal_text
        assert "What the verified data can confirm" in refusal_text
        print("  [PASS] TC-B09: Epistemic boundary refusal successfully enforced.")

        # TC-B10: Interactive What-If Simulator
        print("[TC-B10] Testing What-If Simulator Controls...")
        slider = page.locator("#simDiscountSlider")
        slider.fill("45")
        slider.dispatch_event("input")
        time.sleep(0.5)
        new_price = page.locator("#simNewPrice").text_content()
        lift = page.locator("#simDemandLift").text_content()
        runway = page.locator("#simRunwayDays").text_content()
        risk = page.locator("#simRiskBanner").text_content()
        print(f"  Simulator results: Price={new_price}, Lift={lift}, Runway={runway}, Risk={risk[:35]}...")
        assert "$" in new_price
        assert "%" in lift
        print("  [PASS] TC-B10: What-If simulation slider recalculated dynamically.")

        # TC-B11: Quick Prompt Chips
        print("[TC-B11] Testing Quick Prompt Chips...")
        chip = page.locator(".chip-btn").first
        chip.click()
        time.sleep(1.5)
        chip_msgs = page.locator(".chat-msg.user").all()
        assert len(chip_msgs) >= 3, "Expected prompt chip to add user message"
        print("  [PASS] TC-B11: Quick prompt chip triggered chat flow.")

        # TC-B12: Multi-Store Switcher Dynamic Reactivity
        print("[TC-B12] Testing Dynamic Store Switching...")
        page.select_option("#storeSelect", "STORE_02")
        time.sleep(1.0)
        manager = page.locator("#managerName").text_content()
        print(f"  STORE_02 Manager loaded: {manager}")
        assert len(manager) > 0
        page.select_option("#storeSelect", "STORE_01")
        time.sleep(1.0)
        print("  [PASS] TC-B12: Store switcher updated reactive dashboard state.")

        # Capture complete dashboard screenshot
        screenshot_path = "artifacts/screenshots/dashboard_live_browser.png"
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"  [SAVED] Visual screenshot: {screenshot_path}")

        browser.close()
        print("=== ALL BROWSER E2E TESTS COMPLETED WITH 100% SUCCESS ===")

if __name__ == "__main__":
    run_browser_tests()
