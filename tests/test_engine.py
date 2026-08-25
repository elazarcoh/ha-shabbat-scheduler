import asyncio
import dataclasses
from datetime import time
from unittest.mock import patch

import pytest
from homeassistant.const import EVENT_CALL_SERVICE
from homeassistant.core import Context, callback
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.shabbat_scheduler.const import EVENT_RULE_APPLIED
from custom_components.shabbat_scheduler.engine import ShabbatEngine
from custom_components.shabbat_scheduler.models import Replay, Rule
from custom_components.shabbat_scheduler.store import RuleStore

# The v2 idiom, used throughout this file: a rule is an `action`
# ("domain.service") plus a `target` selector, not a v1 `Action` enum plus a
# `devices` tuple plus a climate-shaped `settings` dict. Outcomes changed
# with it - `_call` reports "called" / "failed" / "would_call", never v1's
# "changed" / "ok" / "skipped", because v2 hands the call to
# `async_call_from_config` instead of comparing the entity's current state
# against a desired one it understands.
_ON = "input_boolean.turn_on"
_OFF = "input_boolean.turn_off"


@pytest.fixture
async def engine(hass, jerusalem, test_booleans):
    store = RuleStore(hass)
    await store.async_load()
    return ShabbatEngine(hass, store)


def _rule(action=_ON, entities=("input_boolean.t",), **kwargs):
    return Rule(
        id="r", profile=1, day="1", time=time(11, 0),
        action=action,
        target={"entity_id": list(entities)} if entities else {},
        **kwargs,
    )


async def test_apply_calls_the_rules_action(hass, engine):
    hass.states.async_set("input_boolean.t", "off")
    results = await engine.async_apply_rule(_rule())
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.t").state == "on"
    assert results[0]["outcome"] == "called"


async def test_a_target_entity_that_does_not_exist_is_still_reported_as_called(
    hass, engine
):
    """A characterisation test, pinning a KNOWN GAP rather than hiding it.

    v1 read each device's state itself, so a typo'd entity id came back
    `failed`. v2 hands the whole target to `async_call_from_config`, and
    Home Assistant's own service layer accepts a target naming an entity
    that does not exist without raising - so the engine has nothing to
    report but success. A misspelt entity id in a rule therefore looks
    like a rule that fired.

    This is the quiet-failure shape the project exists to prevent, and it
    is NOT fixed here (Task 12 carries the API and the card; it does not
    redesign execution). The test exists so the gap is visible and so
    that whoever closes it is told by a failing test that they did.
    """
    results = await engine.async_apply_rule(_rule(entities=("input_boolean.nope",)))

    assert results[0]["outcome"] == "called"


async def test_dry_run_makes_no_service_calls(hass, jerusalem, test_booleans):
    store = RuleStore(hass)
    await store.async_load()
    await store.async_set_dry_run(True)
    engine = ShabbatEngine(hass, store)

    hass.states.async_set("input_boolean.t", "off")
    results = await engine.async_apply_rule(_rule())
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.t").state == "off"
    assert results[0]["outcome"] == "would_call"  # reports what WOULD happen


async def test_a_rule_can_still_call_a_script(hass, engine):
    """v1's `Action.CUSTOM` + `script` field is now just an ordinary action."""
    calls = []

    async def record(call):
        calls.append(call)

    hass.services.async_register("script", "turn_on", record)
    await engine.async_apply_rule(
        _rule(action="script.turn_on", entities=("script.demo",))
    )
    await hass.async_block_till_done()

    assert calls[0].data["entity_id"] == ["script.demo"]


async def test_last_run_is_recorded(hass, engine):
    hass.states.async_set("input_boolean.t", "off")
    await engine.async_apply_rule(_rule())
    assert engine.last_run
    # Keyed on the call, not on an entity: one v2 result covers the whole
    # target, which may be an area or a label with no single entity in it.
    assert engine.last_run[0]["action"] == _ON
    assert engine.last_run[0]["target"] == {"entity_id": ["input_boolean.t"]}


async def test_engine_recognises_its_own_context(hass, engine):
    """A context the engine issued for a call must later be recognised as ours.

    This is what a future enforcement feature needs to tell "we changed this"
    apart from "a human changed this" - the entire reason for recording
    contexts at all.
    """
    captured = []

    async def record(call):
        captured.append(call)

    hass.services.async_register("input_boolean", "turn_on", record)
    hass.states.async_set("input_boolean.t", "off")

    await engine.async_apply_rule(_rule())
    await hass.async_block_till_done()

    assert captured, "expected the engine to have called input_boolean.turn_on"
    issued_context = captured[0].context

    # No longer keyed per entity - see ShabbatEngine.is_our_context.
    assert engine.is_our_context(issued_context)
    assert not engine.is_our_context(Context())


# --- One expanded call failing must not abort the rest of the rule ---------


async def test_a_later_expanded_call_still_runs_after_an_earlier_one_fails(
    hass, engine
):
    """v1 made one call per device and proved a sibling device survived a
    failure. v2 makes ONE call for the whole target, so the surviving form
    of that property is the climate shim, which is the only thing that
    still turns one authored action into several calls: if
    `climate.set_hvac_mode` fails, `climate.set_temperature` must still be
    attempted rather than the rule aborting half-applied.
    """
    hvac_attempts = []

    async def always_fail(call):
        hvac_attempts.append(call)
        raise RuntimeError("unit did not answer")

    hass.services.async_register("climate", "set_hvac_mode", always_fail)
    temperature = async_mock_service(hass, "climate", "set_temperature")

    rule = Rule(
        id="r", profile=1, day="1", time=time(11, 0),
        action="climate.set_temperature",
        target={"entity_id": ["climate.ac"]},
        data={"hvac_mode": "cool", "temperature": 22},
    )
    with patch("custom_components.shabbat_scheduler.engine.asyncio.sleep"):
        results = await engine.async_apply_rule(rule)
    await hass.async_block_till_done()

    assert len(hvac_attempts) == 3          # retried, then given up on
    assert len(temperature) == 1            # ...and the next call still ran
    by_action = {r["action"]: r["outcome"] for r in results}
    assert by_action["climate.set_hvac_mode"] == "failed"
    assert by_action["climate.set_temperature"] == "called"


