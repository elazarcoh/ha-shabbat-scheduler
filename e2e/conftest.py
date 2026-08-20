"""End-to-end fixtures. Skips entirely when the dev container is down."""

import os
import urllib.error
import urllib.request

import pytest

BASE = "http://127.0.0.1:8124"


@pytest.fixture(autouse=True)
def _real_sockets(socket_enabled):
    """Undo pytest-homeassistant-custom-component's global socket block.

    That plugin is a dev dependency of tests/ and registers itself
    globally (pytest11 entry point), so its pytest_runtest_setup hook
    disables all sockets before *every* test in the whole run - including
    these, which is exactly the network e2e needs to reach the Docker
    container and drive a real browser. Depending on pytest-socket's own
    `socket_enabled` fixture is the documented way HA's own test suite
    re-enables real networking for a test; making it autouse here applies
    it to every test collected under e2e/ without each test asking for it
    by name. It has no effect outside this directory.
    """


def _up() -> bool:
    try:
        urllib.request.urlopen(f"{BASE}/", timeout=3)
    except (urllib.error.URLError, OSError):
        return False
    return True


@pytest.fixture(scope="session")
def base_url() -> str:
    if not _up():
        pytest.skip("dev container is not running; see dev/README.md")
    return BASE


def _token_works(value: str) -> bool:
    """Does this token still authenticate?"""
    request = urllib.request.Request(
        f"{BASE}/api/config", headers={"Authorization": f"Bearer {value}"}
    )
    try:
        urllib.request.urlopen(request, timeout=5)
    except (urllib.error.URLError, OSError):
        return False
    return True


@pytest.fixture(scope="session")
def token() -> str:
    """A token that actually works, or a skip that says why.

    An EXPIRED token is checked for, not just a missing one. The tokens
    minted from an auth-code exchange last 30 minutes, and an expired one
    does not fail loudly: Home Assistant closes the websocket with a
    normal 1000, the frontend never finishes loading, and every test in
    this directory dies on a 30-second Playwright timeout with nothing
    pointing at the cause. That misdiagnoses as "the card is broken" -
    it cost a real debugging cycle once - so it is worth one HTTP call
    to say the true thing instead.
    """
    value = os.environ.get("HA_DEV_TOKEN")
    if not value:
        pytest.skip("HA_DEV_TOKEN is not set; see dev/README.md")
    if not _token_works(value):
        pytest.skip(
            "HA_DEV_TOKEN is rejected - it has most likely expired "
            "(they last 30 minutes). Mint a fresh one; see dev/README.md"
        )
    return value


@pytest.fixture
def page(base_url, token):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context()
        # The token must be injected BEFORE any page script runs. Setting
        # it after a goto is too late: the frontend has already redirected
        # to /auth/authorize by then.
        context.add_init_script(
            f"""
            localStorage.setItem('hassTokens', JSON.stringify({{
              access_token: '{token}',
              token_type: 'Bearer',
              expires_in: 1800,
              hassUrl: '{base_url}',
              clientId: '{base_url}',
              expires: 9999999999999,
              refresh_token: ''
            }}));
            """
        )
        yield context.new_page()
        browser.close()
