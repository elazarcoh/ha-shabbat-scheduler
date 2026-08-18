from datetime import time

import pytest

from custom_components.shabbat_scheduler.models import Action, EREV
from custom_components.shabbat_scheduler.rule_schema import (
    RuleValidationError,
    changes_from_api,
    rule_from_api,
)

VALID = {
    "profile": 1,
    "day": "1",
    "time": "11:00:00",
    "action": "on",
    "devices": ["climate.a"],
    "settings": {"temperature": 26},
}


def test_builds_a_rule():
    rule = rule_from_api(VALID, "generated-id")
    assert rule.id == "generated-id"
    assert rule.profile == 1
    assert rule.day == "1"
    assert rule.time == time(11, 0)
    assert rule.action is Action.ON
    assert rule.devices == ("climate.a",)


def test_client_supplied_id_is_ignored():
    rule = rule_from_api({**VALID, "id": "client-chosen"}, "generated-id")
    assert rule.id == "generated-id"


def test_erev_is_a_valid_day():
    assert rule_from_api({**VALID, "day": EREV}, "x").day == EREV


@pytest.mark.parametrize(
    "bad",
    [
        {"day": "dya_1"},
        {"day": "0"},
        {"day": "4"},
        {"profile": 0},
        {"profile": 4},
        {"time": "nonsense"},
        {"action": "sideways"},
    ],
)
def test_malformed_input_is_rejected(bad):
    with pytest.raises(RuleValidationError):
        rule_from_api({**VALID, **bad}, "x")


def test_custom_action_requires_a_script():
    with pytest.raises(RuleValidationError):
        rule_from_api({**VALID, "action": "custom"}, "x")


def test_custom_action_with_a_script_is_accepted():
    rule = rule_from_api(
        {**VALID, "action": "custom", "script": "script.demo"}, "x"
    )
    assert rule.action is Action.CUSTOM
    assert rule.script == "script.demo"


def test_changes_validates_only_supplied_keys():
    assert changes_from_api({"enabled": False}) == {"enabled": False}
    assert changes_from_api({"time": "18:00:00"})["time"] == time(18, 0)


def test_changes_rejects_id():
    with pytest.raises(RuleValidationError):
        changes_from_api({"id": "nope"})


def test_changes_rejects_unknown_field():
    with pytest.raises(RuleValidationError):
        changes_from_api({"colour": "red"})


# Tests for Fix Round 1 issues

def test_validate_rule_rejects_custom_without_script():
    """validate_rule should reject a rule with custom action but no script."""
    from custom_components.shabbat_scheduler.rule_schema import validate_rule
    from custom_components.shabbat_scheduler.models import Rule

    rule = Rule(
        id="x",
        profile=1,
        day="1",
        time=time(11, 0),
        action=Action.CUSTOM,
        devices=(),
        settings={},
        name=None,
        icon=None,
        enabled=True,
        script=None,
        variables={},
        replay_on_restart=False,
        color=None,
    )
    with pytest.raises(RuleValidationError):
        validate_rule(rule)


def test_validate_rule_accepts_custom_with_script():
    """validate_rule should accept a rule with custom action and script."""
    from custom_components.shabbat_scheduler.rule_schema import validate_rule
    from custom_components.shabbat_scheduler.models import Rule

    rule = Rule(
        id="x",
        profile=1,
        day="1",
        time=time(11, 0),
        action=Action.CUSTOM,
        devices=(),
        settings={},
        name=None,
        icon=None,
        enabled=True,
        script="script.demo",
        variables={},
        replay_on_restart=False,
        color=None,
    )
    validate_rule(rule)  # Should not raise


def test_day_rejects_unicode_digits():
    """Unicode digits like Arabic-Indic should be rejected."""
    with pytest.raises(RuleValidationError):
        rule_from_api({**VALID, "day": "٣"}, "x")


def test_profile_rejects_boolean():
    """Boolean True/False should be rejected even though bool is a subclass of int."""
    with pytest.raises(RuleValidationError):
        rule_from_api({**VALID, "profile": True}, "x")


def test_profile_rejects_float():
    """Floats should be rejected, not truncated."""
    with pytest.raises(RuleValidationError):
        rule_from_api({**VALID, "profile": 2.9}, "x")


def test_devices_rejects_string():
    """String should be rejected; devices must be a list or tuple."""
    with pytest.raises(RuleValidationError):
        rule_from_api({**VALID, "devices": "climate.a"}, "x")


def test_settings_rejects_non_mapping():
    """Non-mapping values should be rejected with RuleValidationError."""
    with pytest.raises(RuleValidationError):
        rule_from_api({**VALID, "settings": "nope"}, "x")


def test_variables_rejects_non_mapping():
    """Non-mapping values should be rejected with RuleValidationError."""
    with pytest.raises(RuleValidationError):
        rule_from_api({**VALID, "variables": "nope"}, "x")
