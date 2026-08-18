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
