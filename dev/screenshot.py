"""Screenshot the card, for the README.

Not a test - a one-shot tool. Uses the same login-flow pattern
e2e/conftest.py uses to get a working token into the page before any
frontend script runs, because injecting it after a `goto()` is too late.

The `hassTokens` shape below matches e2e/conftest.py's `page` fixture
exactly (access_token, token_type, expires_in, hassUrl, clientId,
expires, refresh_token) - that is the shape actually proven to get past
Home Assistant's frontend auth check, not a guess.
"""

import json
import sys
import urllib.request

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8124"


def _post(path: str, payload) -> dict:
    request = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(payload).encode() if isinstance(payload, dict)
        else payload.encode(),
        headers={"Content-Type": "application/json" if isinstance(payload, dict)
                  else "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode())


def mint_token() -> str:
    flow = _post("/auth/login_flow", {
        "client_id": BASE, "handler": ["homeassistant", None],
        "redirect_uri": BASE, "type": "authorize",
    })
    step = _post(f"/auth/login_flow/{flow['flow_id']}", {
        "client_id": BASE, "username": "dev", "password": "devdevdev",
    })
    token = _post(
        "/auth/token",
        f"grant_type=authorization_code&code={step['result']}&client_id={BASE}",
    )
    return token["access_token"]


def main() -> None:
    token = mint_token()
    out_path = sys.argv[1] if len(sys.argv) > 1 else "docs/images/card-screenshot.png"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 900, "height": 700})
        # Same shape as e2e/conftest.py's `page` fixture - see module
        # docstring. Injected via add_init_script so it lands before the
        # frontend's first script runs; setting it after goto() is too
        # late, the frontend has already redirected to /auth/authorize.
        context.add_init_script(f"""
            localStorage.setItem('hassTokens', JSON.stringify({{
              access_token: {json.dumps(token)},
              token_type: 'Bearer',
              expires_in: 1800,
              hassUrl: {json.dumps(BASE)},
              clientId: {json.dumps(BASE)},
              expires: 9999999999999,
              refresh_token: ''
            }}));
        """)
        page = context.new_page()
        page.goto(f"{BASE}/shabbat-scheduler/0")
        page.wait_for_selector("shabbat-scheduler-card", timeout=15_000)
        page.wait_for_timeout(1_000)  # let the day groups finish rendering
        page.locator("shabbat-scheduler-card").screenshot(path=out_path)
        browser.close()

    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
