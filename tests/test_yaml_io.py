from datetime import time

import yaml

from custom_components.shabbat_scheduler.models import EREV, Rule
from custom_components.shabbat_scheduler.yaml_io import export_yaml, import_yaml


def _rules():
    return [
        Rule(id="a", profile=1, day=EREV, time=time(23, 0), action="off",
             devices=("climate.a",)),
        Rule(id="b", profile=1, day="1", time=time(11, 0), action="on",
             devices=("climate.a",), name="בוקר שבת"),
    ]


def test_export_groups_by_profile_and_day():
    parsed = yaml.safe_load(export_yaml({"temperature": 26}, _rules()))
    assert parsed["defaults"] == {"temperature": 26}
    assert set(parsed["profiles"]["1_day"]) == {"erev", "day_1"}
    assert parsed["profiles"]["1_day"]["erev"][0]["at"] == "23:00:00"
    assert parsed["profiles"]["1_day"]["day_1"][0]["name"] == "בוקר שבת"


def test_round_trip_preserves_rules():
    # The nested form README documents. A flat `{"temperature": 26}` used to
    # round-trip, but it never meant anything - merge_defaults only reads
    # `devices` and `settings` - and import now rejects it rather than
    # persisting a default that silently does nothing (final review C2).
    defaults, rules = import_yaml(
        export_yaml({"settings": {"temperature": 26}}, _rules())
    )
    assert defaults == {"settings": {"temperature": 26}}
    assert {(r.profile, r.day, r.time, r.action) for r in rules} == {
        (1, EREV, time(23, 0), "off"),
        (1, "1", time(11, 0), "on"),
    }
    assert {r.id for r in rules} == {"a", "b"}


def test_export_writes_hebrew_unescaped_in_raw_text():
    text = export_yaml({"temperature": 26}, _rules())
    assert "בוקר שבת" in text
    assert "\\u" not in text


def test_export_orders_erev_before_numbered_days():
    keys = list(yaml.safe_load(export_yaml({}, _rules()))["profiles"]["1_day"])
    assert keys.index("erev") < keys.index("day_1")


def test_import_honours_existing_id():
    text = """
defaults: {}
profiles:
  2_day:
    day_2:
      - id: "existing-id"
        at: "18:00"
        action: "off"
        devices: [climate.a]
"""
    _defaults, rules = import_yaml(text)
    assert len(rules) == 1
    assert rules[0].id == "existing-id"


def test_import_generates_ids_when_absent():
    text = """
defaults: {}
profiles:
  2_day:
    day_2:
      - at: "18:00"
        action: "off"
        devices: [climate.a]
"""
    _defaults, rules = import_yaml(text)
    assert len(rules) == 1
    assert rules[0].id
    assert rules[0].profile == 2
    assert rules[0].day == "2"
    assert rules[0].time == time(18, 0)


def test_import_accepts_empty_document():
    defaults, rules = import_yaml("")
    assert defaults == {}
    assert rules == []


# --- Final review C3: an unvalidated day key used to brick the integration -

import pytest


def _one_rule(profile_key: str, day_key: str) -> str:
    return f"""
defaults: {{}}
profiles:
  {profile_key}:
    {day_key}:
      - at: "23:00"
        action: "off"
        devices: [climate.a]
"""


def test_import_rejects_an_unrecognised_day_key():
    """`dya_1` used to pass straight through into .storage.

    block.py then does int(rule.day) unguarded, so every later setup raised -
    and so did export_yaml, leaving the user unable even to dump their rules
    to find the typo. Recovery meant hand-editing .storage.
    """
    with pytest.raises(ValueError):
        import_yaml(_one_rule("1_day", "dya_1"))


def test_import_rejects_a_non_positive_day_number():
    with pytest.raises(ValueError):
        import_yaml(_one_rule("1_day", "day_0"))


def test_import_rejects_a_non_numeric_day_number():
    with pytest.raises(ValueError):
        import_yaml(_one_rule("1_day", "day_erev"))


def test_import_rejects_an_unrecognised_profile_key():
    with pytest.raises(ValueError):
        import_yaml(_one_rule("one_day", "day_1"))


