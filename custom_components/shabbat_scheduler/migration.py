"""Converting a v1 rule store into the v2 shape.

Pure, so the conversion is testable against real stored payloads without
an instance.

The governing rule: a rule that cannot be converted is KEPT, DISABLED and
REPORTED. An upgrade that silently drops someone's schedule is the worst
outcome this code could produce - they would find out on Shabbat, when
nothing can be fixed.
"""

from __future__ import annotations

_UNCHANGED = ("id", "profile", "day", "time", "name", "icon", "color")


def migrate_v1_rule(raw: dict) -> tuple[dict | None, str | None]:
    """One v1 rule as v2, or None plus the reason it could not be."""
    action = raw.get("action")
    out = {key: raw[key] for key in _UNCHANGED if key in raw}
    out["enabled"] = raw.get("enabled", True)
    out["replay"] = {"enabled": bool(raw.get("replay_on_restart", False))}

    if action == "custom":
        script = raw.get("script")
        if not script:
            return None, "a custom rule with no script has nothing to call"
        out["action"] = "script.turn_on"
        out["target"] = {"entity_id": [script]}
        variables = raw.get("variables") or {}
        out["data"] = {"variables": dict(variables)} if variables else {}
        return out, None

    devices = list(raw.get("devices") or ())
    if not devices:
        return None, "a rule with no devices has nothing to target"

    domain = devices[0].split(".", 1)[0]
    if any(d.split(".", 1)[0] != domain for d in devices):
        return None, "a rule targeting several domains cannot become one action"

    out["target"] = {"entity_id": devices}
    settings = dict(raw.get("settings") or {})

    if action == "off":
        out["action"] = f"{domain}.turn_off"
        out["data"] = {}
        return out, None

    if action != "on":
        return None, f"unknown v1 action {action!r}"

    if domain == "climate" and settings:
        out["action"] = "climate.set_temperature"
        out["data"] = settings
    else:
        out["action"] = f"{domain}.turn_on"
        out["data"] = settings
    return out, None


def migrate_v1_defaults(raw: dict) -> dict:
    out: dict = {}
    devices = list(raw.get("devices") or ())
    if devices:
        out["target"] = {"entity_id": devices}
    settings = dict(raw.get("settings") or {})
    if settings:
        out["data"] = settings
    return out


def migrate_v1(data: dict) -> tuple[dict, list[str]]:
    """The whole store as v2, plus the ids of rules that could not convert."""
    rules: list[dict] = []
    failed: list[str] = []

    for raw in data.get("rules", []):
        converted, reason = migrate_v1_rule(raw)
        if converted is None:
            # Kept so nothing is lost, disabled so it cannot fire in a
            # shape nothing understands, and reported so the user is told.
            rules.append(
                {
                    "id": raw.get("id", ""),
                    "profile": raw.get("profile", 1),
                    "day": raw.get("day", "erev"),
                    "time": raw.get("time", "00:00:00"),
                    "action": "shabbat_scheduler.unmigrated",
                    "target": {},
                    "data": {},
                    "enabled": False,
                    "name": raw.get("name"),
                    "replay": {"enabled": False},
                    "migration_error": reason,
                }
            )
            failed.append(raw.get("id", ""))
            continue
        rules.append(converted)

    out = dict(data)
    out["rules"] = rules
    out["defaults"] = migrate_v1_defaults(data.get("defaults") or {})
    return out, failed
