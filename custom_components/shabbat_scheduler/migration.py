"""Converting a v1 rule store into the v2 shape.

Pure, so the conversion is testable against real stored payloads without
an instance.

The governing rule: a rule that cannot be converted is KEPT, DISABLED and
REPORTED. An upgrade that silently drops someone's schedule is the worst
outcome this code could produce - they would find out on Shabbat, when
nothing can be fixed.

The second governing rule, which cost eight rounds of fixes to learn:
`migrate_v1` MUST BE TOTAL. It is the one function in this codebase that
must never raise. Anything it raises escapes `_MigratingStore.
_async_migrate_func` -> `Store.async_load` -> `RuleStore.async_load` ->
`async_setup_entry`, which fails with `ConfigEntryState.SETUP_ERROR` - and
because the store is then still at version 1, EVERY SUBSEQUENT RESTART
FAILS IDENTICALLY. No entities, no engine, nothing scheduled, and the only
trace is a setup traceback nobody reads on the one week they cannot. Every
coercion below is therefore guarded, and `migrate_v1` also wraps the
per-rule conversion in a catch-all so an unanticipated shape becomes one
kept-disabled-reported rule rather than a permanently unbootable install.
`yaml_io.import_yaml` closed the identical hole at the YAML door first.

The third governing rule, learned last and the most expensive: THE QUESTION
IS NOT ONLY "WHAT NONSENSE CAN A V1 STORE CONTAIN?" BUT "WHAT DID A VALID,
WORKING V1 STORE DO?". Five rounds of fixes asked only the first, and every
defect they found was reachable only by hand-editing `.storage`. The two
worst defects in this converter were valid, documented v1 configs that v2
mishandled - a rule inheriting `defaults.devices`, and a rule spanning two
domains - and both were found by reading v1's source at `5192d4c` rather
than by inventing malformed input. Every claim this module makes about "what
v1 did" is therefore cited to a file and line of that commit, so the next
person can check it instead of trusting it. The full enumeration is in
`.superpowers/sdd/2026-08-24-shabbat-scheduler-v2-model/upgrade-path-fix-report.md`.
"""

from __future__ import annotations

import logging
from datetime import time as _time

from .models import EREV

# stdlib only - this module imports zero Home Assistant, by constraint.
_LOGGER = logging.getLogger(__name__)

_UNCHANGED = ("id", "profile", "day", "time", "name", "icon", "color")

# Every domain v1 could actually drive: `climate`, plus
# `device_ops._SIMPLE_DOMAINS` (5192d4c:device_ops.py:14). Any other domain
# fell through v1's `plan_calls` and came back as
# `Skip("unsupported domain 'x'")` - v1 made NO service call for it, ever.
# So a v1 rule on `lock.front` never did anything, and migrating it to
# `lock.turn_on` invents a service that does not even exist. Worse, some
# domains outside this list DO have a `turn_on` (`scene`, `script`), so the
# invented call would quietly start working - behaviour the user never had
# and never asked for.
#
# This is a fact about v1, not about Home Assistant, which is why it lives
# in the v1 -> v2 converter and not in `device_ops`: it does not run on any
# v2 path. A rule a user authors in v2 can name any service they like.
_V1_SIMPLE_DOMAINS = ("switch", "light", "input_boolean", "fan")
_V1_DOMAINS = ("climate", *_V1_SIMPLE_DOMAINS)

# The only three keys v1 ever read out of `settings`
# (5192d4c:device_ops.py:_plan_climate, one branch each). Every other key -
# `swing_mode`, `humidity`, `target_temp_high`, a typo - v1 ignored
# entirely, and the rule worked. Carrying them into `climate.set_temperature`
# BREAKS a rule that used to work: the schema is PREVENT_EXTRA and rejects
# the whole call, so the temperature never gets set either.
_V1_CLIMATE_SETTINGS = ("hvac_mode", "temperature", "fan_mode")


def _parses_as_time(value) -> bool:
    try:
        _time.fromisoformat(str(value))
    except (TypeError, ValueError):
        return False
    return True