def test_import_accepts_yaml_1_1_booleans_for_actions():
    """Unquoted `action: on` is what a human writes; YAML 1.1 makes it True.

    Export always quotes, so only hand-edited documents hit this - and they
    used to fail with a bare "'True' is not a valid Action".
    """
    text = """
defaults: {}
profiles:
  1_day:
    day_1:
      - at: "11:00"
        action: on
      - at: "23:00"
        action: off
"""
    _defaults, rules = import_yaml(text)
    assert [rule.action for rule in rules] == ["on", "off"]


# --- Final review C2: unvalidated defaults used to brick the integration ---


def test_import_rejects_a_non_mapping_settings_default():
    """`settings: not_a_dict` used to be written straight to .storage.

    merge_defaults then did `{**"not_a_dict"}` on every setup, so the entry
    could never load again without hand-editing .storage - and nothing ran
    on Shabbat with nothing to say why. Validated with the same guard the
    websocket API uses, at the door.
    """
    with pytest.raises(ValueError):
        import_yaml("defaults:\n  settings: not_a_dict\n")


def test_import_rejects_a_bare_string_devices_default():
    with pytest.raises(ValueError):
        import_yaml("defaults:\n  devices: climate.a\n")


def test_import_rejects_an_unknown_defaults_key():
    """Only `devices` and `settings` mean anything to merge_defaults.

    Anything else silently did nothing, which is worse than being told.
    """
    with pytest.raises(ValueError):
        import_yaml("defaults:\n  temperature: 26\n")


def test_import_rejects_a_non_mapping_defaults_block():
    with pytest.raises(ValueError):
        import_yaml("defaults: not_a_mapping\n")


def test_import_keeps_a_valid_nested_defaults_block():
    defaults, _rules = import_yaml(
        "defaults:\n  devices: [climate.a]\n  settings: {temperature: 26}\n"
    )
    assert list(defaults["devices"]) == ["climate.a"]
    assert defaults["settings"] == {"temperature": 26}


# --- The YAML door gets the same typing the API door got ---


def test_import_rejects_a_quoted_false_for_enabled():
    """`enabled: "false"` is a truthy STRING, and the rule used to run.

    The quoted form is what you get from a careless hand-edit or a YAML
    dumper that stringifies. It displayed as off in every UI and fired
    anyway - the exact silent failure this project exists to avoid.
    """
    text = (
        'profiles:\n  1_day:\n    day_1:\n'
        '      - {id: r1, at: "11:00:00", action: "on", enabled: "false"}\n'
    )
    with pytest.raises(ValueError):
        import_yaml(text)


def test_import_rejects_a_custom_action_with_no_script():
    """It used to import, and then do precisely nothing, forever."""
    text = (
        'profiles:\n  1_day:\n    day_1:\n'
        '      - {id: r1, at: "11:00:00", action: custom}\n'
    )
    with pytest.raises(ValueError):
        import_yaml(text)


def test_import_rejects_a_misspelt_key():
    """`temperture` used to be dropped in silence."""
    text = (
        'profiles:\n  1_day:\n    day_1:\n'
        '      - {id: r1, at: "11:00:00", action: "on", temperture: 26}\n'
    )
    with pytest.raises(ValueError):
        import_yaml(text)


def test_import_rejects_a_non_string_name():
    text = (
        'profiles:\n  1_day:\n    day_1:\n'
        '      - {id: r1, at: "11:00:00", action: "on", name: {a: b}}\n'
    )
    with pytest.raises(ValueError):
        import_yaml(text)


def test_import_rejects_a_rule_with_no_at():
    text = 'profiles:\n  1_day:\n    day_1:\n      - {id: r1, action: "on"}\n'
    with pytest.raises(ValueError):
        import_yaml(text)


def test_import_still_accepts_a_real_boolean_enabled():
    _defaults, rules = import_yaml(
        'profiles:\n  1_day:\n    day_1:\n'
        '      - {id: r1, at: "11:00:00", action: "on", enabled: false}\n'
    )
    assert rules[0].enabled is False


def test_import_still_accepts_unquoted_yaml_booleans_for_action():
    """`action: on` parses as True. Hand-writing that must keep working."""
    _defaults, rules = import_yaml(
        'profiles:\n  1_day:\n    day_1:\n      - {id: r1, at: "11:00:00", action: on}\n'
    )
    assert rules[0].action == "on"
