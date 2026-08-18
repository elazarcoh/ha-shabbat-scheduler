import asyncio
import itertools
from datetime import time
from unittest.mock import patch

import pytest
from homeassistant.components.climate import (
    DATA_COMPONENT as CLIMATE_DATA_COMPONENT,
)
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import EVENT_CALL_SERVICE
from homeassistant.core import Context
from homeassistant.setup import async_setup_component

from custom_components.shabbat_scheduler.engine import ShabbatEngine
from custom_components.shabbat_scheduler.models import Action, Rule
from custom_components.shabbat_scheduler.store import RuleStore


@pytest.fixture
async def engine(hass, jerusalem, test_booleans):
    store = RuleStore(hass)
    await store.async_load()
    return ShabbatEngine(hass, store)


def _rule(action=Action.ON, devices=("input_boolean.t",), **kwargs):
    return Rule(
        id="r", profile=1, day="1", time=time(11, 0),
        action=action, devices=devices, **kwargs,
    )


async def test_apply_turns_on_an_input_boolean(hass, engine):
    hass.states.async_set("input_boolean.t", "off")
    results = await engine.async_apply_rule(_rule())
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.t").state == "on"
    assert results[0]["outcome"] == "changed"


async def test_apply_skips_when_already_correct(hass, engine):
    hass.states.async_set("input_boolean.t", "on")
    results = await engine.async_apply_rule(_rule())
    assert results[0]["outcome"] == "ok"


async def test_unknown_state_forces_apply(hass, engine):
    hass.states.async_set("input_boolean.t", "unknown")
    results = await engine.async_apply_rule(_rule())
    assert results[0]["outcome"] == "changed"


async def test_missing_entity_is_reported_not_raised(hass, engine):
    results = await engine.async_apply_rule(_rule(devices=("input_boolean.nope",)))
    assert results[0]["outcome"] == "failed"


async def test_dry_run_makes_no_service_calls(hass, jerusalem, test_booleans):
    store = RuleStore(hass)
    await store.async_load()
    await store.async_set_dry_run(True)
    engine = ShabbatEngine(hass, store)

    hass.states.async_set("input_boolean.t", "off")
    results = await engine.async_apply_rule(_rule())
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.t").state == "off"
    assert results[0]["outcome"] == "changed"  # reports what WOULD change


async def test_custom_rule_calls_its_script(hass, engine):
    calls = []

    async def record(call):
        calls.append(call)

    hass.services.async_register("script", "turn_on", record)
    await engine.async_apply_rule(
        _rule(action=Action.CUSTOM, devices=(), script="script.demo")
    )
    await hass.async_block_till_done()

    assert calls[0].data["entity_id"] == "script.demo"


async def test_last_run_is_recorded(hass, engine):
    hass.states.async_set("input_boolean.t", "off")
    await engine.async_apply_rule(_rule())
    assert engine.last_run
    assert engine.last_run[0]["entity_id"] == "input_boolean.t"


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

    assert engine.is_our_context("input_boolean.t", issued_context)
    assert not engine.is_our_context("input_boolean.t", Context())


# --- Finding 1: idempotent re-apply must not re-issue a landed command -----


async def test_reapplying_same_rule_with_no_state_change_is_a_noop(hass, engine):
    """Applying an already-satisfied rule a second time must be a no-op.

    Regression test for the staleness guard stamping `_last_command` AFTER
    the awaited service call returned: for a synchronous local entity (like
    input_boolean) the entity's own `last_updated` lands DURING the call,
    so a post-call stamp is always later than that write - the guard then
    reports "stale" forever and forces a real service call on every repeat
    apply, even though nothing changed. This is exactly the "keeps
    re-asserting" failure mode the whole engine exists to avoid.
    """
    hass.states.async_set("input_boolean.t", "off")
    rule = _rule()

    first = await engine.async_apply_rule(rule)
    await hass.async_block_till_done()
    assert first[0]["outcome"] == "changed"
    assert hass.states.get("input_boolean.t").state == "on"

    seen_service_calls = []
    hass.bus.async_listen(
        EVENT_CALL_SERVICE,
        lambda event: seen_service_calls.append(event.data),
    )

    second = await engine.async_apply_rule(rule)
    await hass.async_block_till_done()

    assert second[0]["outcome"] == "ok"
    assert not seen_service_calls, (
        f"expected no service call on the second apply, got {seen_service_calls}"
    )


# --- Finding 2: two rules on one device must not interleave ----------------


