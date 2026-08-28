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


# --- describe_data_violations / validate_data_against_target -------------
#
# Real bug this exists for (2026-08-28, elazar's actual production instance):
# a rule authored for a kids-room AC (fan_modes including "silent") was
# re-targeted, via the card, to a living-room unit whose fan_modes do NOT
# include "silent" - the rule saved without complaint and only failed hours
# later when it actually fired. These tests mock the entity's live state the
# way elazar's real units report it, standing in for "a real device" per
# their own instruction to simulate one rather than needing the dev
# container for this.

async def test_a_fan_mode_the_target_does_not_advertise_is_rejected(hass):
    hass.states.async_set(
        "climate.living_room", "cool", {"fan_modes": ["auto", "quiet", "low"]},
    )
    with pytest.raises(RuleValidationError, match="fan_mode 'silent' is not valid"):
        await async_validate_rule(hass, _rule(
            target={"entity_id": ["climate.living_room"]},
            data={"fan_mode": "silent"},
        ))


async def test_a_fan_mode_the_target_does_advertise_is_accepted(hass):
    hass.states.async_set(
        "climate.kids_room", "cool", {"fan_modes": ["auto", "silent"]},
    )
    await async_validate_rule(hass, _rule(
        target={"entity_id": ["climate.kids_room"]},
        data={"fan_mode": "silent"},
    ))


async def test_an_invalid_hvac_mode_is_also_caught(hass):
    hass.states.async_set(
        "climate.living_room", "cool", {"hvac_modes": ["off", "cool", "heat"]},
    )
    with pytest.raises(RuleValidationError, match="hvac_mode 'dry' is not valid"):
        await async_validate_rule(hass, _rule(
            target={"entity_id": ["climate.living_room"]},
            data={"hvac_mode": "dry"},
        ))


async def test_a_target_that_does_not_currently_resolve_is_not_checked(hass):
    """No entity named `climate.does_not_exist` exists - that failure

    belongs at fire time (module docstring), same as an unknown service.
    """
    await async_validate_rule(hass, _rule(
        target={"entity_id": ["climate.does_not_exist"]},
        data={"fan_mode": "silent"},
    ))


async def test_an_entity_with_no_such_attribute_is_not_checked(hass):
    """A switch has no `fan_modes` attribute at all - the field simply

    does not apply to this domain, not a violation.
    """
    hass.states.async_set("switch.plug", "on")
    await async_validate_rule(hass, _rule(
        target={"entity_id": ["switch.plug"]},
        data={"fan_mode": "silent"},
    ))


async def test_a_field_this_check_does_not_recognise_is_ignored(hass):
    hass.states.async_set("climate.living_room", "cool", {"fan_modes": ["auto"]})
    await async_validate_rule(hass, _rule(
        target={"entity_id": ["climate.living_room"]},
        data={"temperature": 9999},
    ))


async def test_one_bad_entity_among_several_targeted_is_still_caught(hass):
    hass.states.async_set(
        "climate.kids_room", "cool", {"fan_modes": ["auto", "silent"]},
    )
    hass.states.async_set(
        "climate.living_room", "cool", {"fan_modes": ["auto", "quiet"]},
    )
    with pytest.raises(RuleValidationError, match="climate.living_room"):
        await async_validate_rule(hass, _rule(
            target={"entity_id": ["climate.kids_room", "climate.living_room"]},
            data={"fan_mode": "silent"},
        ))


async def test_describe_data_violations_reports_every_violation_not_just_the_first(hass):
    from custom_components.shabbat_scheduler.ha_validation import (
        describe_data_violations,
    )

    hass.states.async_set(
        "climate.living_room", "cool",
        {"fan_modes": ["auto", "quiet"], "hvac_modes": ["off", "cool"]},
    )
    violations = describe_data_violations(
        hass,
        {"entity_id": ["climate.living_room"]},
        {"fan_mode": "silent", "hvac_mode": "dry"},
    )

    assert len(violations) == 2
    assert any("fan_mode" in v for v in violations)
    assert any("hvac_mode" in v for v in violations)