# --- A PROPERTY v2 GAVE UP, recorded rather than left to be discovered -----


async def test_two_rules_on_one_device_at_one_instant_can_interleave(hass, engine):
    """CHARACTERISATION TEST. This records a GUARANTEE v2 NO LONGER MAKES.

    The spec named this exact failure: "the unit left off with a target
    temperature applied - a state matching neither rule." v1 prevented it
    with a lock keyed on `entity_id`, so two rules touching one air
    conditioner at the same minute could not have their calls interleave.
    v1's `test_concurrent_rules_on_same_device_do_not_interleave` proved
    it, and this test stands in that one's place.

    Task 6 re-keyed the lock to `rule.id`, of necessity: a v2 target may
    be an area, a floor or a label, so there is no single entity to key a
    lock on, and a call may carry no entity at all (`notify.*`). The lock
    still stops ONE rule interleaving with a re-entrant application of
    ITSELF. It no longer stops two DIFFERENT rules interleaving with each
    other. See the comment on `ShabbatEngine._locks`.

    What still protects the household is DETECTION, not prevention:
    `block.find_conflicts` reports any two enabled rules at the same
    profile/day/time whose resolved targets overlap, and the card shows
    that as a conflict. The user is told; the engine no longer refuses on
    their behalf. That is the whole of the trade.

    The interleave below is forced deterministically rather than raced
    for: rule A is held inside its first service call while rule B runs
    to completion. Under v1's per-entity lock, B could not have started.
    """
    calls: list[tuple[str, object]] = []
    rule_a_is_inside = asyncio.Event()
    release_rule_a = asyncio.Event()

    async def set_hvac_mode(call):
        mode = call.data.get("hvac_mode")
        calls.append(("hvac_mode", mode))
        if mode == "cool":              # rule A: hold it mid-rule
            rule_a_is_inside.set()
            await release_rule_a.wait()

    async def set_temperature(call):
        calls.append(("temperature", call.data.get("temperature")))

    hass.services.async_register("climate", "set_hvac_mode", set_hvac_mode)
    hass.services.async_register("climate", "set_temperature", set_temperature)

    def _climate_rule(rule_id, hvac_mode, temperature):
        # Each expands, via the climate shim, into set_hvac_mode then
        # set_temperature - the only path in v2 that still turns one
        # authored action into several calls, and so the only place two
        # rules CAN interleave.
        return Rule(
            id=rule_id, profile=1, day="1", time=time(11, 0),
            action="climate.set_temperature",
            target={"entity_id": ["climate.ac"]},
            data={"hvac_mode": hvac_mode, "temperature": temperature},
        )

    task_a = asyncio.create_task(
        engine.async_apply_rule(_climate_rule("a", "cool", 22))
    )
    await rule_a_is_inside.wait()

    # Rule A is suspended inside its FIRST call, holding only its own
    # lock. Rule B runs the whole way through, on the same entity.
    await engine.async_apply_rule(_climate_rule("b", "heat", 24))

    assert calls == [("hvac_mode", "cool"), ("hvac_mode", "heat"),
                     ("temperature", 24)], calls

    release_rule_a.set()
    await task_a
    await hass.async_block_till_done()

    # The damage, spelled out: rule A's temperature lands LAST, after rule
    # B's mode and B's temperature. The unit is left on rule B's hvac_mode
    # carrying rule A's temperature - a state matching NEITHER rule, which
    # is the spec's own words for the outcome v1 existed to prevent.
    assert calls == [("hvac_mode", "cool"), ("hvac_mode", "heat"),
                     ("temperature", 24), ("temperature", 22)], calls


async def test_one_rule_still_cannot_interleave_with_itself(hass, engine):
    """The half of v1's guarantee that DID survive the re-keying.

    `_locks` is keyed on `rule.id`, so a rule applied twice concurrently -
    a timer and a catch-up racing, a manual re-trigger - still runs its
    expanded calls as two complete, uninterrupted sequences. Without this
    the test above would read as "locking was simply removed".
    """
    calls: list[tuple[str, object]] = []
    first_is_inside = asyncio.Event()
    release_first = asyncio.Event()

    async def set_hvac_mode(call):
        calls.append(("hvac_mode", call.data.get("hvac_mode")))
        if not first_is_inside.is_set():
            first_is_inside.set()
            await release_first.wait()

    async def set_temperature(call):
        calls.append(("temperature", call.data.get("temperature")))

    hass.services.async_register("climate", "set_hvac_mode", set_hvac_mode)
    hass.services.async_register("climate", "set_temperature", set_temperature)

    rule = Rule(
        id="same-rule", profile=1, day="1", time=time(11, 0),
        action="climate.set_temperature",
        target={"entity_id": ["climate.ac"]},
        data={"hvac_mode": "cool", "temperature": 22},
    )

    first = asyncio.create_task(engine.async_apply_rule(rule))
    await first_is_inside.wait()
    second = asyncio.create_task(engine.async_apply_rule(rule))

    # The second application is blocked on the SAME lock, so it cannot
    # have reached any service call while the first is still inside one.
    await asyncio.sleep(0)
    assert calls == [("hvac_mode", "cool")], calls

    release_first.set()
    await asyncio.gather(first, second)
    await hass.async_block_till_done()

    # Two whole sequences, never interleaved.
    assert calls == [
        ("hvac_mode", "cool"), ("temperature", 22),
        ("hvac_mode", "cool"), ("temperature", 22),
    ], calls


