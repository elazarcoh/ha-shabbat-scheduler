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
from pytest_homeassistant_custom_component.common import (
    async_capture_events,
    async_mock_service,
)

from custom_components.shabbat_scheduler.const import (
    CANDLE_SENSOR,
    EVENT_RULE_COMPLETED,
    HAVDALAH_SENSOR,
)
from custom_components.shabbat_scheduler.engine import ShabbatEngine
from custom_components.shabbat_scheduler.logbook import async_describe_events
from custom_components.shabbat_scheduler.models import Replay, Rule
from custom_components.shabbat_scheduler.store import RuleStore

# A block entirely in the future relative to whatever "today" the suite
# happens to run on, so `_upcoming` (built from the real clock at refresh
# time) is never accidentally already-past. Friday candle lighting ->
# Saturday havdalah, Israel summer time (+03:00), one full day.
#
# A hardcoded CALENDAR date, not an offset from "now" - which is exactly
# why this needed bumping TWICE already:
# - 2026-08-31: this file's own two non-frozen tests,
#   test_a_future_rule_with_replay_off_reports_nothing_at_all and
#   test_future_rules_are_not_replayed_only_armed, failed the moment the
#   real date passed 2026-08-29. Bumped one week forward.
# - 2026-09-05: the SAME two tests, same reason - one week of margin was
#   not enough; the real date passed 2026-09-05 (this bump's own target
#   day) less than a week later. That is the second time this exact
#   comment's own prediction ("if this rots again, bump it forward
#   again") came true almost immediately, which is worth more margin
#   than another single week: bumped FOUR weeks forward this time (28
#   days - a multiple of 7, so the weekdays and every `_local` offset
#   below stay exactly as they were).
# - 2026-10-05: rotted a third time. Bumped 520 weeks (ten years: still a
#   multiple of 7, still Israel summer time) so it stops being a chore.
# A relative `dt_util.now() + timedelta(...)` would need every literal
# below (`_local`, any other date arithmetic in this file) re-verified
# against a non-frozen `now` at collection time - a bigger change than a
# date bump, and one worth doing if this rots a third time.
_CANDLE = "2036-09-19T15:44:00+00:00"     # 18:44 local, Friday
_HAVDALAH = "2036-09-20T17:01:00+00:00"   # 20:01 local, Saturday
_DAY_1 = date(2036, 9, 20)
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


async def test_a_stale_skip_fires_its_own_event_and_reaches_the_logbook(hass, engine):
    """A stale skip used to fire NO event at all.

    `async_catch_up` appended the result and `continue`d, so
    `async_apply_rule` - the only thing that fires anything - was never
    reached. The skip existed solely inside the aggregate `last_run`,
    which the next rule to run overwrites. Nothing durable said the rule
    had not been replayed.
    """
    events = async_capture_events(hass, EVENT_RULE_COMPLETED)
    described = {}
    async_describe_events(hass, lambda d, e, f: described.__setitem__(e, f))

    await _prepare(engine, hass, [
        _rule(
            "on11", time(11, 0), "input_boolean.t",
            Replay(enabled=True, within=timedelta(hours=2)),
        ),
    ])

    with freeze_time(_local("23:00")):
        await engine.async_catch_up()
    await hass.async_block_till_done()

    per_rule = [e for e in events if e.data.get("rule_id") == "on11"]
    assert len(per_rule) == 1
    assert per_rule[0].data["results"][0]["outcome"] == "skipped_stale"

    row = described[EVENT_RULE_COMPLETED](per_rule[0])["message"]
    assert "stale" in row.lower()
    assert "did not run" in row.lower()
    assert "on11" in row


