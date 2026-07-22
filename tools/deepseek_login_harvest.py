#!/usr/bin/env python3
"""Local-only DeepSeek login + session harvester.

Credentials are read from environment variables or prompted securely. They are
never written to disk. The resulting browser session token is saved to the
normal Dulus auth file for local testing.

Usage:
  export DEEPSEEK_EMAIL='your-email'
  export DEEPSEEK_PASSWORD='your-password'
  python tools/deepseek_login_harvest.py

Set DULUS_DEEPSEEK_HEADLESS=0 to watch the browser window.
"""
from __future__ import annotations

import getpass
import json
import os
import pathlib
import time
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

OUT = pathlib.Path.home() / ".dulus" / "deepseek_web.json"
PROFILE = pathlib.Path.home() / ".dulus" / "playwright" / "deepseek-login"
MARKER = "DULUS_SESSION_CAPTURE"


def _credential(name: str, secret: bool = False) -> str:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    return (getpass.getpass(f"{name}: ") if secret else input(f"{name}: ")).strip()


def main() -> int:
    email = _credential("DEEPSEEK_EMAIL")
    password = _credential("DEEPSEEK_PASSWORD", secret=True)
    if not email or not password:
        raise SystemExit("Email and password are required")

    headless = os.environ.get("DULUS_DEEPSEEK_HEADLESS", "0").lower() in (
        "1", "true", "yes", "on"
    )
    captured: dict = {}
    PROFILE.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE),
            headless=headless,
            executable_path=os.environ.get("DULUS_BROWSER_EXECUTABLE") or None,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            viewport={"width": 1400, "height": 900},
        )
        page = browser.pages[0] if browser.pages else browser.new_page()

        def on_request(request):
            if "chat.deepseek.com" not in request.url or request.method != "POST":
                return
            if "/chat/completion" not in request.url:
                return
            auth = request.headers.get("authorization", "")
            if not auth:
                return
            captured["token"] = auth.removeprefix("Bearer ").strip()
            captured["headers"] = dict(request.headers)
            captured["url"] = request.url
            try:
                body = json.loads(request.post_data or "{}")
                captured["model"] = body.get("model", "deepseek_v3")
                captured["chat_session_id"] = body.get("chat_session_id")
            except Exception:
                pass
            print("DeepSeek completion payload captured")

        page.on("request", on_request)
        page.goto("https://chat.deepseek.com/", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)

        # Fill login only when the page exposes login fields. If the persistent
        # profile is already authenticated, this block is skipped.
        email_box = page.locator('input[type="email"]').first
        password_box = page.locator('input[type="password"]').first
        if email_box.count() and password_box.count():
            email_box.fill(email)
            password_box.fill(password)
            buttons = page.locator("button")
            clicked = False
            for label in ("Log in", "Login", "Sign in", "Se connecter", "登录"):
                button = buttons.filter(has_text=label).first
                if button.count():
                    button.click()
                    clicked = True
                    break
            if not clicked:
                password_box.press("Enter")
            page.wait_for_timeout(5000)
            print("Login submitted; complete any CAPTCHA or 2FA in the browser if requested")

        # Send a harmless marker to trigger the authenticated completion request.
        inputs = [
            'textarea[placeholder*="message" i]',
            'textarea[placeholder*="ask" i]',
            'textarea',
            '[contenteditable="true"]',
        ]
        chat_input = None
        for selector in inputs:
            candidate = page.locator(selector).first
            if candidate.count() and candidate.is_visible():
                chat_input = candidate
                break
        if chat_input is None:
            diagnostic = pathlib.Path('/tmp/deepseek-login-diagnostic.png')
            page.screenshot(path=str(diagnostic), full_page=True)
            print(f"DeepSeek page: {page.url} | title: {page.title()}")
            print(f"Diagnostic screenshot: {diagnostic}")
            raise RuntimeError("DeepSeek chat input was not found; complete login in the browser")
        chat_input.fill(MARKER)
        chat_input.press("Enter")

        deadline = time.time() + 120
        while time.time() < deadline and not captured.get("token"):
            page.wait_for_timeout(500)
        if not captured.get("token"):
            raise RuntimeError("No authenticated DeepSeek completion request was captured")

        captured["cookies"] = browser.cookies()
        captured["harvested_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(captured, indent=2), encoding="utf-8")
        print(f"Saved local DeepSeek session to {OUT}")
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
