from datetime import time, timedelta

import pytest
import yaml

from custom_components.shabbat_scheduler.models import EREV, Replay, Rule
from custom_components.shabbat_scheduler.yaml_io import export_yaml, import_yaml


def _rules():
    return [
        Rule(id="a", profile=1, day=EREV, time=time(23, 0),
             action="switch.turn_off", target={"entity_id": ["climate.a"]}),
        Rule(id="b", profile=1, day="1", time=time(11, 0),
             action="switch.turn_on", target={"entity_id": ["climate.a"]},
             name="בוקר שבת"),
    ]


def test_export_groups_by_profile_and_day():
    parsed = yaml.safe_load(export_yaml({}, _rules()))
    assert set(parsed["profiles"]["1_day"]) == {"erev", "day_1"}
    assert parsed["profiles"]["1_day"]["erev"][0]["at"] == "23:00:00"
    assert parsed["profiles"]["1_day"]["day_1"][0]["name"] == "בוקר שבת"


def test_round_trip_preserves_rules():
    defaults, rules = import_yaml(
        export_yaml({"data": {"temperature": 26}}, _rules())
    )
    assert defaults == {"data": {"temperature": 26}}
    assert {(r.profile, r.day, r.time, r.action) for r in rules} == {
        (1, EREV, time(23, 0), "switch.turn_off"),
        (1, "1", time(11, 0), "switch.turn_on"),
    }
    assert {r.id for r in rules} == {"a", "b"}


def test_export_writes_hebrew_unescaped_in_raw_text():
    text = export_yaml({}, _rules())
    assert "בוקר שבת" in text
    assert "\\u" not in text


def test_export_orders_erev_before_numbered_days():
    keys = list(yaml.safe_load(export_yaml({}, _rules()))["profiles"]["1_day"])
    assert keys.index("erev") < keys.index("day_1")


def test_a_v2_rule_round_trips():
    """A full v2 rule - action, target, data, condition and replay - all
    survive an export/import cycle with the same id.
    """
    rules = [Rule(id="a", profile=1, day="1", time=time(11, 0),
                  action="climate.set_temperature",
                  target={"entity_id": ["climate.salon"]},
                  data={"temperature": 26},
                  condition=({"condition": "state", "entity_id": "x", "state": "on"},),
                  replay=Replay(enabled=True, within=timedelta(hours=2)))]
    _defaults, back = import_yaml(export_yaml({}, rules))
    assert back[0] == rules[0]


def test_the_window_survives_as_a_duration():
    """`replay.within` round-trips as 'HH:MM:SS', not as a raw number of
    seconds - Task 5's bug, where the store briefly wrote seconds while
    the API accepted only 'HH:MM:SS' and a read-then-write was rejected.
    """
    rules = [Rule(id="a", profile=1, day="1", time=time(11, 0),
                  action="switch.turn_on",
                  replay=Replay(enabled=True, within=timedelta(hours=2)))]
    text = export_yaml({}, rules)
    assert "02:00:00" in text
    _defaults, back = import_yaml(text)
    assert back[0].replay.within == timedelta(hours=2)


def test_an_empty_condition_is_not_written():
    text = export_yaml({}, [Rule(id="a", profile=1, day="1", time=time(11, 0),
                                  action="switch.turn_on")])
    assert "condition" not in text


def test_empty_target_and_data_are_not_written():
    text = export_yaml({}, [Rule(id="a", profile=1, day="1", time=time(11, 0),
                                  action="switch.turn_on")])
    assert "target" not in text
    assert "data" not in text


def test_default_replay_is_not_written():
    text = export_yaml({}, [Rule(id="a", profile=1, day="1", time=time(11, 0),
                                  action="switch.turn_on")])
    assert "replay" not in text


def test_a_v1_file_is_rejected_with_a_useful_message():
    """Not silently half-imported."""
    with pytest.raises(ValueError, match="v1"):
        import_yaml("profiles:\n  1_day:\n    day_1:\n"
                    "      - {id: a, at: '11:00:00', action: 'on', devices: [climate.x]}\n")


