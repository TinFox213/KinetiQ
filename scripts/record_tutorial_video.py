import os
import sys
import time
import shutil
from playwright.sync_api import sync_playwright

def record_tutorial():
    output_dir = os.path.abspath("artifacts/videos")
    os.makedirs(output_dir, exist_ok=True)

    print("[RECORDER] Launching browser with video recording enabled...")
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=output_dir,
            record_video_size={"width": 1280, "height": 720}
        )
        page = context.new_page()

        print("[RECORDER] Navigating to KinetiQ Login Portal...")
        page.goto("http://localhost:8000", wait_until="networkidle")
        page.wait_for_timeout(2000)

        # 1. Hover over Quick Demo cards
        cards = page.query_selector_all(".quick-demo-card")
        for card in cards:
            card.hover()
            page.wait_for_timeout(800)

        # 2. Click Store Manager Quick Demo Login
        print("[RECORDER] Clicking Store Manager Quick Demo Login...")
        page.click(".role-store_manager .btn-quick-login")
        page.wait_for_selector("#dashboardView", state="visible", timeout=10000)
        page.wait_for_timeout(2500)

        # 3. Explore Morning Scorecard and Action Queue
        print("[RECORDER] Reviewing Morning Scorecard and Action Queue...")
        page.hover("#kpiDeadCapital")
        page.wait_for_timeout(1000)
        page.click("[data-tab='deadStock']")
        page.wait_for_timeout(1500)
        page.click("[data-tab='surges']")
        page.wait_for_timeout(1500)
        page.click("[data-tab='rebalance']")
        page.wait_for_timeout(2000)

        # 4. Switch to Supply Chain Director
        print("[RECORDER] Switching Role to Supply Chain Director...")
        page.select_option("#roleSwitcherSelect", "supply_chain_director")
        page.wait_for_timeout(2500)

        # Commit an inter-store transfer if available
        commit_btn = page.query_selector(".btn-commit-action")
        if commit_btn:
            commit_btn.click()
            page.wait_for_timeout(2000)

        # 5. Switch to Executive & CFO
        print("[RECORDER] Switching Role to Executive & CFO...")
        page.select_option("#roleSwitcherSelect", "executive")
        page.wait_for_timeout(2500)

        # 6. Interact with What-If Simulator Slider
        print("[RECORDER] Interacting with What-If Price Elasticity Simulator...")
        slider = page.query_selector("#simDiscountSlider")
        if slider:
            slider.evaluate("el => { el.value = 30; el.dispatchEvent(new Event('input')); }")
            page.wait_for_timeout(2000)

        # 7. Conversational Copilot Chat
        print("[RECORDER] Interacting with Grounded Copilot...")
        chat_input = page.query_selector("#chatInput")
        if chat_input:
            chat_input.fill("What is the top stockout risk this week and what is the locked capital in INR?")
            page.click("#btnSendChat")
            page.wait_for_timeout(3500)

        # 8. Open Tutorial Video Modal Demo
        print("[RECORDER] Opening Tutorial Video Modal...")
        page.click("#btnOpenTutorialModal")
        page.wait_for_timeout(2500)
        page.click("#btnCloseTutorialModal")
        page.wait_for_timeout(1500)

        # Finalize and close context
        print("[RECORDER] Finalizing video recording...")
        page.close()
        video_path = page.video.path()
        context.close()
        browser.close()

        final_dest = os.path.join(output_dir, "kinetiq_tutorial_walkthrough.webm")
        if os.path.exists(video_path):
            shutil.copy(video_path, final_dest)
            # Copy to static for web playback
            static_dest = os.path.join("public", "static", "kinetiq_tutorial_walkthrough.webm")
            os.makedirs(os.path.dirname(static_dest), exist_ok=True)
            shutil.copy(video_path, static_dest)
            
            # Also copy to frontend/dist for local serving
            dist_dest = os.path.join("frontend", "dist", "kinetiq_tutorial_walkthrough.webm")
            shutil.copy(video_path, dist_dest)
            
            print(f"[RECORDER] Successfully generated tutorial video: {final_dest} ({os.path.getsize(final_dest)} bytes)")

if __name__ == "__main__":
    record_tutorial()
