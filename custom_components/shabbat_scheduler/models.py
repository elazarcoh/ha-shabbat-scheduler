"""Domain models. No Home Assistant imports - keep this pure."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

EREV = "erev"


@dataclass(frozen=True)
class Replay:
    """Whether, and how late, a rule may be re-run after a restart.

    Opt-in per rule because only the author knows what is safe to repeat:
    re-running "turn the AC off" is harmless, re-running "start the
    dishwasher" is not. `within` bounds how stale a rule may be and still
    be worth replaying - firing an 11:00 rule at 23:00 is worse than not
    firing it at all. None means no bound, which is what v1 did.
    """

    enabled: bool = False
    within: timedelta | None = None


@dataclass(frozen=True)
class Rule:
    """One scheduled Home Assistant service call within a block profile."""

    id: str
    profile: int              # block length this rule belongs to (1, 2 or 3)
    day: str                  # EREV, or "1".."3" for a full day
    time: time                # absolute clock time
    action: str               # "domain.service", any Home Assistant action
    target: dict = field(default_factory=dict)   # HA target selector
    data: dict = field(default_factory=dict)     # the service's own data
    condition: tuple = ()     # HA condition configs; all must pass
    replay: Replay = field(default_factory=Replay)
    name: str | None = None
    icon: str | None = None
    color: str | None = None
    enabled: bool = True


@dataclass(frozen=True)
class Block:
    """One contiguous Shabbat/Chag period."""

    candle_lighting: datetime
    havdalah: datetime
    length: int                    # number of full days
    erev_date: date
    day_dates: tuple[date, ...]    # index 0 is day_1


@dataclass(frozen=True)
class ResolvedRule:
    """A rule bound to a concrete datetime for a specific block."""

    when: datetime
    rule: Rule


@dataclass(frozen=True)
class Conflict:
    """Two or more enabled rules disagree for one device at one moment."""

    profile: int
    day: str
    time: time
    device: str
    rule_ids: tuple[str, ...]
