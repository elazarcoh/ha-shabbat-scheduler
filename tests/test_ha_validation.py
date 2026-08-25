"""Validation that needs Home Assistant's own schemas."""

from datetime import time

import pytest

from custom_components.shabbat_scheduler.ha_validation import async_validate_rule
from custom_components.shabbat_scheduler.models import Rule
from custom_components.shabbat_scheduler.rule_schema import RuleValidationError


def _rule(**over):
    base = dict(
        id="r1", profile=1, day="1", time=time(11, 0),
        action="climate.set_temperature",
        target={"entity_id": ["climate.salon"]},
    )
    base.update(over)
    return Rule(**base)


async def test_a_plain_entity_target_is_accepted(hass):
    await async_validate_rule(hass, _rule())


async def test_area_and_label_targets_are_accepted(hass):
    await async_validate_rule(hass, _rule(target={"area_id": "salon"}))
    await async_validate_rule(hass, _rule(target={"label_id": "shabbat"}))


async def test_an_unknown_target_key_is_rejected(hass):
    with pytest.raises(RuleValidationError):
        await async_validate_rule(hass, _rule(target={"room": "salon"}))


async def test_a_valid_condition_is_accepted(hass):
    await async_validate_rule(hass, _rule(condition=(
        {"condition": "state", "entity_id": "binary_sensor.x", "state": "on"},
    )))


async def test_a_malformed_condition_is_rejected(hass):
    with pytest.raises(RuleValidationError):
        await async_validate_rule(hass, _rule(condition=(
            {"condition": "state"},          # no entity_id, no state
        )))


async def test_an_unknown_condition_type_is_rejected(hass):
    with pytest.raises(RuleValidationError):
        await async_validate_rule(hass, _rule(condition=(
            {"condition": "vibes", "entity_id": "x"},
        )))


async def test_an_empty_target_is_accepted(hass):
    """Some actions need none - notify.persistent_notification, for one."""
    await async_validate_rule(hass, _rule(action="notify.persistent_notification", target={}))


async def test_a_valid_sun_condition_is_accepted(hass):
    """`sun` dispatches to homeassistant.components.sun's own condition platform,

    unlike `state`/`numeric_state`/`vibes` above, which never leave core
    condition.py. This exercises `SunCondition.async_validate_config`.
    """
    await async_validate_rule(hass, _rule(condition=(
        {"condition": "sun", "before": "sunset"},
    )))


async def test_a_malformed_sun_condition_is_rejected(hass):
    """Neither `before` nor `after` given - rejected by the sun platform's

    own `cv.has_at_least_one_key("before", "after")`, not by core condition.py.
    """
    with pytest.raises(RuleValidationError):
        await async_validate_rule(hass, _rule(condition=(
            {"condition": "sun"},
        )))


async def test_a_valid_zone_condition_is_accepted(hass):
    """`zone` dispatches to homeassistant.components.zone's own condition

    platform. No zone or device_tracker entity needs to exist for shape
    validation - `cv.entity_ids` only checks the entity_id format.
    """
    await async_validate_rule(hass, _rule(condition=(
        {"condition": "zone", "entity_id": "device_tracker.x", "zone": "zone.home"},
    )))


async def test_a_malformed_zone_condition_is_rejected(hass):
    """No `zone` given - rejected by the zone platform's own schema."""
    with pytest.raises(RuleValidationError):
        await async_validate_rule(hass, _rule(condition=(
            {"condition": "zone", "entity_id": "device_tracker.x"},
        )))