async def test_a_rule_due_with_replay_off_is_reported_not_silently_skipped(
    hass, engine, test_booleans
):
    """The constraint violated on its DEFAULT path.

    Replay is off unless the author switched it on - the project owner's
    explicit decision - so this branch is what happens after every
    ordinary restart, and "why didn't my rules run?" is the question it
    exists to answer. It used to be a bare `continue`: no result, no
    event, no durable outcome, no logbook row. The near-identical
    `skipped_stale` branch one line below got all four, so this asserts
    all four here too.

    Reporting only. `calls` must stay empty: nothing about saying why a
    rule did not fire may make it fire.
    """
    calls = async_mock_service(hass, "input_boolean", "turn_on")
    events = async_capture_events(hass, EVENT_RULE_COMPLETED)
    described = {}
    async_describe_events(hass, lambda d, e, f: described.__setitem__(e, f))

    await _prepare(engine, hass, [
        # Constructed explicitly rather than relying on `Replay()`'s
        # default, so this test cannot be silently re-aimed if that
        # default ever changes.
        _rule("on11", time(11, 0), "input_boolean.t", Replay(enabled=False)),
    ])

    with freeze_time(_local("14:00")):
        results = await engine.async_catch_up()
    await hass.async_block_till_done()

    # 1. It fired nothing. That is the constraint, not a side note.
    assert calls == []

    # 2. A result exists, so the pass summary cannot claim nothing was due.
    assert [r["outcome"] for r in results] == ["skipped_no_replay"]

    # 3. A durable per-rule outcome, which is what the card reads.
    outcome = engine.store.last_outcome("on11")
    assert outcome is not None
    assert outcome["outcome"] == "skipped_no_replay"
    assert outcome["detail"] == "replay is switched off for this rule"

    # 4. Its own event, and a logbook row naming the rule and the reason.
    per_rule = [e for e in events if e.data.get("rule_id") == "on11"]
    assert len(per_rule) == 1
    assert per_rule[0].data["results"][0]["outcome"] == "skipped_no_replay"
    row = described[EVENT_RULE_COMPLETED](per_rule[0])["message"]
    assert "did not run" in row.lower()
    assert "replay is switched off" in row
    assert "on11" in row


async def test_the_catch_up_summary_cannot_claim_nothing_was_due(hass, engine):
    """The false statement the bare `continue` produced.

    Two rules were due and neither had opted in, and the summary row read
    "no rule was due for replay". Driven through the engine rather than
    through a hand-built payload, because the defect was that the engine
    produced an EMPTY results list - a logbook test alone could not have
    caught it.
    """
    events = async_capture_events(hass, EVENT_RULE_COMPLETED)
    described = {}
    async_describe_events(hass, lambda d, e, f: described.__setitem__(e, f))

    await _prepare(engine, hass, [
        _rule("on09", time(9, 0), "input_boolean.t", Replay(enabled=False)),
        _rule("on11", time(11, 0), "input_boolean.salon", Replay(enabled=False)),
    ])

    with freeze_time(_local("14:00")):
        await engine.async_catch_up()
    await hass.async_block_till_done()

    summary = [e for e in events if e.data.get("catch_up")]
    assert len(summary) == 1
    message = described[EVENT_RULE_COMPLETED](summary[0])["message"]
    assert "no rule was due for replay" not in message
    assert "2 due but replay is off" in message


async def test_a_future_rule_with_replay_off_reports_nothing_at_all(
    hass, engine, test_booleans
):
    """Only PAST-DUE rules are reported, and the guard order is why.

    A rule still in the future is armed, not skipped - saying "did not
    run" about a rule that is going to run in four hours is a lie in the
    other direction, and a card full of them after a restart would train
    the reader to ignore the one line that matters. This pins the future
    check staying AHEAD of the replay check.
    """
    events = async_capture_events(hass, EVENT_RULE_COMPLETED)
    await _prepare(engine, hass, [
        _rule("on18", time(18, 0), "input_boolean.t", Replay(enabled=False)),
    ])

    with freeze_time(_local("14:00")):
        results = await engine.async_catch_up()
    await hass.async_block_till_done()

    assert results == []
    assert [e for e in events if e.data.get("rule_id") == "on18"] == []
    assert engine.store.last_outcome("on18") is None
    assert engine.upcoming()


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
    """Omitting `within` means no bound at all on how late a replay may
    fire."""
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


# --- Superseded replays ---------------------------------------------------
#
# The owner's own schedule: a light ON at 17:00 replayable for 5h, the same
# light OFF at 18:00 replayable for 3h. Each rule used to be judged alone,
# so a restart at 21:30 replayed the ON (4.5h late, inside 5h) and skipped
# the OFF (3.5h late, outside 3h) - turning the light ON hours after the
# schedule had turned it off. And a restart at 19:00 replayed both, in
# order: the light flashed on, then off. Only the LATEST due command for a
# device states what the schedule wants now; anything earlier on that same
# device is history.


