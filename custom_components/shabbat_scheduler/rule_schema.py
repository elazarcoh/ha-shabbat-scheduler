"""Validation for rules arriving from the API. No Home Assistant imports.

Kept pure so it is testable without a running instance and usable from both
the websocket layer and YAML import.

Validates shape and type only. Whether `action` names a real service, or
`target`/`condition` are valid for it, is Home Assistant's own business -
`ha_validation.py` applies HA's own schemas for that.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import time, timedelta

from .const import MAX_PROFILE, MIN_PROFILE
from .models import EREV, Replay, Rule

_FIELDS = {
    "profile", "day", "time", "action", "target", "data",
    "condition", "replay", "name", "icon", "color", "enabled",
}

_DEFAULTS_FIELDS = {"target", "data"}

# Server-owned, and handed out on every rule the card reads (see
# `_state_payload`), so a read-modify-write client echoes it back - but NOT
# a field on `Rule` at all. An outcome is what happened to a rule, not part
# of its definition; it lives in the store's own outcome map, keyed by rule
# id.
#
# Dropped UNCONDITIONALLY rather than validated and stored: there is
# nowhere to put it - `Rule` has no such field, so keeping it would be a
# TypeError - and forging it would make the card report "fired" for a rule
# that never ran, or "blocked" for one that did, which is the precise lie
# this whole feature exists to make impossible.
_NEVER_STORED_FIELDS = {"last_outcome"}


class RuleValidationError(ValueError):
    """A rule as supplied cannot be built."""


def _strip_never_stored(data: dict) -> dict:
    """Drop the fields no client and no document may ever set. See above."""
    return {
        key: value for key, value in data.items()
        if key not in _NEVER_STORED_FIELDS
    }


def _check_unknown_fields(data: dict, allowed: set[str] = _FIELDS) -> None:
    """Check for unknown fields in data."""
    unknown = set(data) - allowed
    if unknown:
        raise RuleValidationError(f"unknown field(s): {sorted(unknown)}")


_VALID_DAYS = tuple(str(n) for n in range(MIN_PROFILE, MAX_PROFILE + 1))


def _day(value) -> str:
    text = str(value)
    if text == EREV:
        return text
    if text in _VALID_DAYS:
        return text
    raise RuleValidationError(
        f"day must be {EREV!r} or '{MIN_PROFILE}'..'{MAX_PROFILE}', got {value!r}"
    )


def _profile(value) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RuleValidationError(
            f"profile must be an integer {MIN_PROFILE}..{MAX_PROFILE}, got {value!r}"
        )
    if not MIN_PROFILE <= value <= MAX_PROFILE:
        raise RuleValidationError(
            f"profile must be an integer {MIN_PROFILE}..{MAX_PROFILE}, got {value!r}"
        )
    return value


def _time(value) -> time:
    try:
        return time.fromisoformat(str(value))
    except ValueError as err:
        raise RuleValidationError(f"time is not a valid clock time: {value!r}") from err


def _action(value) -> str:
    """A Home Assistant service, "domain.service".

    Only the shape is checked here: whether the service EXISTS is Home
    Assistant's business, and asking it would drag an instance into this
    module. ha_validation.py does not check it either - a service can be
    added or removed at any time, so a rule naming one that is missing
    today may be perfectly correct tomorrow. The failure surfaces at fire
    time, reported, which is the honest place for it.
    """
    if not isinstance(value, str):
        raise RuleValidationError(f"action must be a string, got {value!r}")
    parts = value.split(".")
    if len(parts) != 2 or not all(parts):
        raise RuleValidationError(
            f"action must be 'domain.service', got {value!r}"
        )
    return value


def _mapping(field: str, value) -> dict:
    if not isinstance(value, Mapping):
        raise RuleValidationError(f"{field} must be a mapping, got {value!r}")
    return dict(value)


def _condition(value) -> tuple:
    if isinstance(value, Mapping) or not isinstance(value, (list, tuple)):
        raise RuleValidationError(
            f"condition must be a list of conditions, got {value!r}"
        )
    for item in value:
        if not isinstance(item, Mapping):
            raise RuleValidationError(
                f"each condition must be a mapping, got {item!r}"
            )
    return tuple(dict(item) for item in value)


def _duration(value) -> timedelta:
    """'HH:MM:SS' into a timedelta."""
    text = str(value)
    parts = text.split(":")
    if len(parts) != 3 or not all(p.isdecimal() for p in parts):
        raise RuleValidationError(
            f"replay.within must be 'HH:MM:SS', got {value!r}"
        )
    hours, minutes, seconds = (int(p) for p in parts)
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)


def _replay(value) -> Replay:
    data = _mapping("replay", value)
    unknown = set(data) - {"enabled", "within"}
    if unknown:
        raise RuleValidationError(f"unknown replay field(s): {sorted(unknown)}")
    enabled = _bool("replay.enabled", data.get("enabled", False))
    within = data.get("within")
    return Replay(
        enabled=enabled,
        within=None if within is None else _duration(within),
    )


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
    if field in ("target", "data"):
        return _mapping(field, value)
    if field == "condition":
        return _condition(value)
    if field == "replay":
        return _replay(value)
    if field == "enabled":
        return _bool(field, value)
    if field in ("name", "icon", "color"):
        return _text(field, value)
    # Every rule field is now typed; only the defaults payload, which
    # shares this helper for its own two keys, ever reaches here.
    return value


def validate_defaults(data: dict) -> dict:
    """Validate a defaults payload into coerced kwargs.

    Shares the same 'target'/'data' shape guards as rule fields, coerced
    via the same helpers used for rules - a non-mapping value is rejected
    here rather than persisted, so a malformed defaults payload cannot
    blow up later at rule-resolution time.
    """
    _check_unknown_fields(data, _DEFAULTS_FIELDS)
    return {field: _coerce(field, value) for field, value in data.items()}


def changes_from_api(data: dict) -> dict:
    """Validate a partial update into kwargs for dataclasses.replace."""
    if "id" in data:
        raise RuleValidationError("id cannot be changed")
    payload = _strip_never_stored(data)
    _check_unknown_fields(payload)
    return {field: _coerce(field, value) for field, value in payload.items()}


def rule_from_api(data: dict, rule_id: str) -> Rule:
    """Build a validated Rule. Any client-supplied id is ignored."""
    payload = _strip_never_stored(
        {key: value for key, value in data.items() if key != "id"}
    )
    _check_unknown_fields(payload)

    for required in ("profile", "day", "time", "action"):
        if required not in payload:
            raise RuleValidationError(f"missing required field: {required}")

    kwargs = {field: _coerce(field, value) for field, value in payload.items()}
    return Rule(id=rule_id, **kwargs)