# --- Task 10: retry on failure ----------------------------------------------


async def test_failed_call_is_retried_then_notified(hass, engine):
    # A bare `switch` entity: the switch component is not loaded, so the stub
    # service below is the only handler and can be made to fail on demand.
    hass.states.async_set("switch.t", "off")
    attempts = []

    async def always_fail(call):
        attempts.append(call)
        raise RuntimeError("boom")

    hass.services.async_register("switch", "turn_on", always_fail)

    rule = _rule(action="switch.turn_on", entities=("switch.t",))
    # Patch sleep so the test does not actually wait 60 seconds. It is not
    # merely slow if left alone: any test that also freezes time freezes
    # `time.monotonic()`, which IS the event loop's clock, so this sleep
    # would never return at all. See the `timeout` setting in pyproject.toml.
    with patch("custom_components.shabbat_scheduler.engine.asyncio.sleep"):
        results = await engine.async_apply_rule(rule)

    assert len(attempts) == 3
    assert results[0]["outcome"] == "failed"
    # This HA version's persistent_notification no longer creates entity
    # states (see homeassistant/components/persistent_notification) - it
    # keeps notifications in hass.data instead, so that's what we check.
    assert hass.data.get("persistent_notification")


async def test_retry_succeeds_on_second_attempt(hass, engine):
    hass.states.async_set("switch.t", "off")
    attempts = []

    async def fail_once(call):
        attempts.append(call)
        if len(attempts) == 1:
            raise RuntimeError("transient")

    hass.services.async_register("switch", "turn_on", fail_once)

    with patch("custom_components.shabbat_scheduler.engine.asyncio.sleep"):
        results = await engine.async_apply_rule(
            _rule(action="switch.turn_on", entities=("switch.t",))
        )

    assert len(attempts) == 2
    assert results[0]["outcome"] == "called"


from datetime import timedelta

from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.shabbat_scheduler.const import (
    CANDLE_SENSOR,
    EVENT_RULE_APPLIED,
    HAVDALAH_SENSOR,
)


def _set_zmanim(hass, candle: str, havdalah: str):
    hass.states.async_set(CANDLE_SENSOR, candle)
    hass.states.async_set(HAVDALAH_SENSOR, havdalah)


async def test_refresh_computes_the_block(hass, engine):
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.async_refresh()
    assert engine.current_block.length == 1


async def test_missing_sensor_keeps_the_cached_block(hass, engine):
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.async_refresh()

    hass.states.async_remove(CANDLE_SENSOR)
    await engine.async_refresh()
    assert engine.current_block is not None  # cached, not wiped


async def test_no_matching_profile_notifies(hass, engine):
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    # The master must be on, otherwise refresh returns before the check.
    await engine.store.async_set_enabled(True)
    await engine.store.async_add(
        Rule(id="r", profile=3, day="1", time=time(11, 0), action=_ON)
    )
    await engine.async_refresh()

    assert engine.upcoming() == []
    # DEVIATION from the brief (flagged, not silently fixed): this HA
    # version's persistent_notification no longer creates
    # `persistent_notification.*` entity states (see the sibling test
    # `test_failed_call_is_retried_then_notified` above, which already
    # documents this and checks hass.data instead). The brief's literal
    # assertion on hass.states.async_all() would always be empty here, so
    # the notification would never be verified as having fired. Using the
    # same hass.data check already established in this file.
    assert hass.data.get("persistent_notification")


async def test_disabled_master_schedules_nothing(hass, engine):
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_add(
        Rule(id="r", profile=1, day="1", time=time(11, 0),
             action=_ON, target={"entity_id": ["input_boolean.t"]})
    )
    await engine.async_refresh()  # master defaults OFF
    assert engine.upcoming() == []


@pytest.mark.parametrize("expected_lingering_timers", [True])
# DEVIATION from the brief (flagged, not silently fixed): once time is
# frozen (see below) `async_refresh` schedules a genuine
# `async_track_point_in_time` callback ~23h out for the rule's `when`. That
# handle is still pending at test teardown, which
# pytest-homeassistant-custom-component's `verify_cleanup` fixture treats as
# a hard failure ("Lingering timer") outside tests/components/*. This is a
# real, scheduling-only test - nothing in it fires or cancels the timer - so
# the framework's own documented escape hatch applies (see
# `expected_lingering_timers` in pytest_homeassistant_custom_component's
# plugins.py).
async def test_enabled_master_lists_upcoming_rules(hass, engine, freezer):
    # DEVIATION from the brief (flagged, not silently fixed): async_refresh
    # filters to `item.when > now` using the real wall clock, and the
    # brief's fixed zmanim literals place day 1 at 2026-08-15T11:00
    # Asia/Jerusalem. That instant is now in the past relative to the
    # machine's real clock, so without freezing time this test would fail
    # for a reason unrelated to the code under test - it is time-bombed as
    # written. Freezing to a moment before the block keeps the brief's exact
    # zmanim literals unchanged while restoring the comparison it depends on.
    freezer.move_to("2026-08-14T12:00:00+03:00")
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    await engine.store.async_add(
        Rule(id="r", profile=1, day="1", time=time(11, 0),
             action=_ON, target={"entity_id": ["input_boolean.t"]})
    )
    await engine.async_refresh()
    assert [item.rule.id for item in engine.upcoming()] == ["r"]


# --- Fix round 1: implausible zmanim must notify, not fail silently -------


