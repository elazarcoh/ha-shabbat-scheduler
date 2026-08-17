"""YAML import/export of the whole rule set.

An export/import view over .storage - never a live-watched source of truth,
because two writers with no reconciliation story is how this gets confusing.
"""

from __future__ import annotations

import uuid
from datetime import time

import yaml

from .models import Action, EREV, Rule

_OPTIONAL_FIELDS = (
    "name", "icon", "script", "color", "replay_on_restart", "variables",
)


def _day_key(day: str) -> str:
    return EREV if day == EREV else f"day_{day}"


def _day_from_key(key: str) -> str:
    return EREV if key == EREV else key.removeprefix("day_")


def export_yaml(defaults: dict, rules: list[Rule]) -> str:
    """Render the rule set grouped by profile and day, for human review."""
    profiles: dict[str, dict[str, list[dict]]] = {}

    for rule in sorted(rules, key=lambda r: (r.profile, r.day, r.time)):
        profile_key = f"{rule.profile}_day"
        day_key = _day_key(rule.day)
        entry: dict = {
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
    defaults = data.get("defaults") or {}
    rules: list[Rule] = []

    for profile_key, days in (data.get("profiles") or {}).items():
        profile = int(str(profile_key).split("_", 1)[0])
        for day_key, entries in (days or {}).items():
            day = _day_from_key(day_key)
            for entry in entries or []:
                rules.append(
                    Rule(
                        id=entry.get("id") or uuid.uuid4().hex,
                        profile=profile,
                        day=day,
                        time=time.fromisoformat(str(entry["at"])),
                        action=Action(entry["action"]),
                        devices=tuple(entry.get("devices", ())),
                        settings=dict(entry.get("settings", {})),
                        name=entry.get("name"),
                        icon=entry.get("icon"),
                        enabled=entry.get("enabled", True),
                        script=entry.get("script"),
                        variables=dict(entry.get("variables", {})),
                        replay_on_restart=entry.get("replay_on_restart", False),
                        color=entry.get("color"),
                    )
                )

    return defaults, rules
