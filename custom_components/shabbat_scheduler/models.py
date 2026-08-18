"""Domain models. No Home Assistant imports - keep this pure."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from enum import Enum

EREV = "erev"


class Action(str, Enum):
    """What a rule does when it fires."""

    ON = "on"
    OFF = "off"
    CUSTOM = "custom"


@dataclass
class Rule:
    """A single scheduled action within one block-length profile."""

    id: str
    profile: int          # block length this rule belongs to (1, 2 or 3)
    day: str              # EREV, or "1".."3" for a full day
    time: time            # absolute clock time
    action: Action
    devices: tuple[str, ...] = ()
    settings: dict = field(default_factory=dict)
    name: str | None = None
    icon: str | None = None
    enabled: bool = True
    script: str | None = None
    variables: dict = field(default_factory=dict)
    replay_on_restart: bool = False
    color: str | None = None


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
