"""End-to-end fixtures. Skips entirely when the dev container is down."""

import os
import urllib.error
import urllib.request

import pytest
import pytest_socket

BASE = "http://127.0.0.1:8124"

_HERE = os.path.dirname(os.path.abspath(__file__))


def _is_e2e(report) -> bool:
    """Is this report for a test in THIS directory?

    The hook below runs for the whole session - `uv run pytest` collects
    tests/ as well - so the tally has to be limited to e2e or a full run
    would never see "everything skipped".
    """
    path = str(getattr(report, "fspath", "") or "")
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    return os.path.dirname(path) == _HERE


def _e2e_all_skipped(terminalreporter) -> tuple[bool, list]:
    """Every e2e test skipped, and none of them actually ran - plus the
    skip reports themselves, for callers that want to say why.

    Shared by `pytest_terminal_summary` (prints the loud banner) and
    `pytest_sessionfinish` (fails the run in CI) so the two hooks cannot
    disagree about what "all skipped" means.
    """
    stats = terminalreporter.stats
    skipped = [r for r in stats.get("skipped", []) if _is_e2e(r)]
    if not skipped:
        return False, skipped
    # A test that actually ran has a `call` report; a test skipped during
    # setup never gets one. So "no call reports at all" is exactly "every
    # e2e test skipped", regardless of pass or fail.
    ran = [
        report
        for outcome in ("passed", "failed", "error")
        for report in stats.get(outcome, [])
        if _is_e2e(report) and getattr(report, "when", None) == "call"
    ]
    return not ran, skipped


def pytest_terminal_summary(terminalreporter) -> None:
    """Say out loud when e2e verified nothing.

    The skips themselves are correct - there is no dev container on a CI
    box and no token in a plain `uv run pytest` - but a silent skip is
    how this suite stayed RED, unnoticed, through an entire plan: every
    run said "N passed" for the Python suite and never mentioned that the
    only tests that exercise Home Assistant's own elements in a real
    browser had not run at all.

    Reasons are printed rather than a hard-coded "no HA_DEV_TOKEN",
    because a down container and an EXPIRED token skip for different
    reasons and the fix differs. See the `token` fixture.
    """
    all_skipped, skipped = _e2e_all_skipped(terminalreporter)
    if not all_skipped:
        return

    terminalreporter.write_sep(
        "=",
        "e2e: ALL TESTS SKIPPED - nothing about the card was verified",
        red=True,
        bold=True,
    )
    reasons = []
    for report in skipped:
        reason = report.longrepr[2] if isinstance(report.longrepr, tuple) else ""
        reason = str(reason).removeprefix("Skipped: ")
        if reason and reason not in reasons:
            reasons.append(reason)
    for reason in reasons or ["(no reason reported)"]:
        terminalreporter.write_line(f"e2e: {reason}", red=True)
    terminalreporter.write_line(
        f"e2e: {len(skipped)} test(s) skipped. See dev/README.md.", red=True
    )


def pytest_sessionfinish(session) -> None:
    """In CI ONLY, fail the run outright when e2e verified nothing.

    `pytest_terminal_summary` above already SAYS this out loud, but a
    loud banner is not a failure - the exact gap that let this suite stay
    RED, unnoticed, through an entire plan: every CI run still exited 0
    and reported "N passed" for the Python suite while the only tests
    that exercise the card in a real browser silently skipped. Printing
    was necessary but not sufficient; this makes it load-bearing.

    Gated on `CI` (which GitHub Actions sets for every job, and nothing
    else does) rather than applying unconditionally, because outside CI
    this is the correct, EXPECTED outcome: a developer running `uv run
    pytest` locally with no dev container up and no `HA_DEV_TOKEN` set
    should get a clean skip with the banner above, not a failing test
    run for a container they never intended to start.

    `terminalreporter.stats` is populated by `pytest_runtest_logreport`
    as each test finishes running - well before any `sessionfinish` hook
    fires - so reading it here is safe regardless of hook ordering
    between this and the terminal reporter's own summary.
    """
    if not os.environ.get("CI"):
        return
    terminalreporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if terminalreporter is None:
        return
    all_skipped, _ = _e2e_all_skipped(terminalreporter)
    if all_skipped:
        session.exitstatus = 1


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

    This alone is NOT sufficient for `base_url`/`token` below, and the
    `enable_socket()` calls in `_up`/`_token_works` are not redundant with
    it. Both plugins implement `pytest_runtest_setup`, and pytest-socket's
    own hook decides enable-vs-disable from the test's static
    `fixturenames` list - a decision that races the *same* hook on
    pytest's core runner, which is what actually instantiates
    session-scoped fixtures. Which one wins is plugin registration order,
    and that is NOT guaranteed across environments: a freshly-`uv sync`-ed
    CI runner and a long-lived local .venv with identical locked package
    versions were observed to order pytest-socket differently relative to
    that runner hook, so `_up()`'s very first request failed with
    `HASocketBlockedError` in CI while the exact same suite, same
    versions, passed locally - the same class of nondeterminism already
    on record for `aiohttp_client` in pyproject.toml's `-p no:aiohttp`
    comment, here hitting a different pair of plugins. This fixture still
    covers anything else under e2e/ that touches a real socket from a
    *function*-scoped fixture or a test body, where ordering happens to
    not matter for the fixtures actually in this suite - but `base_url`
    and `token` are session-scoped and must not depend on hook order.
    """


def _up() -> bool:
    # Do not rely on pytest-socket's own hook having already run - see
    # `_real_sockets` above. Calling enable_socket() directly is
    # order-independent: it just restores the real socket.socket.
    pytest_socket.enable_socket()
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
    pytest_socket.enable_socket()  # see _up()
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
    # Same reasoning as `_up()`/`_token_works()` above: this fixture's own
    # setup is exactly where the pytest-socket-vs-runner-hook race can
    # land, and on a freshly-`uv sync`-ed CI runner it did - every test
    # errored here with HASocketBlockedError before this call was added,
    # because launching a real Chromium and connecting to it needs real
    # sockets too, not just the HTTP calls in base_url/token. The
    # `_real_sockets` autouse fixture's `socket_enabled` request was not
    # enough to guarantee this ran first; a direct, order-independent call
    # is.
    pytest_socket.enable_socket()
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
