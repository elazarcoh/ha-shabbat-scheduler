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