async def test_implausible_zmanim_notifies_and_schedules_nothing(hass, engine):
    """havdalah at/before candle lighting must surface a notification.

    The no-matching-profile silent-failure path already raises a
    persistent_notification; this path (compute_block's ValueError) must
    be equally loud, not just logged.
    """
    # havdalah BEFORE candle lighting - implausible per compute_block.
    _set_zmanim(hass, "2026-08-15T17:01:00+00:00", "2026-08-14T15:44:00+00:00")
    await engine.store.async_set_enabled(True)
    await engine.store.async_add(
        Rule(id="r", profile=1, day="1", time=time(11, 0),
             action=_ON, target={"entity_id": ["input_boolean.t"]})
    )
    await engine.async_refresh()

    assert engine.upcoming() == []
    assert hass.data.get("persistent_notification")


# --- Task 12: restart catch-up ---------------------------------------------

from freezegun import freeze_time


# DEVIATION from the brief (flagged, not silently fixed): the brief's three
# catch-up tests never call `engine.async_refresh()`, but `async_catch_up`
# reads `self._block`, which starts as None and is only ever populated by
# `async_refresh()` (see its assignment from `compute_block(*zmanim)`). As
# written, every one of the brief's tests would exercise nothing but the
# `self._block is None` early-return - test 1 would then fail outright
# (asserting "on" while the device never gets touched) and tests 2-3 would
# pass, but only vacuously, for the wrong reason. In real use,
# `async_setup_entry` calls `async_refresh()` before `async_catch_up()` so
# `_block` is already populated by the time catch-up runs; these tests add
# that same call to match. `async_refresh()` is called outside `freeze_time`
# since block computation only reads the zmanim sensors, never the clock.
#
# v2 NOTE for this whole section: catch-up is now OPT-IN per rule
# (`replay.enabled`) rather than a desired-state comparison the engine
# derives for itself, so every rule below that is expected to replay says
# so. "custom rule" in the names below means what v1 called
# `Action.CUSTOM` + a `script` field, which in v2 is just an ordinary
# `script.turn_on` action - the property each test pins is unchanged.
async def test_catch_up_applies_the_last_passed_rule(hass, engine):
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    hass.states.async_set("input_boolean.t", "off")
    await engine.store.async_replace_all({}, [
        Rule(id="on", profile=1, day="1", time=time(11, 0),
             action=_ON, target={"entity_id": ["input_boolean.t"]},
             replay=Replay(enabled=True)),
        Rule(id="off", profile=1, day="1", time=time(18, 0),
             action=_OFF, target={"entity_id": ["input_boolean.t"]},
             replay=Replay(enabled=True)),
    ])
    await engine.async_refresh()

    # 11:30 local - the 11:00 ON has passed, 18:00 OFF has not.
    with freeze_time("2026-08-15T08:30:00+00:00"):
        results = await engine.async_catch_up()
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.t").state == "on"
    assert [r["outcome"] for r in results] == ["called"]


async def test_catch_up_before_any_rule_does_nothing(hass, engine):
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    hass.states.async_set("input_boolean.t", "off")
    await engine.store.async_replace_all({}, [
        Rule(id="on", profile=1, day="1", time=time(11, 0),
             action=_ON, target={"entity_id": ["input_boolean.t"]}),
    ])
    await engine.async_refresh()

    with freeze_time("2026-08-15T06:00:00+00:00"):  # 09:00 local
        assert await engine.async_catch_up() == []


async def test_catch_up_skips_custom_rules_by_default(hass, engine):
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    calls = []

    async def record(call):
        calls.append(call)

    hass.services.async_register("script", "turn_on", record)
    await engine.store.async_replace_all({}, [
        Rule(id="c", profile=1, day="1", time=time(11, 0),
             action="script.turn_on",
             target={"entity_id": ["script.demo"]}),
    ])
    await engine.async_refresh()

    with freeze_time("2026-08-15T08:30:00+00:00"):
        await engine.async_catch_up()
    await hass.async_block_till_done()
    assert calls == []


# --- Fix round 1: custom replay must be gated by resolve_rules, not free --


async def test_catch_up_replays_a_passed_replay_on_restart_custom_rule(hass, engine):
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    calls = []

    async def record(call):
        calls.append(call)

    hass.services.async_register("script", "turn_on", record)
    await engine.store.async_replace_all({}, [
        Rule(id="c", profile=1, day="1", time=time(11, 0),
             action="script.turn_on",
             target={"entity_id": ["script.demo"]},
             replay=Replay(enabled=True)),
    ])
    await engine.async_refresh()

    # 11:30 local - the 11:00 custom rule has passed.
    with freeze_time("2026-08-15T08:30:00+00:00"):
        await engine.async_catch_up()
    await hass.async_block_till_done()
    assert len(calls) == 1


async def test_catch_up_does_not_replay_a_custom_rule_that_has_not_passed(hass, engine):
    # Regression test for the bug the coordinator's round-1 review caught:
    # the original implementation looped over the unfiltered rule list and
    # replayed every opted-in rule unconditionally,
    # firing scripts scheduled for later the same day immediately on
    # restart. Confirmed to fail against the pre-fix code (calls == 1).
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    calls = []

    async def record(call):
        calls.append(call)

    hass.services.async_register("script", "turn_on", record)
    await engine.store.async_replace_all({}, [
        Rule(id="c", profile=1, day="1", time=time(18, 0),
             action="script.turn_on",
             target={"entity_id": ["script.demo"]},
             replay=Replay(enabled=True)),
    ])
    await engine.async_refresh()

    # 11:30 local - the 18:00 custom rule has NOT passed yet.
    with freeze_time("2026-08-15T08:30:00+00:00"):
        await engine.async_catch_up()
    await hass.async_block_till_done()
    assert calls == []


