"""Pure scheduling logic. No Home Assistant imports belong in this module."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, tzinfo

from .models import EREV, Action, Block, Conflict, ResolvedRule, Rule


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


def merge_defaults(defaults: dict, rule: Rule) -> Rule:
    """Fill unset keys from the global defaults, per key, without mutating."""
    devices = rule.devices or tuple(defaults.get("devices", ()))
    settings = {**defaults.get("settings", {}), **rule.settings}
    return replace(rule, devices=tuple(devices), settings=settings)


def has_profile(rules: list[Rule], length: int) -> bool:
    """True when at least one rule is authored for this block length."""
    return any(rule.profile == length for rule in rules)


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


_STATEFUL_ACTIONS = (Action.ON, Action.OFF)


def find_conflicts(rules: list[Rule]) -> list[Conflict]:
    """Find enabled rules that disagree for one device at one moment.

    There is no precedence rule by design, so a conflict has no defined
    winner - it is reported rather than resolved.
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
