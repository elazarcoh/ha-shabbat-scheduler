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


def _collect_key_paths(obj, prefix=()):
    """Recursively collect all key paths in a nested dict structure."""
    paths = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            current_path = prefix + (key,)
            paths.add(current_path)
            paths.update(_collect_key_paths(value, current_path))
    return paths


def test_hebrew_translation_has_the_same_shape():
    strings = _load(COMPONENT / "strings.json")
    hebrew = _load(COMPONENT / "translations/he.json")
    strings_paths = _collect_key_paths(strings)
    hebrew_paths = _collect_key_paths(hebrew)
    assert strings_paths == hebrew_paths
