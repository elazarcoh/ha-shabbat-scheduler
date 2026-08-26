"""Execution through Home Assistant's own service machinery.

v1's engine branched on a closed set of domains (`Action.ON/OFF/CUSTOM`
resolving through `plan_calls`). v2's `Rule.action` is any
"domain.service" string, dispatched through `async_call_from_config` -
the same machinery HA's own scripts and automations use. These tests
prove that path, not the v1 climate-shaped one that test_engine.py still
covers pending its own rewrite.
"""

from datetime import time
from unittest.mock import patch

from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.shabbat_scheduler.engine import ShabbatEngine
from custom_components.shabbat_scheduler.models import Rule
from custom_components.shabbat_scheduler.store import RuleStore


async def _engine(hass):
    store = RuleStore(hass)
    await store.async_load()
    return ShabbatEngine(hass, store)


async def test_a_rule_calls_its_action(hass, test_booleans):
    engine = await _engine(hass)
    rule = Rule(
        id="r", profile=1, day="1", time=time(11, 0),
        action="input_boolean.turn_on",
        target={"entity_id": ["input_boolean.salon"]},
    )
    results = await engine.async_apply_rule(rule)

    assert hass.states.get("input_boolean.salon").state == "on"
    assert [r["outcome"] for r in results] == ["called"]
    assert results[0]["action"] == "input_boolean.turn_on"


async def test_any_domain_works_not_just_climate_and_switches(hass):
    """v1 returned "unsupported domain" for everything but four domains."""
    engine = await _engine(hass)
    calls = async_mock_service(hass, "notify", "persistent_notification")
    rule = Rule(
        id="r", profile=1, day="1", time=time(11, 0),
        action="notify.persistent_notification",
        data={"message": "Shabbat shalom"},
    )
    results = await engine.async_apply_rule(rule)

    assert len(calls) == 1
    assert calls[0].data["message"] == "Shabbat shalom"
    assert results[0]["outcome"] == "called"


async def test_the_climate_shim_sends_two_calls(hass):
    engine = await _engine(hass)
    mode = async_mock_service(hass, "climate", "set_hvac_mode")
    temp = async_mock_service(hass, "climate", "set_temperature")
    # A real target entity: this test is about the shim splitting one
    # action into two calls, not about the unknown-target check (Plan-2
    # Gap B), which would otherwise report both calls failed.
    hass.states.async_set("climate.salon", "off")
    rule = Rule(
        id="r", profile=1, day="1", time=time(11, 0),
        action="climate.set_temperature",
        target={"entity_id": ["climate.salon"]},
        data={"temperature": 26, "hvac_mode": "cool"},
    )
    results = await engine.async_apply_rule(rule)

    assert len(mode) == 1 and len(temp) == 1
    assert "hvac_mode" not in temp[0].data
    assert [r["outcome"] for r in results] == ["called", "called"]


async def test_a_failing_call_is_reported_not_swallowed(hass):
    engine = await _engine(hass)
    rule = Rule(
        id="r", profile=1, day="1", time=time(11, 0),
        action="nonexistent.service",
    )
    # RETRY_ATTEMPTS x RETRY_DELAY_SECONDS is a genuine 60s of real sleep
    # between the 3 attempts; patched out so the failure path is still
    # exercised without slowing the suite down.
    with patch("custom_components.shabbat_scheduler.engine.asyncio.sleep"):
        results = await engine.async_apply_rule(rule)

    assert results[0]["outcome"] == "failed"
    assert results[0]["error"]


async def test_a_final_failure_notifies_because_a_rule_that_does_not_fire_must_say_why(
    hass,
):
    """last_run is a passive attribute nobody polls, and a log line is
    invisible on a headless instance during Shabbat - the one scenario this
    integration exists for. The household must be TOLD, not merely have
    the failure recorded somewhere queryable."""
    engine = await _engine(hass)
    rule = Rule(
        id="r", profile=1, day="1", time=time(11, 0),
        name="Havdalah lights",
        action="nonexistent.service",
        target={"entity_id": ["light.does_not_exist"]},
    )
    with patch("custom_components.shabbat_scheduler.engine.asyncio.sleep"):
        await engine.async_apply_rule(rule)

    notifications = hass.data.get("persistent_notification", {})
    assert notifications, "expected a persistent_notification on final failure"
    message = next(iter(notifications.values()))["message"]
    assert "Havdalah lights" in message
    assert "nonexistent.service" in message


async def test_a_successful_call_creates_no_notification(hass, test_booleans):
    engine = await _engine(hass)
    rule = Rule(
        id="r", profile=1, day="1", time=time(11, 0),
        action="input_boolean.turn_on",
        target={"entity_id": ["input_boolean.salon"]},
    )
    await engine.async_apply_rule(rule)

    assert not hass.data.get("persistent_notification")


async def test_the_call_carries_our_context_so_changes_attribute_to_us(
    hass, test_booleans
):
    engine = await _engine(hass)
    rule = Rule(
        id="r", profile=1, day="1", time=time(11, 0),
        action="input_boolean.turn_on",
        target={"entity_id": ["input_boolean.salon"]},
    )
    await engine.async_apply_rule(rule)

    state = hass.states.get("input_boolean.salon")
    assert engine.is_our_context(state.context)


async def test_simulate_calls_nothing(hass, test_booleans):
    engine = await _engine(hass)
    rule = Rule(
        id="r", profile=1, day="1", time=time(11, 0),
        action="input_boolean.turn_on",
        target={"entity_id": ["input_boolean.salon"]},
    )
    results = await engine.async_apply_rule(rule, simulate=True)

    assert hass.states.get("input_boolean.salon").state == "off"
    assert results[0]["outcome"] == "would_call"