class _RecordingClimate(ClimateEntity):
    """A bare climate entity that records the order service calls land in.

    Each setter yields (`await asyncio.sleep(0)`) between recording the call
    and applying it, giving a missing per-device lock a real opportunity to
    let a second concurrent rule's calls land in between.
    """

    _attr_hvac_modes = [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT]
    _attr_fan_modes = ["low", "high", "quiet"]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE
    )

    def __init__(self, call_log: list[tuple[str, object]], temperature_unit) -> None:
        self.entity_id = "climate.ac"
        self._attr_temperature_unit = temperature_unit
        self._call_log = call_log
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_target_temperature = 20
        self._attr_fan_mode = "low"

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        self._call_log.append(("hvac_mode", hvac_mode))
        await asyncio.sleep(0)
        self._attr_hvac_mode = hvac_mode
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs) -> None:
        self._call_log.append(("temperature", kwargs.get("temperature")))
        await asyncio.sleep(0)
        self._attr_target_temperature = kwargs.get("temperature")
        self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        self._call_log.append(("fan_mode", fan_mode))
        await asyncio.sleep(0)
        self._attr_fan_mode = fan_mode
        self.async_write_ha_state()


async def test_concurrent_rules_on_same_device_do_not_interleave(hass, engine):
    """Two rules firing at once on one climate entity must not interleave.

    The spec calls out the exact failure this guards against: the unit left
    off with a target temperature applied - a state matching neither rule.
    Each rule below issues three climate calls (hvac_mode, temperature,
    fan_mode); every value is distinct from the entity's initial state AND
    from the other rule's values, in both attribute-position and
    across-rules, so a full, uncontaminated triplet is expected from
    whichever rule runs first or second.
    """
    call_log: list[tuple[str, object]] = []
    await async_setup_component(hass, "climate", {})
    component = hass.data[CLIMATE_DATA_COMPONENT]
    await component.async_add_entities(
        [_RecordingClimate(call_log, hass.config.units.temperature_unit)]
    )
    await hass.async_block_till_done()

    rule_a = _rule(
        devices=("climate.ac",),
        settings={"hvac_mode": "cool", "temperature": 22, "fan_mode": "high"},
    )
    rule_b = Rule(
        id="r2", profile=1, day="1", time=time(11, 0), action=Action.ON,
        devices=("climate.ac",),
        settings={"hvac_mode": "heat", "temperature": 24, "fan_mode": "quiet"},
    )

    await asyncio.gather(
        engine.async_apply_rule(rule_a), engine.async_apply_rule(rule_b)
    )
    await hass.async_block_till_done()

    assert len(call_log) == 6, call_log

    owner_by_value = {
        "cool": "A", "heat": "B",
        22: "A", 24: "B",
        "high": "A", "quiet": "B",
    }
    labels = [owner_by_value[value] for _attr, value in call_log]
    runs = [label for label, _ in itertools.groupby(labels)]
    assert len(runs) == 2, f"calls interleaved: {labels}"

    # The final state must be wholly one rule's configuration, never a mix
    # (e.g. rule B's hvac_mode with rule A's temperature).
    final = hass.states.get("climate.ac")
    final_owner = owner_by_value[final.attributes["fan_mode"]]
    if final_owner == "A":
        assert final.state == "cool"
        assert final.attributes["temperature"] == 22
    else:
        assert final.state == "heat"
        assert final.attributes["temperature"] == 24


# --- Finding 3: one device failing must not block its siblings -------------


async def test_sibling_device_still_applied_after_a_failure(hass, engine):
    """One device's service call raising must not abort the rest of the rule."""
    seen_entity_ids = []

    async def flaky_turn_on(call):
        seen_entity_ids.append(call.data["entity_id"])
        if call.data["entity_id"] == "input_boolean.t":
            raise RuntimeError("simulated failure for input_boolean.t")

    hass.services.async_register("input_boolean", "turn_on", flaky_turn_on)
    hass.states.async_set("input_boolean.t", "off")
    hass.states.async_set("input_boolean.salon", "off")

    # Task 10 added retry-on-failure: input_boolean.t now fails all
    # RETRY_ATTEMPTS attempts before the rule moves on. Patch sleep so the
    # retry delays between those attempts don't slow the test down.
    with patch("custom_components.shabbat_scheduler.engine.asyncio.sleep"):
        results = await engine.async_apply_rule(
            _rule(devices=("input_boolean.t", "input_boolean.salon"))
        )
    await hass.async_block_till_done()

    # Both devices were reached - the failure on the first (retried
    # RETRY_ATTEMPTS times) did not abort processing of the second.
    assert seen_entity_ids == ["input_boolean.t"] * 3 + ["input_boolean.salon"]

    by_entity = {r["entity_id"]: r["outcome"] for r in results}
    assert by_entity["input_boolean.t"] == "failed"
    assert by_entity["input_boolean.salon"] == "changed"


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

    rule = _rule(devices=("switch.t",))
    # Patch sleep so the test does not actually wait 60 seconds.
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
        results = await engine.async_apply_rule(_rule(devices=("switch.t",)))

    assert len(attempts) == 2
    assert results[0]["outcome"] == "changed"


