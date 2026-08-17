# Shabbat Scheduler Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Home Assistant custom integration that drives appliances across Shabbat/Chag blocks from an explicit, per-block-length rule set, applying each rule once and idempotently.

**Architecture:** All scheduling logic lives in pure functions (`block.py`, `device_ops.py`) with zero Home Assistant imports, so it is unit-testable in milliseconds. A thin engine layer executes those decisions against HA, serialising commands per device and stamping every call with an HA `Context`. Rules persist in HA `.storage`; YAML is an import/export view only.

**Tech Stack:** Python 3.14 (uv-managed), Home Assistant 2026.8.1, `uv` for dependency management, `pytest` + `pytest-homeassistant-custom-component` + `pytest-asyncio`, `PyYAML`.

## Global Constraints

Every task's requirements implicitly include this section.

- Target Home Assistant **2026.8.1**, Python **3.14** (uv-managed, not the
  system 3.13.5). Home Assistant raised its Python floor to `>=3.14.2` at
  release 2026.3.0, so 2026.8.1 cannot be installed on 3.13 — verified against
  PyPI metadata. Obtain the interpreter with `uv python install 3.14`.
- `.storage` is the **source of truth**. YAML is import/export only — never a live-watched source.
- **Fire once, never re-assert.** No enforcement in v1. A rule acts at its moment and then leaves the device alone.
- **No implicit precedence.** Overlapping rules are surfaced as warnings, never silently resolved. Saving with conflicts is always permitted.
- **Climate ON is three separate service calls**: `set_hvac_mode` → `set_temperature` → `set_fan_mode`. Never the combined `set_temperature(hvac_mode=…)` form.
- **Fan-mode synonyms**: `quiet ↔ silent ↔ low`. If none is supported, skip only that sub-call and warn.
- **Staleness guard**: a state that is `unknown`, `unavailable`, or last updated *before* our most recent command to that device counts as **must apply**, never "already correct".
- **Every service call carries an HA `Context`** that the engine records.
- `action: custom` rules are **excluded from restart catch-up** unless `replay_on_restart: true`.
- Master switch **defaults to OFF** on first install.
- Device failures retry **3 times, 30 s apart**, then raise a `persistent_notification`.
- Commands to a single device are **serialised** — two rules firing at the same instant must not interleave.
- Timezone always comes from `hass.config.time_zone`; never hardcode.
- Domain string is `shabbat_scheduler` everywhere.

---

## File Structure

```
custom_components/shabbat_scheduler/
  __init__.py        config entry setup, platform forwarding, engine lifecycle
  manifest.json      integration metadata
  const.py           DOMAIN, storage keys, defaults, fan synonym table
  models.py          Rule, Block, ResolvedRule, Conflict, Call, ApplyResult
  block.py           PURE: compute_block, resolve_rules, find_conflicts, desired_state_at, merge_defaults
  device_ops.py      PURE: resolve_fan_mode, plan_calls
  store.py           .storage load/save, rule CRUD
  yaml_io.py         export_yaml / import_yaml over the rule set
  engine.py          timers, per-device queue, apply, retry, catch-up, dry_run
  switch.py          master switch + per-rule switches
  sensor.py          next_block, next_action, last_run sensors
  config_flow.py     single-instance setup
  services.yaml      service descriptions

tests/
  conftest.py        shared fixtures
  test_block.py      block computation + resolution
  test_conflicts.py  conflict detection + desired_state_at ambiguity
  test_device_ops.py fan synonyms + idempotent call planning
  test_store.py      storage CRUD
  test_yaml_io.py    YAML round-trip
  test_engine.py     scheduling, apply, retry, catch-up, dry_run
  test_entities.py   config entry setup, switches + sensors
  test_services.py   simulate, dry-run, YAML services
  test_end_to_end.py a full block driven by real timers
```

**Boundary rationale:** `block.py` and `device_ops.py` contain every non-obvious decision and import nothing from Home Assistant, so the risky logic is testable without a running instance. `engine.py` only executes decisions those modules hand it.

---

### Task 1: Project scaffold and domain models

