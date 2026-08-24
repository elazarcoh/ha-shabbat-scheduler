"""Restart catch-up as opt-in replay.

v1's catch-up asked "what state should this device be in now?" - which
only worked because it understood `hvac_mode`/`temperature`/`fan_mode`. An
opaque service call has no queryable desired state, so that question
cannot be asked any more. Replay is explicit instead: the rule's author
says what is safe to repeat (`Rule.replay.enabled`), bounded by how stale
it may be (`Rule.replay.within`), and still guarded by the rule's own
condition. See engine.py's `async_catch_up`.
"""

from datetime import date, datetime, time, timedelta

import pytest
from freezegun import freeze_time
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.shabbat_scheduler.const import CANDLE_SENSOR, HAVDALAH_SENSOR
from custom_components.shabbat_scheduler.engine import ShabbatEngine
from custom_components.shabbat_scheduler.models import Replay, Rule
from custom_components.shabbat_scheduler.store import RuleStore

# A block entirely in the future relative to whatever "today" the suite
# happens to run on, so `_upcoming` (built from the real clock at refresh
# time) is never accidentally already-past. Friday candle lighting ->
# Saturday havdalah, Israel summer time (+03:00), one full day.
_CANDLE = "2026-08-28T15:44:00+00:00"     # 18:44 local, Friday
_HAVDALAH = "2026-08-29T17:01:00+00:00"   # 20:01 local, Saturday
_DAY_1 = date(2026, 8, 29)
_LOCAL_OFFSET = timedelta(hours=3)  # Israel summer time


def _local(clock: str) -> str:
    """A UTC instant for the given local (Israel, +03:00) clock time on day 1."""
    hour, minute = (int(part) for part in clock.split(":"))
    local_dt = datetime.combine(_DAY_1, time(hour, minute))
    return (local_dt - _LOCAL_OFFSET).strftime("%Y-%m-%dT%H:%M:%S+00:00")


@pytest.fixture
async def engine(hass, jerusalem):
    store = RuleStore(hass)
    await store.async_load()
    eng = ShabbatEngine(hass, store)
    yield eng
    # async_refresh schedules a timer per upcoming rule; several of these
    # tests leave rules still in the future, so without this the
    # pytest-homeassistant plugin fails every test in this module at
    # teardown over a lingering timer that has nothing to do with replay.
    await eng.async_shutdown()


def _set_zmanim(hass) -> None:
    hass.states.async_set(CANDLE_SENSOR, _CANDLE)
    hass.states.async_set(HAVDALAH_SENSOR, _HAVDALAH)


def _rule(rule_id, at: time, entity_id: str, replay: Replay = Replay(), condition=()):
    return Rule(
        id=rule_id, profile=1, day="1", time=at,
        action="input_boolean.turn_on",
        target={"entity_id": [entity_id]},
        replay=replay,
        condition=condition,
    )


async def _prepare(engine, hass, rules):
    _set_zmanim(hass)
    await engine.store.async_set_enabled(True)
    await engine.store.async_replace_all({}, rules)
    await engine.async_refresh()  # unfrozen: block computation only reads sensors


async def test_only_opted_in_rules_replay(hass, engine, test_booleans):
    await _prepare(engine, hass, [
        Rule(
            id="on11", profile=1, day="1", time=time(11, 0),
            action="input_boolean.turn_on",
            target={"entity_id": ["input_boolean.t"]},
            replay=Replay(enabled=True),
        ),
        Rule(
            id="on12", profile=1, day="1", time=time(12, 0),
            action="input_boolean.turn_on",
            target={"entity_id": ["input_boolean.salon"]},
            # replay NOT opted in - default Replay()
        ),
    ])

    with freeze_time(_local("14:00")):  # mid-block, both rules already passed
        await engine.async_catch_up()
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.t").state == "on"      # opted in
    assert hass.states.get("input_boolean.salon").state == "off"  # not opted in