from datetime import timedelta

from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.shabbat_scheduler.const import CANDLE_SENSOR, HAVDALAH_SENSOR


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
        Rule(id="r", profile=3, day="1", time=time(11, 0), action=Action.ON)
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
             action=Action.ON, devices=("input_boolean.t",))
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
             action=Action.ON, devices=("input_boolean.t",))
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
             action=Action.ON, devices=("input_boolean.t",))
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
async def test_catch_up_applies_the_last_passed_rule(hass, engine):
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    hass.states.async_set("input_boolean.t", "off")
    await engine.store.async_replace_all({}, [
        Rule(id="on", profile=1, day="1", time=time(11, 0),
             action=Action.ON, devices=("input_boolean.t",)),
        Rule(id="off", profile=1, day="1", time=time(18, 0),
             action=Action.OFF, devices=("input_boolean.t",)),
    ])
    await engine.async_refresh()

    # 11:30 local - the 11:00 ON has passed, 18:00 OFF has not.
    with freeze_time("2026-08-15T08:30:00+00:00"):
        results = await engine.async_catch_up()
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.t").state == "on"
    assert [r["outcome"] for r in results] == ["changed"]


async def test_catch_up_before_any_rule_does_nothing(hass, engine):
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    hass.states.async_set("input_boolean.t", "off")
    await engine.store.async_replace_all({}, [
        Rule(id="on", profile=1, day="1", time=time(11, 0),
             action=Action.ON, devices=("input_boolean.t",)),
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
             action=Action.CUSTOM, script="script.demo"),
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
             action=Action.CUSTOM, script="script.demo",
             replay_on_restart=True),
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
    # replayed every `replay_on_restart` custom rule unconditionally,
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
             action=Action.CUSTOM, script="script.demo",
             replay_on_restart=True),
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
             action=Action.CUSTOM, script="script.demo",
             replay_on_restart=True, enabled=False),
    ])
    await engine.async_refresh()

    with freeze_time("2026-08-15T08:30:00+00:00"):
        await engine.async_catch_up()
    await hass.async_block_till_done()
    assert calls == []


async def test_catch_up_declines_to_act_on_a_conflicting_pair(hass, engine):
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    hass.states.async_set("input_boolean.t", "off")
    await engine.store.async_replace_all({}, [
        Rule(id="on", profile=1, day="1", time=time(11, 0),
             action=Action.ON, devices=("input_boolean.t",)),
        Rule(id="off-same-time", profile=1, day="1", time=time(11, 0),
             action=Action.OFF, devices=("input_boolean.t",)),
    ])
    await engine.async_refresh()

    with freeze_time("2026-08-15T08:30:00+00:00"):
        results = await engine.async_catch_up()
    await hass.async_block_till_done()

    assert results == []
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
             action=Action.OFF, devices=("input_boolean.t",)),
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
             action=Action.OFF, devices=("input_boolean.t",)),
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
             action=Action.ON, devices=("input_boolean.t",)),
        Rule(id="late-off", profile=1, day="1", time=time(23, 0),
             action=Action.OFF, devices=("input_boolean.t",)),
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


async def test_unsupported_domain_reports_skipped_not_ok(hass, engine, caplog):
    """A cover./media_player. rule used to report success and do nothing."""
    hass.states.async_set("cover.a", "open")
    results = await engine.async_apply_rule(
        _rule(action=Action.OFF, devices=("cover.a",))
    )

    assert [item["outcome"] for item in results] == ["skipped"]
    assert "cover" in caplog.text
    assert "cover.a" in caplog.text


async def test_unsupported_fan_mode_is_logged_with_entity_and_mode(
    hass, engine, caplog
):
    hass.states.async_set(
        "climate.ac", "cool",
        {"fan_modes": ["auto", "high"], "fan_mode": "auto"},
    )
    results = await engine.async_apply_rule(
        _rule(devices=("climate.ac",), settings={"fan_mode": "quiet"})
    )

    assert [item["outcome"] for item in results] == ["skipped"]
    assert results[0]["attribute"] == "fan_mode"
    assert "climate.ac" in caplog.text
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
        results = await engine.async_apply_rule(_rule(devices=("switch.t",)))

    assert results[0]["outcome"] == "failed"
    assert "cloud auth expired" in results[0]["reason"]

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
        Rule(id="r", profile=1, day="1", time=time(11, 0), action=Action.ON,
             devices=("input_boolean.t",), enabled=False),
    ])
    await engine.async_refresh()

    assert engine.upcoming() == []
    assert "shabbat_scheduler_no_profile" in hass.data["persistent_notification"]
