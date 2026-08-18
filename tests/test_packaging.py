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
