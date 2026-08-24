"""Validation that needs Home Assistant's own schemas.

The structural half lives in `rule_schema.py`, which is deliberately free
of Home Assistant so the tricky parsing is testable without an instance.
This is the other half: the target and the conditions are Home
Assistant's own formats, and validating them by hand would mean
reimplementing - and then drifting from - schemas HA already publishes.

Deliberately NOT checked here: whether `action` names a service that
currently exists. Services come and go with integrations and reloads, so
a rule naming one that is missing right now may be correct an hour later.
That failure belongs at fire time, where it is reported against the rule.
"""

from __future__ import annotations

import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import condition
from homeassistant.helpers import config_validation as cv

from .models import Rule
from .rule_schema import RuleValidationError

_TARGET_SCHEMA = vol.Schema(cv.TARGET_SERVICE_FIELDS)


async def async_validate_rule(hass: HomeAssistant, rule: Rule) -> None:
    """Raise RuleValidationError if HA would refuse this rule's shape."""
    try:
        _TARGET_SCHEMA(dict(rule.target))
    except vol.Invalid as err:
        raise RuleValidationError(f"target is not valid: {err}") from err

    for item in rule.condition:
        try:
            validated = cv.CONDITION_SCHEMA(dict(item))
            await condition.async_validate_condition_config(hass, validated)
        except (vol.Invalid, HomeAssistantError) as err:
            raise RuleValidationError(f"condition is not valid: {err}") from err
