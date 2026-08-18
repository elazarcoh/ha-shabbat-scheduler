"""Validation for rules arriving from the API. No Home Assistant imports.

Kept pure so it is testable without a running instance and usable from both
the websocket layer and YAML import.
"""

from __future__ import annotations

from datetime import time

from .models import Action, EREV, Rule

_FIELDS = {
    "profile", "day", "time", "action", "devices", "settings", "name",
    "icon", "enabled", "script", "variables", "replay_on_restart", "color",
}


class RuleValidationError(ValueError):
    """A rule as supplied cannot be built."""


def _day(value) -> str:
    text = str(value)
    if text == EREV:
        return text
    if text.isdigit() and 1 <= int(text) <= 3:
        return text
    raise RuleValidationError(
        f"day must be {EREV!r} or '1'..'3', got {value!r}"
    )


def _profile(value) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as err:
        raise RuleValidationError(f"profile must be 1..3, got {value!r}") from err
    if not 1 <= number <= 3:
        raise RuleValidationError(f"profile must be 1..3, got {value!r}")
    return number


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
        return tuple(value or ())
    if field in ("settings", "variables"):
        return dict(value or {})
    return value


def changes_from_api(data: dict) -> dict:
    """Validate a partial update into kwargs for dataclasses.replace."""
    if "id" in data:
        raise RuleValidationError("id cannot be changed")
    unknown = set(data) - _FIELDS
    if unknown:
        raise RuleValidationError(f"unknown field(s): {sorted(unknown)}")
    return {field: _coerce(field, value) for field, value in data.items()}


def rule_from_api(data: dict, rule_id: str) -> Rule:
    """Build a validated Rule. Any client-supplied id is ignored."""
    payload = {key: value for key, value in data.items() if key != "id"}
    unknown = set(payload) - _FIELDS
    if unknown:
        raise RuleValidationError(f"unknown field(s): {sorted(unknown)}")

    for required in ("profile", "day", "time", "action"):
        if required not in payload:
            raise RuleValidationError(f"missing required field: {required}")

    kwargs = {field: _coerce(field, value) for field, value in payload.items()}
    rule = Rule(id=rule_id, **kwargs)

    if rule.action is Action.CUSTOM and not rule.script:
        raise RuleValidationError("a custom action requires a script")
    return rule
