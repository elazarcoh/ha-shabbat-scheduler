"""YAML import/export of the whole rule set.

An export/import view over .storage - never a live-watched source of truth,
because two writers with no reconciliation story is how this gets confusing.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping

import yaml

from .models import Action, EREV, Rule
from .rule_schema import rule_from_api, validate_defaults

_OPTIONAL_FIELDS = (
    "name", "icon", "script", "color", "replay_on_restart", "variables",
)


def _day_key(day: str) -> str:
    return EREV if day == EREV else f"day_{day}"


def _day_from_key(key) -> str:
    """Parse a day key, rejecting anything that is not erev or day_<n>.

    Validated at the door rather than trusted: an unrecognised key used to be
    passed through verbatim and persisted, after which block.py's int(day)
    raised on every setup AND on every export - so the user could not even
    dump their rules to find the typo, and recovery meant hand-editing
    .storage.
    """
    text = str(key)
    if text == EREV:
        return EREV
    number = text.removeprefix("day_") if text.startswith("day_") else ""
    if not number.isdecimal() or int(number) < 1:
        raise ValueError(
            f"unknown day key {text!r}: expected 'erev' or 'day_<n>' "
            "with n >= 1, e.g. 'day_1'"
        )
    return str(int(number))


def _profile_from_key(key) -> int:
    """Parse a profile key like '1_day'. Same reasoning as _day_from_key."""
    number = str(key).split("_", 1)[0]
    if not number.isdecimal() or int(number) < 1:
        raise ValueError(
            f"unknown profile key {str(key)!r}: expected '<n>_day' with "
            "n >= 1, e.g. '1_day'"
        )
    return int(number)


def _action_from_value(value) -> Action:
    """Accept YAML 1.1 booleans for actions.

    An unquoted `action: on` - the most natural thing to hand-write - parses
    as the boolean True. Export always quotes, so only hand-edits land here.
    """
    if value is True:
        return Action.ON
    if value is False:
        return Action.OFF
    return Action(str(value))


def _rule_from_entry(entry, profile: int, day: str) -> Rule:
    """Build one rule from a YAML entry, via the same guards the API uses.

    This used to construct the Rule by hand, which meant the YAML door had
    no typing behind it at all: a quoted `enabled: "false"` imported as a
    truthy string, so the rule read as OFF everywhere it was displayed and
    RAN anyway; `action: custom` with no script imported silently inert;
    and a misspelt key was dropped without a word. Translating to the API
    shape and handing it to rule_from_api means one set of rules for both
    doors, and any new field is typed in one place.

    Only the genuinely YAML-shaped parts are handled here: the `at` key
    (the API calls it `time`), YAML 1.1's `on`/`off` booleans, and an id
    that - unlike the API's - is preserved so a round trip keeps entities.
    """
    if not isinstance(entry, Mapping):
        raise ValueError(f"each rule must be a mapping, got {entry!r}")
    for required in ("at", "action"):
        if required not in entry:
            raise ValueError(f"a {_day_key(day)} rule is missing {required!r}")

    payload = {
        key: value for key, value in entry.items()
        if key not in ("id", "at", "action")
    }
    payload["time"] = str(entry["at"])
    payload["action"] = _action_from_value(entry["action"])
    payload["profile"] = profile
    payload["day"] = day

    return rule_from_api(payload, entry.get("id") or uuid.uuid4().hex)


def export_yaml(defaults: dict, rules: list[Rule]) -> str:
    """Render the rule set grouped by profile and day, for human review."""
    profiles: dict[str, dict[str, list[dict]]] = {}

    def _day_rank(day: str) -> int:
        return 0 if day == EREV else int(day)

    for rule in sorted(rules, key=lambda r: (r.profile, _day_rank(r.day), r.time)):
        profile_key = f"{rule.profile}_day"
        day_key = _day_key(rule.day)
        entry: dict = {
            "id": rule.id,
            "at": rule.time.isoformat(),
            "action": rule.action.value,
        }
        if rule.devices:
            entry["devices"] = list(rule.devices)
        if rule.settings:
            entry["settings"] = dict(rule.settings)
        if not rule.enabled:
            entry["enabled"] = False
        for name in _OPTIONAL_FIELDS:
            value = getattr(rule, name)
            if value:
                entry[name] = value
        profiles.setdefault(profile_key, {}).setdefault(day_key, []).append(entry)

    return yaml.safe_dump(
        {"defaults": defaults, "profiles": profiles},
        allow_unicode=True,
        sort_keys=False,
    )


def import_yaml(text: str) -> tuple[dict, list[Rule]]:
    """Parse a rule set. Ids are generated for entries that lack one."""
    data = yaml.safe_load(text) or {}
    # Validated with exactly the same guard the websocket API uses, and
    # BEFORE anything is returned to be persisted. An unvalidated
    # `defaults` used to be written straight to .storage, after which
    # merge_defaults raised TypeError on every subsequent setup - the
    # integration could then never start again without hand-editing
    # .storage, and nothing ran on Shabbat with nothing to explain why.
    # RuleValidationError is a ValueError, which the import_yaml service
    # already turns into a ServiceValidationError.
    raw_defaults = data.get("defaults") or {}
    if not isinstance(raw_defaults, dict):
        raise ValueError(f"defaults must be a mapping, got {raw_defaults!r}")
    defaults = validate_defaults(raw_defaults)
    rules: list[Rule] = []

    for profile_key, days in (data.get("profiles") or {}).items():
        profile = _profile_from_key(profile_key)
        for day_key, entries in (days or {}).items():
            day = _day_from_key(day_key)
            for entry in entries or []:
                rules.append(_rule_from_entry(entry, profile, day))

    return defaults, rules