def test_import_honours_existing_id():
    text = """
defaults: {}
profiles:
  2_day:
    day_2:
      - id: "existing-id"
        at: "18:00"
        action: "switch.turn_off"
        target: {entity_id: [climate.a]}
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
        action: "switch.turn_off"
        target: {entity_id: [climate.a]}
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


def _one_rule(profile_key: str, day_key: str) -> str:
    return f"""
defaults: {{}}
profiles:
  {profile_key}:
    {day_key}:
      - at: "23:00"
        action: "switch.turn_off"
        target: {{entity_id: [climate.a]}}
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


# --- defaults are now {target, data}, the same shape merge_defaults reads ---


def test_import_rejects_a_non_mapping_target_default():
    with pytest.raises(ValueError):
        import_yaml("defaults:\n  target: not_a_dict\n")


def test_import_rejects_a_bare_string_data_default():
    with pytest.raises(ValueError):
        import_yaml("defaults:\n  data: climate.a\n")


def test_import_rejects_an_unknown_defaults_key():
    """Only `target` and `data` mean anything to merge_defaults.

    Anything else silently did nothing, which is worse than being told.
    """
    with pytest.raises(ValueError):
        import_yaml("defaults:\n  temperature: 26\n")


def test_import_rejects_a_non_mapping_defaults_block():
    with pytest.raises(ValueError):
        import_yaml("defaults: not_a_mapping\n")


def test_import_keeps_a_valid_nested_defaults_block():
    defaults, _rules = import_yaml(
        "defaults:\n  target: {entity_id: [climate.a]}\n  data: {temperature: 26}\n"
    )
    assert list(defaults["target"]["entity_id"]) == ["climate.a"]
    assert defaults["data"] == {"temperature": 26}


# --- The YAML door gets the same typing the API door got ---


def test_import_rejects_a_quoted_false_for_enabled():
    """`enabled: "false"` is a truthy STRING, and the rule used to run.

    The quoted form is what you get from a careless hand-edit or a YAML
    dumper that stringifies. It displayed as off in every UI and fired
    anyway - the exact silent failure this project exists to avoid.
    """
    text = (
        'profiles:\n  1_day:\n    day_1:\n'
        '      - {id: r1, at: "11:00:00", action: "switch.turn_on", enabled: "false"}\n'
    )
    with pytest.raises(ValueError):
        import_yaml(text)


def test_import_rejects_a_misspelt_key():
    """`temperture` used to be dropped in silence."""
    text = (
        'profiles:\n  1_day:\n    day_1:\n'
        '      - {id: r1, at: "11:00:00", action: "switch.turn_on", temperture: 26}\n'
    )
    with pytest.raises(ValueError):
        import_yaml(text)


def test_import_rejects_a_non_string_name():
    text = (
        'profiles:\n  1_day:\n    day_1:\n'
        '      - {id: r1, at: "11:00:00", action: "switch.turn_on", name: {a: b}}\n'
    )
    with pytest.raises(ValueError):
        import_yaml(text)


def test_import_rejects_a_rule_with_no_at():
    text = 'profiles:\n  1_day:\n    day_1:\n      - {id: r1, action: "switch.turn_on"}\n'
    with pytest.raises(ValueError):
        import_yaml(text)


def test_import_rejects_an_invalid_action_shape():
    text = 'profiles:\n  1_day:\n    day_1:\n      - {id: r1, at: "11:00:00", action: sideways}\n'
    with pytest.raises(ValueError):
        import_yaml(text)


def test_import_still_accepts_a_real_boolean_enabled():
    _defaults, rules = import_yaml(
        'profiles:\n  1_day:\n    day_1:\n'
        '      - {id: r1, at: "11:00:00", action: "switch.turn_on", enabled: false}\n'
    )
    assert rules[0].enabled is False


# --- I4: the export must be able to carry an UNMIGRATED rule, and the ----
#     import must not destroy it. `docs/known-behaviours.md` sent the user
#     here to read `migration_source`, and the round trip both failed to
#     show it and permanently deleted it - along with `migration_error`,
#     which is the flag the repair issue is derived from, so following the
#     documented advice also deleted the warning.