def _switch(rule_id, at: time, service: str, entity_id: str = "input_boolean.t",
            replay: Replay = Replay(), condition=()):
    return Rule(
        id=rule_id, profile=1, day="1", time=at,
        action=f"input_boolean.{service}",
        target={"entity_id": [entity_id]},
        replay=replay,
        condition=condition,
    )


_OWNERS_SCHEDULE = [
    _switch("on17", time(17, 0), "turn_on",
            replay=Replay(enabled=True, within=timedelta(hours=5))),
    _switch("off18", time(18, 0), "turn_off",
            replay=Replay(enabled=True, within=timedelta(hours=3))),
]


async def _states_during_catch_up(hass, engine, clock: str) -> tuple[list, list]:
    seen: list[str] = []
    hass.bus.async_listen(
        "state_changed",
        lambda e: e.data["entity_id"] == "input_boolean.t"
        and seen.append(e.data["new_state"].state),
    )
    with freeze_time(_local(clock)):
        results = await engine.async_catch_up()
    await hass.async_block_till_done()
    return seen, results


async def test_a_stale_later_off_still_supersedes_an_earlier_on(
    hass, engine, test_booleans
):
    """21:30: the OFF is too stale to replay, and the ON must not replay
    either - the light stays off, as the schedule has it since 18:00."""
    await _prepare(engine, hass, _OWNERS_SCHEDULE)

    seen, results = await _states_during_catch_up(hass, engine, "21:30")

    assert seen == []
    assert hass.states.get("input_boolean.t").state == "off"
    by_rule = {r["rule_id"]: r for r in results}
    assert by_rule["on17"]["outcome"] == "skipped_superseded"
    assert "off18" in by_rule["on17"]["reason"]
    assert by_rule["off18"]["outcome"] == "skipped_stale"
    assert engine.store.last_outcome("on17")["outcome"] == "skipped_superseded"


async def test_both_in_window_replays_only_the_latest_no_flash(
    hass, engine, test_booleans
):
    await _prepare(engine, hass, _OWNERS_SCHEDULE)

    seen, results = await _states_during_catch_up(hass, engine, "19:00")

    # Replaying both used to give ["on", "off"]: a visible flash.
    assert seen == []
    assert hass.states.get("input_boolean.t").state == "off"
    assert [r["outcome"] for r in results] == ["skipped_superseded", "called"]


async def test_a_later_rule_still_in_the_future_supersedes_nothing(
    hass, engine, test_booleans
):
    await _prepare(engine, hass, _OWNERS_SCHEDULE)

    seen, _ = await _states_during_catch_up(hass, engine, "17:30")

    assert seen == ["on"]


async def test_a_later_rule_with_replay_off_still_supersedes(
    hass, engine, test_booleans
):
    """Not replaying the OFF is the author's call; resurrecting the ON it
    replaced is not."""
    await _prepare(engine, hass, [
        _switch("on17", time(17, 0), "turn_on", replay=Replay(enabled=True)),
        _switch("off18", time(18, 0), "turn_off", replay=Replay(enabled=False)),
    ])

    seen, results = await _states_during_catch_up(hass, engine, "19:00")

    assert seen == []
    assert [r["outcome"] for r in results] == [
        "skipped_superseded", "skipped_no_replay",
    ]


async def test_a_later_rule_whose_condition_fails_supersedes_nothing(
    hass, engine, test_booleans
):
    """An OFF that would have been blocked never replaced the ON."""
    hass.states.async_set("binary_sensor.away", "off")
    await _prepare(engine, hass, [
        _switch("on17", time(17, 0), "turn_on", replay=Replay(enabled=True)),
        _switch(
            "off18", time(18, 0), "turn_off", replay=Replay(enabled=True),
            condition=({"condition": "state", "entity_id": "binary_sensor.away",
                        "state": "on"},),
        ),
    ])

    seen, results = await _states_during_catch_up(hass, engine, "19:00")

    assert seen == ["on"]
    assert [r["outcome"] for r in results] == ["called", "blocked"]


