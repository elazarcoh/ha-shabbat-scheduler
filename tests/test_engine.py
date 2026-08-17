from datetime import time

import pytest
from homeassistant.core import Context

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
