"""Conditions evaluated at fire time.

A rule may carry HA condition configs (`Rule.condition`); all must pass or
the rule is blocked. A blocked rule must SAY so - `results == []` would be
indistinguishable from "nothing to do", which is exactly the failure this
whole project exists to prevent. See engine.py's `_conditions_pass`.
"""

from datetime import time

from pytest_homeassistant_custom_component.common import async_capture_events

from custom_components.shabbat_scheduler.const import EVENT_RULE_COMPLETED
from custom_components.shabbat_scheduler.engine import ShabbatEngine
from custom_components.shabbat_scheduler.models import Rule
from custom_components.shabbat_scheduler.store import RuleStore


async def _engine(hass):
    store = RuleStore(hass)
    await store.async_load()
    return ShabbatEngine(hass, store)


def _rule(condition):
    return Rule(
        id="r", profile=1, day="1", time=time(11, 0),
        action="input_boolean.turn_on",
        target={"entity_id": ["input_boolean.salon"]},
        condition=condition,
    )


async def test_a_rule_with_a_passing_condition_fires(hass, test_booleans):
    engine = await _engine(hass)
    hass.states.async_set("binary_sensor.gate", "on")
    rule = _rule(({"condition": "state",
                   "entity_id": "binary_sensor.gate",
                   "state": "on"},))
    results = await engine.async_apply_rule(rule)
    assert hass.states.get("input_boolean.salon").state == "on"
    assert results[0]["outcome"] == "called"


async def test_a_rule_with_a_failing_condition_does_not_fire(hass, test_booleans):
    engine = await _engine(hass)
    hass.states.async_set("binary_sensor.gate", "off")
    rule = _rule(({"condition": "state",
                   "entity_id": "binary_sensor.gate",
                   "state": "on"},))
    results = await engine.async_apply_rule(rule)
    assert hass.states.get("input_boolean.salon").state == "off"


async def test_a_blocked_rule_says_so_rather_than_looking_successful(
    hass, test_booleans
):
    engine = await _engine(hass)
    hass.states.async_set("binary_sensor.gate", "off")
    rule = _rule(({"condition": "state",
                   "entity_id": "binary_sensor.gate",
                   "state": "on"},))
    results = await engine.async_apply_rule(rule)

    assert results == [{"outcome": "blocked", "reason": "condition not met"}]
    # "no results" would be indistinguishable from "nothing to do".
    assert results != []


async def test_every_condition_must_pass(hass, test_booleans):
    engine = await _engine(hass)
    hass.states.async_set("binary_sensor.a", "on")
    hass.states.async_set("binary_sensor.b", "off")
    rule = _rule((
        {"condition": "state", "entity_id": "binary_sensor.a", "state": "on"},
        {"condition": "state", "entity_id": "binary_sensor.b", "state": "on"},
    ))
    results = await engine.async_apply_rule(rule)
    assert results[0]["outcome"] == "blocked"


async def test_a_condition_that_errors_blocks_rather_than_fires(hass, test_booleans):
    """Erring towards not acting: an unexpected error is not consent."""
    engine = await _engine(hass)
    rule = _rule(({"condition": "state",
                   "entity_id": "binary_sensor.missing",
                   "state": "on"},))
    results = await engine.async_apply_rule(rule)
    assert results[0]["outcome"] == "blocked"


async def test_a_blocked_rule_is_visible_in_the_logbook(hass, test_booleans):
    """It fires EVENT_RULE_COMPLETED carrying the blocked result."""
    engine = await _engine(hass)
    events = async_capture_events(hass, EVENT_RULE_COMPLETED)
    hass.states.async_set("binary_sensor.gate", "off")
    rule = _rule(({"condition": "state",
                   "entity_id": "binary_sensor.gate",
                   "state": "on"},))
    await engine.async_apply_rule(rule)
    assert events[0].data["results"][0]["outcome"] == "blocked"