async def test_a_later_rule_on_only_some_of_the_targets_supersedes_nothing(
    hass, engine, test_booleans
):
    await _prepare(engine, hass, [
        Rule(
            id="on17", profile=1, day="1", time=time(17, 0),
            action="input_boolean.turn_on",
            target={"entity_id": ["input_boolean.t", "input_boolean.salon"]},
            replay=Replay(enabled=True),
        ),
        _switch("off18", time(18, 0), "turn_off", replay=Replay(enabled=False)),
    ])

    with freeze_time(_local("19:00")):
        results = await engine.async_catch_up()
    await hass.async_block_till_done()

    assert results[0]["outcome"] == "called"
    assert hass.states.get("input_boolean.salon").state == "on"


async def test_a_toggle_neither_supersedes_nor_is_superseded(
    hass, engine, test_booleans
):
    """A toggle's effect depends on the state before it, so dropping
    either side of a toggle changes the outcome."""
    await _prepare(engine, hass, [
        _switch("on17", time(17, 0), "turn_on", replay=Replay(enabled=True)),
        _switch("tog18", time(18, 0), "toggle", replay=Replay(enabled=True)),
    ])

    seen, _ = await _states_during_catch_up(hass, engine, "19:00")

    assert seen == ["on", "off"]


async def test_a_different_kind_of_command_supersedes_nothing(hass, engine):
    """A 17:00 mode and an 18:00 temperature on the same AC are both
    still wanted; replaying only the temperature would lose the mode."""
    mode = async_mock_service(hass, "climate", "set_hvac_mode")
    temp = async_mock_service(hass, "climate", "set_temperature")
    hass.states.async_set("climate.ac", "off")
    target = {"entity_id": ["climate.ac"]}
    await _prepare(engine, hass, [
        Rule(id="mode17", profile=1, day="1", time=time(17, 0),
             action="climate.set_hvac_mode", target=target,
             data={"hvac_mode": "cool"}, replay=Replay(enabled=True)),
        Rule(id="temp18", profile=1, day="1", time=time(18, 0),
             action="climate.set_temperature", target=target,
             data={"temperature": 24}, replay=Replay(enabled=True)),
    ])

    with freeze_time(_local("19:00")):
        await engine.async_catch_up()
    await hass.async_block_till_done()

    assert len(mode) == 1
    assert len(temp) == 1


async def test_turning_an_ac_off_supersedes_setting_its_mode(hass, engine):
    mode = async_mock_service(hass, "climate", "set_hvac_mode")
    off = async_mock_service(hass, "climate", "turn_off")
    hass.states.async_set("climate.ac", "cool")
    target = {"entity_id": ["climate.ac"]}
    await _prepare(engine, hass, [
        Rule(id="mode17", profile=1, day="1", time=time(17, 0),
             action="climate.set_hvac_mode", target=target,
             data={"hvac_mode": "cool"}, replay=Replay(enabled=True)),
        Rule(id="off18", profile=1, day="1", time=time(18, 0),
             action="climate.turn_off", target=target,
             replay=Replay(enabled=True, within=timedelta(hours=1))),
    ])

    with freeze_time(_local("21:30")):
        results = await engine.async_catch_up()
    await hass.async_block_till_done()

    assert mode == [] and off == []
    assert [r["outcome"] for r in results] == ["skipped_superseded", "skipped_stale"]


async def test_a_superseded_skip_reaches_the_logbook(hass, engine, test_booleans):
    events = async_capture_events(hass, EVENT_RULE_COMPLETED)
    described = {}
    async_describe_events(hass, lambda d, e, f: described.__setitem__(e, f))
    await _prepare(engine, hass, _OWNERS_SCHEDULE)

    await _states_during_catch_up(hass, engine, "21:30")

    per_rule = [e for e in events if e.data.get("rule_id") == "on17"]
    assert len(per_rule) == 1
    row = described[EVENT_RULE_COMPLETED](per_rule[0])["message"]
    assert "did not run" in row and "superseded" in row and "off18" in row
    summary = [e for e in events if e.data.get("catch_up")]
    message = described[EVENT_RULE_COMPLETED](summary[0])["message"]
    assert "1 superseded by a later rule" in message