**Files:**
- Create: `pyproject.toml`
- Create: `custom_components/shabbat_scheduler/__init__.py` (empty placeholder)
- Create: `custom_components/shabbat_scheduler/const.py`
- Create: `custom_components/shabbat_scheduler/models.py`
- Create: `tests/conftest.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `Action` (str enum: `ON="on"`, `OFF="off"`, `CUSTOM="custom"`); `EREV = "erev"`; `Rule` dataclass; `Block` frozen dataclass; `ResolvedRule` frozen dataclass; `Conflict` frozen dataclass; `DOMAIN = "shabbat_scheduler"`; `FAN_SYNONYMS`.

- [ ] **Step 1: Create the uv project and install dependencies**

```bash
cd /home/rpi4/ha-shabbat-scheduler
# HA 2026.8.1 requires Python >=3.14.2; the system interpreter is 3.13.5.
uv python install 3.14
uv init --name shabbat-scheduler --no-package --python 3.14 .
uv add --dev pytest pytest-asyncio pytest-homeassistant-custom-component
uv add pyyaml
```

Verify the resolved versions before continuing — a silent backtrack to an
older Home Assistant is the failure mode to catch here:

```bash
uv run python -c "import homeassistant, sys; print(sys.version.split()[0], homeassistant.__version__)"
```

Expected: a `3.14.x` interpreter and `homeassistant` `2026.8.1` or a later
`2026.8.x` patch. If either is lower, stop and report rather than proceeding.

`requires-python` must be `>=3.14.2`, not `>=3.14`. `uv.lock` resolves two
branches: below 3.14.2 it pins `homeassistant==2026.2.3` (six months older,
different API surface), and at/above it the intended `2026.8.x`. A loose floor
lets a future `uv sync` on a 3.14.0/3.14.1 interpreter silently take the old
branch. Commit `.python-version` as well, so the interpreter is pinned rather
than merely constrained.

Then replace the generated `pyproject.toml` `[project]` section body so it reads:

```toml
[project]
name = "shabbat-scheduler"
version = "0.1.0"
description = "Home Assistant integration scheduling appliances across Shabbat and Chag"
requires-python = ">=3.14.2"
dependencies = ["pyyaml"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_models.py`:

```python
from datetime import date, datetime, time, timezone

from custom_components.shabbat_scheduler.models import (
    Action,
    Block,
    Conflict,
    EREV,
    ResolvedRule,
    Rule,
)


def test_rule_defaults():
    rule = Rule(id="r1", profile=1, day=EREV, time=time(23, 0), action=Action.OFF)
    assert rule.enabled is True
    assert rule.devices == ()
    assert rule.settings == {}
    assert rule.replay_on_restart is False


def test_action_is_str_enum():
    assert Action.ON == "on"
    assert Action("off") is Action.OFF


def test_block_is_frozen():
    block = Block(
        candle_lighting=datetime(2026, 8, 14, 18, 44, tzinfo=timezone.utc),
        havdalah=datetime(2026, 8, 15, 20, 1, tzinfo=timezone.utc),
        length=1,
        erev_date=date(2026, 8, 14),
        day_dates=(date(2026, 8, 15),),
    )
    assert block.length == 1
    try:
        block.length = 2
    except Exception as err:  # frozen dataclass raises FrozenInstanceError
        assert "frozen" in type(err).__name__.lower()
    else:
        raise AssertionError("Block should be immutable")


def test_resolved_rule_and_conflict_construct():
    rule = Rule(id="r1", profile=1, day="1", time=time(11, 0), action=Action.ON)
    resolved = ResolvedRule(
        when=datetime(2026, 8, 15, 11, 0, tzinfo=timezone.utc), rule=rule
    )
    assert resolved.rule.id == "r1"

    conflict = Conflict(
        profile=1, day="1", time=time(11, 0), device="climate.a", rule_ids=("r1", "r2")
    )
    assert conflict.rule_ids == ("r1", "r2")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'custom_components'`

- [ ] **Step 4: Write the implementation**

Create `custom_components/shabbat_scheduler/__init__.py` as an empty file.

Create `custom_components/shabbat_scheduler/const.py`:

```python
"""Constants for the Shabbat Scheduler integration."""

DOMAIN = "shabbat_scheduler"

STORAGE_KEY = "shabbat_scheduler.rules"
STORAGE_VERSION = 1

EVENT_RULE_APPLIED = "shabbat_scheduler_rule_applied"

RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 30

# Fan-mode names differ per manufacturer for the same intent. Ordered by
# preference: the requested value first, then acceptable substitutes.
FAN_SYNONYMS: dict[str, tuple[str, ...]] = {
    "quiet": ("quiet", "silent", "low"),
    "silent": ("silent", "quiet", "low"),
    "low": ("low", "quiet", "silent"),
}
```

Create `custom_components/shabbat_scheduler/models.py`:

```python
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
```

Create `tests/conftest.py`:

```python
"""Shared fixtures.

pytest-homeassistant-custom-component ships the `hass` fixture; custom
integrations are only loaded when `enable_custom_integrations` is requested.
"""

import pytest
from homeassistant.setup import async_setup_component


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Make the custom component importable in every test."""
    yield


@pytest.fixture
async def jerusalem(hass):
    """Pin the test instance to the real deployment timezone.

    The default test timezone is US/Pacific, which silently shifts every date
    calculation in this integration. Any test touching dates MUST use this.
    """
    await hass.config.async_set_time_zone("Asia/Jerusalem")
    return hass


@pytest.fixture
async def test_booleans(hass):
    """Real input_boolean entities with real turn_on/turn_off services.

    `hass.states.async_set` alone creates a state but no service, so calls
    would fail with ServiceNotFound. Setting the component up gives genuine
    end-to-end behaviour against throwaway entities rather than appliances.
    """
    await async_setup_component(
        hass,
        "input_boolean",
        {"input_boolean": {"t": {"name": "T"}, "salon": {"name": "Salon"}}},
    )
    await hass.async_block_till_done()
    return hass
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_models.py -v`
Expected: PASS, 4 tests

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock custom_components tests
git commit -m "feat: project scaffold and domain models"
```

---

### Task 2: Block computation

**Files:**
- Create: `custom_components/shabbat_scheduler/block.py`
- Test: `tests/test_block.py`

**Interfaces:**
- Consumes: `Block` from `models.py`.
- Produces: `compute_block(candle_lighting: datetime, havdalah: datetime) -> Block`. Raises `ValueError` when `havdalah <= candle_lighting`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_block.py`:

```python
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from custom_components.shabbat_scheduler.block import compute_block

TZ = ZoneInfo("Asia/Jerusalem")


def test_regular_shabbat_is_one_day():
    # Real values observed on the live instance.
    block = compute_block(
        datetime(2026, 8, 14, 18, 44, tzinfo=TZ),
        datetime(2026, 8, 15, 20, 1, tzinfo=TZ),
    )
    assert block.length == 1
    assert block.erev_date == date(2026, 8, 14)
    assert block.day_dates == (date(2026, 8, 15),)


def test_chag_adjacent_to_shabbat_is_two_days():
    block = compute_block(
        datetime(2026, 10, 1, 18, 0, tzinfo=TZ),
        datetime(2026, 10, 3, 19, 30, tzinfo=TZ),
    )
    assert block.length == 2
    assert block.erev_date == date(2026, 10, 1)
    assert block.day_dates == (date(2026, 10, 2), date(2026, 10, 3))


def test_three_day_block():
    block = compute_block(
        datetime(2026, 9, 30, 18, 0, tzinfo=TZ),
        datetime(2026, 10, 3, 19, 30, tzinfo=TZ),
    )
    assert block.length == 3
    assert block.day_dates == (
        date(2026, 10, 1),
        date(2026, 10, 2),
        date(2026, 10, 3),
    )


def test_havdalah_before_candle_lighting_is_rejected():
    with pytest.raises(ValueError):
        compute_block(
            datetime(2026, 8, 15, 20, 1, tzinfo=TZ),
            datetime(2026, 8, 14, 18, 44, tzinfo=TZ),
        )


def test_same_day_havdalah_is_rejected():
    # A zero-length block is meaningless and would produce no full days.
    with pytest.raises(ValueError):
        compute_block(
            datetime(2026, 8, 14, 18, 44, tzinfo=TZ),
            datetime(2026, 8, 14, 23, 0, tzinfo=TZ),
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_block.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'custom_components.shabbat_scheduler.block'`

- [ ] **Step 3: Write minimal implementation**

Create `custom_components/shabbat_scheduler/block.py`:

```python
"""Pure scheduling logic. No Home Assistant imports belong in this module."""

from __future__ import annotations

from datetime import datetime, timedelta

from .models import Block


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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_block.py -v`
Expected: PASS, 5 tests

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler/block.py tests/test_block.py
git commit -m "feat: compute block length and dates from zmanim"
```

---

### Task 3: Defaults merge and rule resolution

**Files:**
- Modify: `custom_components/shabbat_scheduler/block.py`
- Test: `tests/test_block.py`

**Interfaces:**
- Consumes: `compute_block`, `Rule`, `ResolvedRule`, `Action`, `EREV`.
- Produces:
  - `merge_defaults(defaults: dict, rule: Rule) -> Rule` — returns a new `Rule` with `settings` and `devices` filled from defaults where unset (shallow, per-key).
  - `resolve_rules(rules: list[Rule], block: Block, tz: tzinfo) -> list[ResolvedRule]` — selects the profile matching `block.length`, drops disabled rules, binds each to a concrete datetime, sorted ascending by `when`.
  - `has_profile(rules: list[Rule], length: int) -> bool`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_block.py`:

```python
from datetime import time

from custom_components.shabbat_scheduler.block import (
    has_profile,
    merge_defaults,
    resolve_rules,
)
from custom_components.shabbat_scheduler.models import Action, EREV, Rule


def _block_1day():
    return compute_block(
        datetime(2026, 8, 14, 18, 44, tzinfo=TZ),
        datetime(2026, 8, 15, 20, 1, tzinfo=TZ),
    )


def test_merge_defaults_fills_unset_keys_only():
    defaults = {
        "devices": ["climate.a"],
        "settings": {"temperature": 26, "fan_mode": "quiet"},
    }
    rule = Rule(
        id="r1",
        profile=1,
        day="1",
        time=time(11, 0),
        action=Action.ON,
        settings={"temperature": 24},
    )
    merged = merge_defaults(defaults, rule)
    assert merged.devices == ("climate.a",)
    assert merged.settings == {"temperature": 24, "fan_mode": "quiet"}
    # The original must not be mutated.
    assert rule.settings == {"temperature": 24}


def test_merge_defaults_keeps_explicit_devices():
    defaults = {"devices": ["climate.a"]}
    rule = Rule(
        id="r1",
        profile=1,
        day="1",
        time=time(11, 0),
        action=Action.ON,
        devices=("climate.b",),
    )
    assert merge_defaults(defaults, rule).devices == ("climate.b",)


def test_resolve_binds_erev_and_days_to_dates():
    rules = [
        Rule(id="a", profile=1, day="1", time=time(11, 0), action=Action.ON),
        Rule(id="b", profile=1, day=EREV, time=time(23, 0), action=Action.OFF),
    ]
    resolved = resolve_rules(rules, _block_1day(), TZ)
    assert [r.rule.id for r in resolved] == ["b", "a"]  # sorted by datetime
    assert resolved[0].when == datetime(2026, 8, 14, 23, 0, tzinfo=TZ)
    assert resolved[1].when == datetime(2026, 8, 15, 11, 0, tzinfo=TZ)


def test_resolve_selects_only_the_matching_profile():
    rules = [
        Rule(id="a", profile=1, day="1", time=time(11, 0), action=Action.ON),
        Rule(id="b", profile=3, day="1", time=time(11, 0), action=Action.ON),
    ]
    resolved = resolve_rules(rules, _block_1day(), TZ)
    assert [r.rule.id for r in resolved] == ["a"]


def test_resolve_drops_disabled_rules():
    rules = [
        Rule(
            id="a", profile=1, day="1", time=time(11, 0),
            action=Action.ON, enabled=False,
        )
    ]
    assert resolve_rules(rules, _block_1day(), TZ) == []


def test_resolve_keeps_post_havdalah_times():
    # 23:00 on the last day is after havdalah (20:01) and must still resolve.
    rules = [Rule(id="a", profile=1, day="1", time=time(23, 0), action=Action.OFF)]
    resolved = resolve_rules(rules, _block_1day(), TZ)
    assert resolved[0].when == datetime(2026, 8, 15, 23, 0, tzinfo=TZ)


def test_has_profile():
    rules = [Rule(id="a", profile=2, day="1", time=time(11, 0), action=Action.ON)]
    assert has_profile(rules, 2) is True
    assert has_profile(rules, 1) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_block.py -v`
Expected: FAIL with `ImportError: cannot import name 'has_profile'`

- [ ] **Step 3: Write minimal implementation**

Append to `custom_components/shabbat_scheduler/block.py`:

```python
from dataclasses import replace
from datetime import tzinfo

from .models import EREV, ResolvedRule, Rule


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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_block.py -v`
Expected: PASS, 12 tests

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler/block.py tests/test_block.py
git commit -m "feat: merge defaults and resolve rules to concrete datetimes"
```

---

### Task 4: Conflict detection

**Files:**
- Modify: `custom_components/shabbat_scheduler/block.py`
- Test: `tests/test_conflicts.py`

**Interfaces:**
- Consumes: `Rule`, `Conflict`, `Action`.
- Produces: `find_conflicts(rules: list[Rule]) -> list[Conflict]` — same profile+day+time+device with differing `on`/`off` actions. `custom` rules are excluded because their devices are display-only and their effect is not derivable.

- [ ] **Step 1: Write the failing test**

Create `tests/test_conflicts.py`:

```python
from datetime import time

from custom_components.shabbat_scheduler.block import find_conflicts
from custom_components.shabbat_scheduler.models import Action, Rule


def _rule(rule_id, action, devices=("climate.a",), day="1", at=time(18, 0), profile=1):
    return Rule(
        id=rule_id, profile=profile, day=day, time=at,
        action=action, devices=devices,
    )


def test_opposing_actions_on_one_device_conflict():
    conflicts = find_conflicts([_rule("a", Action.ON), _rule("b", Action.OFF)])
    assert len(conflicts) == 1
    assert conflicts[0].device == "climate.a"
    assert set(conflicts[0].rule_ids) == {"a", "b"}


def test_identical_actions_are_not_conflicts():
    assert find_conflicts([_rule("a", Action.OFF), _rule("b", Action.OFF)]) == []


def test_different_times_are_not_conflicts():
    assert find_conflicts(
        [_rule("a", Action.ON), _rule("b", Action.OFF, at=time(19, 0))]
    ) == []


def test_different_devices_are_not_conflicts():
    assert find_conflicts(
        [_rule("a", Action.ON), _rule("b", Action.OFF, devices=("climate.b",))]
    ) == []


def test_different_profiles_are_not_conflicts():
    assert find_conflicts(
        [_rule("a", Action.ON), _rule("b", Action.OFF, profile=2)]
    ) == []


def test_disabled_rules_do_not_conflict():
    enabled = _rule("a", Action.ON)
    disabled = Rule(
        id="b", profile=1, day="1", time=time(18, 0),
        action=Action.OFF, devices=("climate.a",), enabled=False,
    )
    assert find_conflicts([enabled, disabled]) == []


def test_custom_rules_are_excluded():
    custom = Rule(
        id="b", profile=1, day="1", time=time(18, 0),
        action=Action.CUSTOM, devices=("climate.a",), script="script.x",
    )
    assert find_conflicts([_rule("a", Action.ON), custom]) == []


def test_conflict_detected_per_shared_device():
    conflicts = find_conflicts([
        _rule("a", Action.ON, devices=("climate.a", "climate.b")),
        _rule("b", Action.OFF, devices=("climate.b",)),
    ])
    assert len(conflicts) == 1
    assert conflicts[0].device == "climate.b"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_conflicts.py -v`
Expected: FAIL with `ImportError: cannot import name 'find_conflicts'`

- [ ] **Step 3: Write minimal implementation**

Append to `custom_components/shabbat_scheduler/block.py`:

```python
from .models import Action, Conflict

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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_conflicts.py -v`
Expected: PASS, 8 tests

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler/block.py tests/test_conflicts.py
git commit -m "feat: detect conflicting rules without resolving them"
```

---

### Task 5: Desired state

**Files:**
- Modify: `custom_components/shabbat_scheduler/block.py`
- Test: `tests/test_conflicts.py`

**Interfaces:**
- Consumes: `resolve_rules`, `Rule`, `Conflict`.
- Produces: `desired_state_at(rules, block, when, device, tz) -> Rule | Conflict | None`. Returns the most recent already-passed `on`/`off` rule for that device; `Conflict` when the latest moment is ambiguous; `None` when undefined. **This is the function enforcement will later reuse — keep it exported and pure.**

- [ ] **Step 1: Write the failing test**

Append to `tests/test_conflicts.py`:

```python
from datetime import datetime
from zoneinfo import ZoneInfo

from custom_components.shabbat_scheduler.block import compute_block, desired_state_at
from custom_components.shabbat_scheduler.models import Conflict

TZ = ZoneInfo("Asia/Jerusalem")


def _block():
    return compute_block(
        datetime(2026, 8, 14, 18, 44, tzinfo=TZ),
        datetime(2026, 8, 15, 20, 1, tzinfo=TZ),
    )


def _rules():
    return [
        Rule(id="on", profile=1, day="1", time=time(11, 0),
             action=Action.ON, devices=("climate.a",)),
        Rule(id="off", profile=1, day="1", time=time(18, 0),
             action=Action.OFF, devices=("climate.a",)),
    ]


def test_returns_none_before_the_first_rule():
    when = datetime(2026, 8, 15, 9, 0, tzinfo=TZ)
    assert desired_state_at(_rules(), _block(), when, "climate.a", TZ) is None


def test_returns_the_most_recent_passed_rule():
    when = datetime(2026, 8, 15, 12, 0, tzinfo=TZ)
    result = desired_state_at(_rules(), _block(), when, "climate.a", TZ)
    assert result.id == "on"


def test_returns_the_latest_when_several_have_passed():
    when = datetime(2026, 8, 15, 19, 0, tzinfo=TZ)
    result = desired_state_at(_rules(), _block(), when, "climate.a", TZ)
    assert result.id == "off"


def test_exact_boundary_counts_as_passed():
    when = datetime(2026, 8, 15, 11, 0, tzinfo=TZ)
    result = desired_state_at(_rules(), _block(), when, "climate.a", TZ)
    assert result.id == "on"


def test_unknown_device_is_undefined():
    when = datetime(2026, 8, 15, 19, 0, tzinfo=TZ)
    assert desired_state_at(_rules(), _block(), when, "climate.zzz", TZ) is None


def test_ambiguous_latest_moment_returns_a_conflict():
    rules = [
        Rule(id="a", profile=1, day="1", time=time(18, 0),
             action=Action.ON, devices=("climate.a",)),
        Rule(id="b", profile=1, day="1", time=time(18, 0),
             action=Action.OFF, devices=("climate.a",)),
    ]
    when = datetime(2026, 8, 15, 19, 0, tzinfo=TZ)
    result = desired_state_at(rules, _block(), when, "climate.a", TZ)
    assert isinstance(result, Conflict)
    assert set(result.rule_ids) == {"a", "b"}


def test_custom_rules_never_define_desired_state():
    rules = [
        Rule(id="c", profile=1, day="1", time=time(11, 0), action=Action.CUSTOM,
             devices=("climate.a",), script="script.x"),
    ]
    when = datetime(2026, 8, 15, 12, 0, tzinfo=TZ)
    assert desired_state_at(rules, _block(), when, "climate.a", TZ) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_conflicts.py -v`
Expected: FAIL with `ImportError: cannot import name 'desired_state_at'`

- [ ] **Step 3: Write minimal implementation**

Append to `custom_components/shabbat_scheduler/block.py`:

```python
def desired_state_at(
    rules: list[Rule],
    block: Block,
    when: datetime,
    device: str,
    tz: tzinfo,
) -> Rule | Conflict | None:
    """What state should `device` be in at `when`?

    Restart catch-up is one caller; enforcement would be a second caller of
    this same function, which is why it lives here rather than inside the
    catch-up routine.

    Returns None where undefined (before the first rule, or the device is
    driven only by custom rules), and a Conflict where the answer is
    ambiguous - callers must decline to act rather than guess.
    """
    passed = [
        item
        for item in resolve_rules(rules, block, tz)
        if item.when <= when
        and item.rule.action in _STATEFUL_ACTIONS
        and device in item.rule.devices
    ]
    if not passed:
        return None

    latest = passed[-1].when
    tied = [item.rule for item in passed if item.when == latest]

    if len({rule.action for rule in tied}) > 1:
        first = tied[0]
        return Conflict(
            profile=first.profile,
            day=first.day,
            time=first.time,
            device=device,
            rule_ids=tuple(rule.id for rule in tied),
        )

    return tied[-1]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_conflicts.py -v`
Expected: PASS, 15 tests

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler/block.py tests/test_conflicts.py
git commit -m "feat: desired_state_at with explicit conflict reporting"
```

---

### Task 6: Idempotent call planning

**Files:**
- Create: `custom_components/shabbat_scheduler/device_ops.py`
- Test: `tests/test_device_ops.py`

**Interfaces:**
- Consumes: `Action`, `FAN_SYNONYMS`.
- Produces:
  - `resolve_fan_mode(requested: str, supported: list[str]) -> str | None`
  - `Call` frozen dataclass: `domain`, `service`, `data: dict`, `attribute: str`, `from_value`, `to_value`.
  - `plan_calls(entity_id, current_state, current_attrs, action, settings, force) -> list[Call]` — returns only the calls whose values actually differ, unless `force` is `True`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_device_ops.py`:

```python
from custom_components.shabbat_scheduler.device_ops import (
    Call,
    plan_calls,
    resolve_fan_mode,
)
from custom_components.shabbat_scheduler.models import Action

CLIMATE_ATTRS = {
    "fan_modes": ["auto", "quiet", "low", "high"],
    "temperature": 26,
    "fan_mode": "auto",
}


def test_resolve_fan_mode_exact_match():
    assert resolve_fan_mode("quiet", ["auto", "quiet"]) == "quiet"


def test_resolve_fan_mode_falls_back_to_synonym():
    # The aux_cloud units expose "silent" where the other AC exposes "quiet".
    assert resolve_fan_mode("quiet", ["auto", "silent", "low"]) == "silent"


def test_resolve_fan_mode_returns_none_when_unsupported():
    assert resolve_fan_mode("quiet", ["auto", "high"]) is None


def test_climate_on_emits_three_separate_calls():
    calls = plan_calls(
        "climate.a", "off", CLIMATE_ATTRS, Action.ON,
        {"hvac_mode": "cool", "temperature": 24, "fan_mode": "quiet"}, force=False,
    )
    assert [c.service for c in calls] == [
        "set_hvac_mode", "set_temperature", "set_fan_mode",
    ]
    # Never the combined form - it silently fails to power on aux_cloud units.
    assert all("hvac_mode" not in c.data for c in calls if c.service == "set_temperature")


def test_already_correct_values_are_skipped():
    calls = plan_calls(
        "climate.a", "cool", CLIMATE_ATTRS, Action.ON,
        {"hvac_mode": "cool", "temperature": 26, "fan_mode": "auto"}, force=False,
    )
    assert calls == []


def test_only_differing_values_are_emitted():
    calls = plan_calls(
        "climate.a", "cool", CLIMATE_ATTRS, Action.ON,
        {"hvac_mode": "cool", "temperature": 24, "fan_mode": "auto"}, force=False,
    )
    assert [c.attribute for c in calls] == ["temperature"]
    assert calls[0].from_value == 26
    assert calls[0].to_value == 24


def test_force_emits_everything_even_when_matching():
    calls = plan_calls(
        "climate.a", "cool", CLIMATE_ATTRS, Action.ON,
        {"hvac_mode": "cool", "temperature": 26, "fan_mode": "auto"}, force=True,
    )
    assert len(calls) == 3


def test_unsupported_fan_mode_is_skipped_not_fatal():
    attrs = {**CLIMATE_ATTRS, "fan_modes": ["auto", "high"]}
    calls = plan_calls(
        "climate.a", "off", attrs, Action.ON,
        {"hvac_mode": "cool", "fan_mode": "quiet"}, force=False,
    )
    assert [c.service for c in calls] == ["set_hvac_mode"]


def test_climate_off_when_already_off_is_skipped():
    assert plan_calls("climate.a", "off", CLIMATE_ATTRS, Action.OFF, {}, force=False) == []


def test_climate_off_when_on_emits_turn_off():
    calls = plan_calls("climate.a", "cool", CLIMATE_ATTRS, Action.OFF, {}, force=False)
    assert [(c.domain, c.service) for c in calls] == [("climate", "turn_off")]


def test_switch_domain_uses_turn_on_off():
    calls = plan_calls("switch.a", "off", {}, Action.ON, {}, force=False)
    assert [(c.domain, c.service) for c in calls] == [("switch", "turn_on")]


def test_input_boolean_domain_supported_for_testing():
    calls = plan_calls("input_boolean.t", "off", {}, Action.ON, {}, force=False)
    assert [(c.domain, c.service) for c in calls] == [("input_boolean", "turn_on")]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_device_ops.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'custom_components.shabbat_scheduler.device_ops'`

- [ ] **Step 3: Write minimal implementation**

Create `custom_components/shabbat_scheduler/device_ops.py`:

```python
"""Pure translation of a desired state into the service calls needed.

Nothing here talks to Home Assistant; the engine executes what this returns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .const import FAN_SYNONYMS
from .models import Action

_SIMPLE_DOMAINS = ("switch", "light", "input_boolean", "fan")


@dataclass(frozen=True)
class Call:
    """One service call, annotated for change reporting."""

    domain: str
    service: str
    data: dict = field(default_factory=dict)
    attribute: str = ""
    from_value: Any = None
    to_value: Any = None


def resolve_fan_mode(requested: str, supported: list[str]) -> str | None:
    """Map a requested fan mode onto one this device actually exposes."""
    if requested in supported:
        return requested
    for candidate in FAN_SYNONYMS.get(requested, ()):
        if candidate in supported:
            return candidate
    return None


def plan_calls(
    entity_id: str,
    current_state: str,
    current_attrs: dict,
    action: Action,
    settings: dict,
    force: bool,
) -> list[Call]:
    """Return only the calls whose values genuinely differ.

    `force` is set by the caller when the reading cannot be trusted (unknown,
    unavailable, or older than our last command), in which case everything is
    re-sent rather than skipped.
    """
    domain = entity_id.split(".", 1)[0]

    if domain == "climate":
        return _plan_climate(current_state, current_attrs, action, settings, force)

    if domain in _SIMPLE_DOMAINS:
        service = "turn_on" if action is Action.ON else "turn_off"
        wanted = "on" if action is Action.ON else "off"
        if not force and current_state == wanted:
            return []
        return [
            Call(
                domain=domain,
                service=service,
                data={"entity_id": entity_id},
                attribute="state",
                from_value=current_state,
                to_value=wanted,
            )
        ]

    return []


def _plan_climate(
    current_state: str,
    attrs: dict,
    action: Action,
    settings: dict,
    force: bool,
) -> list[Call]:
    if action is Action.OFF:
        if not force and current_state == "off":
            return []
        return [
            Call(
                domain="climate",
                service="turn_off",
                attribute="state",
                from_value=current_state,
                to_value="off",
            )
        ]

    calls: list[Call] = []

    hvac_mode = settings.get("hvac_mode")
    if hvac_mode is not None and (force or current_state != hvac_mode):
        calls.append(
            Call(
                domain="climate",
                service="set_hvac_mode",
                data={"hvac_mode": hvac_mode},
                attribute="hvac_mode",
                from_value=current_state,
                to_value=hvac_mode,
            )
        )

    temperature = settings.get("temperature")
    if temperature is not None and (force or attrs.get("temperature") != temperature):
        calls.append(
            Call(
                domain="climate",
                service="set_temperature",
                data={"temperature": temperature},
                attribute="temperature",
                from_value=attrs.get("temperature"),
                to_value=temperature,
            )
        )

    fan_mode = settings.get("fan_mode")
    if fan_mode is not None:
        actual = resolve_fan_mode(fan_mode, list(attrs.get("fan_modes", [])))
        if actual is None:
            # Unsupported everywhere - skip this sub-call, never fail the rule.
            return calls
        if force or attrs.get("fan_mode") != actual:
            calls.append(
                Call(
                    domain="climate",
                    service="set_fan_mode",
                    data={"fan_mode": actual},
                    attribute="fan_mode",
                    from_value=attrs.get("fan_mode"),
                    to_value=actual,
                )
            )

    return calls
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_device_ops.py -v`
Expected: PASS, 12 tests

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler/device_ops.py tests/test_device_ops.py
git commit -m "feat: plan only the service calls that differ from current state"
```

---

### Task 7: Rule storage

**Files:**
- Create: `custom_components/shabbat_scheduler/store.py`
- Test: `tests/test_store.py`

**Interfaces:**
- Consumes: `Rule`, `Action`, `DOMAIN`, `STORAGE_KEY`, `STORAGE_VERSION`.
- Produces: `RuleStore` class with `async_load()`, `async_save()`, `rules -> list[Rule]`, `defaults -> dict`, `enabled -> bool`, `dry_run -> bool`, `async_add(rule)`, `async_update(rule_id, **changes)`, `async_delete(rule_id)`, `async_replace_all(defaults, rules)`, plus module-level `rule_to_dict` / `rule_from_dict`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_store.py`:

```python
from datetime import time

from custom_components.shabbat_scheduler.models import Action, EREV, Rule
from custom_components.shabbat_scheduler.store import (
    RuleStore,
    rule_from_dict,
    rule_to_dict,
)


def test_rule_dict_round_trip():
    rule = Rule(
        id="r1", profile=2, day=EREV, time=time(22, 30), action=Action.ON,
        devices=("climate.a",), settings={"temperature": 26}, name="test",
    )
    restored = rule_from_dict(rule_to_dict(rule))
    assert restored == rule


async def test_store_starts_empty_and_disabled(hass):
    store = RuleStore(hass)
    await store.async_load()
    assert store.rules == []
    assert store.enabled is False  # master switch defaults OFF
    assert store.dry_run is False


async def test_add_and_persist(hass):
    store = RuleStore(hass)
    await store.async_load()
    rule = Rule(id="r1", profile=1, day="1", time=time(11, 0), action=Action.ON)
    await store.async_add(rule)

    reloaded = RuleStore(hass)
    await reloaded.async_load()
    assert [r.id for r in reloaded.rules] == ["r1"]


async def test_update_changes_only_named_fields(hass):
    store = RuleStore(hass)
    await store.async_load()
    await store.async_add(
        Rule(id="r1", profile=1, day="1", time=time(11, 0), action=Action.ON)
    )
    await store.async_update("r1", enabled=False)
    assert store.rules[0].enabled is False
    assert store.rules[0].time == time(11, 0)


async def test_delete(hass):
    store = RuleStore(hass)
    await store.async_load()
    await store.async_add(
        Rule(id="r1", profile=1, day="1", time=time(11, 0), action=Action.ON)
    )
    await store.async_delete("r1")
    assert store.rules == []


async def test_replace_all_swaps_defaults_and_rules(hass):
    store = RuleStore(hass)
    await store.async_load()
    await store.async_replace_all(
        {"temperature": 26},
        [Rule(id="x", profile=3, day="2", time=time(9, 0), action=Action.OFF)],
    )
    assert store.defaults == {"temperature": 26}
    assert [r.id for r in store.rules] == ["x"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'custom_components.shabbat_scheduler.store'`

- [ ] **Step 3: Write minimal implementation**

Create `custom_components/shabbat_scheduler/store.py`:

```python
"""Persistence of the rule set in Home Assistant's .storage.

.storage is the source of truth; YAML is only ever an import/export view.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import time

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION
from .models import Action, Rule


def rule_to_dict(rule: Rule) -> dict:
    """Serialise a rule for storage."""
    return {
        "id": rule.id,
        "profile": rule.profile,
        "day": rule.day,
        "time": rule.time.isoformat(),
        "action": rule.action.value,
        "devices": list(rule.devices),
        "settings": dict(rule.settings),
        "name": rule.name,
        "icon": rule.icon,
        "enabled": rule.enabled,
        "script": rule.script,
        "variables": dict(rule.variables),
        "replay_on_restart": rule.replay_on_restart,
        "color": rule.color,
    }


def rule_from_dict(data: dict) -> Rule:
    """Deserialise a stored rule."""
    return Rule(
        id=data["id"],
        profile=int(data["profile"]),
        day=str(data["day"]),
        time=time.fromisoformat(data["time"]),
        action=Action(data["action"]),
        devices=tuple(data.get("devices", ())),
        settings=dict(data.get("settings", {})),
        name=data.get("name"),
        icon=data.get("icon"),
        enabled=data.get("enabled", True),
        script=data.get("script"),
        variables=dict(data.get("variables", {})),
        replay_on_restart=data.get("replay_on_restart", False),
        color=data.get("color"),
    )


class RuleStore:
    """Loads, mutates and persists the rule set."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._rules: list[Rule] = []
        self._defaults: dict = {}
        self._enabled: bool = False
        self._dry_run: bool = False

    @property
    def rules(self) -> list[Rule]:
        return list(self._rules)

    @property
    def defaults(self) -> dict:
        return dict(self._defaults)

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def dry_run(self) -> bool:
        return self._dry_run

    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        self._rules = [rule_from_dict(item) for item in data.get("rules", [])]
        self._defaults = data.get("defaults", {})
        # Master switch defaults OFF so a fresh install cannot act.
        self._enabled = data.get("enabled", False)
        self._dry_run = data.get("dry_run", False)

    async def async_save(self) -> None:
        await self._store.async_save(
            {
                "rules": [rule_to_dict(rule) for rule in self._rules],
                "defaults": self._defaults,
                "enabled": self._enabled,
                "dry_run": self._dry_run,
            }
        )

    async def async_set_enabled(self, value: bool) -> None:
        self._enabled = value
        await self.async_save()

    async def async_set_dry_run(self, value: bool) -> None:
        self._dry_run = value
        await self.async_save()

    async def async_add(self, rule: Rule) -> None:
        self._rules.append(rule)
        await self.async_save()

    async def async_update(self, rule_id: str, **changes) -> None:
        self._rules = [
            replace(rule, **changes) if rule.id == rule_id else rule
            for rule in self._rules
        ]
        await self.async_save()

    async def async_delete(self, rule_id: str) -> None:
        self._rules = [rule for rule in self._rules if rule.id != rule_id]
        await self.async_save()

    async def async_replace_all(self, defaults: dict, rules: list[Rule]) -> None:
        self._defaults = dict(defaults)
        self._rules = list(rules)
        await self.async_save()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_store.py -v`
Expected: PASS, 6 tests

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler/store.py tests/test_store.py
git commit -m "feat: persist rules in .storage with master switch defaulting off"
```

---

### Task 8: YAML import and export

**Files:**
- Create: `custom_components/shabbat_scheduler/yaml_io.py`
- Test: `tests/test_yaml_io.py`

**Interfaces:**
- Consumes: `Rule`, `Action`, `EREV`.
- Produces:
  - `export_yaml(defaults: dict, rules: list[Rule]) -> str` — grouped by profile then day.
  - `import_yaml(text: str) -> tuple[dict, list[Rule]]` — generates ids where absent.

- [ ] **Step 1: Write the failing test**

Create `tests/test_yaml_io.py`:

```python
from datetime import time

import yaml

from custom_components.shabbat_scheduler.models import Action, EREV, Rule
from custom_components.shabbat_scheduler.yaml_io import export_yaml, import_yaml


def _rules():
    return [
        Rule(id="a", profile=1, day=EREV, time=time(23, 0), action=Action.OFF,
             devices=("climate.a",)),
        Rule(id="b", profile=1, day="1", time=time(11, 0), action=Action.ON,
             devices=("climate.a",), name="בוקר שבת"),
    ]


def test_export_groups_by_profile_and_day():
    text = export_yaml({"temperature": 26}, _rules())
    parsed = yaml.safe_load(text)
    assert parsed["defaults"] == {"temperature": 26}
    assert set(parsed["profiles"]["1_day"]) == {"erev", "day_1"}
    assert parsed["profiles"]["1_day"]["erev"][0]["at"] == "23:00:00"
    assert parsed["profiles"]["1_day"]["day_1"][0]["name"] == "בוקר שבת"
    # Assert on the RAW text: safe_load decodes \uXXXX escapes, so parsing
    # first would pass whether or not allow_unicode was set.
    assert "בוקר שבת" in text
    assert "\\u" not in text


def test_export_orders_erev_before_numbered_days():
    keys = list(yaml.safe_load(export_yaml({}, _rules()))["profiles"]["1_day"])
    assert keys.index("erev") < keys.index("day_1")


def test_round_trip_preserves_ids():
    _defaults, rules = import_yaml(export_yaml({}, _rules()))
    assert {r.id for r in rules} == {"a", "b"}


def test_round_trip_preserves_rules():
    defaults, rules = import_yaml(export_yaml({"temperature": 26}, _rules()))
    assert defaults == {"temperature": 26}
    assert {(r.profile, r.day, r.time, r.action) for r in rules} == {
        (1, EREV, time(23, 0), Action.OFF),
        (1, "1", time(11, 0), Action.ON),
    }


def test_import_generates_ids_when_absent():
    text = """
defaults: {}
profiles:
  2_day:
    day_2:
      - at: "18:00"
        action: "off"
        devices: [climate.a]
"""
    _defaults, rules = import_yaml(text)
    assert len(rules) == 1
    assert rules[0].id
    assert rules[0].profile == 2
    assert rules[0].day == "2"
    assert rules[0].time == time(18, 0)


def test_import_accepts_empty_document():
    defaults, rules = import_yaml("")
    assert defaults == {}
    assert rules == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_yaml_io.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'custom_components.shabbat_scheduler.yaml_io'`

- [ ] **Step 3: Write minimal implementation**

Create `custom_components/shabbat_scheduler/yaml_io.py`:

```python
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

    # erev must rank before the numbered days: it is the evening *before*
    # them. Sorting r.day as a plain string puts day_1..3 first, which
    # inverts this file's whole reason for existing.
    def _rank(rule: Rule) -> tuple:
        return (rule.profile, 0 if rule.day == EREV else int(rule.day), rule.time)

    for rule in sorted(rules, key=_rank):
        profile_key = f"{rule.profile}_day"
        day_key = _day_key(rule.day)
        entry: dict = {
            # Exported so a round trip preserves rule identity. Switch
            # entities derive their unique_id from it, and import replaces
            # the whole set - regenerating ids would orphan every entity.
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_yaml_io.py -v`
Expected: PASS, 4 tests

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler/yaml_io.py tests/test_yaml_io.py
git commit -m "feat: YAML import/export grouped by profile and day"
```

---

### Task 9: Engine — applying a rule

**Files:**
- Create: `custom_components/shabbat_scheduler/engine.py`
- Test: `tests/test_engine.py`

**Interfaces:**
- Consumes: `plan_calls`, `Call`, `Rule`, `Action`, `RuleStore`, `EVENT_RULE_APPLIED`, `RETRY_ATTEMPTS`, `RETRY_DELAY_SECONDS`.
- Produces: `ShabbatEngine` class with `async_apply_rule(rule: Rule, force: bool = False) -> list[dict]`, and `last_run: list[dict]`. Each result dict has keys `entity_id`, `attribute`, `outcome` (`"changed"` / `"ok"` / `"failed"` / `"skipped"`), `from`, `to`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_engine.py`:

```python
from datetime import time

import pytest

from custom_components.shabbat_scheduler.engine import ShabbatEngine
from custom_components.shabbat_scheduler.models import Action, Rule
from custom_components.shabbat_scheduler.store import RuleStore


@pytest.fixture
async def engine(hass, jerusalem, test_booleans):
    store = RuleStore(hass)
    await store.async_load()
    return ShabbatEngine(hass, store)


def _rule(action=Action.ON, devices=("input_boolean.t",), **kwargs):
    return Rule(
        id="r", profile=1, day="1", time=time(11, 0),
        action=action, devices=devices, **kwargs,
    )


async def test_apply_turns_on_an_input_boolean(hass, engine):
    hass.states.async_set("input_boolean.t", "off")
    results = await engine.async_apply_rule(_rule())
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.t").state == "on"
    assert results[0]["outcome"] == "changed"


async def test_apply_skips_when_already_correct(hass, engine):
    hass.states.async_set("input_boolean.t", "on")
    results = await engine.async_apply_rule(_rule())
    assert results[0]["outcome"] == "ok"


async def test_unknown_state_forces_apply(hass, engine):
    hass.states.async_set("input_boolean.t", "unknown")
    results = await engine.async_apply_rule(_rule())
    assert results[0]["outcome"] == "changed"


async def test_missing_entity_is_reported_not_raised(hass, engine):
    results = await engine.async_apply_rule(_rule(devices=("input_boolean.nope",)))
    assert results[0]["outcome"] == "failed"


async def test_dry_run_makes_no_service_calls(hass, jerusalem, test_booleans):
    store = RuleStore(hass)
    await store.async_load()
    await store.async_set_dry_run(True)
    engine = ShabbatEngine(hass, store)

    hass.states.async_set("input_boolean.t", "off")
    results = await engine.async_apply_rule(_rule())
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.t").state == "off"
    assert results[0]["outcome"] == "changed"  # reports what WOULD change


async def test_custom_rule_calls_its_script(hass, engine):
    calls = []

    async def record(call):
        calls.append(call)

    hass.services.async_register("script", "turn_on", record)
    await engine.async_apply_rule(
        _rule(action=Action.CUSTOM, devices=(), script="script.demo")
    )
    await hass.async_block_till_done()

    assert calls[0].data["entity_id"] == "script.demo"


async def test_last_run_is_recorded(hass, engine):
    hass.states.async_set("input_boolean.t", "off")
    await engine.async_apply_rule(_rule())
    assert engine.last_run
    assert engine.last_run[0]["entity_id"] == "input_boolean.t"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_engine.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'custom_components.shabbat_scheduler.engine'`

- [ ] **Step 3: Write minimal implementation**

Create `custom_components/shabbat_scheduler/engine.py`:

```python
"""Executes the decisions the pure modules make."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict, deque
from datetime import datetime

from homeassistant.core import Context, HomeAssistant
from homeassistant.util import dt as dt_util

from .const import EVENT_RULE_APPLIED
from .device_ops import plan_calls
from .models import Action, Rule
from .store import RuleStore

_LOGGER = logging.getLogger(__name__)

_UNTRUSTED_STATES = ("unknown", "unavailable")


class ShabbatEngine:
    """Applies rules idempotently, one device at a time."""

    def __init__(self, hass: HomeAssistant, store: RuleStore) -> None:
        self.hass = hass
        self.store = store
        self.last_run: list[dict] = []
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._last_command: dict[str, datetime] = {}

    async def async_apply_rule(self, rule: Rule, force: bool = False) -> list[dict]:
        """Apply one rule, returning a per-attribute outcome report."""
        if rule.action is Action.CUSTOM:
            results = await self._apply_custom(rule)
        else:
            results = []
            for entity_id in rule.devices:
                results.extend(await self._apply_device(rule, entity_id, force))

        self.last_run = results
        self.hass.bus.async_fire(
            EVENT_RULE_APPLIED, {"rule_id": rule.id, "results": results}
        )
        return results

    async def _apply_custom(self, rule: Rule) -> list[dict]:
        if not rule.script:
            return []
        if self.store.dry_run:
            return [
                {
                    "entity_id": rule.script, "attribute": "script",
                    "outcome": "changed", "from": None, "to": "run",
                }
            ]
        await self.hass.services.async_call(
            "script", "turn_on",
            {"entity_id": rule.script, "variables": dict(rule.variables)},
            blocking=True, context=self._new_context(),
        )
        return [
            {
                "entity_id": rule.script, "attribute": "script",
                "outcome": "changed", "from": None, "to": "run",
            }
        ]

    async def _apply_device(
        self, rule: Rule, entity_id: str, force: bool
    ) -> list[dict]:
        state = self.hass.states.get(entity_id)
        if state is None:
            _LOGGER.warning("%s: entity not found", entity_id)
            return [
                {
                    "entity_id": entity_id, "attribute": "state",
                    "outcome": "failed", "from": None, "to": None,
                }
            ]

        must_apply = force or state.state in _UNTRUSTED_STATES or self._is_stale(
            entity_id, state.last_updated
        )
        calls = plan_calls(
            entity_id, state.state, dict(state.attributes),
            rule.action, rule.settings, must_apply,
        )

        if not calls:
            return [
                {
                    "entity_id": entity_id, "attribute": "state",
                    "outcome": "ok", "from": state.state, "to": state.state,
                }
            ]

        results: list[dict] = []
        async with self._locks[entity_id]:
            for call in calls:
                results.append(await self._execute(entity_id, call))
        return results

    def _is_stale(self, entity_id: str, last_updated: datetime) -> bool:
        """True when the reading predates our own most recent command.

        The aux_cloud units lag several seconds on fan_mode, so a naive read
        would skip a command that never actually landed.
        """
        sent = self._last_command.get(entity_id)
        return sent is not None and last_updated < sent

    def _new_context(self) -> Context:
        return Context()

    async def _execute(self, entity_id: str, call) -> dict:
        result = {
            "entity_id": entity_id,
            "attribute": call.attribute,
            "from": call.from_value,
            "to": call.to_value,
        }

        if self.store.dry_run:
            result["outcome"] = "changed"
            return result

        data = {"entity_id": entity_id, **call.data}
        # Stamp BEFORE issuing: the entity's own last_updated is set during
        # the awaited call, so stamping afterwards would make every reading
        # look stale forever and force a re-apply on every pass - which is
        # exactly the re-assertion behaviour this design exists to avoid.
        # Stamping first also correctly forces on failure, since we cannot
        # know whether a failed call landed.
        self._last_command[entity_id] = dt_util.utcnow()
        try:
            await self.hass.services.async_call(
                call.domain, call.service, data,
                blocking=True, context=self._new_context(entity_id),
            )
        except Exception:  # noqa: BLE001 - one device must not abort the rest
            _LOGGER.exception("%s: %s.%s failed", entity_id, call.domain, call.service)
            result["outcome"] = "failed"
            return result

        result["outcome"] = "changed"
        return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_engine.py -v`
Expected: PASS, 7 tests

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler/engine.py tests/test_engine.py
git commit -m "feat: idempotent rule application with per-device locking"
```

---

### Task 10: Engine — retry on failure

**Files:**
- Modify: `custom_components/shabbat_scheduler/engine.py`
- Test: `tests/test_engine.py`

**Interfaces:**
- Consumes: `RETRY_ATTEMPTS`, `RETRY_DELAY_SECONDS`.
- Produces: `_execute` retries a failing call `RETRY_ATTEMPTS` times, `RETRY_DELAY_SECONDS` apart, then raises a `persistent_notification`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_engine.py`:

```python
from unittest.mock import patch


async def test_failed_call_is_retried_then_notified(hass, engine):
    # A bare `switch` entity: the switch component is not loaded, so the stub
    # service below is the only handler and can be made to fail on demand.
    hass.states.async_set("switch.t", "off")
    attempts = []

    async def always_fail(call):
        attempts.append(call)
        raise RuntimeError("boom")

    hass.services.async_register("switch", "turn_on", always_fail)

    rule = _rule(devices=("switch.t",))
    # Patch sleep so the test does not actually wait 60 seconds.
    with patch("custom_components.shabbat_scheduler.engine.asyncio.sleep"):
        results = await engine.async_apply_rule(rule)

    assert len(attempts) == 3
    assert results[0]["outcome"] == "failed"
    notifications = [
        state for state in hass.states.async_all()
        if state.entity_id.startswith("persistent_notification.")
    ]
    assert notifications


async def test_retry_succeeds_on_second_attempt(hass, engine):
    hass.states.async_set("switch.t", "off")
    attempts = []

    async def fail_once(call):
        attempts.append(call)
        if len(attempts) == 1:
            raise RuntimeError("transient")

    hass.services.async_register("switch", "turn_on", fail_once)

    with patch("custom_components.shabbat_scheduler.engine.asyncio.sleep"):
        results = await engine.async_apply_rule(_rule(devices=("switch.t",)))

    assert len(attempts) == 2
    assert results[0]["outcome"] == "changed"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_engine.py -k retry -v`
Expected: FAIL — only one attempt is made, `len(attempts) == 1`

- [ ] **Step 3: Write minimal implementation**

In `custom_components/shabbat_scheduler/engine.py`, add the import and replace `_execute`:

```python
from homeassistant.components import persistent_notification

from .const import EVENT_RULE_APPLIED, RETRY_ATTEMPTS, RETRY_DELAY_SECONDS
```

```python
    async def _execute(self, entity_id: str, call) -> dict:
        result = {
            "entity_id": entity_id,
            "attribute": call.attribute,
            "from": call.from_value,
            "to": call.to_value,
        }

        if self.store.dry_run:
            result["outcome"] = "changed"
            return result

        data = {"entity_id": entity_id, **call.data}
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            # Stamped before each attempt - see the note in Task 9. Stamping
            # after a successful call makes every later reading look stale.
            self._last_command[entity_id] = dt_util.utcnow()
            try:
                await self.hass.services.async_call(
                    call.domain, call.service, data,
                    blocking=True, context=self._new_context(entity_id),
                )
            except Exception:  # noqa: BLE001 - one device must not abort the rest
                _LOGGER.warning(
                    "%s: %s.%s failed (attempt %s/%s)",
                    entity_id, call.domain, call.service, attempt, RETRY_ATTEMPTS,
                )
                if attempt < RETRY_ATTEMPTS:
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
                    continue
                persistent_notification.async_create(
                    self.hass,
                    f"{entity_id}: {call.domain}.{call.service} failed after "
                    f"{RETRY_ATTEMPTS} attempts.",
                    title="Shabbat Scheduler",
                )
                result["outcome"] = "failed"
                return result

            result["outcome"] = "changed"
            return result

        result["outcome"] = "failed"
        return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_engine.py -v`
Expected: PASS, 9 tests

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler/engine.py tests/test_engine.py
git commit -m "feat: retry failed device commands then notify"
```

---

### Task 11: Engine — block detection and scheduling

**Files:**
- Modify: `custom_components/shabbat_scheduler/engine.py`
- Test: `tests/test_engine.py`

**Interfaces:**
- Consumes: `compute_block`, `resolve_rules`, `merge_defaults`, `has_profile`.
- Produces on `ShabbatEngine`:
  - `current_block` property (`Block | None`, cached across sensor outages).
  - `async_refresh() -> None` — recompute block from the jewish_calendar sensors, cancel old timers, schedule new ones, warn if no profile matches.
  - `upcoming() -> list[ResolvedRule]`.
  - Constants `CANDLE_SENSOR = "sensor.jewish_calendar_upcoming_candle_lighting"`, `HAVDALAH_SENSOR = "sensor.jewish_calendar_upcoming_havdalah"` in `const.py`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_engine.py`:

```python
from datetime import timedelta

from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.shabbat_scheduler.const import CANDLE_SENSOR, HAVDALAH_SENSOR


def _set_zmanim(hass, candle: str, havdalah: str):
    hass.states.async_set(CANDLE_SENSOR, candle)
    hass.states.async_set(HAVDALAH_SENSOR, havdalah)


async def test_refresh_computes_the_block(hass, engine):
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.async_refresh()
    assert engine.current_block.length == 1


async def test_missing_sensor_keeps_the_cached_block(hass, engine):
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.async_refresh()

    hass.states.async_remove(CANDLE_SENSOR)
    await engine.async_refresh()
    assert engine.current_block is not None  # cached, not wiped


async def test_no_matching_profile_notifies(hass, engine):
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    # The master must be on, otherwise refresh returns before the check.
    await engine.store.async_set_enabled(True)
    await engine.store.async_add(
        Rule(id="r", profile=3, day="1", time=time(11, 0), action=Action.ON)
    )
    await engine.async_refresh()

    assert engine.upcoming() == []
    notifications = [
        state for state in hass.states.async_all()
        if state.entity_id.startswith("persistent_notification.")
    ]
    assert notifications


async def test_disabled_master_schedules_nothing(hass, engine):
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_add(
        Rule(id="r", profile=1, day="1", time=time(11, 0),
             action=Action.ON, devices=("input_boolean.t",))
    )
    await engine.async_refresh()  # master defaults OFF
    assert engine.upcoming() == []


async def test_enabled_master_lists_upcoming_rules(hass, engine):
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    await engine.store.async_add(
        Rule(id="r", profile=1, day="1", time=time(11, 0),
             action=Action.ON, devices=("input_boolean.t",))
    )
    await engine.async_refresh()
    assert [item.rule.id for item in engine.upcoming()] == ["r"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_engine.py -k refresh -v`
Expected: FAIL with `ImportError: cannot import name 'CANDLE_SENSOR'`

- [ ] **Step 3: Write minimal implementation**

Add to `custom_components/shabbat_scheduler/const.py`:

```python
CANDLE_SENSOR = "sensor.jewish_calendar_upcoming_candle_lighting"
HAVDALAH_SENSOR = "sensor.jewish_calendar_upcoming_havdalah"
```

Add to `custom_components/shabbat_scheduler/engine.py`:

```python
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.util import dt as dt_util

from .block import compute_block, has_profile, merge_defaults, resolve_rules
from .const import CANDLE_SENSOR, HAVDALAH_SENSOR
from .models import Block, ResolvedRule
```

Extend `__init__` with:

```python
        self._block: Block | None = None
        self._unsubscribes: list = []
        self._upcoming: list[ResolvedRule] = []
```

Then add:

```python
    @property
    def current_block(self) -> Block | None:
        return self._block

    def upcoming(self) -> list[ResolvedRule]:
        return list(self._upcoming)

    def _read_zmanim(self) -> tuple[datetime, datetime] | None:
        candle = self.hass.states.get(CANDLE_SENSOR)
        havdalah = self.hass.states.get(HAVDALAH_SENSOR)
        if candle is None or havdalah is None:
            return None
        start = dt_util.parse_datetime(candle.state)
        end = dt_util.parse_datetime(havdalah.state)
        if start is None or end is None:
            return None
        return start, end

    async def async_refresh(self) -> None:
        """Recompute the block and rebuild every timer."""
        for cancel in self._unsubscribes:
            cancel()
        self._unsubscribes = []
        self._upcoming = []

        zmanim = self._read_zmanim()
        if zmanim is not None:
            try:
                # Cache survives a jewish_calendar outage so the schedule is
                # never silently wiped.
                self._block = compute_block(*zmanim)
            except ValueError:
                # Loud silence: refusing to act is safe, doing it quietly is
                # not. This mirrors the missing-profile notification below.
                _LOGGER.warning("Ignoring implausible zmanim pair %s", zmanim)
                persistent_notification.async_create(
                    self.hass,
                    "Candle lighting and havdalah do not form a valid period, "
                    "so the Shabbat schedule is not running. Check "
                    f"{CANDLE_SENSOR} and {HAVDALAH_SENSOR}.",
                    title="Shabbat Scheduler",
                )

        if self._block is None or not self.store.enabled:
            return

        rules = [merge_defaults(self.store.defaults, r) for r in self.store.rules]

        if not has_profile(rules, self._block.length):
            persistent_notification.async_create(
                self.hass,
                f"No rules are configured for a {self._block.length}-day block; "
                "nothing will run.",
                title="Shabbat Scheduler",
            )
            return

        tz = dt_util.get_time_zone(self.hass.config.time_zone)
        now = dt_util.now()
        self._upcoming = [
            item for item in resolve_rules(rules, self._block, tz) if item.when > now
        ]

        for item in self._upcoming:
            self._unsubscribes.append(
                async_track_point_in_time(
                    self.hass, self._make_callback(item), item.when
                )
            )

    def _make_callback(self, item: ResolvedRule):
        async def _fire(_now) -> None:
            await self.async_apply_rule(item.rule)

        return _fire
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_engine.py -v`
Expected: PASS, 14 tests

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler/const.py custom_components/shabbat_scheduler/engine.py tests/test_engine.py
git commit -m "feat: derive block from zmanim and schedule rule timers"
```

---

### Task 12: Engine — restart catch-up

**Files:**
- Modify: `custom_components/shabbat_scheduler/engine.py`
- Test: `tests/test_engine.py`

**Interfaces:**
- Consumes: `desired_state_at`.
- Produces: `async_catch_up() -> list[dict]` on `ShabbatEngine`. Applies, per device, only the single most recent already-passed rule, idempotently. Skips `custom` rules unless `replay_on_restart`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_engine.py`:

```python
from freezegun import freeze_time


async def test_catch_up_applies_the_last_passed_rule(hass, engine):
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    hass.states.async_set("input_boolean.t", "off")
    await engine.store.async_replace_all({}, [
        Rule(id="on", profile=1, day="1", time=time(11, 0),
             action=Action.ON, devices=("input_boolean.t",)),
        Rule(id="off", profile=1, day="1", time=time(18, 0),
             action=Action.OFF, devices=("input_boolean.t",)),
    ])

    # 11:30 local - the 11:00 ON has passed, 18:00 OFF has not.
    with freeze_time("2026-08-15T08:30:00+00:00"):
        results = await engine.async_catch_up()
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.t").state == "on"
    assert [r["outcome"] for r in results] == ["changed"]


async def test_catch_up_before_any_rule_does_nothing(hass, engine):
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    hass.states.async_set("input_boolean.t", "off")
    await engine.store.async_replace_all({}, [
        Rule(id="on", profile=1, day="1", time=time(11, 0),
             action=Action.ON, devices=("input_boolean.t",)),
    ])

    with freeze_time("2026-08-15T06:00:00+00:00"):  # 09:00 local
        assert await engine.async_catch_up() == []


async def test_catch_up_skips_custom_rules_by_default(hass, engine):
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    calls = []

    async def record(call):
        calls.append(call)

    hass.services.async_register("script", "turn_on", record)
    await engine.store.async_replace_all({}, [
        Rule(id="c", profile=1, day="1", time=time(11, 0),
             action=Action.CUSTOM, script="script.demo"),
    ])

    with freeze_time("2026-08-15T08:30:00+00:00"):
        await engine.async_catch_up()
    await hass.async_block_till_done()
    assert calls == []
```

Add the test-only dependency:

```bash
uv add --dev freezegun
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_engine.py -k catch_up -v`
Expected: FAIL with `AttributeError: 'ShabbatEngine' object has no attribute 'async_catch_up'`

- [ ] **Step 3: Write minimal implementation**

Add to `custom_components/shabbat_scheduler/engine.py`:

```python
from .block import desired_state_at
from .models import Conflict
```

```python
    async def async_catch_up(self) -> list[dict]:
        """Re-apply the current desired state after a restart.

        Only the most recent already-passed rule per device is applied, and
        because application is idempotent this is safe to repeat.
        """
        if self._block is None or not self.store.enabled:
            return []

        tz = dt_util.get_time_zone(self.hass.config.time_zone)
        now = dt_util.now()
        rules = [merge_defaults(self.store.defaults, r) for r in self.store.rules]

        devices = {device for rule in rules for device in rule.devices}
        results: list[dict] = []

        for device in sorted(devices):
            wanted = desired_state_at(rules, self._block, now, device, tz)
            if wanted is None:
                continue
            if isinstance(wanted, Conflict):
                _LOGGER.warning(
                    "%s: ambiguous desired state (rules %s); not acting",
                    device, ", ".join(wanted.rule_ids),
                )
                continue
            results.extend(await self._apply_device(wanted, device, force=False))

        # Custom rules are excluded above because desired_state_at ignores
        # them; replay them only where explicitly opted in.
        for rule in rules:
            if rule.action is Action.CUSTOM and rule.replay_on_restart:
                results.extend(await self._apply_custom(rule))

        self.last_run = results
        return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_engine.py -v`
Expected: PASS, 17 tests

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler/engine.py tests/test_engine.py pyproject.toml uv.lock
git commit -m "feat: restart catch-up applies current desired state idempotently"
```

---

### Task 13: Integration setup and switch entities

Setup and switches ship together because neither is testable without the other:
platforms cannot load without a config entry, and an entry that forwards no
platforms proves nothing.

**Files:**
- Create: `custom_components/shabbat_scheduler/manifest.json`
- Create: `custom_components/shabbat_scheduler/config_flow.py`
- Modify: `custom_components/shabbat_scheduler/__init__.py`
- Modify: `custom_components/shabbat_scheduler/engine.py` (add `async_shutdown`)
- Create: `custom_components/shabbat_scheduler/switch.py`
- Test: `tests/test_entities.py`

**Interfaces:**
- Consumes: `RuleStore`, `ShabbatEngine`, `DOMAIN`, `CANDLE_SENSOR`, `HAVDALAH_SENSOR`.
- Produces:
  - `async_setup_entry(hass, entry)` in `__init__.py`, populating `hass.data[DOMAIN][entry.entry_id] = {"store": …, "engine": …}`, forwarding `PLATFORMS = [Platform.SWITCH]`, running `async_refresh()` then `async_catch_up()` once, and re-refreshing when the zmanim sensors change.
  - `ShabbatEngine.async_shutdown()` cancelling every pending timer.
  - Single-instance config flow aborting with `single_instance_allowed`.
  - `switch.async_setup_entry` creating `MasterSwitch` (unique id `f"{entry.entry_id}_master"`) and one `RuleSwitch` per rule (unique id `f"{entry.entry_id}_rule_{rule.id}"`). Toggling either persists via the store and calls `engine.async_refresh()`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_entities.py`:

```python
from datetime import time

from homeassistant.const import STATE_OFF, STATE_ON
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shabbat_scheduler.const import DOMAIN
from custom_components.shabbat_scheduler.models import Action, Rule
from custom_components.shabbat_scheduler.store import RuleStore


async def _setup(hass, rules=()):
    await hass.config.async_set_time_zone("Asia/Jerusalem")
    store = RuleStore(hass)
    await store.async_load()
    for rule in rules:
        await store.async_add(rule)

    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_entry_sets_up_and_unloads(hass):
    entry = await _setup(hass)
    assert entry.entry_id in hass.data[DOMAIN]

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.entry_id not in hass.data[DOMAIN]


async def test_only_one_instance_allowed(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == "create_entry"

    second = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert second["type"] == "abort"
    assert second["reason"] == "single_instance_allowed"


async def test_master_switch_defaults_off(hass):
    await _setup(hass)
    state = hass.states.get("switch.shabbat_scheduler")
    assert state is not None
    assert state.state == STATE_OFF


async def test_master_switch_turns_on_and_persists(hass):
    await _setup(hass)
    await hass.services.async_call(
        "switch", "turn_on",
        {"entity_id": "switch.shabbat_scheduler"}, blocking=True,
    )
    assert hass.states.get("switch.shabbat_scheduler").state == STATE_ON

    reloaded = RuleStore(hass)
    await reloaded.async_load()
    assert reloaded.enabled is True


async def test_one_switch_per_rule(hass):
    await _setup(hass, [
        Rule(id="r1", profile=1, day="1", time=time(11, 0),
             action=Action.ON, name="בוקר שבת"),
    ])
    matching = [
        state.entity_id for state in hass.states.async_all()
        if state.entity_id.startswith("switch.") and "r1" in state.entity_id
    ]
    assert matching


async def test_rule_switch_toggle_persists(hass):
    await _setup(hass, [
        Rule(id="r1", profile=1, day="1", time=time(11, 0), action=Action.ON),
    ])
    entity_id = next(
        state.entity_id for state in hass.states.async_all()
        if state.entity_id.startswith("switch.") and "r1" in state.entity_id
    )
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": entity_id}, blocking=True
    )

    reloaded = RuleStore(hass)
    await reloaded.async_load()
    assert reloaded.rules[0].enabled is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_entities.py -v`
Expected: FAIL — the integration cannot be set up yet (no `manifest.json` / `async_setup_entry`)

- [ ] **Step 3: Write the integration setup**

Create `custom_components/shabbat_scheduler/manifest.json`:

```json
{
  "domain": "shabbat_scheduler",
  "name": "Shabbat Scheduler",
  "codeowners": [],
  "config_flow": true,
  "documentation": "https://github.com/elazarcoh/ha-shabbat-scheduler",
  "iot_class": "local_push",
  "requirements": ["pyyaml"],
  "version": "0.1.0"
}
```

Create `custom_components/shabbat_scheduler/config_flow.py`:

```python
"""Single-instance config flow - all configuration lives in the rule store."""

from __future__ import annotations

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN


class ShabbatSchedulerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Nothing to ask for; the integration is configured through its rules."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        return self.async_create_entry(title="Shabbat Scheduler", data={})
```

Add to `ShabbatEngine` in `custom_components/shabbat_scheduler/engine.py`:

```python
    async def async_shutdown(self) -> None:
        """Cancel every pending timer."""
        for cancel in self._unsubscribes:
            cancel()
        self._unsubscribes = []
```

Replace `custom_components/shabbat_scheduler/__init__.py`:

```python
"""Shabbat Scheduler integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_state_change_event

from .const import CANDLE_SENSOR, DOMAIN, HAVDALAH_SENSOR
from .engine import ShabbatEngine
from .store import RuleStore

PLATFORMS = [Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    store = RuleStore(hass)
    await store.async_load()
    engine = ShabbatEngine(hass, store)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "store": store,
        "engine": engine,
    }

    await engine.async_refresh()
    # Re-apply the current desired state after a restart, so a reboot part-way
    # through a block does not leave devices stranded.
    await engine.async_catch_up()

    async def _zmanim_changed(_event) -> None:
        await engine.async_refresh()

    entry.async_on_unload(
        async_track_state_change_event(
            hass, [CANDLE_SENSOR, HAVDALAH_SENSOR], _zmanim_changed
        )
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        await data["engine"].async_shutdown()
    return unloaded
```

Create `custom_components/shabbat_scheduler/switch.py`:

```python
"""Master switch plus one switch per rule.

Per-rule switches exist so the integration is fully usable with native
entities/tile cards before any custom card ships.
"""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .engine import ShabbatEngine
from .models import Rule
from .store import RuleStore


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    store: RuleStore = data["store"]
    engine: ShabbatEngine = data["engine"]

    entities: list[SwitchEntity] = [MasterSwitch(entry, store, engine)]
    entities.extend(RuleSwitch(entry, store, engine, rule) for rule in store.rules)
    async_add_entities(entities)


class MasterSwitch(SwitchEntity):
    """Enables or disables the whole flow."""

    _attr_has_entity_name = False
    _attr_name = "Shabbat Scheduler"
    _attr_icon = "mdi:candle"

    def __init__(
        self, entry: ConfigEntry, store: RuleStore, engine: ShabbatEngine
    ) -> None:
        self._store = store
        self._engine = engine
        self._attr_unique_id = f"{entry.entry_id}_master"

    @property
    def is_on(self) -> bool:
        return self._store.enabled

    async def async_turn_on(self, **kwargs) -> None:
        await self._store.async_set_enabled(True)
        await self._engine.async_refresh()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        await self._store.async_set_enabled(False)
        await self._engine.async_refresh()
        self.async_write_ha_state()


class RuleSwitch(SwitchEntity):
    """Enables or disables a single rule."""

    _attr_has_entity_name = False

    def __init__(
        self,
        entry: ConfigEntry,
        store: RuleStore,
        engine: ShabbatEngine,
        rule: Rule,
    ) -> None:
        self._store = store
        self._engine = engine
        self._rule_id = rule.id
        self._attr_unique_id = f"{entry.entry_id}_rule_{rule.id}"
        self._attr_name = rule.name or (
            f"{rule.profile}d {rule.day} {rule.time.strftime('%H:%M')} "
            f"{rule.action.value}"
        )
        self._attr_icon = rule.icon or (
            "mdi:power-plug" if rule.action.value == "on" else "mdi:power-plug-off"
        )

    def _current(self) -> Rule | None:
        return next(
            (rule for rule in self._store.rules if rule.id == self._rule_id), None
        )

    @property
    def is_on(self) -> bool:
        rule = self._current()
        return bool(rule and rule.enabled)

    @property
    def extra_state_attributes(self) -> dict:
        rule = self._current()
        if rule is None:
            return {}
        return {
            "profile": rule.profile,
            "day": rule.day,
            "time": rule.time.isoformat(),
            "action": rule.action.value,
            "devices": list(rule.devices),
        }

    async def async_turn_on(self, **kwargs) -> None:
        await self._store.async_update(self._rule_id, enabled=True)
        await self._engine.async_refresh()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        await self._store.async_update(self._rule_id, enabled=False)
        await self._engine.async_refresh()
        self.async_write_ha_state()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_entities.py -v`
Expected: PASS, 6 tests

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler tests/test_entities.py
git commit -m "feat: config entry setup, master switch and per-rule switches"
```

---

### Task 14: Sensor entities

**Files:**
- Create: `custom_components/shabbat_scheduler/sensor.py`
- Modify: `custom_components/shabbat_scheduler/__init__.py` (add `Platform.SENSOR`)
- Test: `tests/test_entities.py`

**Interfaces:**
- Consumes: `ShabbatEngine`.
- Produces: `sensor.async_setup_entry` creating `NextBlockSensor` (state = block length or `unknown`), `NextActionSensor` (state = ISO datetime of next fire or `unknown`), `LastRunSensor` (state = count of results, attribute `results`).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_entities.py`:

```python
async def test_next_block_sensor_reports_length(hass):
    hass.states.async_set(
        "sensor.jewish_calendar_upcoming_candle_lighting",
        "2026-08-14T15:44:00+00:00",
    )
    hass.states.async_set(
        "sensor.jewish_calendar_upcoming_havdalah", "2026-08-15T17:01:00+00:00"
    )
    await _setup(hass)
    state = hass.states.get("sensor.shabbat_scheduler_next_block")
    assert state is not None
    assert state.state == "1"


async def test_next_action_sensor_unknown_when_master_off(hass):
    hass.states.async_set(
        "sensor.jewish_calendar_upcoming_candle_lighting",
        "2026-08-14T15:44:00+00:00",
    )
    hass.states.async_set(
        "sensor.jewish_calendar_upcoming_havdalah", "2026-08-15T17:01:00+00:00"
    )
    await _setup(hass, [
        Rule(id="r1", profile=1, day="1", time=time(11, 0), action=Action.ON),
    ])
    assert hass.states.get("sensor.shabbat_scheduler_next_action").state == "unknown"


async def test_last_run_sensor_exists(hass):
    await _setup(hass)
    assert hass.states.get("sensor.shabbat_scheduler_last_run") is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_entities.py -k sensor -v`
Expected: FAIL — sensors do not exist

- [ ] **Step 3: Write minimal implementation**

Create `custom_components/shabbat_scheduler/sensor.py`:

```python
"""Diagnostic sensors: what block is next, what fires next, what last ran."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .engine import ShabbatEngine


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    engine: ShabbatEngine = hass.data[DOMAIN][entry.entry_id]["engine"]
    async_add_entities(
        [
            NextBlockSensor(entry, engine),
            NextActionSensor(entry, engine),
            LastRunSensor(entry, engine),
        ]
    )


class _Base(SensorEntity):
    _attr_has_entity_name = False

    def __init__(self, entry: ConfigEntry, engine: ShabbatEngine, key: str) -> None:
        self._engine = engine
        self._attr_unique_id = f"{entry.entry_id}_{key}"


class NextBlockSensor(_Base):
    _attr_name = "Shabbat Scheduler Next Block"
    _attr_icon = "mdi:calendar-range"

    def __init__(self, entry: ConfigEntry, engine: ShabbatEngine) -> None:
        super().__init__(entry, engine, "next_block")

    @property
    def native_value(self):
        block = self._engine.current_block
        return block.length if block else None

    @property
    def extra_state_attributes(self) -> dict:
        block = self._engine.current_block
        if block is None:
            return {}
        return {
            "candle_lighting": block.candle_lighting.isoformat(),
            "havdalah": block.havdalah.isoformat(),
            "erev_date": block.erev_date.isoformat(),
            "day_dates": [day.isoformat() for day in block.day_dates],
        }


class NextActionSensor(_Base):
    _attr_name = "Shabbat Scheduler Next Action"
    _attr_icon = "mdi:clock-outline"

    def __init__(self, entry: ConfigEntry, engine: ShabbatEngine) -> None:
        super().__init__(entry, engine, "next_action")

    @property
    def native_value(self):
        upcoming = self._engine.upcoming()
        return upcoming[0].when.isoformat() if upcoming else None

    @property
    def extra_state_attributes(self) -> dict:
        upcoming = self._engine.upcoming()
        if not upcoming:
            return {}
        item = upcoming[0]
        return {
            "rule_id": item.rule.id,
            "name": item.rule.name,
            "action": item.rule.action.value,
            "devices": list(item.rule.devices),
        }


class LastRunSensor(_Base):
    _attr_name = "Shabbat Scheduler Last Run"
    _attr_icon = "mdi:history"

    def __init__(self, entry: ConfigEntry, engine: ShabbatEngine) -> None:
        super().__init__(entry, engine, "last_run")

    @property
    def native_value(self):
        return len(self._engine.last_run)

    @property
    def extra_state_attributes(self) -> dict:
        return {"results": self._engine.last_run}
```

Then in `custom_components/shabbat_scheduler/__init__.py`, change:

```python
PLATFORMS = [Platform.SWITCH]
```

to:

```python
PLATFORMS = [Platform.SWITCH, Platform.SENSOR]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_entities.py -v`
Expected: PASS, 9 tests

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler tests/test_entities.py
git commit -m "feat: next-block, next-action and last-run sensors"
```

---

### Task 15: Services — simulate, dry-run toggle, YAML import/export

**Files:**
- Create: `custom_components/shabbat_scheduler/services.yaml`
- Modify: `custom_components/shabbat_scheduler/__init__.py`
- Test: `tests/test_services.py`

**Interfaces:**
- Consumes: `compute_block`, `resolve_rules`, `merge_defaults`, `find_conflicts`, `export_yaml`, `import_yaml`.
- Produces four services, all returning a response where noted:
  - `shabbat_scheduler.simulate` (`{block_length}` optional) → `{profile, rules: [...], conflicts: [...], warnings: [...]}`
  - `shabbat_scheduler.set_dry_run` (`{enabled: bool}`)
  - `shabbat_scheduler.export_yaml` → `{yaml: str}`
  - `shabbat_scheduler.import_yaml` (`{yaml: str}`)

- [ ] **Step 1: Write the failing test**

Create `tests/test_services.py`:

```python
from datetime import time

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shabbat_scheduler.const import DOMAIN
from custom_components.shabbat_scheduler.models import Action, Rule
from custom_components.shabbat_scheduler.store import RuleStore


async def _setup(hass, rules=()):
    await hass.config.async_set_time_zone("Asia/Jerusalem")
    store = RuleStore(hass)
    await store.async_load()
    if rules:
        await store.async_replace_all({}, list(rules))
    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_simulate_returns_resolved_rules(hass):
    hass.states.async_set(
        "sensor.jewish_calendar_upcoming_candle_lighting",
        "2026-08-14T15:44:00+00:00",
    )
    hass.states.async_set(
        "sensor.jewish_calendar_upcoming_havdalah", "2026-08-15T17:01:00+00:00"
    )
    await _setup(hass, [
        Rule(id="r1", profile=1, day="1", time=time(11, 0),
             action=Action.ON, devices=("climate.a",)),
    ])

    response = await hass.services.async_call(
        DOMAIN, "simulate", {}, blocking=True, return_response=True
    )
    assert response["profile"] == 1
    assert len(response["rules"]) == 1
    assert response["rules"][0]["action"] == "on"


async def test_simulate_reports_conflicts(hass):
    hass.states.async_set(
        "sensor.jewish_calendar_upcoming_candle_lighting",
        "2026-08-14T15:44:00+00:00",
    )
    hass.states.async_set(
        "sensor.jewish_calendar_upcoming_havdalah", "2026-08-15T17:01:00+00:00"
    )
    await _setup(hass, [
        Rule(id="a", profile=1, day="1", time=time(18, 0),
             action=Action.ON, devices=("climate.a",)),
        Rule(id="b", profile=1, day="1", time=time(18, 0),
             action=Action.OFF, devices=("climate.a",)),
    ])

    response = await hass.services.async_call(
        DOMAIN, "simulate", {}, blocking=True, return_response=True
    )
    assert len(response["conflicts"]) == 1


async def test_simulate_warns_when_profile_missing(hass):
    hass.states.async_set(
        "sensor.jewish_calendar_upcoming_candle_lighting",
        "2026-08-14T15:44:00+00:00",
    )
    hass.states.async_set(
        "sensor.jewish_calendar_upcoming_havdalah", "2026-08-15T17:01:00+00:00"
    )
    await _setup(hass, [
        Rule(id="r1", profile=3, day="1", time=time(11, 0), action=Action.ON),
    ])

    response = await hass.services.async_call(
        DOMAIN, "simulate", {}, blocking=True, return_response=True
    )
    assert response["warnings"]


async def test_set_dry_run(hass):
    await _setup(hass)
    await hass.services.async_call(
        DOMAIN, "set_dry_run", {"enabled": True}, blocking=True
    )
    store = RuleStore(hass)
    await store.async_load()
    assert store.dry_run is True


async def test_yaml_export_then_import(hass):
    await _setup(hass, [
        Rule(id="r1", profile=1, day="1", time=time(11, 0),
             action=Action.ON, devices=("climate.a",)),
    ])
    exported = await hass.services.async_call(
        DOMAIN, "export_yaml", {}, blocking=True, return_response=True
    )
    assert "profiles" in exported["yaml"]

    await hass.services.async_call(
        DOMAIN, "import_yaml", {"yaml": exported["yaml"]}, blocking=True
    )
    store = RuleStore(hass)
    await store.async_load()
    assert len(store.rules) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_services.py -v`
Expected: FAIL with `ServiceNotFound: shabbat_scheduler.simulate`

- [ ] **Step 3: Write minimal implementation**

Create `custom_components/shabbat_scheduler/services.yaml`:

```yaml
simulate:
  name: Simulate
  description: >-
    Resolve the schedule for a block without side effects. Answers "what will
    happen this Shabbat?" and "what happens on a 3-day chag?".
  fields:
    block_length:
      name: Block length
      description: Days to simulate. Defaults to the upcoming block.
      required: false
      selector:
        number:
          min: 1
          max: 3

set_dry_run:
  name: Set dry run
  description: >-
    When enabled, rules report what they would change but call no services.
  fields:
    enabled:
      name: Enabled
      required: true
      selector:
        boolean:

export_yaml:
  name: Export YAML
  description: Return the whole rule set as YAML.

import_yaml:
  name: Import YAML
  description: Replace the whole rule set from YAML.
  fields:
    yaml:
      name: YAML
      required: true
      selector:
        text:
          multiline: true
```

Add to `custom_components/shabbat_scheduler/__init__.py`:

```python
import voluptuous as vol
from homeassistant.core import ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.util import dt as dt_util

from .block import compute_block, find_conflicts, has_profile, merge_defaults, resolve_rules
from .yaml_io import export_yaml, import_yaml
```

Then, inside `async_setup_entry` before forwarding platforms:

```python
    async def _simulate(call: ServiceCall) -> ServiceResponse:
        block = engine.current_block
        length = call.data.get("block_length")
        if length is not None and block is not None:
            # Re-derive a hypothetical block of the requested length.
            block = compute_block(
                block.candle_lighting,
                block.candle_lighting.replace(hour=20, minute=0)
                + timedelta(days=int(length)),
            )
        if block is None:
            return {"profile": None, "rules": [], "conflicts": [], "warnings": [
                "No block could be derived; is the Jewish Calendar integration set up?"
            ]}

        rules = [merge_defaults(store.defaults, r) for r in store.rules]
        warnings: list[str] = []
        if not has_profile(rules, block.length):
            warnings.append(
                f"No rules configured for a {block.length}-day block."
            )

        tz = dt_util.get_time_zone(hass.config.time_zone)
        resolved = resolve_rules(rules, block, tz)
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
                for item in resolved
            ],
            "conflicts": [
                {
                    "device": conflict.device,
                    "time": conflict.time.isoformat(),
                    "day": conflict.day,
                    "rule_ids": list(conflict.rule_ids),
                }
                for conflict in find_conflicts(rules)
            ],
            "warnings": warnings,
        }

    async def _set_dry_run(call: ServiceCall) -> None:
        await store.async_set_dry_run(bool(call.data["enabled"]))

    async def _export_yaml(_call: ServiceCall) -> ServiceResponse:
        return {"yaml": export_yaml(store.defaults, store.rules)}

    async def _import_yaml(call: ServiceCall) -> None:
        defaults, rules = import_yaml(call.data["yaml"])
        await store.async_replace_all(defaults, rules)
        await engine.async_refresh()

    hass.services.async_register(
        DOMAIN, "simulate", _simulate,
        schema=vol.Schema({vol.Optional("block_length"): vol.All(int, vol.Range(1, 3))}),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN, "set_dry_run", _set_dry_run,
        schema=vol.Schema({vol.Required("enabled"): bool}),
    )
    hass.services.async_register(
        DOMAIN, "export_yaml", _export_yaml,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN, "import_yaml", _import_yaml,
        schema=vol.Schema({vol.Required("yaml"): str}),
    )
