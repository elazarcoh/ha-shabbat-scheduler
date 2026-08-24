"""Pure scheduling logic. No Home Assistant imports belong in this module."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, tzinfo

from .models import EREV, Block, Conflict, ResolvedRule, Rule


def compute_block(candle_lighting: datetime, havdalah: datetime) -> Block:
    """Derive a block from the two zmanim that bound it.

    Length is measured in calendar dates, which lands on the everyday
    vocabulary: a regular Shabbat is 1 day (Fri evening -> Sat), a Chag
    adjacent to Shabbat is 2, and so on.
    """
    if havdalah <= candle_lighting:
        raise ValueError("havdalah must be after candle lighting")

    erev_date = candle_lighting.date()
    length = (havdalah.date() - erev_date).days
    if length < 1:
        raise ValueError("block must span at least one full day")

    day_dates = tuple(erev_date + timedelta(days=i) for i in range(1, length + 1))
    return Block(
        candle_lighting=candle_lighting,
        havdalah=havdalah,
        length=length,
        erev_date=erev_date,
        day_dates=day_dates,
    )


def block_payload(block: Block | None) -> dict | None:
    """The block as JSON-able data for the card.

    Pure, and returns only strings and ints, so it stays inside this
    module's no-Home-Assistant boundary and crosses a websocket intact.

    `dates` is keyed exactly the way rules spell their `day` field -
    'erev', then '1'..'n' - so the card can group rules by day without
    knowing anything about how a block is derived.
    """
    if block is None:
        return None
    dates = {"erev": block.erev_date.isoformat()}
    for index, day in enumerate(block.day_dates, start=1):
        dates[str(index)] = day.isoformat()
    return {
        "length": block.length,
        "candle_lighting": block.candle_lighting.isoformat(),
        "havdalah": block.havdalah.isoformat(),
        "dates": dates,
    }


def merge_defaults(defaults: dict, rule: Rule) -> Rule:
    """Fill unset keys from the global defaults, per key, without mutating.

    v1's `devices`/`settings` became `target`/`data` in the v2 Rule
    (models.py, Task 1); this still had to be updated to match, because
    `engine._merged_rules()` calls this on every refresh and catch-up -
    unlike `find_conflicts`/`preview_payload` below, which are not on
    that path and are left for Task 9's rewrite.
    """
    target = dict(rule.target) or dict(defaults.get("target", {}))
    data = {**defaults.get("data", {}), **rule.data}
    return replace(rule, target=target, data=data)


def has_profile(rules: list[Rule], length: int) -> bool:
    """True when at least one ENABLED rule is authored for this block length.

    Disabled rules used to count, so a profile whose rules were all switched
    off passed the check and then scheduled nothing - with no missing-profile
    notification to say so.
    """
    return any(rule.profile == length and rule.enabled for rule in rules)


def resolve_rules(
    rules: list[Rule], block: Block, tz: tzinfo
) -> list[ResolvedRule]:
    """Bind the profile matching this block to concrete datetimes."""
    resolved: list[ResolvedRule] = []
    for rule in rules:
        if rule.profile != block.length or not rule.enabled:
            continue

        if rule.day == EREV:
            day_date = block.erev_date
        else:
            index = int(rule.day)
            if index < 1 or index > block.length:
                continue
            day_date = block.day_dates[index - 1]

        resolved.append(
            ResolvedRule(
                when=datetime.combine(day_date, rule.time, tzinfo=tz), rule=rule
            )
        )

    return sorted(resolved, key=lambda item: item.when)


def find_conflicts(rules: list[Rule]) -> list[Conflict]:
    """Find enabled rules that disagree for one device at one moment.

    There is no precedence rule by design, so a conflict has no defined
    winner - it is reported rather than resolved.

    STALE, pending Task 9's rewrite: `_STATEFUL_ACTIONS` (an Action-enum
    tuple) died with the enum in Task 8, and this still references it. Not
    fixed here - Task 9 gives this function a new signature entirely
    (`find_conflicts(rules, resolve)`), so patching the old one now would
    be thrown away immediately. Calling this today raises NameError.
    """
    grouped: dict[tuple, list[Rule]] = {}
    for rule in rules:
        if not rule.enabled or rule.action not in _STATEFUL_ACTIONS:
            continue
        for device in rule.devices:
            grouped.setdefault(
                (rule.profile, rule.day, rule.time, device), []
            ).append(rule)

    conflicts: list[Conflict] = []
    for (profile, day, at, device), group in grouped.items():
        if len({rule.action for rule in group}) > 1:
            conflicts.append(
                Conflict(
                    profile=profile,
                    day=day,
                    time=at,
                    device=device,
                    rule_ids=tuple(rule.id for rule in group),
                )
            )
    return conflicts


def conflict_warnings(defaults: dict, rules: list[Rule]) -> list[dict]:
    """Conflicts as plain data, with the defaults merged in FIRST.

    The merge is not optional: find_conflicts iterates `rule.devices`, so a
    rule taking its devices from `defaults` - the shape the README
    documents as the common case - contributes nothing at all unmerged,
    and every caller is then told a conflicting schedule is clean.
    """
    merged = [merge_defaults(defaults, rule) for rule in rules]
    return [
        {
            "kind": "conflict",
            "device": conflict.device,
            "profile": conflict.profile,
            "day": conflict.day,
            "time": conflict.time.isoformat(),
            "rule_ids": list(conflict.rule_ids),
        }
        for conflict in find_conflicts(merged)
    ]


def preview_payload(
    defaults: dict,
    rules: list[Rule],
    block: Block | None,
    tz: tzinfo,
    block_length: int | None = None,
) -> dict:
    """What a block WOULD do: the one answer behind `preview` and `simulate`.

    Both used to build this themselves, and a comment claimed they "cannot
    drift apart" while they already had - the service returned bare-string
    warnings and conflicts with no `kind`/`profile`, the websocket command
    returned dicts with both. Now there is one implementation, so the claim
    is true by construction rather than by everyone remembering.

    Pure, and returns JSON-able data only, so it stays inside this module's
    no-Home-Assistant boundary and is testable without an instance.
    """
    if block_length is not None and block is not None:
        # A hypothetical block of the requested length, anchored on the
        # real candle lighting.
        block = compute_block(
            block.candle_lighting,
            block.candle_lighting.replace(hour=20, minute=0)
            + timedelta(days=int(block_length)),
        )

    if block is None:
        return {
            "profile": None,
            "rules": [],
            "conflicts": [],
            "warnings": [
                {
                    "kind": "no_block",
                    "message": "No block could be derived from the "
                    "Jewish Calendar sensors.",
                }
            ],
        }

    merged = [merge_defaults(defaults, rule) for rule in rules]
    warnings: list[dict] = []
    if not has_profile(merged, block.length):
        warnings.append(
            {
                "kind": "no_profile",
                "message": f"No enabled rules for a {block.length}-day block.",
            }
        )

    return {
        "profile": block.length,
        "rules": [
            {
                "when": item.when.isoformat(),
                "rule_id": item.rule.id,
                "name": item.rule.name,
                "action": item.rule.action.value,
                "devices": list(item.rule.devices),
            }
            for item in resolve_rules(merged, block, tz)
        ],
        "conflicts": conflict_warnings(defaults, rules),
        "warnings": warnings,
    }