# A block spans at most three calendar days (a two-day Chag adjacent to
# Shabbat), which is why `rule_schema._profile` hard-caps `profile` to
# 1..3 and `rule_schema._day` accepts only `erev` or '1'..'3'. Both bounds
# apply here for a reason beyond tidiness - see `_parses_as_day`.
_MAX_PROFILE = 3


def _parses_as_profile(value) -> bool:
    """An integer in 1..`_MAX_PROFILE`.

    The range matters as much as the type. A migrated rule never passes
    through `rule_schema._profile`, so nothing else would catch a
    `profile` of 7 - and `resolve_rules` skips every rule whose
    `profile != block.length`, so such a rule is silently unschedulable
    for every block that can exist. See `_parses_as_day`.
    """
    try:
        number = int(value)
    except (TypeError, ValueError):
        return False
    return 1 <= number <= _MAX_PROFILE


def _parses_as_day(value) -> bool:
    """`erev`, or a day index in 1..`_MAX_PROFILE`.

    Two distinct failures are being prevented here, and the second is why
    the bound is 1..3 rather than "any positive integer".

    A non-numeric `day` does not break `rule_from_dict` - it does
    `str(data["day"])`, which never raises - but it crashes far worse
    later: `resolve_rules` does `index = int(rule.day)` inside one loop
    over every rule, uncaught all the way up to `engine.async_refresh`,
    so one bad `day` aborts resolving the *whole* schedule.

    An out-of-range but numeric `day` is quieter and just as bad. A rule
    only ever fires when `block.length == rule.profile`, and `profile` is
    capped at `_MAX_PROFILE`; `resolve_rules` then `continue`s whenever
    `index > block.length`. So `day: "7"` migrates clean, reports no
    error, looks healthy in the UI, and hits that `continue` for every
    block that can ever exist - it never fires and nobody is told. This
    module exists to prevent exactly that.
    """
    text = str(value)
    if text == EREV:
        return True
    try:
        number = int(text)
    except (TypeError, ValueError):
        return False
    return 1 <= number <= _MAX_PROFILE


def safe_day(raw: dict) -> str:
    """A `day` guaranteed to be `EREV` or a schedulable index. See `safe_time`."""
    value = raw.get("day", EREV)
    return str(value) if _parses_as_day(value) else EREV


def safe_time(raw: dict) -> str:
    """A `time` string guaranteed to satisfy `time.fromisoformat`.

    Used for the keep-disable-report placeholder too: that record must
    load cleanly regardless of *why* the original rule failed - a rule
    that failed for an unrelated reason (no devices, say) might still
    carry a malformed `time`, and the fallback record must not repeat
    the same crash it exists to avoid.
    """
    value = raw.get("time")
    return str(value) if _parses_as_time(value) else "00:00:00"


def safe_profile(raw: dict) -> int:
    """A `profile` guaranteed to satisfy `int()`. See `safe_time`."""
    value = raw.get("profile", 1)
    return int(value) if _parses_as_profile(value) else 1


def _entity_ids(value) -> list[str] | None:
    """A v1 `devices` list as a list of entity ids, or None if it is not one.

    `list(value or ())` was not enough on either of its two call sites.
    `devices: 5` raised TypeError (see the module docstring for what that
    costs); `devices: "climate.salon"` - the single-device shape a human
    hand-editing `.storage` writes first - silently became the CHARACTERS
    of the string, one bogus "domain" per letter; and `devices: [None]`
    reached `devices[0].split(".", 1)` and raised AttributeError.

    None means "this is not a device list at all", which the caller routes
    through keep-disable-report; `[]` means "no devices", which already had
    its own reason.
    """
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        return None
    if not all(isinstance(item, str) and item for item in value):
        return None
    return list(value)


def _settings(value) -> dict | None:
    """A v1 `settings`/`variables` mapping, or None if it is not one.

    `dict(raw.get("settings") or {})` raised ValueError on `'hot'` and
    TypeError on `5` - on the SUCCESS path, so one corrupt field took the
    whole store's load down rather than one rule. Absent and null are the
    only non-mappings tolerated: anything else is data this function cannot
    claim to understand, and guessing on the user's behalf is what the
    keep-disable-report path exists to avoid.
    """
    if value is None:
        return {}
    if not isinstance(value, dict):
        return None
    return dict(value)