```

Add `from datetime import timedelta` to the imports.

- [ ] **Step 4: Run all tests to verify they pass**

Run: `uv run pytest -v`
Expected: PASS, all tests

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler tests/test_services.py
git commit -m "feat: simulate, dry-run toggle and YAML import/export services"
```

---

### Task 16: End-to-end verification against test booleans

**Files:**
- Test: `tests/test_end_to_end.py`

**Interfaces:**
- Consumes: everything above.
- Produces: no production code — a single test proving a full block runs correctly from timers, against `input_boolean` entities rather than real appliances.

- [ ] **Step 1: Write the failing test**

Create `tests/test_end_to_end.py`:

```python
from datetime import time

from freezegun import freeze_time
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.shabbat_scheduler.const import DOMAIN
from custom_components.shabbat_scheduler.models import Action, Rule
from custom_components.shabbat_scheduler.store import RuleStore


async def test_full_one_day_block_drives_test_booleans(hass, jerusalem, test_booleans):
    hass.states.async_set(
        "sensor.jewish_calendar_upcoming_candle_lighting",
        "2026-08-14T15:44:00+00:00",
    )
    hass.states.async_set(
        "sensor.jewish_calendar_upcoming_havdalah", "2026-08-15T17:01:00+00:00"
    )
    hass.states.async_set("input_boolean.salon", "off")

    store = RuleStore(hass)
    await store.async_load()
    await store.async_replace_all({"devices": ["input_boolean.salon"]}, [
        Rule(id="on", profile=1, day="1", time=time(11, 0), action=Action.ON),
        Rule(id="off", profile=1, day="1", time=time(18, 0), action=Action.OFF),
    ])
    await store.async_set_enabled(True)

    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)

    # Start the clock before the first rule so both timers are still pending.
    with freeze_time("2026-08-15T05:00:00+00:00"):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        engine = hass.data[DOMAIN][entry.entry_id]["engine"]
        assert [item.rule.id for item in engine.upcoming()] == ["on", "off"]

    # 11:00 local
    async_fire_time_changed(hass, dt_util.parse_datetime("2026-08-15T08:00:00+00:00"))
    await hass.async_block_till_done()
    assert hass.states.get("input_boolean.salon").state == "on"

    # 18:00 local
    async_fire_time_changed(hass, dt_util.parse_datetime("2026-08-15T15:00:00+00:00"))
    await hass.async_block_till_done()
    assert hass.states.get("input_boolean.salon").state == "off"


async def test_manual_change_is_not_reverted(hass, jerusalem, test_booleans):
    """Fire-once means the plugin must never fight a manual override."""
    hass.states.async_set(
        "sensor.jewish_calendar_upcoming_candle_lighting",
        "2026-08-14T15:44:00+00:00",
    )
    hass.states.async_set(
        "sensor.jewish_calendar_upcoming_havdalah", "2026-08-15T17:01:00+00:00"
    )
    hass.states.async_set("input_boolean.salon", "off")

    store = RuleStore(hass)
    await store.async_load()
    await store.async_replace_all({"devices": ["input_boolean.salon"]}, [
        Rule(id="on", profile=1, day="1", time=time(11, 0), action=Action.ON),
    ])
    await store.async_set_enabled(True)

    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    with freeze_time("2026-08-15T05:00:00+00:00"):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    async_fire_time_changed(hass, dt_util.parse_datetime("2026-08-15T08:00:00+00:00"))
    await hass.async_block_till_done()
    assert hass.states.get("input_boolean.salon").state == "on"

    # User turns it off by hand five minutes later.
    hass.states.async_set("input_boolean.salon", "off")
    async_fire_time_changed(hass, dt_util.parse_datetime("2026-08-15T08:30:00+00:00"))
    await hass.async_block_till_done()
    assert hass.states.get("input_boolean.salon").state == "off"
```

- [ ] **Step 2: Run test to verify it fails or passes**

Run: `uv run pytest tests/test_end_to_end.py -v`
Expected: PASS if every earlier task is correct. If it fails, the failure identifies which layer is wrong — fix that layer's unit test first, not this one.

- [ ] **Step 3: Run the whole suite**

Run: `uv run pytest -v`
Expected: PASS, all tests

- [ ] **Step 4: Commit**

```bash
git add tests/test_end_to_end.py
git commit -m "test: end-to-end block execution against test booleans"
```

---

## Deferred to Plan 2

- Websocket API (`rules/list|create|update|delete|reorder`, `preview`, `validate`).
- The custom Lovelace card.
- Device/entity-existence validation warnings surfaced in the UI.

## Deployment notes

Deployment is **not** part of this plan and must not be attempted during it. All
work above runs locally under `pytest` on the Pi and needs no Home Assistant
access.

When the plan is complete, installing on the live instance requires copying
`id_ed25519_ha_deploy` to the Pi so `ssh ha` works, then placing
`custom_components/shabbat_scheduler/` into `/config/`. Per the spec's rollout,
the master switch defaults to OFF, so installation alone cannot affect any
appliance, and the seven existing automations stay untouched.