async def test_catch_up_does_not_replay_a_disabled_custom_rule(hass, engine):
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    calls = []

    async def record(call):
        calls.append(call)

    hass.services.async_register("script", "turn_on", record)
    await engine.store.async_replace_all({}, [
        Rule(id="c", profile=1, day="1", time=time(11, 0),
             action="script.turn_on",
             target={"entity_id": ["script.demo"]},
             replay=Replay(enabled=True), enabled=False),
    ])
    await engine.async_refresh()

    with freeze_time("2026-08-15T08:30:00+00:00"):
        await engine.async_catch_up()
    await hass.async_block_till_done()
    assert calls == []


async def test_catch_up_on_a_conflicting_pair_applies_both_in_order(hass, engine):
    """DELIBERATE v2 CHANGE, pinned here rather than left to be discovered.

    v1's catch-up asked `block.desired_state_at` what state each device
    should be in, and when two rules at the same moment gave contradictory
    answers it DECLINED to act - `results == []`, the device untouched.
    `desired_state_at` is gone (Task 8; test_replay.py asserts its
    absence), because an opaque service call has no queryable desired
    state to compare. So catch-up no longer arbitrates: it replays every
    opted-in passed rule in time order, and for a same-moment pair the
    LAST one applied wins.

    That is not a silent loss - `find_conflicts` still reports this pair
    as a conflict over the websocket, which is where the user is told.
    But the engine no longer refuses on their behalf, and this test says
    so out loud so nobody reads v1's docstring and believes otherwise.
    """
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    hass.states.async_set("input_boolean.t", "off")
    await engine.store.async_replace_all({}, [
        Rule(id="on", profile=1, day="1", time=time(11, 0),
             action=_ON, target={"entity_id": ["input_boolean.t"]},
             replay=Replay(enabled=True)),
        Rule(id="off-same-time", profile=1, day="1", time=time(11, 0),
             action=_OFF, target={"entity_id": ["input_boolean.t"]},
             replay=Replay(enabled=True)),
    ])
    await engine.async_refresh()

    with freeze_time("2026-08-15T08:30:00+00:00"):
        results = await engine.async_catch_up()
    await hass.async_block_till_done()

    assert [r["outcome"] for r in results] == ["called", "called"]
    # Both ran; the schedule's own order decided the outcome, not the engine.
    assert hass.states.get("input_boolean.t").state == "off"


# --- Final review C1: a rolled-forward zmanim pair must not cancel the -----
# --- remaining rules of the block that is still in force -------------------

from datetime import date


# The hold now arms a release timer (NEW-1) for `tail + 1s`; this test stops
# at the tail itself, so that timer is legitimately still pending at teardown.
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_rolled_forward_zmanim_keep_the_current_blocks_tail(
    hass, engine, freezer
):
    """At havdalah jewish_calendar advances to NEXT week - mid-block.

    Both zmanim sensors jump to the following occurrence the moment
    `now >= havdalah`, which fires the state listener and refreshes. If the
    engine adopted that candidate block it would cancel every still-pending
    timer of the block actually in force, so a deliberately post-havdalah
    rule ("23:00 turn everything off on the last day") would never fire and
    the AC would run all night with nothing in the log.
    """
    freezer.move_to("2026-08-15T05:00:00+00:00")
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    hass.states.async_set("input_boolean.t", "on")
    await engine.store.async_replace_all({}, [
        Rule(id="late-off", profile=1, day="1", time=time(23, 0),
             action=_OFF, target={"entity_id": ["input_boolean.t"]}),
    ])
    await engine.async_refresh()
    assert [item.rule.id for item in engine.upcoming()] == ["late-off"]

    # Havdalah passes (20:01 local); the sensors roll forward to next week.
    freezer.move_to("2026-08-15T17:01:30+00:00")
    _set_zmanim(hass, "2026-08-21T15:36:00+00:00", "2026-08-22T16:53:00+00:00")
    await engine.async_refresh()

    assert engine.current_block.erev_date == date(2026, 8, 14)
    assert [item.rule.id for item in engine.upcoming()] == ["late-off"]

    # 23:00 Asia/Jerusalem == 20:00 UTC.
    async_fire_time_changed(
        hass, dt_util.parse_datetime("2026-08-15T20:00:00+00:00")
    )
    await hass.async_block_till_done()
    assert hass.states.get("input_boolean.t").state == "off"


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_next_block_is_adopted_once_the_tail_has_passed(
    hass, engine, freezer
):
    """The hold is only until the current block's last rule is spent."""
    freezer.move_to("2026-08-15T05:00:00+00:00")
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    await engine.store.async_replace_all({}, [
        Rule(id="late-off", profile=1, day="1", time=time(23, 0),
             action=_OFF, target={"entity_id": ["input_boolean.t"]}),
    ])
    await engine.async_refresh()
    assert engine.current_block.erev_date == date(2026, 8, 14)

    # Sunday morning: the 23:00 tail is long gone.
    freezer.move_to("2026-08-16T05:00:00+00:00")
    _set_zmanim(hass, "2026-08-21T15:36:00+00:00", "2026-08-22T16:53:00+00:00")
    await engine.async_refresh()

    assert engine.current_block.erev_date == date(2026, 8, 21)
    assert [item.rule.id for item in engine.upcoming()] == ["late-off"]