def v1_effective_devices(raw: dict, defaults: dict | None = None) -> list[str] | None:
    """v1's `rule.devices or defaults["devices"]`, or None if unparseable.

    One place, because two callers need the same answer: `migrate_v1_rule`
    to convert the rule, and `_domain_parts` to decide whether it has to be
    split first. See `migrate_v1_defaults` for the citation.
    """
    devices = _entity_ids(raw.get("devices"))
    if devices is None:
        return None
    if devices:
        return devices
    return list((defaults or {}).get("devices") or [])


def _domain_of(entity_id: str) -> str:
    return entity_id.split(".", 1)[0]


def v1_domain_groups(devices: list[str]) -> dict[str, list[str]]:
    """`devices` grouped by domain, first-appearance order preserved.

    Order matters twice over: the derived ids of a split rule come from it,
    and they must be the same on a re-migration of the same store.
    """
    groups: dict[str, list[str]] = {}
    for entity_id in devices:
        groups.setdefault(_domain_of(entity_id), []).append(entity_id)
    return groups


def _unique_id(candidate: str, taken: set[str]) -> str:
    """`candidate`, suffixed until it collides with nothing. Deterministic.

    Only ever called for an id this module DERIVES - a split part or an
    unmigratable rule's placeholder - never for an id the user set, which
    must survive untouched. `taken` starts as every id in the v1 store and
    grows as ids are handed out, so a derived id can collide neither with a
    real rule (a hand-edited store can contain anything, including
    `e-climate` right next to `e`) nor with another derived one.
    """
    unique = candidate
    counter = 2
    while unique in taken:
        unique = f"{candidate}-{counter}"
        counter += 1
    taken.add(unique)
    return unique


def _domain_parts(raw: dict, defaults: dict, taken: set[str]) -> list[dict]:
    """One `raw` per domain the rule targets. Usually `[raw]` unchanged.

    v1 looped over `rule.devices` and re-derived the domain PER ENTITY
    (`for entity_id in rule.devices: await self._apply_device(...)`,
    5192d4c:engine.py:104, then `domain = entity_id.split(".", 1)[0]` at
    5192d4c:device_ops.py:71). So a rule spanning `climate.salon` and
    `switch.boiler` was not merely legal - it drove both correctly, and the
    v1 card let you select several devices for one rule.

    v2 is one rule, one action. Keeping such a rule as a single rule is
    impossible; keeping it DISABLED throws away a working piece of
    someone's schedule, which is the same mistake as refusing to inherit
    `defaults.devices`. So it becomes one v2 rule per domain, each with its
    own correct action, and each stashing the original v1 rule in
    `migration_source` because the rule count changing under the user is
    exactly the kind of surprise that needs a paper trail.

    The ids are DERIVED, `{id}-{domain}`, not random: a re-migration of the
    same store - restoring a `.storage` backup, say - must produce the same
    ids, or the rules come back as strangers with new entities. Both parts
    are renamed rather than one keeping the original id, so that nothing
    implies one of them is "the real rule" and the other a copy: `e-climate`
    and `e-switch` say what happened; `e` and `e-switch` would leave a
    reader unable to tell whether `e` had always been climate-only.
    """
    if raw.get("action") == "custom":
        # `_apply_custom` (5192d4c:engine.py:451-470) used `rule.script` and
        # `rule.variables` and never looked at `devices` at all. A v1 custom
        # rule could carry devices - nothing stopped it - and they did
        # nothing, so splitting on them would turn one script call into
        # several.
        return [raw]

    devices = v1_effective_devices(raw, defaults)
    if devices is None or len(devices) < 2:
        return [raw]
    groups = v1_domain_groups(devices)
    if len(groups) < 2:
        return [raw]

    rule_id = raw.get("id")
    parts = []
    for domain, group in groups.items():
        # `devices` is written explicitly even when it was inherited: the
        # part must not re-inherit the whole mixed list.
        part = {**raw, "devices": group}
        if rule_id:
            part["id"] = _unique_id(f"{rule_id}-{domain}", taken)
        parts.append(part)

    # The user is told properly through a repair issue, derived from the
    # `migration_source` each part carries (`repairs.ISSUE_SPLIT_RULES`).
    # This is the maintainer's copy - a log line on its own would be
    # invisible during the one upgrade it describes.
    _LOGGER.warning(
        "Rule %r targeted several domains, which v1 drove per entity and v2 "
        "cannot express as one action; it has been split into %s. Every part "
        "stays enabled and keeps a copy of the original rule.",
        rule_id, [part.get("id") for part in parts],
    )
    return parts


