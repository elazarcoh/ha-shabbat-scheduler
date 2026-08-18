import dataclasses
from datetime import date, datetime, time, timezone

import pytest

from custom_components.shabbat_scheduler.models import (
    Action,
    Block,
    Conflict,
    EREV,
    ResolvedRule,
    Rule,
)


def test_rule_defaults():
    rule = Rule(id="r1", profile=1, day=EREV, time=time(23, 0), action=Action.OFF)
    assert rule.enabled is True
    assert rule.devices == ()
    assert rule.settings == {}
    assert rule.replay_on_restart is False


def test_action_is_str_enum():
    assert Action.ON == "on"
    assert Action("off") is Action.OFF


def test_block_is_frozen():
    block = Block(
        candle_lighting=datetime(2026, 8, 14, 18, 44, tzinfo=timezone.utc),
        havdalah=datetime(2026, 8, 15, 20, 1, tzinfo=timezone.utc),
        length=1,
        erev_date=date(2026, 8, 14),
        day_dates=(date(2026, 8, 15),),
    )
    assert block.length == 1
    try:
        block.length = 2
    except Exception as err:  # frozen dataclass raises FrozenInstanceError
        assert "frozen" in type(err).__name__.lower()
    else:
        raise AssertionError("Block should be immutable")


def test_resolved_rule_and_conflict_construct():
    rule = Rule(id="r1", profile=1, day="1", time=time(11, 0), action=Action.ON)
    resolved = ResolvedRule(
        when=datetime(2026, 8, 15, 11, 0, tzinfo=timezone.utc), rule=rule
    )
    assert resolved.rule.id == "r1"

    conflict = Conflict(
        profile=1, day="1", time=time(11, 0), device="climate.a", rule_ids=("r1", "r2")
    )
    assert conflict.rule_ids == ("r1", "r2")


def test_rule_is_frozen():
    rule = Rule(id="r1", profile=1, day=EREV, time=time(23, 0), action=Action.OFF)
    with pytest.raises(dataclasses.FrozenInstanceError):
        rule.enabled = False


def test_rule_replace_produces_a_new_rule():
    rule = Rule(id="r1", profile=1, day=EREV, time=time(23, 0), action=Action.OFF)
    updated = dataclasses.replace(rule, enabled=False)
    assert updated.enabled is False
    assert rule.enabled is True
    assert updated is not rule