# --- Re-review NEW-1: the hold must RELEASE ITSELF once the tail is spent --


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_the_hold_releases_itself_and_arms_the_next_block(
    hass, engine, freezer
):
    """Holding the block is only half the fix; letting go is the other half.

    Nothing else can release it. After havdalah the jewish_calendar sensors
    hold NEXT week's values and do not change again until the next havdalah,
    and HA fires EVENT_STATE_REPORTED (not state_changed) when a state is
    re-published identically - so the zmanim listener never runs. The tail
    rule fires on its own timer and async_apply_rule does not refresh. If
    the hold does not expire by itself, `_block` stays a week old with no
    timers for the block that is actually coming, and the WHOLE of the next
    Shabbat is silently skipped.
    """
    freezer.move_to("2026-08-15T05:00:00+00:00")
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    hass.states.async_set("input_boolean.t", "on")
    await engine.store.async_replace_all({}, [
        Rule(id="morning-on", profile=1, day="1", time=time(9, 0),
             action=_ON, target={"entity_id": ["input_boolean.t"]}),
        Rule(id="late-off", profile=1, day="1", time=time(23, 0),
             action=_OFF, target={"entity_id": ["input_boolean.t"]}),
    ])
    await engine.async_refresh()
    assert engine.current_block.erev_date == date(2026, 8, 14)

    # 20:01:30 local - havdalah has just passed and the sensors rolled
    # forward, so the listener refreshes and the hold must engage.
    freezer.move_to("2026-08-15T17:01:30+00:00")
    _set_zmanim(hass, "2026-08-21T15:36:00+00:00", "2026-08-22T16:53:00+00:00")
    await engine.async_refresh()
    assert engine.current_block.erev_date == date(2026, 8, 14)
    assert [item.rule.id for item in engine.upcoming()] == ["late-off"]

    # 23:00 local - the tail fires on its own timer, nothing else happens.
    freezer.move_to("2026-08-15T20:00:00+00:00")
    async_fire_time_changed(
        hass, dt_util.parse_datetime("2026-08-15T20:00:00+00:00")
    )
    await hass.async_block_till_done()
    assert hass.states.get("input_boolean.t").state == "off"

    # Moments later the hold is protecting nothing and must let go on its
    # own - no restart, no switch toggle, no YAML import, no state change.
    freezer.move_to("2026-08-15T20:00:05+00:00")
    async_fire_time_changed(
        hass, dt_util.parse_datetime("2026-08-15T20:00:01+00:00")
    )
    await hass.async_block_till_done()

    assert engine.current_block.erev_date == date(2026, 8, 21)
    assert [item.rule.id for item in engine.upcoming()] == [
        "morning-on", "late-off"
    ]

    # ...and the next Shabbat genuinely happens: 09:00 local on 22 Aug.
    async_fire_time_changed(
        hass, dt_util.parse_datetime("2026-08-22T06:00:00+00:00")
    )
    await hass.async_block_till_done()
    assert hass.states.get("input_boolean.t").state == "on"


# --- Re-review: the hold must survive a restart inside its own window -----


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_a_restart_inside_the_hold_still_fires_the_pending_tail(
    hass, jerusalem, test_booleans, freezer
):
    """A restart between havdalah and the tail used to lose the tail rule.

    The hold lives only in memory. Restart HA at 21:00 with a 23:00 rule
    still pending and `_block` starts as None, so setup reads the
    already-rolled-forward sensors, adopts NEXT week's block, and catch-up
    against a wholly-future block does nothing. The 23:00 OFF never fires
    and the air conditioner runs the night, silently. The block in force
    therefore has to outlive the process.
    """
    freezer.move_to("2026-08-15T05:00:00+00:00")
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")

    store = RuleStore(hass)
    await store.async_load()
    await store.async_set_enabled(True)
    await store.async_replace_all({}, [
        Rule(id="late-off", profile=1, day="1", time=time(23, 0),
             action=_OFF, target={"entity_id": ["input_boolean.t"]}),
    ])
    engine = ShabbatEngine(hass, store)
    hass.states.async_set("input_boolean.t", "on")
    await engine.async_refresh()
    assert engine.current_block.erev_date == date(2026, 8, 14)

    # 20:01:30 local - havdalah passes, the sensors roll forward, the hold
    # engages on the 14 Aug block.
    freezer.move_to("2026-08-15T17:01:30+00:00")
    _set_zmanim(hass, "2026-08-21T15:36:00+00:00", "2026-08-22T16:53:00+00:00")
    await engine.async_refresh()
    assert engine.current_block.erev_date == date(2026, 8, 14)

    # 21:00 local - Home Assistant restarts. Every timer and all in-memory
    # state is gone; only .storage survives, and the sensors read next week.
    freezer.move_to("2026-08-15T18:00:00+00:00")
    await engine.async_shutdown()

    restarted_store = RuleStore(hass)
    await restarted_store.async_load()
    restarted = ShabbatEngine(hass, restarted_store)
    await restarted.async_refresh()

    assert restarted.current_block.erev_date == date(2026, 8, 14)
    assert [item.rule.id for item in restarted.upcoming()] == ["late-off"]

    # 23:00 local - the rule the restart nearly ate.
    freezer.move_to("2026-08-15T20:00:00+00:00")
    async_fire_time_changed(
        hass, dt_util.parse_datetime("2026-08-15T20:00:00+00:00")
    )
    await hass.async_block_till_done()
    assert hass.states.get("input_boolean.t").state == "off"


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_a_restart_after_the_tail_adopts_the_next_block(
    hass, jerusalem, test_booleans, freezer
):
    """The persisted block must not pin the engine to a spent block."""
    freezer.move_to("2026-08-15T05:00:00+00:00")
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")

    store = RuleStore(hass)
    await store.async_load()
    await store.async_set_enabled(True)
    await store.async_replace_all({}, [
        Rule(id="late-off", profile=1, day="1", time=time(23, 0),
             action=_OFF, target={"entity_id": ["input_boolean.t"]}),
    ])
    engine = ShabbatEngine(hass, store)
    await engine.async_refresh()
    assert store.active_block is not None
    await engine.async_shutdown()

    # Tuesday: the 14 Aug block's tail is days gone.
    freezer.move_to("2026-08-18T05:00:00+00:00")
    _set_zmanim(hass, "2026-08-21T15:36:00+00:00", "2026-08-22T16:53:00+00:00")
    restarted_store = RuleStore(hass)
    await restarted_store.async_load()
    restarted = ShabbatEngine(hass, restarted_store)
    await restarted.async_refresh()

    assert restarted.current_block.erev_date == date(2026, 8, 21)
    # ...and the spent block is not left lying in .storage forever.
    assert restarted_store.active_block == (
        restarted.current_block.candle_lighting,
        restarted.current_block.havdalah,
    )