def migrate_v1_rule(
    raw: dict, defaults: dict | None = None
) -> tuple[dict | None, str | None]:
    """One v1 rule as v2, or None plus the reason it could not be.

    `defaults` is the v1 store's global defaults as `v1_defaults` normalises
    them - `{"devices": [...], "settings": {...}}`. Both are resolved against
    this rule HERE, per rule, exactly as v1's own `merge_defaults` did, and
    for the same reason in both cases: v2's defaults are domain-blind and
    cannot express what v1's meant. See `migrate_v1_defaults`.
    """
    defaults = defaults or {}
    default_devices = defaults.get("devices") or []
    default_settings = defaults.get("settings") or {}
    # id, time, profile and day are required fields on the v2 Rule
    # dataclass - `rule_from_dict` does `data["id"]`, `data["profile"]`,
    # `data["day"]` and `data["time"]` unconditionally. A "successfully"
    # migrated rule with any of these missing or malformed would raise on
    # load, aborting every other rule in the store along with it - and by
    # then HA has already written version 2, so every subsequent start
    # fails identically with no way back. `_UNCHANGED` below only copies a
    # key when it is present in `raw`, so a v1 rule missing one of these
    # outright - not just malformed - would otherwise sail through this
    # function's success path and only fail once the store tries to load
    # it back. Treating any of this as unmigratable instead routes it
    # through keep-disable-report, same as any other rule this code
    # cannot safely convert.
    if not raw.get("id"):
        return None, "a rule with no id cannot be migrated"
    if "profile" not in raw:
        return None, "a rule with no profile cannot be migrated"
    if not _parses_as_profile(raw["profile"]):
        return None, (
            f"profile must be an integer 1..{_MAX_PROFILE}: {raw['profile']!r}"
        )
    if "day" not in raw:
        return None, "a rule with no day cannot be migrated"
    if not _parses_as_day(raw["day"]):
        return None, (
            f"day must be {EREV!r} or '1'..'{_MAX_PROFILE}': {raw['day']!r}"
        )
    time_value = raw.get("time")
    if not time_value:
        return None, "a rule with no time cannot be migrated"
    if not _parses_as_time(time_value):
        return None, f"time is not a valid clock time: {time_value!r}"

    # Guarded before anything is built: a field this function cannot parse
    # is a rule it cannot claim to have understood, whichever branch below
    # would have consumed it. Uniform on purpose - the alternative,
    # checking `settings` only where it is read, means a future reader has
    # to work out which v1 actions consume which fields before they can
    # tell whether a corrupt one matters. The whole raw rule is stashed in
    # `migration_source`, so being told about it costs the user one field
    # to fix rather than a rule to rewrite.
    settings = _settings(raw.get("settings"))
    if settings is None:
        return None, f"settings must be a mapping: {raw.get('settings')!r}"
    variables = _settings(raw.get("variables"))
    if variables is None:
        return None, f"variables must be a mapping: {raw.get('variables')!r}"

    action = raw.get("action")
    out = {key: raw[key] for key in _UNCHANGED if key in raw}
    out["enabled"] = raw.get("enabled", True)
    out["replay"] = {"enabled": bool(raw.get("replay_on_restart", False))}

    if action == "custom":
        script = raw.get("script")
        if not script:
            return None, "a custom rule with no script has nothing to call"
        if not isinstance(script, str):
            # Otherwise this lands on a target of `{"entity_id": [5]}`,
            # which migrates "successfully" and fails at fire time.
            return None, f"script must be an entity id: {script!r}"
        out["action"] = "script.turn_on"
        out["target"] = {"entity_id": [script]}
        out["data"] = {"variables": variables} if variables else {}
        return out, None

    # v1's `merge_defaults` was, verbatim:
    #     devices = rule.devices or tuple(defaults.get("devices", ()))
    # (5192d4c:block.py:61) so a rule with no devices of its own INHERITED
    # the global ones, and `defaults.devices` existed for precisely that -
    # the shape the v1 README documented as the common case. Treating such a
    # rule as "nothing to target" disabled the ENTIRE SCHEDULE of anyone who
    # wrote their config the documented way, on upgrade, with the whole
    # thing discovered on a Shabbat when nothing can be fixed. `or`, per
    # rule, not merged: a rule's own devices win outright.
    devices = v1_effective_devices(raw, defaults)
    if devices is None:
        return None, (
            f"devices must be a list of entity ids: {raw.get('devices')!r}"
        )
    if not devices:
        return None, (
            "a rule with no devices, and no shared default devices to "
            "inherit, has nothing to target"
        )

    groups = v1_domain_groups(devices)
    if len(groups) > 1:
        # Unreachable from `migrate_v1`, which splits a mixed-domain rule
        # into one part per domain before calling this (`_domain_parts`).
        # Kept because this function's contract is "one v1 rule, one v2
        # rule", and a direct caller handing it a mixed list deserves the
        # honest answer rather than a silently climate-only conversion.
        return None, "a rule targeting several domains cannot become one action"
    domain = next(iter(groups))

    if domain not in _V1_DOMAINS:
        # v1 made no service call for this rule, ever - see `_V1_DOMAINS`.
        # Kept, disabled and reported rather than converted, because the
        # only two things v2 could do instead are invent a service that
        # does not exist (`lock.turn_on`) or invent one that does and start
        # doing something the user never had (`scene.turn_on`).
        return None, (
            f"v1 could not drive the {domain!r} domain - it made no service "
            f"call for {', '.join(devices)} - so there is no v1 behaviour to "
            "migrate. Re-author this rule as a v2 action if you want it."
        )

    # Written into the rule's own target rather than left to v2's defaults
    # inheritance, even though `merge_defaults` would supply it. The action
    # below is derived from THESE devices and is then frozen into the rule,
    # so a floating target could later point at a domain the frozen action
    # does not belong to; and the card renders `target` verbatim, so an
    # empty one shows the user nothing about what the rule will act on. A
    # migrated rule should describe itself. `defaults.devices` still becomes
    # `defaults.target` for rules authored later.
    out["target"] = {"entity_id": devices}

    if action == "off":
        out["action"] = f"{domain}.turn_off"
        out["data"] = {}
        return out, None

    if action != "on":
        return None, f"unknown v1 action {action!r}"

    if domain != "climate":
        # v1's simple domains called `turn_on` and ignored `settings`
        # completely (5192d4c:device_ops.py:76-90). Carrying them through
        # would get the migrated call rejected at fire time - `switch.turn_on`
        # does not accept a `temperature` key.
        if settings:
            _LOGGER.warning(
                "Rule %r: v1 ignored `settings` for the %s domain, so %s "
                "has not been carried over. The rule fires exactly as it did "
                "in v1.", raw.get("id"), domain, sorted(settings),
            )
        out["action"] = f"{domain}.turn_on"
        out["data"] = {}
        return out, None

    # The GLOBAL v1 settings are folded in per key: v1 resolved them against
    # this rule before reading them (5192d4c:block.py:62) and the merge order
    # matches `block.merge_defaults`, so the effective payload is unchanged.
    # Only climate ever sees them - see `migrate_v1_defaults`.
    merged = {**(default_settings or {}), **settings}
    # `value is not None` is not decoration. v1 gated each of its three keys
    # on the VALUE, not on the key's presence - `hvac_mode =
    # settings.get("hvac_mode")` then `if hvac_mode is not None`
    # (5192d4c:device_ops.py:126, and the same shape at :140 and :153). A
    # null therefore produced NO call in v1, while filtering on key
    # membership carried it into `climate.set_hvac_mode {hvac_mode: None}`,
    # which Home Assistant refuses. Reachable from a VALID v1 config, not
    # only a hand-edit: v1 applied no per-key validation to `settings`, so
    # its own API and YAML doors both accepted a null.
    #
    # Note this also reproduces v1's SUPPRESSION: the merge happens first,
    # so a rule writing `hvac_mode: null` overrides an inherited `cool` and
    # then drops out here, exactly as v1's merge-then-check did.
    recognised = {
        key: value
        for key, value in merged.items()
        if key in _V1_CLIMATE_SETTINGS and value is not None
    }
    ignored = sorted(key for key in settings if key not in recognised)
    if ignored:
        # Only the keys THIS RULE carried. The global defaults are reported
        # once by `v1_defaults` instead, or this logs the same shared key
        # once per rule in the store.
        _LOGGER.warning(
            "Rule %r: v1 acted on %s only when each was non-null, so %s has "
            "not been carried over. Carrying one would break the rule "
            "outright - `climate.set_temperature` rejects the whole call on "
            "an unrecognised key or a null mode, so the temperature would "
            "stop being set too.",
            raw.get("id"), list(_V1_CLIMATE_SETTINGS), ignored,
        )

    if not recognised:
        # v1's `_plan_climate` with no hvac_mode, temperature or fan_mode
        # returned NO CALLS AT ALL (5192d4c:device_ops.py:124-183) and the
        # engine reported `outcome: "ok"` with the state unchanged
        # (5192d4c:engine.py:493-500). So this rule did nothing in v1.
        # Converting it to `climate.turn_on` would make an air conditioner
        # start up, unattended, on a Shabbat, at whatever temperature it was
        # last left at - inventing behaviour on the user's behalf is the one
        # thing this converter must never do. Kept, disabled, and reported,
        # so the user decides.
        #
        # This is also where an all-null `settings` lands, now that the
        # filter above is by value: `{temperature: null}` is a non-empty
        # mapping that v1 acted on in no way at all, so it belongs here
        # rather than becoming one permanently-failing call.
        return None, (
            "a v1 climate 'on' rule with no non-null hvac_mode, temperature "
            "or fan_mode made no service call in v1, so there is no "
            "behaviour to migrate. Give it a temperature or a mode if you "
            "want it to act."
        )

    out["action"] = "climate.set_temperature"
    out["data"] = recognised
    return out, None


