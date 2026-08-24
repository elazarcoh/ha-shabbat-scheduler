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


def test_the_action_enum_still_exists_for_now():
    """Deliberately NOT deleted yet - see the note below.

    `Action` is dead to `Rule` as of this task, but `block.py`,
    `device_ops.py` and `engine.py` still reference it at module level.
    Deleting it here makes `custom_components/shabbat_scheduler/__init__.py`
    unimportable, and because `tests/conftest.py` imports from that
    package, EVERY test in the repo becomes uncollectable - which would
    leave Tasks 2-11 with no way to run their own tests. It dies in
    Task 8, once its last consumer is gone.
    """
    import custom_components.shabbat_scheduler.models as models

    assert hasattr(models, "Action")