async def test_concurrent_refreshes_do_not_double_up_timers(
    hass, engine, freezer
):
    """Persisting the block introduces an await mid-refresh.

    Both zmanim sensors change at the same instant, so two `_zmanim_changed`
    tasks - two `async_refresh` calls - can genuinely overlap. If the second
    starts while the first is inside that await, it cancels nothing (the
    first already cancelled every timer) and both then append their own set,
    so every rule of the block fires twice.
    """
    freezer.move_to("2026-08-15T05:00:00+00:00")
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    hass.states.async_set("input_boolean.t", "on")
    await engine.store.async_replace_all({}, [
        Rule(id="off", profile=1, day="1", time=time(11, 0),
             action=_OFF, target={"entity_id": ["input_boolean.t"]}),
    ])

    fired = []
    hass.bus.async_listen(EVENT_RULE_APPLIED, lambda event: fired.append(event))

    real_save = RuleStore.async_save

    async def yielding_save(self):
        # The mocked .storage in this test harness writes to a dict without
        # ever yielding to the loop, so the overlap this test is about
        # cannot occur unless the executor hop a real Store.async_save
        # performs is put back.
        await asyncio.sleep(0)
        await real_save(self)

    with patch.object(RuleStore, "async_save", yielding_save):
        await asyncio.gather(engine.async_refresh(), engine.async_refresh())

    freezer.move_to("2026-08-15T08:00:00+00:00")
    async_fire_time_changed(
        hass, dt_util.parse_datetime("2026-08-15T08:00:00+00:00")
    )
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.t").state == "off"
    assert len(fired) == 1


# --- Final review I1: block dates must be derived in the LOCAL timezone ----


async def test_block_dates_follow_the_local_timezone_not_utc(hass, test_booleans):
    """HA serialises timestamp sensors as UTC; the dates must still be local.

    Israel hides this bug (evening local == same UTC date), so the test uses
    a timezone west of UTC where the two genuinely differ.
    """
    await hass.config.async_set_time_zone("America/New_York")
    store = RuleStore(hass)
    await store.async_load()
    engine = ShabbatEngine(hass, store)

    # 20:44 local on Friday 14 Aug is 00:44 UTC on Saturday 15 Aug.
    _set_zmanim(hass, "2026-08-15T00:44:00+00:00", "2026-08-16T00:53:00+00:00")
    await engine.async_refresh()

    assert engine.current_block.erev_date == date(2026, 8, 14)
    assert engine.current_block.day_dates == (date(2026, 8, 15),)
    assert engine.current_block.length == 1


# --- Final review I5: unreadable zmanim sensors must not fail silently -----


async def test_unreadable_zmanim_with_no_cached_block_notifies(hass, engine):
    """A renamed/missing jewish_calendar entity used to be wholly silent."""
    await engine.store.async_set_enabled(True)
    await engine.async_refresh()

    assert engine.current_block is None
    assert "shabbat_scheduler_zmanim" in hass.data["persistent_notification"]
    message = hass.data["persistent_notification"]["shabbat_scheduler_zmanim"][
        "message"
    ]
    assert CANDLE_SENSOR in message
    assert HAVDALAH_SENSOR in message


async def test_unreadable_zmanim_is_quiet_when_a_block_is_cached(hass, engine):
    """The cached-block path is correctly quiet - it must stay that way."""
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.async_refresh()
    hass.states.async_remove(CANDLE_SENSOR)
    await engine.async_refresh()

    assert engine.current_block is not None
    assert "shabbat_scheduler_zmanim" not in hass.data.get(
        "persistent_notification", {}
    )


async def test_zmanim_notification_is_dismissed_once_readable(hass, engine):
    await engine.async_refresh()
    assert "shabbat_scheduler_zmanim" in hass.data["persistent_notification"]

    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.async_refresh()
    assert "shabbat_scheduler_zmanim" not in hass.data["persistent_notification"]


# --- Final review I2/I3: nothing may be dropped in silence ----------------


async def test_an_unsupported_domain_is_no_longer_a_thing(hass, engine):
    """v1's `cover.` test, inverted: the limitation it guarded is GONE.

    v1 could only drive four domains and reported `skipped` for anything
    else; the risk was that it reported OK instead. v2 hands every action
    to `async_call_from_config`, so a cover rule is an ordinary rule and
    must actually make the call - there is no allow-list left to fall off.
    """
    calls = async_mock_service(hass, "cover", "close_cover")
    results = await engine.async_apply_rule(
        _rule(action="cover.close_cover", entities=("cover.a",))
    )
    await hass.async_block_till_done()

    assert [item["outcome"] for item in results] == ["called"]
    assert len(calls) == 1


async def test_a_value_home_assistant_rejects_is_reported_failed_not_called(
    hass, engine, caplog
):
    """The successor to v1's unsupported-fan-mode test.

    v1 knew climate's `fan_modes` attribute itself and reported `skipped`
    for a mode the unit did not have. v2 knows nothing about climate, so
    the guarantee has to come from Home Assistant's own service
    validation - and the thing that must not happen is unchanged: a value
    the unit cannot accept must never come back as if the rule fired.
    """
    hass.states.async_set(
        "climate.ac", "cool",
        {"fan_modes": ["auto", "high"], "fan_mode": "auto",
         "supported_features": 8},
    )

    async def reject(_call):
        raise ValueError("Fan mode quiet is not valid")

    hass.services.async_register("climate", "set_fan_mode", reject)

    with patch("custom_components.shabbat_scheduler.engine.asyncio.sleep"):
        results = await engine.async_apply_rule(
            _rule(action="climate.set_fan_mode", entities=("climate.ac",),
                  data={"fan_mode": "quiet"})
        )

    assert [item["outcome"] for item in results] == ["failed"]
    assert "quiet" in results[0]["error"]
    assert "quiet" in caplog.text