def v1_defaults(raw) -> dict:
    """The v1 global defaults, normalised to `{"devices": [], "settings": {}}`.

    The single place either field is parsed, so a malformed one is reported
    once rather than once per rule. Tolerant by contract - see the module
    docstring: nothing here may raise, whatever `.storage` holds.
    """
    devices: list[str] = []
    settings: dict = {}
    if not isinstance(raw, dict):
        return {"devices": devices, "settings": settings}

    parsed_devices = _entity_ids(raw.get("devices"))
    if parsed_devices is None:
        # Consequential now that rules inherit these: every rule with no
        # devices of its own becomes unmigratable, kept-disabled-reported,
        # and the reason names the defaults. So this warning is a second
        # trace of something the user will already have been told about.
        _LOGGER.warning(
            "The v1 defaults' devices are not a list of entity ids (%r); the "
            "shared default target has been dropped. Any rule that had no "
            "devices of its own is kept, disabled and reported.",
            raw.get("devices"),
        )
    else:
        devices = parsed_devices

    parsed_settings = _settings(raw.get("settings"))
    if parsed_settings is None:
        _LOGGER.warning(
            "The v1 defaults' settings are not a mapping (%r); they have been "
            "dropped. Rules that carried their own settings are unaffected.",
            raw.get("settings"),
        )
    else:
        settings = parsed_settings

    ignored = sorted(set(settings) - set(_V1_CLIMATE_SETTINGS))
    if ignored:
        # Reported once, here, rather than once per inheriting rule. v1 read
        # the global `settings` only for climate entities and only for
        # `hvac_mode`/`temperature`/`fan_mode`, so these keys never did
        # anything in v1 either - see `_V1_CLIMATE_SETTINGS`.
        _LOGGER.warning(
            "The v1 defaults' settings carry %s, which v1 never read for any "
            "domain, so they have not been carried over. Every rule fires "
            "exactly as it did in v1.", ignored,
        )

    return {"devices": devices, "settings": settings}


