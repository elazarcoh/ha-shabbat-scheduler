"""Conditions evaluated at fire time.

A rule may carry HA condition configs (`Rule.condition`); all must pass or
the rule is blocked. A blocked rule must SAY so - `results == []` would be
indistinguishable from "nothing to do", which is exactly the failure this
whole project exists to prevent, and it must say WHICH condition blocked
it. See engine.py's `_condition_block_reason`.
"""

from datetime import time

from pytest_homeassistant_custom_component.common import async_capture_events

from custom_components.shabbat_scheduler.const import EVENT_RULE_COMPLETED
from custom_components.shabbat_scheduler.engine import ShabbatEngine
from custom_components.shabbat_scheduler.logbook import async_describe_events
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

    assert len(results) == 1
    assert results[0]["outcome"] == "blocked"
    assert results[0]["reason"]
    # "no results" would be indistinguishable from "nothing to do".
    assert results != []


async def test_the_blocking_condition_is_named(hass, test_booleans):
    """`_condition_block_reason` returns on the FIRST failure.

    With a bare "condition not met" a rule carrying three conditions gives
    the user no way at all to tell which one held it back - and the one
    day they would need to know is the day they cannot investigate.
    """
    engine = await _engine(hass)
    hass.states.async_set("binary_sensor.a", "on")
    hass.states.async_set("binary_sensor.b", "off")
    rule = _rule((
        {"condition": "state", "entity_id": "binary_sensor.a", "state": "on"},
        {"condition": "state", "entity_id": "binary_sensor.b", "state": "on"},
    ))
    results = await engine.async_apply_rule(rule)

    reason = results[0]["reason"]
    assert "binary_sensor.b" in reason      # the one that actually failed
    assert "binary_sensor.a" not in reason  # not the one that passed
    assert "2 of 2" in reason


async def test_a_condition_that_errors_names_itself_too(hass, test_booleans):
    engine = await _engine(hass)
    rule = _rule(({"condition": "state",
                   "entity_id": "binary_sensor.missing",
                   "state": "on"},))
    results = await engine.async_apply_rule(rule)

    reason = results[0]["reason"]
    assert "binary_sensor.missing" in reason
    assert "1 of 1" in reason


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


async def test_the_engines_own_payload_renders_a_blocked_rule_as_blocked(
    hass, test_booleans
):
    """The real engine event through the real describer.

    Not a hand-built payload: the reviewer's finding was precisely that the
    engine's own events rendered identically for a rule that fired and one
    that was blocked, and only driving the describer with what the engine
    actually fires can catch that.
    """
    described = {}
    async_describe_events(hass, lambda d, e, f: described.__setitem__(e, f))

    engine = await _engine(hass)
    events = async_capture_events(hass, EVENT_RULE_COMPLETED)

    hass.states.async_set("binary_sensor.gate", "on")
    passing = _rule(({"condition": "state",
                      "entity_id": "binary_sensor.gate",
                      "state": "on"},))
    await engine.async_apply_rule(passing)

    hass.states.async_set("binary_sensor.gate", "off")
    await engine.async_apply_rule(passing)
    await hass.async_block_till_done()

    fired_row = described[EVENT_RULE_COMPLETED](events[0])["message"]
    blocked_row = described[EVENT_RULE_COMPLETED](events[1])["message"]

    assert fired_row != blocked_row
    assert "did not run" in blocked_row.lower()
    assert "did not run" not in fired_row.lower()
    assert "binary_sensor.gate" in blocked_row
