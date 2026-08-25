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


def validate_target(target: dict) -> None:
    """Raise RuleValidationError if HA would refuse this target selector.

    Factored out of `async_validate_rule` so the shared DEFAULTS can go
    through the identical door. They come out of the same target editor a
    rule's does and are merged into every rule that has no target of its
    own (`block.merge_defaults`), so a defaults target validated more
    loosely than a rule's is a bogus key persisted at save time and
    refused at FIRE time - on Shabbat, hours later, with the dialog that
    could have said so long closed.

    Needs no `hass`: `cv.TARGET_SERVICE_FIELDS` is a pure shape check.
    Whether the entities, areas or labels it names currently EXIST is
    deliberately not asked - here or for a rule - for the same reason
    `action` is not resolved: they come and go with reloads, and that
    failure belongs at fire time where it is reported against the rule.
    """
    try:
        _TARGET_SCHEMA(dict(target))
    except vol.Invalid as err:
        raise RuleValidationError(f"target is not valid: {err}") from err


def validate_defaults_for_ha(defaults: dict) -> None:
    """Raise RuleValidationError if HA would refuse the defaults' target.

    The whole of the HA-side check for a defaults payload, because
    `validate_defaults` (rule_schema.py) accepts exactly `target` and
    `data`: there is no action to resolve and no condition to validate.
    `data` stays unchecked on purpose - it is an opaque service payload
    whose schema belongs to whichever service each inheriting rule names,
    and this integration has no way to know that here.

    `target` may be absent; a defaults payload that sets only `data` is
    normal and has nothing to check.
    """
    target = defaults.get("target")
    if target is None:
        return
    validate_target(target)


async def async_validate_rule(hass: HomeAssistant, rule: Rule) -> None:
    """Raise RuleValidationError if HA would refuse this rule's shape."""
    validate_target(dict(rule.target))

    for item in rule.condition:
        try:
            validated = cv.CONDITION_SCHEMA(dict(item))
            await condition.async_validate_condition_config(hass, validated)
        except (vol.Invalid, HomeAssistantError) as err:
            raise RuleValidationError(f"condition is not valid: {err}") from err