def migrate_v1_defaults(defaults: dict) -> dict:
    """The v2 defaults, from the `v1_defaults`-normalised v1 ones: TARGET only.

    v1's global `settings` are deliberately NOT migrated into v2's
    `defaults.data`. v1 read `settings` for the climate domain and nowhere
    else, but v2's defaults are domain-BLIND: `block.merge_defaults` folds
    `defaults["data"]` into every rule regardless of domain, and the engine
    applies that on every refresh, catch-up and fire. So a v1 store with
    global climate settings plus a `switch.boiler` rule migrated into
    `switch.turn_on` carrying `{hvac_mode, temperature}`, which Home
    Assistant refuses outright - `make_entity_service_schema` defaults to
    PREVENT_EXTRA - after 3 x 30s of retries. A schedule that worked in v1
    stopped working on upgrade, on every rule that was not climate.

    Not migrating them at all would have lost the other half: a v1 climate
    rule with no `settings` of its own DID read the global ones, and would
    have quietly become a bare `climate.turn_on` - the AC coming on at
    whatever temperature it was last left at, reported nowhere. So they are
    inlined onto each climate rule's own `data` instead (see
    `migrate_v1_rule`), which is the only lossless representation available:
    v2 defaults cannot express "climate only", so there is nowhere else for
    a climate-only default to live.

    The cost, stated plainly: the values are materialised per rule, so
    editing the shared defaults afterwards no longer changes them. That is
    a v1 concept v2 does not have, and copying it is honest where
    reinterpreting it is not. The same now goes for `devices`, which
    `migrate_v1_rule` resolves per rule the way v1's `merge_defaults` did -
    and it must, because the migrated ACTION is derived from those devices
    and frozen into the rule.

    `devices` still becomes a shared `defaults.target` as well. Not because
    any migrated rule needs it - they all carry their own target now - but
    because it is what the user set, the card's defaults dialog shows it,
    and a rule authored later inherits it exactly as a v1 rule would have.
    A shared `target` cannot break a rule of the wrong domain the way a
    shared `data` can; it is only ever consulted when a rule has none.
    """
    out: dict = {}
    if defaults.get("devices"):
        out["target"] = {"entity_id": list(defaults["devices"])}
    return out


