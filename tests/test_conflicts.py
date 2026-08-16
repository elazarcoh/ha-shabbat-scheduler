from datetime import time

from custom_components.shabbat_scheduler.block import find_conflicts
from custom_components.shabbat_scheduler.models import Action, Rule


def _rule(rule_id, action, devices=("climate.a",), day="1", at=time(18, 0), profile=1):
    return Rule(
        id=rule_id, profile=profile, day=day, time=at,
        action=action, devices=devices,
    )


def test_opposing_actions_on_one_device_conflict():
    conflicts = find_conflicts([_rule("a", Action.ON), _rule("b", Action.OFF)])
    assert len(conflicts) == 1
    assert conflicts[0].device == "climate.a"
    assert set(conflicts[0].rule_ids) == {"a", "b"}


def test_identical_actions_are_not_conflicts():
    assert find_conflicts([_rule("a", Action.OFF), _rule("b", Action.OFF)]) == []


def test_different_times_are_not_conflicts():
    assert find_conflicts(
        [_rule("a", Action.ON), _rule("b", Action.OFF, at=time(19, 0))]
    ) == []


def test_different_devices_are_not_conflicts():
    assert find_conflicts(
        [_rule("a", Action.ON), _rule("b", Action.OFF, devices=("climate.b",))]
    ) == []


def test_different_profiles_are_not_conflicts():
    assert find_conflicts(
        [_rule("a", Action.ON), _rule("b", Action.OFF, profile=2)]
    ) == []


def test_disabled_rules_do_not_conflict():
    enabled = _rule("a", Action.ON)
    disabled = Rule(
        id="b", profile=1, day="1", time=time(18, 0),
        action=Action.OFF, devices=("climate.a",), enabled=False,
    )
    assert find_conflicts([enabled, disabled]) == []


def test_custom_rules_are_excluded():
    custom = Rule(
        id="b", profile=1, day="1", time=time(18, 0),
        action=Action.CUSTOM, devices=("climate.a",), script="script.x",
    )
    assert find_conflicts([_rule("a", Action.ON), custom]) == []


def test_conflict_detected_per_shared_device():
    conflicts = find_conflicts([
        _rule("a", Action.ON, devices=("climate.a", "climate.b")),
        _rule("b", Action.OFF, devices=("climate.b",)),
    ])
    assert len(conflicts) == 1
    assert conflicts[0].device == "climate.b"
