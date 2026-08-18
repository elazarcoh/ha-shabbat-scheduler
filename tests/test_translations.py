import json
from pathlib import Path

COMPONENT = Path("custom_components/shabbat_scheduler")
SERVICES = ("simulate", "set_dry_run", "export_yaml", "import_yaml")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_strings_covers_the_abort_reason():
    strings = _load(COMPONENT / "strings.json")
    assert "single_instance_allowed" in strings["config"]["abort"]


def test_strings_covers_every_service():
    strings = _load(COMPONENT / "strings.json")
    assert set(strings["services"]) == set(SERVICES)


def test_english_translation_matches_strings():
    assert _load(COMPONENT / "strings.json") == _load(
        COMPONENT / "translations/en.json"
    )


def test_hebrew_translation_has_the_same_shape():
    strings = _load(COMPONENT / "strings.json")
    hebrew = _load(COMPONENT / "translations/he.json")
    assert set(hebrew["config"]["abort"]) == set(strings["config"]["abort"])
    assert set(hebrew["services"]) == set(strings["services"])
