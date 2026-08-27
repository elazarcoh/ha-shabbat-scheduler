"""Screenshot the card in Hebrew, for the README.

One-shot tool, not a test. Same token-injection pattern as screenshot.py,
plus the same 'selectedLanguage' localStorage override
test_the_card_lays_out_right_to_left_in_hebrew (e2e/test_card_e2e.py) uses
- HA's own frontend.set_user_data language doesn't round-trip in time for
first paint on this release, so the localStorage key is what actually
works.
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
            localStorage.setItem('selectedLanguage', JSON.stringify('he'));
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
