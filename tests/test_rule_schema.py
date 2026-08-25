from datetime import time, timedelta

import pytest

from custom_components.shabbat_scheduler.models import Replay
from custom_components.shabbat_scheduler.rule_schema import (
    RuleValidationError,
    changes_from_api,
    rule_from_api,
    validate_defaults,
)

BASE = {
    "profile": 1, "day": "1", "time": "11:00:00",
    "action": "climate.set_temperature",
}


def test_builds_a_rule():
    rule = rule_from_api(BASE, "generated-id")
    assert rule.id == "generated-id"
    assert rule.profile == 1
    assert rule.day == "1"
    assert rule.time == time(11, 0)
    assert rule.action == "climate.set_temperature"


def test_client_supplied_id_is_ignored():
    rule = rule_from_api({**BASE, "id": "client-chosen"}, "generated-id")
    assert rule.id == "generated-id"


def test_erev_is_a_valid_day():
    from custom_components.shabbat_scheduler.models import EREV
    assert rule_from_api({**BASE, "day": EREV}, "x").day == EREV


@pytest.mark.parametrize(
    "bad",
    [
        {"day": "dya_1"},
        {"day": "0"},
        {"day": "4"},
        {"profile": 0},
        {"profile": 4},
        {"time": "nonsense"},
    ],
)
def test_malformed_input_is_rejected(bad):
    with pytest.raises(RuleValidationError):
        rule_from_api({**BASE, **bad}, "x")


def test_changes_validates_only_supplied_keys():
    assert changes_from_api({"enabled": False}) == {"enabled": False}
    assert changes_from_api({"time": "18:00:00"})["time"] == time(18, 0)


def test_changes_rejects_id():
    with pytest.raises(RuleValidationError):
        changes_from_api({"id": "nope"})


def test_changes_rejects_unknown_field():
    with pytest.raises(RuleValidationError):
        changes_from_api({"colour": "red"})


def test_action_must_look_like_a_service():
    for bad in ["climate", "climate.", ".turn_on", "", "climate.set.temp", 7]:
        with pytest.raises(RuleValidationError):
            rule_from_api({**BASE, "action": bad}, "r1")


def test_a_valid_action_is_accepted():
    rule = rule_from_api({**BASE, "action": "scene.turn_on"}, "r1")
    assert rule.action == "scene.turn_on"


def test_target_and_data_must_be_mappings():
    with pytest.raises(RuleValidationError):
        rule_from_api({**BASE, "target": ["climate.salon"]}, "r1")
    with pytest.raises(RuleValidationError):
        rule_from_api({**BASE, "data": "temperature=26"}, "r1")


def test_condition_must_be_a_list_of_mappings():
    with pytest.raises(RuleValidationError):
        rule_from_api({**BASE, "condition": {"condition": "state"}}, "r1")
    rule = rule_from_api(
        {**BASE, "condition": [{"condition": "state", "entity_id": "x", "state": "on"}]},
        "r1",
    )
    assert len(rule.condition) == 1


def test_replay_parses_its_window():
    rule = rule_from_api({**BASE, "replay": {"enabled": True, "within": "02:00:00"}}, "r1")
    assert rule.replay.enabled is True
    assert rule.replay.within == timedelta(hours=2)


def test_replay_enabled_must_be_a_real_boolean():
    """A JS form yielding the string "false" used to render off and RUN."""
    with pytest.raises(RuleValidationError):
        rule_from_api({**BASE, "replay": {"enabled": "false"}}, "r1")


def test_replay_within_must_be_a_duration():
    with pytest.raises(RuleValidationError):
        rule_from_api({**BASE, "replay": {"enabled": True, "within": "soon"}}, "r1")


def test_replay_defaults_to_off_with_no_window():
    rule = rule_from_api(BASE, "r1")
    assert rule.replay == Replay()


def test_the_v1_fields_are_rejected_outright():
    """Silently ignoring them would hide a half-migrated rule."""
    for gone in ("devices", "settings", "script", "variables", "replay_on_restart"):
        with pytest.raises(RuleValidationError):
            rule_from_api({**BASE, gone: "anything"}, "r1")


def test_defaults_take_target_and_data():
    assert validate_defaults({"target": {"entity_id": ["climate.a"]}, "data": {"temperature": 26}})
    with pytest.raises(RuleValidationError):
        validate_defaults({"devices": ["climate.a"]})


# --- Task 11: `last_outcome` is server-owned and not a rule field ---------


def test_a_forged_last_outcome_is_dropped_from_a_create():
    """Dropped, not rejected - and never stored.

    `_state_payload` hands `last_outcome` out on every rule, so a client
    that reads a rule and writes it back sends it whether it means to or
    not: rejecting it would refuse an honest edit for a field the client
    never chose. But it must not land either - a client that could set it
    would make the card claim a rule fired when it never ran.
    """
    rule = rule_from_api(
        {**BASE, "last_outcome": {"outcome": "called", "at": "x", "detail": None}},
        "r1",
    )
    # Not a `Rule` field at all: the outcome map lives in the store, keyed
    # by rule id. Asserted by absence, so an implementation that quietly
    # grew the field would fail here rather than pass by coincidence.
    assert not hasattr(rule, "last_outcome")


def test_a_forged_last_outcome_is_dropped_from_a_partial_update():
    changes = changes_from_api(
        {"name": "renamed",
         "last_outcome": {"outcome": "called", "at": "x", "detail": None}}
    )
    assert changes == {"name": "renamed"}
    assert "last_outcome" not in changes


def test_yaml_import_cannot_smuggle_a_last_outcome_either():
    """`keep_server_fields` is for `migration_error`/`migration_source` only.

    A YAML document is a serialised store, which is why those two survive
    an import - the documented way to inspect an unmigrated rule is to
    export it. A verdict about last Shabbat is not part of the schedule
    anybody authors, so this opt-in must NOT widen to cover it. It is the
    branch a client can reach through the `import_yaml` service, and the
    only test that drives it.
    """
    rule = rule_from_api(
        {
            **BASE,
            "migration_error": "kept",
            "last_outcome": {"outcome": "called", "at": "x", "detail": None},
        },
        "r1",
        keep_server_fields=True,
    )
    assert rule.migration_error == "kept"   # still preserved, deliberately
    assert not hasattr(rule, "last_outcome")


def test_the_profile_bound_matches_the_shared_constant():
    from custom_components.shabbat_scheduler.const import MAX_PROFILE, MIN_PROFILE
    from custom_components.shabbat_scheduler.rule_schema import _profile

    assert _profile(MAX_PROFILE) == MAX_PROFILE
    with pytest.raises(RuleValidationError):
        _profile(MAX_PROFILE + 1)
    with pytest.raises(RuleValidationError):
        _profile(MIN_PROFILE - 1)
