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

from .models import EREV, Replay, Rule

_FIELDS = {
    "profile", "day", "time", "action", "target", "data",
    "condition", "replay", "name", "icon", "color", "enabled",
}

_DEFAULTS_FIELDS = {"target", "data"}

_V1_FIELDS = {"devices", "settings", "script", "variables", "replay_on_restart"}

# Server-owned, never client-settable, but present in every rule the API
# hands out (see store.rule_to_dict): the v1 -> v2 migration writes them so
# the card can say WHICH rule it could not convert, which is the whole
# point of recording them. Rejecting them on the way back in - which is
# what happened until now - means a client that reads a rule, edits one
# field and PUTs it back is refused with "unknown field(s)", for a field it
# never chose to send. They are dropped instead of stored: a client still
# cannot set them, so the guarantee the ledger asked for is intact, but a
# read-modify-write no longer fails.
#
# WHERE THE SEAM IS. Dropping them is right for a websocket client, whose
# payload is an EDIT: it echoes back a rule it did not author these fields
# on, and a forged `migration_error` would put a healthy rule in the
# unmigrated repair issue and make the card claim its migration failed.
# It is wrong for `yaml_io`, whose payload is a SERIALISED STORE: the
# documented way to inspect and re-author an unmigrated rule is to export
# it, and an export that cannot carry these two fields cannot show the user
# the stashed v1 payload - while the import silently deleted it, along with
# the `migration_error` the repair issue is derived from. So the drop stays
# the default and `rule_from_api` takes an explicit opt-in instead;
# `changes_from_api`, which only ever serves the websocket, has none.
_READ_ONLY_FIELDS = {"migration_error", "migration_source"}

# Server-owned like the two above, and handed out on every rule the card
# reads (see `_state_payload`), so a read-modify-write client echoes it
# back - but NOT a field on `Rule` at all. An outcome is what happened to a
# rule, not part of its definition; it lives in the store's own outcome map,
# keyed by rule id.
#
# Dropped UNCONDITIONALLY, which is where this differs from
# `_READ_ONLY_FIELDS`. Those have a `keep_server_fields` opt-in for
# `yaml_io`, because a YAML document is a serialised store and an export
# that cannot carry the stashed v1 payload cannot show the user the rule it
# could not migrate. There is no such argument here: a YAML document is the
# SCHEDULE, and a verdict about last Shabbat re-imported as part of it would
# be a claim about a fire that never happened. There is also nowhere to put
# it - `Rule` has no such field, so keeping it would be a TypeError.
#
# Forging is the reason this is a drop and not a passthrough. A client that
# could set it would make the card report "fired" for a rule that never ran,
# or "blocked" for one that did - which is the precise lie this whole
# feature exists to make impossible.
_NEVER_STORED_FIELDS = {"last_outcome"}


class RuleValidationError(ValueError):
    """A rule as supplied cannot be built."""


def _strip_read_only(data: dict) -> dict:
    """Drop the server-owned fields a client may echo back. See above."""
    return {key: value for key, value in data.items() if key not in _READ_ONLY_FIELDS}


def _strip_never_stored(data: dict) -> dict:
    """Drop the fields no client and no document may ever set. See above."""
    return {
        key: value for key, value in data.items()
        if key not in _NEVER_STORED_FIELDS
    }


def _check_unknown_fields(data: dict, allowed: set[str] = _FIELDS) -> None:
    """Check for unknown fields in data."""
    stale = set(data) & _V1_FIELDS
    if stale:
        raise RuleValidationError(
            f"{sorted(stale)} belong to the v1 rule format. A rule is now an "
            "action with a target and data; see the README."
        )
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
    if field in ("name", "icon", "color", "migration_error"):
        return _text(field, value)
    if field == "migration_source":
        # `dict | None` on the Rule, and what a repair tool would load back
        # through `rule_from_dict`. Preserved verbatim is not the same as
        # unvalidated: the shape is typed here like every other field.
        return None if value is None else _mapping(field, value)
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
    payload = _strip_never_stored(_strip_read_only(data))
    _check_unknown_fields(payload)
    return {field: _coerce(field, value) for field, value in payload.items()}


def rule_from_api(
    data: dict, rule_id: str, *, keep_server_fields: bool = False
) -> Rule:
    """Build a validated Rule. Any client-supplied id is ignored.

    `keep_server_fields` preserves `migration_error`/`migration_source`
    instead of dropping them, and is for `yaml_io` ONLY - a YAML document
    is a serialised store, not a client edit. See `_READ_ONLY_FIELDS`. It
    defaults to off so a new call site is safe by default; the websocket
    API passes nothing and keeps the old behaviour exactly.
    """
    payload = _strip_never_stored(
        {key: value for key, value in data.items() if key != "id"}
    )
    if not keep_server_fields:
        payload = _strip_read_only(payload)
    _check_unknown_fields(
        payload, _FIELDS | _READ_ONLY_FIELDS if keep_server_fields else _FIELDS
    )

    for required in ("profile", "day", "time", "action"):
        if required not in payload:
            raise RuleValidationError(f"missing required field: {required}")

    kwargs = {field: _coerce(field, value) for field, value in payload.items()}
    return Rule(id=rule_id, **kwargs)
