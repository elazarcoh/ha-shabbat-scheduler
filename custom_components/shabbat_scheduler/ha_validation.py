"""Validation that needs Home Assistant's own schemas.

The structural half lives in `rule_schema.py`, which is deliberately free
of Home Assistant so the tricky parsing is testable without an instance.
This is the other half: the target and the conditions are Home
Assistant's own formats, and validating them by hand would mean
reimplementing - and then drifting from - schemas HA already publishes.

Deliberately NOT checked here: whether `action` names a service that
currently exists, or whether a target entity itself currently exists.
Services and entities come and go with integrations and reloads, so a
rule naming one that is missing right now may be correct an hour later.
That failure belongs at fire time, where it is reported against the rule.

`describe_data_violations`/`validate_data_against_target` are a narrower
exception to that rule, not a reversal of it: they check whether an
ALREADY-RESOLVED entity's own advertised options (its `fan_modes`,
`hvac_modes`, and the like) currently accept a value in `data` - not
whether the entity or the service exists at all. That is knowable right
now, from the entity's live state, with no service call - unlike "does
this service exist," which needs nothing but a name and can go stale
between here and fire time regardless.
"""

from __future__ import annotations

import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import condition
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import target as target_helper

from .models import Rule
from .rule_schema import RuleValidationError

_TARGET_SCHEMA = vol.Schema(cv.TARGET_SERVICE_FIELDS)

# Each key is a `data` field this integration knows to be a closed choice
# advertised by the entity itself, at the entity's own "<field>s" attribute
# - climate's `hvac_mode`/`fan_mode`/`swing_mode`, and `preset_mode`, shared
# with a few other domains (climate, fan, humidifier, water_heater).
# Deliberately a short, hand-picked list rather than "every attribute
# ending in 's'": a field this integration does not recognise is simply not
# checked, never guessed at.
_ENUM_DATA_FIELDS = {
    "hvac_mode": "hvac_modes",
    "fan_mode": "fan_modes",
    "swing_mode": "swing_modes",
    "preset_mode": "preset_modes",
}


def _resolve_target_entity_ids(hass: HomeAssistant, target: dict) -> frozenset[str]:
    """The entity ids `target` names RIGHT NOW - areas/labels/devices expanded.

    Same idiom as `engine.py`'s `_inspect_target` and `websocket_api.py`'s
    `_resolver`: a target HA cannot even parse resolves to an empty set here
    rather than raising - malformed shape is `validate_target`'s job, not
    this one's.
    """
    if not target:
        return frozenset()
    try:
        selected = target_helper.async_extract_referenced_entity_ids(
            hass, target_helper.TargetSelection(dict(target)),
        )
    except Exception:  # noqa: BLE001 - a bad target is not this check's job
        return frozenset()
    return frozenset(selected.referenced | selected.indirectly_referenced)


def describe_data_violations(hass: HomeAssistant, target: dict, data: dict) -> list[str]:
    """Every currently-knowable reason `data` would be refused by `target`.

    Checks only the enum fields in `_ENUM_DATA_FIELDS`, and only against
    entities the target resolves to right now, reading each one's own
    "<field>s" attribute - already sitting on its live state, so this needs
    no service call to ask. An entity the target cannot currently resolve -
    a typo, an unloaded integration, an area with nothing in it - is
    silently skipped, same reasoning as `validate_target`: whether it
    exists is a fire-time question, not this one's. An entity that exists
    but does not publish the relevant "<field>s" attribute at all (the
    field does not apply to this domain) is skipped for that field alone.

    This can still be wrong in both directions and that is accepted: a
    value valid now can be rejected later if the entity's own advertised
    options change (a firmware update narrowing fan_modes, say), and a
    value flagged here might already have been accepted moments ago before
    such a change. It only reports what is knowable from the entity's
    CURRENT state - the same trade-off `validate_target` and `action`
    already make deliberately, spelled out in this module's own docstring.
    """
    fields = {key: data[key] for key in _ENUM_DATA_FIELDS if key in data}
    if not fields:
        return []
    violations = []
    for entity_id in sorted(_resolve_target_entity_ids(hass, target)):
        state = hass.states.get(entity_id)
        if state is None:
            continue
        for field in sorted(fields):
            value = fields[field]
            valid = state.attributes.get(_ENUM_DATA_FIELDS[field])
            if valid is None or value in valid:
                continue
            violations.append(
                f"{field} {value!r} is not valid for {entity_id}; "
                f"valid values are: {', '.join(str(v) for v in valid)}"
            )
    return violations


def validate_data_against_target(hass: HomeAssistant, target: dict, data: dict) -> None:
    """Raise RuleValidationError for the first violation `describe_data_violations` finds.

    One error at a time, matching every other check in this module - a
    caller that wants the full list (Run Now's simulate path, which cannot
    stop a card author mid-edit the way a raise does) calls
    `describe_data_violations` directly instead.
    """
    violations = describe_data_violations(hass, target, data)
    if violations:
        raise RuleValidationError(violations[0])


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
    validate_data_against_target(hass, dict(rule.target), dict(rule.data))

    for item in rule.condition:
        try:
            validated = cv.CONDITION_SCHEMA(dict(item))
            await condition.async_validate_condition_config(hass, validated)
        except (vol.Invalid, HomeAssistantError) as err:
            raise RuleValidationError(f"condition is not valid: {err}") from err