def migrate_v1(data) -> tuple[dict, list[str]]:
    """The whole store as v2, plus the ids of rules that could not convert.

    Total by construction: see the module docstring.
    """
    rules: list[dict] = []
    failed: list[str] = []

    if not isinstance(data, dict):
        _LOGGER.error(
            "The stored v1 data is not a mapping (%r); starting from an empty "
            "rule set rather than refusing to start at all.", data
        )
        return {"rules": [], "defaults": {}}, []

    raw_defaults = data.get("defaults")
    if raw_defaults is not None and not isinstance(raw_defaults, dict):
        # Nothing to disable and report against - a malformed `defaults` is
        # not a rule - so it drops to empty and says so. Refusing to start
        # is the defect being fixed here, and inventing a phantom rule to
        # carry the report would put something in the store the user never
        # wrote. A rule that had its own devices and settings is unaffected;
        # a rule that needed to inherit them is kept, disabled and reported
        # by name, which is the channel the user actually sees.
        _LOGGER.warning(
            "The v1 defaults are not a mapping (%r); the shared defaults have "
            "been dropped. Any rule that had no devices of its own is kept, "
            "disabled and reported.", raw_defaults
        )
    defaults = v1_defaults(raw_defaults)

    raw_rules = data.get("rules")
    if raw_rules is not None and not isinstance(raw_rules, (list, tuple)):
        _LOGGER.error(
            "The stored v1 rules are not a list (%r); there is no rule here to "
            "keep. Starting from an empty rule set rather than refusing to "
            "start at all.", raw_rules
        )
        raw_rules = ()

    # Every id the store already uses, so a DERIVED id - a split part, or an
    # unmigratable rule's placeholder - can never land on top of a real rule.
    taken_ids = {
        str(item["id"])
        for item in (raw_rules or ())
        if isinstance(item, dict) and item.get("id")
    }

    for index, item in enumerate(raw_rules or ()):
        # A `.storage` file can be hand-edited into nonsense. Fail-loud
        # would take the whole load down with it; a rule that is not even
        # a mapping is just another shape this code cannot convert, so it
        # is routed through the same keep-disable-report path as anything
        # else, with the raw value preserved for inspection.
        if not isinstance(item, dict):
            parts: list[dict] = [{}]
        else:
            try:
                parts = _domain_parts(item, defaults, taken_ids)
            except Exception:  # noqa: BLE001 - see the catch-all below
                _LOGGER.exception("Splitting a v1 rule raised: %r", item)
                parts = [item]
        split = len(parts) > 1

        for part_index, raw in enumerate(parts):
            converted, reason = _convert_one(raw, item, defaults)
            if converted is not None:
                if split:
                    # The rule count changed under the user, so the original
                    # is stashed whole even though this part migrated
                    # cleanly. `migration_source` alone raises no repair
                    # issue and renders nothing in the card - only
                    # `migration_error` does - so this is a paper trail, not
                    # a warning. The YAML export carries it (see yaml_io).
                    converted["migration_source"] = item
                rules.append(converted)
                continue

            # A fallback id is needed even for a rule that never had one -
            # an empty string repeated across every unnamed failure gives
            # a future repair tool nothing distinct to name. Uniquified for
            # the same reason the split ids are: a store can contain two
            # rules with the same id, and one rule can now produce two
            # failures.
            fallback_id = raw.get("id") or _unique_id(
                f"unmigrated-{index}" if not split
                else f"unmigrated-{index}-{part_index}",
                taken_ids,
            )
            rules.append(_unmigrated_stub(raw, item, fallback_id, reason))
            failed.append(fallback_id)

    out = dict(data)
    out["rules"] = rules
    out["defaults"] = migrate_v1_defaults(defaults)
    return out, failed


