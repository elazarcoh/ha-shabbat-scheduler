from datetime import time, timedelta

import pytest

from custom_components.shabbat_scheduler.models import Replay, Rule


def _rule(**over):
    base = dict(
        id="r1", profile=1, day="1", time=time(11, 0),
        action="climate.set_temperature",
        target={"entity_id": ["climate.salon"]},
        data={"temperature": 26},
    )
    base.update(over)
    return Rule(**base)


def test_a_rule_is_a_service_call():
    rule = _rule()
    assert rule.action == "climate.set_temperature"
    assert rule.target == {"entity_id": ["climate.salon"]}
    assert rule.data == {"temperature": 26}


def test_a_rule_needs_no_condition_or_replay():
    rule = _rule()
    assert rule.condition == ()
    assert rule.replay == Replay()
    assert rule.replay.enabled is False
    assert rule.replay.within is None


def test_replay_carries_its_window():
    rule = _rule(replay=Replay(enabled=True, within=timedelta(hours=2)))
    assert rule.replay.enabled is True
    assert rule.replay.within == timedelta(hours=2)


def test_a_rule_is_immutable():
    rule = _rule()
    with pytest.raises(Exception):
        rule.action = "switch.turn_on"


def test_the_action_enum_is_gone():
    """v1's three-value vocabulary is what made this a climate controller."""
    import custom_components.shabbat_scheduler.models as models

    assert not hasattr(models, "Action")
