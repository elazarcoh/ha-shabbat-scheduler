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
    # id and time are required identity/scheduling fields on the v2 Rule
    # dataclass - `rule_from_dict` does `data["id"]` and
    # `time.fromisoformat(data["time"])` unconditionally. A "successfully"
    # migrated rule missing either would raise on load, aborting every
    # other rule in the store along with it. Treating that as unmigratable
    # instead routes it through keep-disable-report, same as any other
    # rule this code cannot safely convert.
    if not raw.get("id"):
        return None, "a rule with no id cannot be migrated"
    if not raw.get("time"):
        return None, "a rule with no time cannot be migrated"

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

    # v1 only ever read `settings` for the climate domain - every other
    # domain's `turn_on` ignored it. Carrying it through unconditionally
    # gets the migrated call rejected at fire time (e.g. `switch.turn_on`
    # does not accept a `temperature` key).
    if domain == "climate" and settings:
        out["action"] = "climate.set_temperature"
        out["data"] = settings
    else:
        out["action"] = f"{domain}.turn_on"
        out["data"] = {}
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

    for index, item in enumerate(data.get("rules") or ()):
        # A `.storage` file can be hand-edited into nonsense. Fail-loud
        # would take the whole load down with it; a rule that is not even
        # a mapping is just another shape this code cannot convert, so it
        # is routed through the same keep-disable-report path as anything
        # else, with the raw value preserved for inspection.
        raw = item if isinstance(item, dict) else {}
        if not isinstance(item, dict):
            converted, reason = None, f"rule is not a mapping, got {item!r}"
        else:
            converted, reason = migrate_v1_rule(raw)

        if converted is None:
            # A fallback id is needed even for a rule that never had one -
            # an empty string repeated across every unnamed failure gives
            # a future repair tool nothing distinct to name.
            fallback_id = raw.get("id") or f"unmigrated-{index}"
            devices = list(raw.get("devices") or ())
            settings = raw.get("settings")
            # Kept so nothing is lost, disabled so it cannot fire in a
            # shape nothing understands, and reported so the user is
            # told. Target/data are salvaged whenever they are known,
            # and the raw v1 rule is stashed whole under
            # `migration_source` so nothing is lost even when they
            # cannot be derived - "kept" has to mean repairable.
            rules.append(
                {
                    "id": fallback_id,
                    "profile": raw.get("profile", 1),
                    "day": raw.get("day", "erev"),
                    "time": raw.get("time") or "00:00:00",
                    "action": "shabbat_scheduler.unmigrated",
                    "target": {"entity_id": devices} if devices else {},
                    "data": dict(settings) if isinstance(settings, dict) else {},
                    "enabled": False,
                    "name": raw.get("name"),
                    "replay": {"enabled": False},
                    "migration_error": reason,
                    # Always a mapping, even when the source element was
                    # not one - `Rule.migration_source` is typed
                    # `dict | None`, and this is what a repair tool would
                    # actually load back through `rule_from_dict`.
                    "migration_source": item if isinstance(item, dict) else {"raw": item},
                }
            )
            failed.append(fallback_id)
            continue
        rules.append(converted)

    out = dict(data)
    out["rules"] = rules
    out["defaults"] = migrate_v1_defaults(data.get("defaults") or {})
    return out, failed