def _convert_one(
    raw: dict, item, defaults: dict
) -> tuple[dict | None, str | None]:
    """`migrate_v1_rule`, guaranteed not to raise. See the module docstring."""
    if not isinstance(item, dict):
        return None, f"rule is not a mapping, got {item!r}"
    try:
        return migrate_v1_rule(raw, defaults)
    except Exception as err:  # noqa: BLE001 - see below
                # Belt and braces, and the reason this function is total by
                # construction rather than by enumeration. Eight instances
                # of "a v1 rule migrates into something the system cannot
                # handle" have been fixed one field at a time; the ninth
                # must not brick the install while it waits to be found.
                # It is reported, not swallowed: the rule is kept, disabled
                # and named in the repair issue, with the exception in its
                # `migration_error` and the raw v1 rule in
                # `migration_source`. The trade being made is that a real
        # bug in this function shows up as one disabled rule rather
        # than a crash - which is the right trade for the one
        # function whose crash costs the user every rule they have.
        _LOGGER.exception("Migrating a v1 rule raised: %r", item)
        return None, (
            f"the migration raised on this rule: {type(err).__name__}: {err}"
        )


def _unmigrated_stub(raw: dict, item, rule_id: str, reason: str | None) -> dict:
    """The kept-disabled-reported record for a rule that could not convert.

    Kept so nothing is lost, disabled so it cannot fire in a shape nothing
    understands, and reported so the user is told. Target/data are salvaged
    whenever they are known, and the raw v1 rule is stashed whole under
    `migration_source` so nothing is lost even when they cannot be derived -
    "kept" has to mean repairable.

    Every field is guarded the same way the success path is: this record must
    load cleanly regardless of WHY the original rule failed, so a rule that
    failed on one field must not raise here on another.
    """
    devices = _entity_ids(raw.get("devices")) or []
    settings = raw.get("settings")
    return {
        "id": rule_id,
        "profile": safe_profile(raw),
        "day": safe_day(raw),
        "time": safe_time(raw),
        "action": "shabbat_scheduler.unmigrated",
        "target": {"entity_id": devices} if devices else {},
        "data": dict(settings) if isinstance(settings, dict) else {},
        "enabled": False,
        "name": raw.get("name"),
        "replay": {"enabled": False},
        "migration_error": reason,
        # Always a mapping, even when the source element was not one -
        # `Rule.migration_source` is typed `dict | None`, and this is what a
        # repair tool would actually load back through `rule_from_dict`. The
        # ORIGINAL item, not this part: a split part's `devices` are a slice
        # of what the user wrote, and the stash exists to show what they
        # wrote.
        "migration_source": item if isinstance(item, dict) else {"raw": item},
    }