def _unmigrated_stub():
    """What the v1 -> v2 migration actually writes for a rule it could not
    convert: a disabled stub pointing at a service that does not exist,
    plus the two fields that are the only record of why and of what the
    original rule was."""
    return Rule(
        id="d", profile=1, day="1", time=time(11, 0),
        action="shabbat_scheduler.unmigrated",
        enabled=False,
        name="broken",
        migration_error="a custom rule with no script has nothing to call",
        migration_source={
            "id": "d", "profile": 1, "day": "1", "time": "11:00:00",
            "action": "custom", "script": None, "variables": {"minutes": 30},
        },
    )


def test_the_export_carries_the_migration_record():
    """The documented inspection route: export the rule set and read
    `migration_source` directly."""
    entry = yaml.safe_load(
        export_yaml({}, [_unmigrated_stub()])
    )["profiles"]["1_day"]["day_1"][0]
    assert entry["migration_error"] == (
        "a custom rule with no script has nothing to call"
    )
    assert entry["migration_source"]["script"] is None
    assert entry["migration_source"]["variables"] == {"minutes": 30}


def test_an_unmigrated_stub_survives_a_round_trip_intact():
    """The documented RECOVERY route used to be destructive: import ->
    async_replace_all replaced every rule with one whose migration fields
    were both None, so every stub the user did not fix in that one pass
    lost its stashed v1 payload permanently and its repair warning with
    it."""
    stub = _unmigrated_stub()
    _defaults, back = import_yaml(export_yaml({}, [stub]))
    assert back == [stub]


def test_a_migration_record_is_not_written_when_there_is_none():
    """A healthy rule set must not grow two null keys per rule."""
    entry = yaml.safe_load(export_yaml({}, _rules()))["profiles"]["1_day"]["erev"][0]
    assert "migration_error" not in entry
    assert "migration_source" not in entry


def test_the_v1_fields_inside_a_stashed_migration_source_are_not_rejected():
    """`migration_source` is a verbatim v1 rule, so it is full of exactly
    the keys `_check_unknown_fields` rejects by name at the top level. The
    guard is per-level, and this pins that: the v1-field rejection must
    still fire for a real v1 document (the test above this section) while a
    stashed one rides through untouched."""
    _defaults, back = import_yaml(export_yaml({}, [_unmigrated_stub()]))
    assert back[0].migration_source["action"] == "custom"


def test_the_import_still_rejects_a_forged_migration_error_shape():
    """Preserved is not unvalidated: the fields are typed on the way in
    like every other."""
    text = yaml.safe_dump(
        {
            "defaults": {},
            "profiles": {"1_day": {"day_1": [
                {"id": "d", "at": "11:00:00", "action": "switch.turn_on",
                 "migration_error": {"he": "nope"}}
            ]}},
        }
    )
    with pytest.raises(ValueError, match="migration_error"):
        import_yaml(text)


def test_a_forged_migration_source_shape_is_rejected_too():
    text = yaml.safe_dump(
        {
            "defaults": {},
            "profiles": {"1_day": {"day_1": [
                {"id": "d", "at": "11:00:00", "action": "switch.turn_on",
                 "migration_source": "the original rule"}
            ]}},
        }
    )
    with pytest.raises(ValueError, match="migration_source"):
        import_yaml(text)


def test_the_api_door_still_drops_the_migration_fields():
    """The seam. `_READ_ONLY_FIELDS` exists so a websocket CLIENT cannot
    forge a `migration_error` - it echoes the whole rule back on a
    read-modify-write, and a forged one would add its rule to the repair
    issue and make the card claim the migration failed. That protection is
    unchanged; only `yaml_io`, which round-trips storage rather than
    accepting a client edit, opts in."""
    from custom_components.shabbat_scheduler.rule_schema import (
        changes_from_api,
        rule_from_api,
    )

    payload = {
        "profile": 1, "day": "1", "time": "11:00:00", "action": "switch.turn_on",
        "migration_error": "forged", "migration_source": {"forged": True},
    }
    built = rule_from_api(payload, "x")
    assert built.migration_error is None
    assert built.migration_source is None
    assert "migration_error" not in changes_from_api(payload)
    assert "migration_source" not in changes_from_api(payload)
