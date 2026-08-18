"""Validation for rules arriving from the API. No Home Assistant imports.

Kept pure so it is testable without a running instance and usable from both
the websocket layer and YAML import.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import time

from .models import Action, EREV, Rule

_FIELDS = {
    "profile", "day", "time", "action", "devices", "settings", "name",
    "icon", "enabled", "script", "variables", "replay_on_restart", "color",
}

_DEFAULTS_FIELDS = {"devices", "settings"}


class RuleValidationError(ValueError):
    """A rule as supplied cannot be built."""


def _check_unknown_fields(data: dict, allowed: set[str] = _FIELDS) -> None:
    """Check for unknown fields in data."""
    unknown = set(data) - allowed
    if unknown:
        raise RuleValidationError(f"unknown field(s): {sorted(unknown)}")


def _day(value) -> str:
    text = str(value)
    if text == EREV:
        return text
    if text in ("1", "2", "3"):
        return text
    raise RuleValidationError(
        f"day must be {EREV!r} or '1'..'3', got {value!r}"
    )


def _profile(value) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RuleValidationError(f"profile must be an integer 1..3, got {value!r}")
    if not 1 <= value <= 3:
        raise RuleValidationError(f"profile must be an integer 1..3, got {value!r}")
    return value


def _time(value) -> time:
    try:
        return time.fromisoformat(str(value))
    except ValueError as err:
        raise RuleValidationError(f"time is not a valid clock time: {value!r}") from err


def _action(value) -> Action:
    try:
        return Action(value)
    except ValueError as err:
        raise RuleValidationError(
            f"action must be one of on/off/custom, got {value!r}"
        ) from err


def _bool(field: str, value) -> bool:
    """A real bool, never a truthy string.

    `{"enabled": "false"}` - what a JS form binding yields when it forgets
    to parse - used to sail through: the API echoed the rule as
    `"false"`, a card rendered it off, and the engine RAN it, because a
    non-empty string is truthy.
    """
    if not isinstance(value, bool):
        raise RuleValidationError(
            f"{field} must be true or false, got {value!r}"
        )
    return value


def _text(field: str, value) -> str | None:
    """A string or nothing. A dict here breaks entity creation."""
    if value is None or isinstance(value, str):
        return value
    raise RuleValidationError(
        f"{field} must be a string or null, got {value!r}"
    )


def _coerce(field: str, value):
    if field == "day":
        return _day(value)
    if field == "profile":
        return _profile(value)
    if field == "time":
        return _time(value)
    if field == "action":
        return _action(value)
    if field == "devices":
        if isinstance(value, str):
            raise RuleValidationError(f"devices must be a list or tuple, got {value!r}")
        return tuple(value or ())
    if field == "settings":
        if not isinstance(value, Mapping):
            raise RuleValidationError(f"settings must be a mapping, got {value!r}")
        return dict(value)
    if field == "variables":
        if not isinstance(value, Mapping):
            raise RuleValidationError(f"variables must be a mapping, got {value!r}")
        return dict(value)
    if field in ("enabled", "replay_on_restart"):
        return _bool(field, value)
    if field in ("name", "icon", "script", "color"):
        return _text(field, value)
    # Every rule field is now typed; only the defaults payload, which
    # shares this helper for its own two keys, ever reaches here.
    return value


def validate_rule(rule: Rule) -> None:
    """Invariants that need the whole rule, not one field."""
    if rule.action is Action.CUSTOM and not rule.script:
        raise RuleValidationError("a custom action requires a script")


def validate_defaults(data: dict) -> dict:
    """Validate a defaults payload into coerced kwargs.

    Shares the same 'devices'/'settings' shape guards as rule fields,
    coerced via the same helpers used for rules - a bare string for
    'devices' or a non-mapping 'settings' is rejected here rather than
    persisted, so a malformed defaults payload cannot blow up later at
    rule-resolution time.
    """
    _check_unknown_fields(data, _DEFAULTS_FIELDS)
    return {field: _coerce(field, value) for field, value in data.items()}


def changes_from_api(data: dict) -> dict:
    """Validate a partial update into kwargs for dataclasses.replace."""
    if "id" in data:
        raise RuleValidationError("id cannot be changed")
    _check_unknown_fields(data)
    return {field: _coerce(field, value) for field, value in data.items()}


def rule_from_api(data: dict, rule_id: str) -> Rule:
    """Build a validated Rule. Any client-supplied id is ignored."""
    payload = {key: value for key, value in data.items() if key != "id"}
    _check_unknown_fields(payload)

    for required in ("profile", "day", "time", "action"):
        if required not in payload:
            raise RuleValidationError(f"missing required field: {required}")

    kwargs = {field: _coerce(field, value) for field, value in payload.items()}
    rule = Rule(id=rule_id, **kwargs)

    validate_rule(rule)
    return rule