async def test_replays_happen_in_time_order(hass, engine, test_booleans):
    calls = async_mock_service(hass, "input_boolean", "turn_on")
    await _prepare(engine, hass, [
        _rule("at11", time(11, 0), "input_boolean.salon", Replay(enabled=True)),
        _rule("at09", time(9, 0), "input_boolean.t", Replay(enabled=True)),
    ])

    with freeze_time(_local("14:00")):
        await engine.async_catch_up()
    await hass.async_block_till_done()

    assert [c.data["entity_id"] for c in calls] == [
        ["input_boolean.t"],       # 09:00 rule, fires first
        ["input_boolean.salon"],   # 11:00 rule, fires second
    ]


async def test_a_rule_older_than_its_window_is_skipped_and_reported(hass, engine):
    """An 11:00 rule replayed at 23:00 is worse than not replayed."""
    calls = async_mock_service(hass, "input_boolean", "turn_on")
    await _prepare(engine, hass, [
        _rule(
            "on11", time(11, 0), "input_boolean.t",
            Replay(enabled=True, within=timedelta(hours=2)),
        ),
    ])

    with freeze_time(_local("23:00")):
        results = await engine.async_catch_up()
    await hass.async_block_till_done()

    assert any(r["outcome"] == "skipped_stale" for r in results)
    assert calls == []


async def test_a_rule_inside_its_window_is_replayed(hass, engine, test_booleans):
    calls = async_mock_service(hass, "input_boolean", "turn_on")
    await _prepare(engine, hass, [
        _rule(
            "on11", time(11, 0), "input_boolean.t",
            Replay(enabled=True, within=timedelta(hours=2)),
        ),
    ])

    with freeze_time(_local("12:00")):
        await engine.async_catch_up()
    await hass.async_block_till_done()

    assert len(calls) == 1


async def test_no_window_means_no_bound(hass, engine, test_booleans):
    """v1 behaviour, preserved for migrated rules."""
    calls = async_mock_service(hass, "input_boolean", "turn_on")
    await _prepare(engine, hass, [
        _rule("on11", time(11, 0), "input_boolean.t", Replay(enabled=True, within=None)),
    ])

    with freeze_time(_local("23:00")):
        await engine.async_catch_up()
    await hass.async_block_till_done()

    assert len(calls) == 1


async def test_a_rule_whose_condition_fails_is_not_replayed(hass, engine, test_booleans):
    hass.states.async_set("binary_sensor.gate", "off")
    calls = async_mock_service(hass, "input_boolean", "turn_on")
    await _prepare(engine, hass, [
        _rule(
            "on11", time(11, 0), "input_boolean.t", Replay(enabled=True),
            condition=({"condition": "state", "entity_id": "binary_sensor.gate",
                        "state": "on"},),
        ),
    ])

    with freeze_time(_local("14:00")):
        await engine.async_catch_up()
    await hass.async_block_till_done()

    assert calls == []


async def test_future_rules_are_not_replayed_only_armed(hass, engine, test_booleans):
    calls = async_mock_service(hass, "input_boolean", "turn_on")
    await _prepare(engine, hass, [
        _rule("on18", time(18, 0), "input_boolean.t", Replay(enabled=True)),
    ])

    with freeze_time(_local("14:00")):
        await engine.async_catch_up()
    await hass.async_block_till_done()

    assert calls == []
    assert engine.upcoming()


async def test_catch_up_still_happens_at_most_once_per_block(hass, engine, test_booleans):
    calls = async_mock_service(hass, "input_boolean", "turn_on")
    await _prepare(engine, hass, [
        _rule("on11", time(11, 0), "input_boolean.t", Replay(enabled=True)),
    ])

    with freeze_time(_local("14:00")):
        await engine.async_catch_up()
        await engine.async_catch_up()
    await hass.async_block_till_done()

    assert len(calls) == 1


def test_desired_state_at_is_gone():
    """It could only work because v1 understood climate attributes."""
    import custom_components.shabbat_scheduler.block as block

    assert not hasattr(block, "desired_state_at")


def test_the_action_enum_is_finally_gone():
    """v1's three-value vocabulary is what made this a climate controller.

    Kept alive since Task 1 only because block.py, device_ops.py and
    engine.py referenced it at module level, and an unimportable package
    makes every test in the repo uncollectable. This task removes the
    last consumer, so it goes.
    """
    import custom_components.shabbat_scheduler.models as models

    assert not hasattr(models, "Action")
