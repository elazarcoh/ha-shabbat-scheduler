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


@pytest.fixture(scope="session")
def token() -> str:
    value = os.environ.get("HA_DEV_TOKEN")
    if not value:
        pytest.skip("HA_DEV_TOKEN is not set; run dev/seed.py")
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
