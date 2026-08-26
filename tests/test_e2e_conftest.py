"""Unit tests for e2e/conftest.py's CI-only session-exitstatus hook.

Plain unit tests against fake report/session objects, not e2e tests
themselves - they need no dev container and no browser, so they run on
every `uv run pytest`, CI included, and can actually prove the hook does
what it claims without spinning up the real e2e suite to do it.
"""

import os
from types import SimpleNamespace

from e2e.conftest import _HERE, _e2e_all_skipped, pytest_sessionfinish


def _skip_report(reason: str = "dev container is not running; see dev/README.md"):
    return SimpleNamespace(
        fspath=os.path.join(_HERE, "test_card_e2e.py"),
        longrepr=("", 0, f"Skipped: {reason}"),
    )


def _ran_report():
    return SimpleNamespace(
        fspath=os.path.join(_HERE, "test_card_e2e.py"),
        when="call",
    )


class _FakeTerminalReporter:
    def __init__(self, stats: dict):
        self.stats = stats


class _FakePluginManager:
    def __init__(self, terminalreporter):
        self._terminalreporter = terminalreporter

    def get_plugin(self, name):
        assert name == "terminalreporter"
        return self._terminalreporter


class _FakeSession:
    def __init__(self, terminalreporter):
        self.config = SimpleNamespace(
            pluginmanager=_FakePluginManager(terminalreporter)
        )
        self.exitstatus = 0


def test_all_skipped_true_when_every_e2e_test_skipped_and_none_ran():
    reporter = _FakeTerminalReporter({"skipped": [_skip_report()]})
    all_skipped, skipped = _e2e_all_skipped(reporter)
    assert all_skipped is True
    assert len(skipped) == 1


def test_all_skipped_false_when_nothing_was_collected_under_e2e():
    reporter = _FakeTerminalReporter({})
    all_skipped, skipped = _e2e_all_skipped(reporter)
    assert all_skipped is False
    assert skipped == []


def test_all_skipped_false_when_at_least_one_e2e_test_actually_ran():
    reporter = _FakeTerminalReporter(
        {"skipped": [_skip_report()], "passed": [_ran_report()]}
    )
    all_skipped, _ = _e2e_all_skipped(reporter)
    assert all_skipped is False


def test_sessionfinish_fails_the_run_in_ci_when_all_e2e_skipped(monkeypatch):
    monkeypatch.setenv("CI", "true")
    session = _FakeSession(_FakeTerminalReporter({"skipped": [_skip_report()]}))

    pytest_sessionfinish(session)

    assert session.exitstatus == 1


def test_sessionfinish_does_not_touch_exitstatus_outside_ci(monkeypatch):
    monkeypatch.delenv("CI", raising=False)
    session = _FakeSession(_FakeTerminalReporter({"skipped": [_skip_report()]}))

    pytest_sessionfinish(session)

    assert session.exitstatus == 0


def test_sessionfinish_leaves_exitstatus_alone_in_ci_when_a_test_ran(monkeypatch):
    monkeypatch.setenv("CI", "true")
    session = _FakeSession(
        _FakeTerminalReporter({"skipped": [_skip_report()], "passed": [_ran_report()]})
    )

    pytest_sessionfinish(session)

    assert session.exitstatus == 0