# --- Final review I4: a failure must record WHY --------------------------


async def test_failure_records_the_exception_and_a_reason(hass, engine, caplog):
    """The log line and the notification are the only forensic surface.

    On a Shabbat night nobody can investigate live; "failed after 3 attempts"
    cannot distinguish a missing service from a timeout from a cloud auth
    error.
    """
    hass.states.async_set("switch.t", "off")

    async def always_fail(_call):
        raise RuntimeError("cloud auth expired")

    hass.services.async_register("switch", "turn_on", always_fail)

    with patch("custom_components.shabbat_scheduler.engine.asyncio.sleep"):
        results = await engine.async_apply_rule(
            _rule(action="switch.turn_on", entities=("switch.t",))
        )

    assert results[0]["outcome"] == "failed"
    # v1 called this key `reason`; v2's `_call` calls it `error`. It still
    # carries the TYPE as well as the message - an HA exception that
    # stringifies to "" would otherwise leave a `failed` result saying
    # nothing at all about why.
    assert "cloud auth expired" in results[0]["error"]
    assert "RuntimeError" in results[0]["error"]

    message = next(iter(hass.data["persistent_notification"].values()))["message"]
    assert "cloud auth expired" in message
    assert "RuntimeError" in message

    assert "cloud auth expired" in caplog.text
    assert "Traceback" in caplog.text  # exc_info on the final failure


# --- Final review minor: an all-disabled profile must notify --------------


async def test_all_disabled_rules_notify_like_a_missing_profile(hass, engine):
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    await engine.store.async_replace_all({}, [
        Rule(id="r", profile=1, day="1", time=time(11, 0), action=_ON,
             target={"entity_id": ["input_boolean.t"]}, enabled=False),
    ])
    await engine.async_refresh()

    assert engine.upcoming() == []
    assert "shabbat_scheduler_no_profile" in hass.data["persistent_notification"]


# --- Task 8: self-describing event, fired before the calls, shared context -


async def test_event_is_self_describing_and_fires_before_the_calls(hass, engine):
    """The logbook renders historical events, so the payload must stand alone."""
    hass.states.async_set("input_boolean.t", "off")
    order: list[str] = []
    events: list = []

    @callback
    def _event(event):
        events.append(event)
        order.append("event")

    hass.bus.async_listen(EVENT_RULE_APPLIED, _event)

    @callback
    def _call(event):
        order.append("call")

    hass.bus.async_listen(EVENT_CALL_SERVICE, _call)

    rule = _rule()
    rule = dataclasses.replace(rule, name="בוקר שבת")
    await engine.async_apply_rule(rule)
    await hass.async_block_till_done()

    assert events[0].data["rule_id"] == rule.id
    assert events[0].data["name"] == "בוקר שבת"
    # v2 payload: the action and its target, not v1's enum + `devices`.
    assert events[0].data["action"] == _ON
    assert events[0].data["target"] == {"entity_id": ["input_boolean.t"]}
    assert order[0] == "event"  # must precede the calls, or attribution breaks


async def test_all_calls_of_one_rule_share_the_events_context(hass, engine):
    """A rule that expands to SEVERAL calls must stamp them all identically.

    v1 got several calls by having several `devices`; v2 makes one call per
    target, so the surviving multi-call path is the climate shim, which
    turns one authored `climate.set_temperature` into set_hvac_mode +
    set_temperature. Both must carry the event's context or Home
    Assistant attributes half the rule's changes to nothing.
    """
    hvac = async_mock_service(hass, "climate", "set_hvac_mode")
    temperature = async_mock_service(hass, "climate", "set_temperature")
    contexts: list[str] = []
    event_context: list[str] = []

    @callback
    def _event(event):
        event_context.append(event.context.id)

    hass.bus.async_listen(EVENT_RULE_APPLIED, _event)

    @callback
    def _call(event):
        contexts.append(event.context.id)

    hass.bus.async_listen(EVENT_CALL_SERVICE, _call)

    await engine.async_apply_rule(
        Rule(
            id="r", profile=1, day="1", time=time(11, 0),
            action="climate.set_temperature",
            target={"entity_id": ["climate.ac"]},
            data={"hvac_mode": "cool", "temperature": 22},
        )
    )
    await hass.async_block_till_done()

    assert len(hvac) == 1 and len(temperature) == 1  # genuinely two calls
    assert len(contexts) == 2
    assert len(set(contexts)) == 1
    assert contexts[0] == event_context[0]


async def test_concurrent_rules_get_distinct_contexts(hass, engine):
    """Two rules applied at once must not share or overwrite each other's."""
    hass.states.async_set("input_boolean.t", "off")
    hass.states.async_set("input_boolean.salon", "off")
    seen: list[str] = []

    @callback
    def _event(event):
        seen.append(event.context.id)

    hass.bus.async_listen(EVENT_RULE_APPLIED, _event)

    await asyncio.gather(
        engine.async_apply_rule(
            dataclasses.replace(
                _rule(entities=("input_boolean.t",)), id="one"
            )
        ),
        engine.async_apply_rule(
            dataclasses.replace(
                _rule(action=_OFF, entities=("input_boolean.salon",)), id="two"
            )
        ),
    )
    await hass.async_block_till_done()

    assert len(seen) == 2
    assert len(set(seen)) == 2
