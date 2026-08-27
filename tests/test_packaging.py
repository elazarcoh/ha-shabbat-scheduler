import json
from pathlib import Path

MANIFEST = Path("custom_components/shabbat_scheduler/manifest.json")


def test_hacs_json_declares_the_integration():
    hacs = json.loads(Path("hacs.json").read_text(encoding="utf-8"))
    assert hacs["name"]
    assert hacs["homeassistant"]


def test_manifest_has_a_version_for_hacs():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["version"]
    assert manifest["domain"] == "shabbat_scheduler"


def test_readme_is_not_empty():
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "Shabbat Scheduler" in readme
    assert len(readme.splitlines()) > 20


PURE_MODULES = (
    "models.py",
    "block.py",
    "device_ops.py",
    "const.py",
    "rule_schema.py",
    "yaml_io.py",
)


def test_the_pure_modules_import_zero_home_assistant():
    """A Global Constraint of the plan, until now enforced by memory alone.

    All the tricky logic lives in these modules precisely so it is testable
    without a running instance. `yaml_io` now imports `rule_schema`, so the
    boundary is one import away from being crossed transitively.
    """
    root = Path(__file__).parent.parent / "custom_components" / "shabbat_scheduler"
    offenders = {
        name: [
            line.strip()
            for line in (root / name).read_text(encoding="utf-8").splitlines()
            if line.startswith(("import ", "from ")) and "homeassistant" in line
        ]
        for name in PURE_MODULES
    }
    assert {name: lines for name, lines in offenders.items() if lines} == {}


# --- the hang guard guards itself ----------------------------------------


def test_the_timeout_plugin_is_actually_active(pytestconfig):
    """Without pytest-timeout, this suite HANGS rather than fails.

    `freezer` freezes `time.monotonic()`, which IS the asyncio event
    loop's clock, so any `await asyncio.sleep(n)` reached under a frozen
    clock never returns - and neither does `asyncio.wait_for`, whose own
    timeout is measured on that same frozen clock. The engine's retry is
    exactly such a sleep. One failing service call in a frozen test used
    to hang the entire run past 600s instead of failing it. SIGALRM is
    measured on real time and cannot be fooled that way, which is the
    whole reason `timeout_method = "signal"` is not the default here.

    The failure mode this test exists for is QUIET: if pytest-timeout is
    ever absent, pytest treats `timeout`/`timeout_method` as unknown
    options and only WARNS, so the settings evaporate and the hang comes
    back with nothing to say why. `getini` raises for an unregistered
    option, so this fails loudly instead.

    It reads the LIVE config rather than pyproject.toml's text on purpose:
    a value that is written down but not in force is exactly the state
    being guarded against.
    """
    # pytest-timeout registers `timeout` as a STRING ini option, so this
    # coerces rather than comparing to the int in pyproject.toml.
    assert float(pytestconfig.getini("timeout")) == 60.0
    # Not "thread": a thread-based timeout cannot interrupt a coroutine
    # blocked on a frozen event loop, which is the only case that matters.
    assert pytestconfig.getini("timeout_method") == "signal"


def test_pytest_timeout_is_declared_not_merely_inherited():
    """It resolves today only through pytest-homeassistant-custom-component.

    If that transitive edge ever drops, the guard above disappears with
    it - so the dependency is declared outright, and this pins that.
    """
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    assert "pytest-timeout" in pyproject, (
        "pytest-timeout must be an explicit dev dependency; without it the "
        "suite's timeout settings become unknown options and it hangs."
    )
