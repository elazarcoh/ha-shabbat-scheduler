# Shabbat Scheduler v2 — The Model (Plan 1 of 3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the climate-shaped rule model with a generic one — a rule is a Home Assistant service call with an optional condition and an opt-in replay — so the integration decides *when* and Home Assistant decides *what*.

**Architecture:** A rule carries `action`, `target`, `data`, `condition` and `replay`. Execution hands the call to HA's own `async_call_from_config`, with exactly one documented climate compatibility shim. Conditions use HA's condition engine. Structural validation stays in the pure core; HA-schema validation lives in a new HA-facing module. Storage migrates v1 → v2.

**Tech Stack:** Python 3.14, Home Assistant 2026.8.2, `pytest-homeassistant-custom-component`. TypeScript/Lit only where the card would otherwise break.

**Spec:** `docs/superpowers/specs/2026-08-22-shabbat-scheduler-v2-alpha-design.md`

## Global Constraints

- **The integration owns *when*; Home Assistant owns *what*.** Any domain knowledge must justify itself as a compatibility shim, be documented as one, and be narrow. Exactly one is authorised by this plan: the climate `hvac_mode` split.
- **Fire once, never re-assert.** Unchanged and non-negotiable.
- **A rule that does not fire must say why** — blocked by condition, skipped as too stale, or failed. Each is visible in the logbook and in the rule's results. A rule that silently does nothing is the failure this project exists to prevent.
- **Conflicts are warned, never resolved.**
- **The pure modules import zero Home Assistant**: `models.py`, `block.py`, `device_ops.py`, `const.py`, `rule_schema.py`, `yaml_io.py`. `tests/test_packaging.py::test_the_pure_modules_import_zero_home_assistant` enforces this by reading the import lines.
- **Storage migrates, never breaks.** A rule that cannot be migrated is kept, disabled and reported — never dropped.
- Every test for a new behaviour must be observed **failing** before the behaviour exists.
- Development and testing use the throwaway Docker instance on `127.0.0.1:8124`. **Nothing may address 192.168.1.14.**

## A conflict this plan resolves

The spec says validation reuses `cv.TARGET_SERVICE_FIELDS` and `cv.CONDITION_SCHEMA`. It also says `rule_schema.py` stays pure. Both cannot hold in one module.

**Resolution — validation is two layers:**

| Layer | Module | Does |
|---|---|---|
| Structural | `rule_schema.py` (pure) | fields exist, types are right, `time` parses, `profile` 1–3, `day` is `erev`/`1`..`3`, `action` looks like `domain.service`, `replay.within` parses |
| Home Assistant | `ha_validation.py` (**new**, HA-facing) | `target` against `cv.TARGET_SERVICE_FIELDS`, `condition` against `cv.CONDITION_SCHEMA` and `condition.async_validate_condition_config` |

The websocket API calls both, structural first. `yaml_io.py` calls only the structural layer, and the service handler applies the HA layer afterwards — so `yaml_io.py` stays pure.

## File Structure

| File | Change |
|---|---|
| `models.py` | `Rule` reshaped; `Replay` added; `Action` **deleted** |
| `device_ops.py` | `plan_calls`, `_plan_climate`, `_SIMPLE_DOMAINS`, `resolve_fan_mode`, `Call`, `Skip` **deleted**; `expand_action` added |
| `const.py` | `FAN_SYNONYMS` **deleted**; `CANDLE_SENSOR`/`HAVDALAH_SENSOR` become fallback defaults; `STORAGE_VERSION` → 2 |
| `rule_schema.py` | rewritten for the v2 shape, still pure |
| `ha_validation.py` | **new** — the HA-schema layer |
| `store.py` | migrating `Store` subclass; `rule_to_dict`/`rule_from_dict` for v2 |
| `migration.py` | **new**, pure — the v1 → v2 conversion |
| `engine.py` | executes via `async_call_from_config`; conditions; replay; `desired_state_at` use removed |
| `block.py` | `desired_state_at` **deleted**; `find_conflicts` takes a target resolver |
| `config_flow.py` | zmanim sensor selection + options flow |
| `repairs.py` | **new** — missing zmanim, unmigratable rules |
| `yaml_io.py` | v2 shape |
| `websocket_api.py`, card | carried along so nothing breaks |

---

### Task 1: The v2 `Rule`

**Files:**
- Modify: `custom_components/shabbat_scheduler/models.py`
- Test: `tests/test_models.py` (create if absent)

**Interfaces:**
- Produces: `Rule` with the v2 fields; `Replay`; `Action` no longer exists.

- [ ] **Step 1: Write the failing test**

```python
from datetime import time

import pytest

from custom_components.shabbat_scheduler.models import Replay, Rule


def _rule(**over):
    base = dict(
        id="r1", profile=1, day="1", time=time(11, 0),
        action="climate.set_temperature",
        target={"entity_id": ["climate.salon"]},
        data={"temperature": 26},
    )
    base.update(over)
    return Rule(**base)


def test_a_rule_is_a_service_call():
    rule = _rule()
    assert rule.action == "climate.set_temperature"
    assert rule.target == {"entity_id": ["climate.salon"]}
    assert rule.data == {"temperature": 26}


def test_a_rule_needs_no_condition_or_replay():
    rule = _rule()
    assert rule.condition == ()
    assert rule.replay == Replay()
    assert rule.replay.enabled is False
    assert rule.replay.within is None


def test_replay_carries_its_window():
    rule = _rule(replay=Replay(enabled=True, within=timedelta(hours=2)))
    assert rule.replay.enabled is True
    assert rule.replay.within == timedelta(hours=2)


def test_a_rule_is_immutable():
    rule = _rule()
    with pytest.raises(Exception):
        rule.action = "switch.turn_on"


def test_the_action_enum_is_gone():
    """v1's three-value vocabulary is what made this a climate controller."""
    import custom_components.shabbat_scheduler.models as models

    assert not hasattr(models, "Action")
```

Add `from datetime import time, timedelta` at the top.

- [ ] **Step 2: Run and watch it fail**

```bash
uv run pytest tests/test_models.py -q
```

Expected: FAIL — `ImportError: cannot import name 'Replay'`.

- [ ] **Step 3: Reshape `models.py`**

Delete the `Action` enum entirely. Replace the `Rule` dataclass with:

```python
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
```

`script` and `variables` are deleted: a script is `action: script.turn_on`.
`devices` and `settings` are deleted: they are `target` and `data`.

Add `timedelta` to the `datetime` import.

- [ ] **Step 4: Run the test**

```bash
uv run pytest tests/test_models.py -q
```

Expected: PASS. The rest of the suite will not pass until Task 12 — that is expected and handled task by task.

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler/models.py tests/test_models.py
git commit -m "feat: a rule is a Home Assistant service call"
```

---

### Task 2: `expand_action` — the one shim

**Files:**
- Modify: `custom_components/shabbat_scheduler/device_ops.py`, `custom_components/shabbat_scheduler/const.py`
- Test: `tests/test_device_ops.py`

**Interfaces:**
- Produces: `expand_action(action: str, data: dict) -> list[tuple[str, dict]]`.

**Why this exists at all.** Several climate integrations — including the `aux_cloud` units this was built for — intermittently fail to power on when `hvac_mode` and `temperature` arrive together. The ecosystem's most-used scheduler (`nielsfaber/scheduler-component`) hardcodes the same split, commented "fix for climate integrations which don't support setting hvac_mode and temperature together". That independent agreement is the evidence this is unavoidable rather than our special case.

It stays pure so it is testable without Home Assistant, and it is the **only** domain knowledge this plan authorises.

- [ ] **Step 1: Write the failing test**

Replace the whole of `tests/test_device_ops.py` with:

```python
from custom_components.shabbat_scheduler.device_ops import expand_action


def test_most_actions_pass_through_untouched():
    assert expand_action("switch.turn_on", {}) == [("switch.turn_on", {})]
    assert expand_action("scene.turn_on", {"transition": 2}) == [
        ("scene.turn_on", {"transition": 2})
    ]
    assert expand_action("notify.mobile", {"message": "hi"}) == [
        ("notify.mobile", {"message": "hi"})
    ]


def test_set_temperature_with_hvac_mode_is_split():
    """Sent together, several climate integrations silently fail to power on."""
    assert expand_action(
        "climate.set_temperature", {"temperature": 26, "hvac_mode": "cool"}
    ) == [
        ("climate.set_hvac_mode", {"hvac_mode": "cool"}),
        ("climate.set_temperature", {"temperature": 26}),
    ]


def test_set_temperature_without_hvac_mode_is_left_alone():
    assert expand_action("climate.set_temperature", {"temperature": 26}) == [
        ("climate.set_temperature", {"temperature": 26})
    ]


def test_the_split_keeps_every_other_key_on_the_temperature_call():
    calls = expand_action(
        "climate.set_temperature",
        {"temperature": 26, "hvac_mode": "cool", "target_temp_high": 28},
    )
    assert calls[1] == (
        "climate.set_temperature",
        {"temperature": 26, "target_temp_high": 28},
    )


def test_the_split_does_not_mutate_the_caller_s_data():
    data = {"temperature": 26, "hvac_mode": "cool"}
    expand_action("climate.set_temperature", data)
    assert data == {"temperature": 26, "hvac_mode": "cool"}


def test_no_other_climate_service_is_touched():
    assert expand_action("climate.set_hvac_mode", {"hvac_mode": "cool"}) == [
        ("climate.set_hvac_mode", {"hvac_mode": "cool"})
    ]
    assert expand_action("climate.turn_off", {}) == [("climate.turn_off", {})]


def test_the_fan_synonym_table_is_gone():
    """It encoded two AC brands from one house into shared code."""
    import custom_components.shabbat_scheduler.const as const

    assert not hasattr(const, "FAN_SYNONYMS")
```

- [ ] **Step 2: Run and watch it fail**

```bash
uv run pytest tests/test_device_ops.py -q
```

Expected: FAIL — `ImportError: cannot import name 'expand_action'`.

- [ ] **Step 3: Replace `device_ops.py` entirely**

```python
"""Turning one authored action into the service calls to actually make.

Almost nothing belongs here. The integration's job is to decide WHEN
something happens; Home Assistant decides what. This module exists for
the single exception documented below, and stays free of Home Assistant
so that exception is testable without an instance.
"""

from __future__ import annotations

_CLIMATE_SET_TEMPERATURE = "climate.set_temperature"
_CLIMATE_SET_HVAC_MODE = "climate.set_hvac_mode"
_HVAC_MODE = "hvac_mode"


def expand_action(action: str, data: dict) -> list[tuple[str, dict]]:
    """The calls one authored action becomes. Usually itself.

    THE ONE COMPATIBILITY SHIM. `climate.set_temperature` carrying an
    `hvac_mode` is split into `set_hvac_mode` then `set_temperature`,
    because several climate integrations - the `aux_cloud` units this was
    written for among them - intermittently fail to power on when both
    arrive together. The most-used third-party scheduler in the ecosystem
    hardcodes the same split for the same reason, which is the evidence
    that this is a real hardware quirk and not this project's special
    case.

    An author writes the one natural action; this makes it work. Every
    other action passes through untouched, and no other domain knowledge
    belongs in this file.
    """
    if action != _CLIMATE_SET_TEMPERATURE or _HVAC_MODE not in data:
        return [(action, data)]

    rest = {key: value for key, value in data.items() if key != _HVAC_MODE}
    return [
        (_CLIMATE_SET_HVAC_MODE, {_HVAC_MODE: data[_HVAC_MODE]}),
        (_CLIMATE_SET_TEMPERATURE, rest),
    ]
```

- [ ] **Step 4: Delete `FAN_SYNONYMS` from `const.py`**

Remove the whole `FAN_SYNONYMS` dict. **Leave `STORAGE_VERSION` at 1** — Task 5 raises it to 2 in the same commit that adds the migration. Raising it here would mean every load between this task and Task 5 sees a version it has no migration for.

- [ ] **Step 5: Run the tests**

```bash
uv run pytest tests/test_device_ops.py tests/test_packaging.py -q
```

Expected: PASS, including the purity guard.

- [ ] **Step 6: Commit**

```bash
git add custom_components/shabbat_scheduler/device_ops.py custom_components/shabbat_scheduler/const.py tests/test_device_ops.py
git commit -m "feat: one documented climate shim, and nothing else domain-specific"
```

---

### Task 3: Structural validation

**Files:**
- Modify: `custom_components/shabbat_scheduler/rule_schema.py`
- Test: `tests/test_rule_schema.py`

**Interfaces:**
- Consumes: `Rule`, `Replay` (Task 1).
- Produces: `rule_from_api(data, rule_id) -> Rule`, `changes_from_api(data) -> dict`, `validate_defaults(data) -> dict`, `RuleValidationError`.

Stays **pure**. It validates shape and type only; `ha_validation.py` (Task 4) applies HA's own schemas.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_rule_schema.py`:

```python
def test_action_must_look_like_a_service():
    for bad in ["climate", "climate.", ".turn_on", "", "climate.set.temp", 7]:
        with pytest.raises(RuleValidationError):
            rule_from_api({**BASE, "action": bad}, "r1")


def test_a_valid_action_is_accepted():
    rule = rule_from_api({**BASE, "action": "scene.turn_on"}, "r1")
    assert rule.action == "scene.turn_on"


def test_target_and_data_must_be_mappings():
    with pytest.raises(RuleValidationError):
        rule_from_api({**BASE, "target": ["climate.salon"]}, "r1")
    with pytest.raises(RuleValidationError):
        rule_from_api({**BASE, "data": "temperature=26"}, "r1")


def test_condition_must_be_a_list_of_mappings():
    with pytest.raises(RuleValidationError):
        rule_from_api({**BASE, "condition": {"condition": "state"}}, "r1")
    rule = rule_from_api(
        {**BASE, "condition": [{"condition": "state", "entity_id": "x", "state": "on"}]},
        "r1",
    )
    assert len(rule.condition) == 1


def test_replay_parses_its_window():
    rule = rule_from_api({**BASE, "replay": {"enabled": True, "within": "02:00:00"}}, "r1")
    assert rule.replay.enabled is True
    assert rule.replay.within == timedelta(hours=2)


def test_replay_enabled_must_be_a_real_boolean():
    """A JS form yielding the string "false" used to render off and RUN."""
    with pytest.raises(RuleValidationError):
        rule_from_api({**BASE, "replay": {"enabled": "false"}}, "r1")


def test_replay_within_must_be_a_duration():
    with pytest.raises(RuleValidationError):
        rule_from_api({**BASE, "replay": {"enabled": True, "within": "soon"}}, "r1")


def test_replay_defaults_to_off_with_no_window():
    rule = rule_from_api(BASE, "r1")
    assert rule.replay == Replay()


def test_the_v1_fields_are_rejected_outright():
    """Silently ignoring them would hide a half-migrated rule."""
    for gone in ("devices", "settings", "script", "variables", "replay_on_restart"):
        with pytest.raises(RuleValidationError):
            rule_from_api({**BASE, gone: "anything"}, "r1")


def test_defaults_take_target_and_data():
    assert validate_defaults({"target": {"entity_id": ["climate.a"]}, "data": {"temperature": 26}})
    with pytest.raises(RuleValidationError):
        validate_defaults({"devices": ["climate.a"]})
```

Define at the top of the file:

```python
BASE = {
    "profile": 1, "day": "1", "time": "11:00:00",
    "action": "climate.set_temperature",
}
```

- [ ] **Step 2: Run and watch them fail**

```bash
uv run pytest tests/test_rule_schema.py -q
```

Expected: FAIL — the module still validates the v1 shape.

- [ ] **Step 3: Rewrite `rule_schema.py` for v2**

Keep `_check_unknown_fields`, `_day`, `_profile`, `_time`, `_bool`, `_text` as they are. Replace `_FIELDS`, `_DEFAULTS_FIELDS`, the `_coerce` branches for `devices`/`settings`/`action`/`script`/`variables`, and `validate_rule`:

```python
_FIELDS = {
    "profile", "day", "time", "action", "target", "data",
    "condition", "replay", "name", "icon", "color", "enabled",
}

_DEFAULTS_FIELDS = {"target", "data"}

_V1_FIELDS = {"devices", "settings", "script", "variables", "replay_on_restart"}


def _action(value) -> str:
    """A Home Assistant service, "domain.service".

    Only the shape is checked here: whether the service EXISTS is Home
    Assistant's business, and asking it would drag an instance into this
    module. ha_validation.py does not check it either - a service can be
    added or removed at any time, so a rule naming one that is missing
    today may be perfectly correct tomorrow. The failure surfaces at fire
    time, reported, which is the honest place for it.
    """
    if not isinstance(value, str):
        raise RuleValidationError(f"action must be a string, got {value!r}")
    parts = value.split(".")
    if len(parts) != 2 or not all(parts):
        raise RuleValidationError(
            f"action must be 'domain.service', got {value!r}"
        )
    return value


def _mapping(field: str, value) -> dict:
    if not isinstance(value, Mapping):
        raise RuleValidationError(f"{field} must be a mapping, got {value!r}")
    return dict(value)


def _condition(value) -> tuple:
    if isinstance(value, Mapping) or not isinstance(value, (list, tuple)):
        raise RuleValidationError(
            f"condition must be a list of conditions, got {value!r}"
        )
    for item in value:
        if not isinstance(item, Mapping):
            raise RuleValidationError(
                f"each condition must be a mapping, got {item!r}"
            )
    return tuple(dict(item) for item in value)


def _duration(value) -> timedelta:
    """'HH:MM:SS' into a timedelta."""
    text = str(value)
    parts = text.split(":")
    if len(parts) != 3 or not all(p.isdecimal() for p in parts):
        raise RuleValidationError(
            f"replay.within must be 'HH:MM:SS', got {value!r}"
        )
    hours, minutes, seconds = (int(p) for p in parts)
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)


def _replay(value) -> Replay:
    data = _mapping("replay", value)
    unknown = set(data) - {"enabled", "within"}
    if unknown:
        raise RuleValidationError(f"unknown replay field(s): {sorted(unknown)}")
    enabled = _bool("replay.enabled", data.get("enabled", False))
    within = data.get("within")
    return Replay(
        enabled=enabled,
        within=None if within is None else _duration(within),
    )
```

In `_check_unknown_fields`, before the existing unknown check, add:

```python
    stale = set(data) & _V1_FIELDS
    if stale:
        raise RuleValidationError(
            f"{sorted(stale)} belong to the v1 rule format. A rule is now an "
            "action with a target and data; see the README."
        )
```

Wire the new coercers into `_coerce`, drop the `devices`/`settings`/`script`/`variables` branches, and replace `validate_rule`'s custom-action check — there is no longer a `custom` action — with `pass`-equivalent removal: delete the function and its call sites.

Required fields become `("profile", "day", "time", "action")`.

- [ ] **Step 4: Run tests and the purity guard**

```bash
uv run pytest tests/test_rule_schema.py tests/test_packaging.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler/rule_schema.py tests/test_rule_schema.py
git commit -m "feat: structural validation for the v2 rule, still pure"
```

---

### Task 4: `ha_validation.py` — Home Assistant's own schemas

**Files:**
- Create: `custom_components/shabbat_scheduler/ha_validation.py`
- Test: `tests/test_ha_validation.py`

**Interfaces:**
- Consumes: `Rule` (Task 1).
- Produces: `async_validate_rule(hass, rule) -> None`, raising `RuleValidationError`.

**Why a separate module:** `rule_schema.py` is guarded pure by `tests/test_packaging.py`, and HA's schemas live in `homeassistant.helpers`. This is the HA-facing half of the same job.

- [ ] **Step 1: Write the failing tests**

```python
"""Validation that needs Home Assistant's own schemas."""

from datetime import time

import pytest

from custom_components.shabbat_scheduler.ha_validation import async_validate_rule
from custom_components.shabbat_scheduler.models import Rule
from custom_components.shabbat_scheduler.rule_schema import RuleValidationError


def _rule(**over):
    base = dict(
        id="r1", profile=1, day="1", time=time(11, 0),
        action="climate.set_temperature",
        target={"entity_id": ["climate.salon"]},
    )
    base.update(over)
    return Rule(**base)


async def test_a_plain_entity_target_is_accepted(hass):
    await async_validate_rule(hass, _rule())


async def test_area_and_label_targets_are_accepted(hass):
    await async_validate_rule(hass, _rule(target={"area_id": "salon"}))
    await async_validate_rule(hass, _rule(target={"label_id": "shabbat"}))


async def test_an_unknown_target_key_is_rejected(hass):
    with pytest.raises(RuleValidationError):
        await async_validate_rule(hass, _rule(target={"room": "salon"}))


async def test_a_valid_condition_is_accepted(hass):
    await async_validate_rule(hass, _rule(condition=(
        {"condition": "state", "entity_id": "binary_sensor.x", "state": "on"},
    )))


async def test_a_malformed_condition_is_rejected(hass):
    with pytest.raises(RuleValidationError):
        await async_validate_rule(hass, _rule(condition=(
            {"condition": "state"},          # no entity_id, no state
        )))


async def test_an_unknown_condition_type_is_rejected(hass):
    with pytest.raises(RuleValidationError):
        await async_validate_rule(hass, _rule(condition=(
            {"condition": "vibes", "entity_id": "x"},
        )))


async def test_an_empty_target_is_accepted(hass):
    """Some actions need none - notify.persistent_notification, for one."""
    await async_validate_rule(hass, _rule(action="notify.persistent_notification", target={}))
```

- [ ] **Step 2: Run and watch them fail**

```bash
uv run pytest tests/test_ha_validation.py -q
```

Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Create the module**

```python
"""Validation that needs Home Assistant's own schemas.

The structural half lives in `rule_schema.py`, which is deliberately free
of Home Assistant so the tricky parsing is testable without an instance.
This is the other half: the target and the conditions are Home
Assistant's own formats, and validating them by hand would mean
reimplementing - and then drifting from - schemas HA already publishes.

Deliberately NOT checked here: whether `action` names a service that
currently exists. Services come and go with integrations and reloads, so
a rule naming one that is missing right now may be correct an hour later.
That failure belongs at fire time, where it is reported against the rule.
"""

from __future__ import annotations

import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.helpers import condition
from homeassistant.helpers import config_validation as cv

from .models import Rule
from .rule_schema import RuleValidationError

_TARGET_SCHEMA = vol.Schema(cv.TARGET_SERVICE_FIELDS)


async def async_validate_rule(hass: HomeAssistant, rule: Rule) -> None:
    """Raise RuleValidationError if HA would refuse this rule's shape."""
    try:
        _TARGET_SCHEMA(dict(rule.target))
    except vol.Invalid as err:
        raise RuleValidationError(f"target is not valid: {err}") from err

    for item in rule.condition:
        try:
            validated = cv.CONDITION_SCHEMA(dict(item))
            await condition.async_validate_condition_config(hass, validated)
        except (vol.Invalid, HomeAssistantError) as err:
            raise RuleValidationError(f"condition is not valid: {err}") from err
```

Add `from homeassistant.exceptions import HomeAssistantError` to the imports.

- [ ] **Step 4: Run the tests**

```bash
uv run pytest tests/test_ha_validation.py -q
```

Expected: PASS. If `async_validate_condition_config` raises something other than `vol.Invalid`/`HomeAssistantError` for an unknown condition type, widen the `except` to match what it actually raises and say so in your report — do not catch bare `Exception`.

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler/ha_validation.py tests/test_ha_validation.py
git commit -m "feat: validate target and conditions with Home Assistant's own schemas"
```

---

### Task 5: Storage migration, v1 → v2

**Files:**
- Create: `custom_components/shabbat_scheduler/migration.py`
- Modify: `custom_components/shabbat_scheduler/store.py`
- Test: `tests/test_migration.py`

**Interfaces:**
- Produces: `migrate_v1_rule(raw) -> tuple[dict | None, str | None]` (pure — the v2 dict, or `None` plus a reason); `migrate_v1(data) -> tuple[dict, list[str]]` (pure — the whole store plus the ids that failed).

**How HA's migration works** (verified in `helpers/storage.py`): subclass `Store` and override `async def _async_migrate_func(self, old_major_version, old_minor_version, old_data)`. It is called when the stored version differs, and its return value is **saved automatically**.

**The rule that governs everything here:** a rule that cannot be migrated is **kept, disabled and reported**. Dropping one silently is the worst thing an upgrade could do.

- [ ] **Step 1: Write the failing tests**

```python
from custom_components.shabbat_scheduler.migration import migrate_v1, migrate_v1_rule

V1_CLIMATE_ON = {
    "id": "a", "profile": 1, "day": "1", "time": "11:00:00", "action": "on",
    "devices": ["climate.salon"], "settings": {"temperature": 26, "hvac_mode": "cool"},
    "name": "Morning", "enabled": True, "replay_on_restart": True,
}
V1_SIMPLE_ON = {
    "id": "b", "profile": 1, "day": "erev", "time": "22:00:00", "action": "on",
    "devices": ["switch.boiler"], "settings": {},
}
V1_OFF = {
    "id": "c", "profile": 1, "day": "1", "time": "18:00:00", "action": "off",
    "devices": ["climate.salon"], "settings": {},
}
V1_CUSTOM = {
    "id": "d", "profile": 1, "day": "1", "time": "17:00:00", "action": "custom",
    "script": "script.boiler", "variables": {"minutes": 30},
}


def test_a_climate_on_rule_becomes_set_temperature():
    out, reason = migrate_v1_rule(V1_CLIMATE_ON)
    assert reason is None
    assert out["action"] == "climate.set_temperature"
    assert out["target"] == {"entity_id": ["climate.salon"]}
    assert out["data"] == {"temperature": 26, "hvac_mode": "cool"}
    assert out["name"] == "Morning"


def test_a_simple_on_rule_becomes_turn_on():
    out, reason = migrate_v1_rule(V1_SIMPLE_ON)
    assert reason is None
    assert out["action"] == "switch.turn_on"
    assert out["target"] == {"entity_id": ["switch.boiler"]}


def test_an_off_rule_becomes_turn_off():
    out, _ = migrate_v1_rule(V1_OFF)
    assert out["action"] == "climate.turn_off"


def test_a_custom_rule_becomes_a_script_call():
    out, reason = migrate_v1_rule(V1_CUSTOM)
    assert reason is None
    assert out["action"] == "script.turn_on"
    assert out["target"] == {"entity_id": ["script.boiler"]}
    assert out["data"] == {"variables": {"minutes": 30}}


def test_replay_on_restart_becomes_replay_with_no_window():
    """v1 replayed however late it was; tightening that silently would
    change behaviour the user never asked to change."""
    out, _ = migrate_v1_rule(V1_CLIMATE_ON)
    assert out["replay"] == {"enabled": True}
    out2, _ = migrate_v1_rule(V1_SIMPLE_ON)
    assert out2["replay"] == {"enabled": False}


def test_a_rule_with_no_devices_cannot_be_migrated():
    out, reason = migrate_v1_rule({**V1_SIMPLE_ON, "devices": []})
    assert out is None
    assert "device" in reason.lower()


def test_a_custom_rule_with_no_script_cannot_be_migrated():
    out, reason = migrate_v1_rule({**V1_CUSTOM, "script": None})
    assert out is None
    assert "script" in reason.lower()


def test_an_unmigratable_rule_is_kept_and_disabled_not_dropped():
    data = {"rules": [V1_SIMPLE_ON, {**V1_CUSTOM, "script": None}], "defaults": {}}
    out, failed = migrate_v1(data)
    assert len(out["rules"]) == 2, "a dropped rule is the worst upgrade outcome"
    survivor = next(r for r in out["rules"] if r["id"] == "d")
    assert survivor["enabled"] is False
    assert failed == ["d"]


def test_defaults_migrate_too():
    data = {"rules": [], "defaults": {"devices": ["climate.a"], "settings": {"temperature": 26}}}
    out, _ = migrate_v1(data)
    assert out["defaults"] == {
        "target": {"entity_id": ["climate.a"]},
        "data": {"temperature": 26},
    }


def test_the_other_store_keys_survive():
    data = {"rules": [], "defaults": {}, "enabled": True, "dry_run": True,
            "active_block": {"candle_lighting": "x", "havdalah": "y"}}
    out, _ = migrate_v1(data)
    assert out["enabled"] is True
    assert out["dry_run"] is True
    assert out["active_block"] == {"candle_lighting": "x", "havdalah": "y"}
```

- [ ] **Step 2: Run and watch them fail**

```bash
uv run pytest tests/test_migration.py -q
```

Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Create `migration.py`** (pure — no Home Assistant)

```python
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
```

- [ ] **Step 4: Wire the migration into `store.py`**

Add above `RuleStore`:

```python
class _MigratingStore(Store):
    """Home Assistant calls this when the stored version is behind.

    Whatever it returns is saved automatically, so the conversion happens
    exactly once per upgrade.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(hass, STORAGE_VERSION, STORAGE_KEY)
        self.migration_failures: list[str] = []

    async def _async_migrate_func(
        self, old_major_version: int, old_minor_version: int, old_data: dict
    ) -> dict:
        if old_major_version == 1:
            migrated, failed = migrate_v1(old_data)
            self.migration_failures = failed
            return migrated
        return old_data
```

Change `RuleStore.__init__` to `self._store = _MigratingStore(hass)`, and expose `migration_failures` as a property reading `self._store.migration_failures`. **Raise `STORAGE_VERSION` to 2 in `const.py` in this same commit** — the bump and the migration that services it must land together.

Add a `migration_error: str | None = None` field to the v2 `Rule` in `models.py` so a failed rule keeps its reason, and carry it through `rule_to_dict`/`rule_from_dict`. Deliberately do **not** add it to `rule_schema._FIELDS`: it is written by the migration, never by a client, so the API should keep rejecting it.

- [ ] **Step 5: Add the end-to-end migration test**

```python
async def test_a_v1_store_on_disk_migrates_on_load(hass, hass_storage):
    hass_storage["shabbat_scheduler.rules"] = {
        "version": 1,
        "minor_version": 1,
        "key": "shabbat_scheduler.rules",
        "data": {"rules": [V1_CLIMATE_ON], "defaults": {}, "enabled": True},
    }
    store = RuleStore(hass)
    await store.async_load()

    assert len(store.rules) == 1
    assert store.rules[0].action == "climate.set_temperature"
    assert store.enabled is True
    # And it was written back, so the conversion happens once.
    assert hass_storage["shabbat_scheduler.rules"]["version"] == 2
```

- [ ] **Step 6: Run the tests**

```bash
uv run pytest tests/test_migration.py tests/test_packaging.py -q
```

Expected: PASS, purity guard included.

- [ ] **Step 7: Commit**

```bash
git add custom_components/shabbat_scheduler/migration.py custom_components/shabbat_scheduler/store.py custom_components/shabbat_scheduler/models.py tests/test_migration.py
git commit -m "feat: migrate v1 rules, keeping and reporting what cannot convert"
```

---

### Task 6: Execute through Home Assistant

**Files:**
- Modify: `custom_components/shabbat_scheduler/engine.py`
- Test: `tests/test_engine_execute.py`

**Interfaces:**
- Consumes: `expand_action` (Task 2), `Rule` (Task 1).
- Produces: `ShabbatEngine.async_apply_rule(rule, force=False) -> list[dict]` with per-call results `{action, target, data, outcome, error?}`. `outcome` is `called`, `failed`, or `would_call` under dry run. (Task 7 adds a fourth, `blocked`, which is a whole-rule result rather than a per-call one and carries `reason` instead of `action`.)

**What changes and what does not.** Replace `_apply_custom`, `_apply_device` and `plan_calls` with one path built on `async_call_from_config` (`helpers/service.py:239`), which accepts a `context` — so the Context attribution survives. **Keep** the retry (3 × 30s), the per-device lock, the two-event split, and the staleness stamp ordering.

`changed`/`ok`/`failed` becomes `called`/`failed`: an opaque call has no queryable desired state to diff. Fire-once already prevents the re-assertion the diff guarded against.

- [ ] **Step 1: Write the failing tests**

```python
async def test_a_rule_calls_its_action(hass, test_booleans):
    engine = ...  # build as tests/test_engine.py already does
    rule = Rule(id="r", profile=1, day="1", time=time(11, 0),
                action="input_boolean.turn_on",
                target={"entity_id": ["input_boolean.salon"]})
    results = await engine.async_apply_rule(rule)

    assert hass.states.get("input_boolean.salon").state == "on"
    assert [r["outcome"] for r in results] == ["called"]
    assert results[0]["action"] == "input_boolean.turn_on"


async def test_any_domain_works_not_just_climate_and_switches(hass):
    """v1 returned "unsupported domain" for everything but four domains."""
    calls = async_mock_service(hass, "notify", "persistent_notification")
    rule = Rule(id="r", profile=1, day="1", time=time(11, 0),
                action="notify.persistent_notification",
                data={"message": "Shabbat shalom"})
    results = await engine.async_apply_rule(rule)

    assert len(calls) == 1
    assert calls[0].data["message"] == "Shabbat shalom"
    assert results[0]["outcome"] == "called"


async def test_the_climate_shim_sends_two_calls(hass):
    mode = async_mock_service(hass, "climate", "set_hvac_mode")
    temp = async_mock_service(hass, "climate", "set_temperature")
    rule = Rule(id="r", profile=1, day="1", time=time(11, 0),
                action="climate.set_temperature",
                target={"entity_id": ["climate.salon"]},
                data={"temperature": 26, "hvac_mode": "cool"})
    results = await engine.async_apply_rule(rule)

    assert len(mode) == 1 and len(temp) == 1
    assert "hvac_mode" not in temp[0].data
    assert [r["outcome"] for r in results] == ["called", "called"]


async def test_a_failing_call_is_reported_not_swallowed(hass):
    rule = Rule(id="r", profile=1, day="1", time=time(11, 0),
                action="nonexistent.service")
    results = await engine.async_apply_rule(rule)

    assert results[0]["outcome"] == "failed"
    assert results[0]["error"]


async def test_the_call_carries_our_context_so_changes_attribute_to_us(hass, test_booleans):
    rule = Rule(id="r", profile=1, day="1", time=time(11, 0),
                action="input_boolean.turn_on",
                target={"entity_id": ["input_boolean.salon"]})
    await engine.async_apply_rule(rule)

    state = hass.states.get("input_boolean.salon")
    assert engine.is_our_context(state.context)


async def test_dry_run_calls_nothing(hass, test_booleans):
    await engine.store.async_set_dry_run(True)
    rule = Rule(id="r", profile=1, day="1", time=time(11, 0),
                action="input_boolean.turn_on",
                target={"entity_id": ["input_boolean.salon"]})
    results = await engine.async_apply_rule(rule)

    assert hass.states.get("input_boolean.salon").state == "off"
    assert results[0]["outcome"] == "would_call"
```

- [ ] **Step 2: Run and watch them fail**

```bash
uv run pytest tests/test_engine_execute.py -q
```

Expected: FAIL — the engine still branches on `Action`.

- [ ] **Step 3: Replace the apply path in `engine.py`**

Delete `_apply_custom`, `_apply_device` and the `plan_calls` import. Rewrite `async_apply_rule`'s body between the two events:

```python
        results = []
        for action, data in expand_action(rule.action, dict(rule.data)):
            results.append(await self._call(action, rule.target, data, context))
```

and add:

```python
    async def _call(
        self, action: str, target: dict, data: dict, context: Context
    ) -> dict:
        """One service call, retried, reported either way.

        Everything here is Home Assistant's own service machinery -
        `async_call_from_config` validates the config, resolves the target
        and makes the call. This integration's contribution is deciding
        that now is the moment.
        """
        result = {"action": action, "target": dict(target), "data": dict(data)}

        if self.store.dry_run:
            result["outcome"] = "would_call"
            return result

        config = {"action": action, "data": data}
        if target:
            config["target"] = dict(target)

        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                await async_call_from_config(
                    self.hass, config, blocking=True, validate_config=True,
                    context=context,
                )
            except Exception as err:  # noqa: BLE001 - reported, never swallowed
                if attempt == RETRY_ATTEMPTS:
                    result["outcome"] = "failed"
                    result["error"] = str(err)
                    return result
                await asyncio.sleep(RETRY_DELAY_SECONDS)
            else:
                result["outcome"] = "called"
                return result
        return result
```

Update the `EVENT_RULE_APPLIED` payload: `"action": rule.action` and `"target": dict(rule.target)` in place of `action.value`/`devices`. Update `logbook.py`'s describe function to match.

The per-device lock keyed on `entity_id` no longer applies — a target may be an area. Key it on the rule id instead, which preserves "one rule's calls do not interleave with its own re-entry".

- [ ] **Step 4: Run the tests**

```bash
uv run pytest tests/test_engine_execute.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler/engine.py custom_components/shabbat_scheduler/logbook.py tests/test_engine_execute.py
git commit -m "feat: execute any Home Assistant action, not four domains"
```

---

### Task 7: Conditions at fire time

**Files:**
- Modify: `custom_components/shabbat_scheduler/engine.py`
- Test: `tests/test_conditions.py`

**Interfaces:**
- Consumes: `Rule.condition` (Task 1).
- Produces: a rule whose conditions do not all pass returns `[{"outcome": "blocked", "reason": …}]` and calls nothing.

**The constraint that governs this task:** a rule blocked by a condition **must say so**. This is the largest new way for a rule to do nothing, and a silent one would be exactly the failure this project exists to prevent.

- [ ] **Step 1: Write the failing tests**

```python
async def test_a_rule_with_a_passing_condition_fires(hass, test_booleans):
    hass.states.async_set("binary_sensor.gate", "on")
    rule = Rule(..., condition=({"condition": "state",
                                 "entity_id": "binary_sensor.gate",
                                 "state": "on"},))
    results = await engine.async_apply_rule(rule)
    assert hass.states.get("input_boolean.salon").state == "on"
    assert results[0]["outcome"] == "called"


async def test_a_rule_with_a_failing_condition_does_not_fire(hass, test_booleans):
    hass.states.async_set("binary_sensor.gate", "off")
    rule = Rule(..., condition=({"condition": "state",
                                 "entity_id": "binary_sensor.gate",
                                 "state": "on"},))
    results = await engine.async_apply_rule(rule)
    assert hass.states.get("input_boolean.salon").state == "off"


async def test_a_blocked_rule_says_so_rather_than_looking_successful(hass, test_booleans):
    hass.states.async_set("binary_sensor.gate", "off")
    rule = Rule(..., condition=({"condition": "state",
                                 "entity_id": "binary_sensor.gate",
                                 "state": "on"},))
    results = await engine.async_apply_rule(rule)

    assert results == [{"outcome": "blocked", "reason": "condition not met"}]
    # "no results" would be indistinguishable from "nothing to do".
    assert results != []


async def test_every_condition_must_pass(hass, test_booleans):
    hass.states.async_set("binary_sensor.a", "on")
    hass.states.async_set("binary_sensor.b", "off")
    rule = Rule(..., condition=(
        {"condition": "state", "entity_id": "binary_sensor.a", "state": "on"},
        {"condition": "state", "entity_id": "binary_sensor.b", "state": "on"},
    ))
    results = await engine.async_apply_rule(rule)
    assert results[0]["outcome"] == "blocked"


async def test_a_condition_that_errors_blocks_rather_than_fires(hass, test_booleans):
    """Erring towards not acting: an unexpected error is not consent."""
    rule = Rule(..., condition=({"condition": "state",
                                 "entity_id": "binary_sensor.missing",
                                 "state": "on"},))
    results = await engine.async_apply_rule(rule)
    assert results[0]["outcome"] == "blocked"


async def test_a_blocked_rule_is_visible_in_the_logbook(hass, test_booleans):
    """It fires EVENT_RULE_COMPLETED carrying the blocked result."""
    events = async_capture_events(hass, EVENT_RULE_COMPLETED)
    hass.states.async_set("binary_sensor.gate", "off")
    await engine.async_apply_rule(Rule(..., condition=(...,)))
    assert events[0].data["results"][0]["outcome"] == "blocked"
```

- [ ] **Step 2: Run and watch them fail**

```bash
uv run pytest tests/test_conditions.py -q
```

Expected: FAIL — conditions are not evaluated.

- [ ] **Step 3: Evaluate conditions in `async_apply_rule`**

After firing `EVENT_RULE_APPLIED` and before the calls:

```python
        if rule.condition and not await self._conditions_pass(rule):
            results = [{"outcome": "blocked", "reason": "condition not met"}]
            self.last_run = results
            self.last_run_at = dt_util.utcnow()
            self.hass.bus.async_fire(
                EVENT_RULE_COMPLETED, {"rule_id": rule.id, "results": results}
            )
            return results
```

and:

```python
    async def _conditions_pass(self, rule: Rule) -> bool:
        """Every condition must pass. An error counts as not passing.

        Erring towards NOT acting: an unexpected error is not consent to
        drive an appliance on a day nobody can undo it.
        """
        for item in rule.condition:
            try:
                checker = await condition.async_from_config(self.hass, dict(item))
                if not checker(self.hass, {}):
                    return False
            except Exception:  # noqa: BLE001 - a broken condition blocks
                _LOGGER.exception(
                    "Condition on rule %s could not be evaluated; not acting",
                    rule.id,
                )
                return False
        return True
```

- [ ] **Step 4: Run the tests**

```bash
uv run pytest tests/test_conditions.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler/engine.py tests/test_conditions.py
git commit -m "feat: conditions, and a blocked rule that says it was blocked"
```

---

### Task 8: Replay

**Files:**
- Modify: `custom_components/shabbat_scheduler/engine.py`, `custom_components/shabbat_scheduler/block.py`
- Test: `tests/test_replay.py`

**Interfaces:**
- Consumes: `Rule.replay` (Task 1), `resolve_rules` (unchanged).
- Produces: catch-up replays opted-in rules in time order; `desired_state_at` **deleted**.

**Why the old mechanism cannot survive:** `desired_state_at` answers "what state should this device be in now?", which only works because v1 understood `hvac_mode`/`temperature`/`fan_mode`. An opaque service call has no queryable desired state. Replay becomes explicit instead: the author says what is safe to repeat.

- [ ] **Step 1: Write the failing tests**

```python
async def test_only_opted_in_rules_replay(hass, test_booleans):
    # 11:00 replay on, 12:00 replay off; now is 14:00, mid-block.
    ...
    await engine.async_catch_up()
    assert calls_for("11:00 rule") == 1
    assert calls_for("12:00 rule") == 0


async def test_replays_happen_in_time_order(hass, test_booleans):
    ...
    assert [c.data["entity_id"] for c in calls] == ["...09:00", "...11:00"]


async def test_a_rule_older_than_its_window_is_skipped_and_reported(hass):
    """An 11:00 rule replayed at 23:00 is worse than not replayed."""
    # now = 23:00, rule at 11:00, within = 02:00:00
    results = await engine.async_catch_up()
    assert any(r["outcome"] == "skipped_stale" for r in results)
    assert calls == []


async def test_a_rule_inside_its_window_is_replayed(hass):
    # now = 12:00, rule at 11:00, within = 02:00:00
    assert len(calls) == 1


async def test_no_window_means_no_bound(hass):
    """v1 behaviour, preserved for migrated rules."""
    # now = 23:00, rule at 11:00, replay enabled, within = None
    assert len(calls) == 1


async def test_a_rule_whose_condition_fails_is_not_replayed(hass):
    hass.states.async_set("binary_sensor.gate", "off")
    # rule has replay enabled AND a condition on that sensor
    assert calls == []


async def test_future_rules_are_not_replayed_only_armed(hass):
    # rule at 18:00, now 14:00
    assert calls == []
    assert engine.upcoming()


async def test_catch_up_still_happens_at_most_once_per_block(hass):
    await engine.async_catch_up()
    await engine.async_catch_up()
    assert len(calls) == 1


def test_desired_state_at_is_gone():
    """It could only work because v1 understood climate attributes."""
    import custom_components.shabbat_scheduler.block as block

    assert not hasattr(block, "desired_state_at")
```

- [ ] **Step 2: Run and watch them fail**

```bash
uv run pytest tests/test_replay.py -q
```

Expected: FAIL.

- [ ] **Step 3: Rewrite catch-up**

Delete `desired_state_at` from `block.py` and its tests. Replace the engine's catch-up body:

```python
        now = dt_util.now()
        results: list[dict] = []
        for item in resolve_rules(self._merged_rules(), self._block, self._tz()):
            if item.when > now:
                continue                      # future: armed, not replayed
            if not item.rule.replay.enabled:
                continue                      # the author did not opt in
            within = item.rule.replay.within
            if within is not None and now - item.when > within:
                results.append(
                    {
                        "rule_id": item.rule.id,
                        "outcome": "skipped_stale",
                        "reason": f"{now - item.when} late, window {within}",
                    }
                )
                continue
            results.extend(await self.async_apply_rule(item.rule))
```

`resolve_rules` already returns time-ordered items, so replay order follows.

- [ ] **Step 4: Run the tests**

```bash
uv run pytest tests/test_replay.py tests/test_block.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler/engine.py custom_components/shabbat_scheduler/block.py tests/test_replay.py tests/test_block.py
git commit -m "feat: opt-in replay with a staleness window and its condition as guard"
```

---

### Task 9: Conflicts on overlapping targets

**Files:**
- Modify: `custom_components/shabbat_scheduler/block.py`, `custom_components/shabbat_scheduler/websocket_api.py`
- Test: `tests/test_conflicts.py`

**Interfaces:**
- Produces: `find_conflicts(rules, resolve) -> list[Conflict]` where `resolve(target: dict) -> frozenset[str]`; `Conflict` gains `targets`.

A conflict is now: two enabled rules, same profile and day, same time, whose **resolved targets overlap**. Weaker than v1 — two rules setting the same device to the same value now count — but domain-agnostic. Warn, never resolve.

`block.py` stays pure by taking the resolver as an argument. The HA side supplies one built on `homeassistant.helpers.target.async_extract_referenced_entity_ids` (`helpers/target.py:158`).

- [ ] **Step 1: Write the failing tests**

```python
def _resolve(target):
    """A stand-in registry: areas expand to their entities."""
    AREAS = {"salon": {"climate.salon", "light.salon"}}
    out = set(target.get("entity_id", []))
    for area in _as_list(target.get("area_id")):
        out |= AREAS.get(area, set())
    return frozenset(out)


def test_two_rules_on_the_same_entity_at_the_same_time_conflict():
    rules = [rule(id="a", time=T, target={"entity_id": ["climate.salon"]}),
             rule(id="b", time=T, target={"entity_id": ["climate.salon"]})]
    assert find_conflicts(rules, _resolve)


def test_an_area_overlapping_an_entity_conflicts():
    """The reason a resolver is needed at all."""
    rules = [rule(id="a", time=T, target={"area_id": "salon"}),
             rule(id="b", time=T, target={"entity_id": ["climate.salon"]})]
    conflicts = find_conflicts(rules, _resolve)
    assert conflicts and "climate.salon" in conflicts[0].targets


def test_different_times_do_not_conflict():
    assert find_conflicts([rule(id="a", time=T), rule(id="b", time=T2)], _resolve) == []


def test_different_profiles_do_not_conflict():
    assert find_conflicts(
        [rule(id="a", profile=1), rule(id="b", profile=3)], _resolve
    ) == []


def test_a_disabled_rule_never_conflicts():
    assert find_conflicts(
        [rule(id="a"), rule(id="b", enabled=False)], _resolve
    ) == []


def test_non_overlapping_targets_do_not_conflict():
    assert find_conflicts(
        [rule(id="a", target={"entity_id": ["climate.salon"]}),
         rule(id="b", target={"entity_id": ["climate.kids"]})],
        _resolve,
    ) == []


def test_identical_rules_now_conflict_which_v1_would_not_have_flagged():
    """Accepted weakening: without understanding the payload, "same" and
    "opposite" are indistinguishable."""
    same = {"entity_id": ["climate.salon"]}
    assert find_conflicts(
        [rule(id="a", target=same, data={"temperature": 26}),
         rule(id="b", target=same, data={"temperature": 26})],
        _resolve,
    )
```

- [ ] **Step 2: Run and watch them fail**

```bash
uv run pytest tests/test_conflicts.py -q
```

Expected: FAIL — the current signature takes no resolver.

- [ ] **Step 3: Rewrite `find_conflicts` and `Conflict`**

`Conflict` becomes `profile`, `day`, `time`, `targets: frozenset[str]`, `rule_ids: tuple[str, ...]`. Group enabled rules by `(profile, day, time)`, resolve each rule's target once, and emit a conflict for any pair whose sets intersect, carrying the intersection.

Update `conflict_warnings(defaults, rules, resolve)` to pass the resolver through, and the websocket layer to supply one:

```python
from homeassistant.helpers import target as target_helper


def _resolver(hass: HomeAssistant):
    """Resolve a target selector to the entity ids it actually covers.

    Verified against the installed 2026.8.2:
    `TargetSelection.__init__(config)` takes the target dict directly
    (`helpers/target.py:72`), and `async_extract_referenced_entity_ids`
    returns a `SelectedEntities` whose `referenced` holds what was named
    outright and whose `indirectly_referenced` holds what an area, device,
    floor or label expanded into (`:117-125`). A conflict cares about both.
    """

    def resolve(target: dict) -> frozenset[str]:
        selection = target_helper.TargetSelection(dict(target))
        selected = target_helper.async_extract_referenced_entity_ids(hass, selection)
        return frozenset(selected.referenced | selected.indirectly_referenced)

    return resolve
```

Re-check those names against whatever Home Assistant version you are on before trusting them — this shape has moved across releases, and getting it wrong yields a silently empty set, which reports **no conflicts** on a genuinely conflicting schedule. A test with a real area registered, asserting the area's entities come back, is what catches that.

- [ ] **Step 4: Run the tests**

```bash
uv run pytest tests/test_conflicts.py tests/test_packaging.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler/block.py custom_components/shabbat_scheduler/websocket_api.py tests/test_conflicts.py
git commit -m "feat: conflicts on overlapping resolved targets"
```

---

### Task 10: The zmanim source becomes configuration

**Files:**
- Modify: `custom_components/shabbat_scheduler/config_flow.py`, `custom_components/shabbat_scheduler/engine.py`, `custom_components/shabbat_scheduler/const.py`, `strings.json`, `translations/en.json`, `translations/he.json`
- Create: `custom_components/shabbat_scheduler/repairs.py`
- Test: `tests/test_config_flow.py`, `tests/test_repairs.py`

**Why this is an alpha blocker:** `CANDLE_SENSOR` is hardcoded to `sensor.jewish_calendar_upcoming_candle_lighting`. That entity id derives from the Jewish Calendar config entry's *title*. Anyone who named theirs differently — or runs two, for different locations or candle-lighting offsets — gets an integration that silently derives no block at all. It is the first thing an alpha user hits.

- [ ] **Step 1: Write the failing tests**

```python
async def test_the_flow_offers_the_zmanim_sensors(hass):
    hass.states.async_set("sensor.jewish_calendar_upcoming_candle_lighting", "...")
    hass.states.async_set("sensor.jewish_calendar_upcoming_havdalah", "...")
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] == "create_entry"
    assert result["data"]["candle_sensor"] == "sensor.jewish_calendar_upcoming_candle_lighting"


async def test_custom_sensor_names_are_accepted(hass):
    """The whole point: a second Jewish Calendar entry names its sensors
    after its own title, so the defaults do not exist for everyone."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"candle_sensor": "sensor.jc_home_upcoming_candle_lighting",
         "havdalah_sensor": "sensor.jc_home_upcoming_havdalah"},
    )
    assert result["data"]["candle_sensor"] == "sensor.jc_home_upcoming_candle_lighting"


async def test_the_engine_reads_the_configured_sensors(hass):
    ...
    assert engine.current_block is not None


async def test_a_missing_sensor_raises_a_repair_issue(hass):
    """v1 logged a warning and scheduled nothing - invisible unless you
    went looking in the log on the one day you cannot."""
    ...
    issues = async_get_issue_registry(hass)
    assert issues.async_get_issue(DOMAIN, "zmanim_sensor_missing")


async def test_the_options_flow_can_change_them_later(hass):
    ...


async def test_migration_failures_raise_a_repair_issue(hass, hass_storage):
    """Naming the rules, so the user knows what to look at."""
    ...
    issue = issues.async_get_issue(DOMAIN, "unmigrated_rules")
    assert issue is not None
```

- [ ] **Step 2: Run and watch them fail**

```bash
uv run pytest tests/test_config_flow.py tests/test_repairs.py -q
```

Expected: FAIL.

- [ ] **Step 3: Implement**

The config flow gains a form with two `EntitySelector`s filtered to `domain: sensor`, defaulting to the current constant names when those entities exist. Add an options flow so they can be changed later. `const.py` keeps the names as `DEFAULT_CANDLE_SENSOR`/`DEFAULT_HAVDALAH_SENSOR`.

`engine._read_zmanim` reads the entity ids from the config entry rather than the constants. When either entity is missing, create a repair issue via `homeassistant.helpers.issue_registry.async_create_issue` with `is_fixable=False`, `severity=ERROR`, and a translation key naming what to fix — and delete it once they are readable again.

The migration issue is raised from `async_setup_entry` when `store.migration_failures` is non-empty, listing the rule ids in its placeholders.

- [ ] **Step 4: Run the tests**

```bash
uv run pytest tests/test_config_flow.py tests/test_repairs.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler/config_flow.py custom_components/shabbat_scheduler/repairs.py custom_components/shabbat_scheduler/engine.py custom_components/shabbat_scheduler/const.py custom_components/shabbat_scheduler/strings.json custom_components/shabbat_scheduler/translations tests/test_config_flow.py tests/test_repairs.py
git commit -m "feat: choose the zmanim sensors, and say so when they are missing"
```

---

### Task 11: YAML round trip

**Files:**
- Modify: `custom_components/shabbat_scheduler/yaml_io.py`, `custom_components/shabbat_scheduler/__init__.py`
- Test: `tests/test_yaml_io.py`

**Interfaces:**
- Produces: `export_yaml(defaults, rules) -> str`, `import_yaml(text) -> tuple[dict, list[Rule]]` in the v2 shape.

`yaml_io.py` stays pure, so it routes through `rule_schema.rule_from_api` only. The `import_yaml` service handler applies `ha_validation.async_validate_rule` afterwards — that is where HA-schema errors surface.

- [ ] **Step 1: Write the failing tests**

```python
def test_a_v2_rule_round_trips():
    rules = [Rule(id="a", profile=1, day="1", time=time(11, 0),
                  action="climate.set_temperature",
                  target={"entity_id": ["climate.salon"]},
                  data={"temperature": 26},
                  condition=({"condition": "state", "entity_id": "x", "state": "on"},),
                  replay=Replay(enabled=True, within=timedelta(hours=2)))]
    _defaults, back = import_yaml(export_yaml({}, rules))
    assert back[0] == rules[0]


def test_the_window_survives_as_a_duration():
    ...
    assert back[0].replay.within == timedelta(hours=2)


def test_an_empty_condition_is_not_written():
    text = export_yaml({}, [Rule(...)])
    assert "condition" not in text


def test_a_v1_file_is_rejected_with_a_useful_message():
    """Not silently half-imported."""
    with pytest.raises(ValueError, match="v1"):
        import_yaml("profiles:\n  1_day:\n    day_1:\n"
                    "      - {id: a, at: '11:00:00', action: 'on', devices: [climate.x]}\n")
```

- [ ] **Step 2: Run and watch them fail**

```bash
uv run pytest tests/test_yaml_io.py -q
```

- [ ] **Step 3: Update `yaml_io.py`** to emit and parse `action`/`target`/`data`/`condition`/`replay`, keeping `at` as the YAML spelling of `time` and preserving ids. Omit empty collections on export.

- [ ] **Step 4: Run tests and purity guard**

```bash
uv run pytest tests/test_yaml_io.py tests/test_packaging.py -q
```

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler/yaml_io.py custom_components/shabbat_scheduler/__init__.py tests/test_yaml_io.py
git commit -m "feat: YAML round trip for the v2 rule"
```

---

### Task 12: Carry the API and card so nothing breaks

**Files:**
- Modify: `custom_components/shabbat_scheduler/websocket_api.py`, `custom_components/shabbat_scheduler/switch.py`, `custom_components/shabbat_scheduler/sensor.py`, `frontend/src/*`, `frontend/test/*`
- Test: the whole suite

**Interfaces:**
- Produces: a green suite. The card need not yet *edit* the new fields — Plan 2 does that — but it must not lie about them.

**The rule for this task:** where the card cannot yet edit something, it must show the truth rather than a stale climate-shaped guess. A rule row shows its action; the edit dialog shows action, target and data read-only if necessary. **Deleting the dialog's save button is better than saving a v1-shaped payload.**

- [ ] **Step 1: Run the whole suite and inventory the breakage**

```bash
uv run pytest -q 2>&1 | tail -40
npm --prefix frontend test 2>&1 | tail -40
```

Record every failure in your report before changing anything.

- [ ] **Step 2: Update the websocket payload**

`rule_to_dict` now emits the v2 shape, so `_state_payload` follows automatically. `ws_create`/`ws_update` must call `ha_validation.async_validate_rule` after the structural layer, returning the message as a websocket error so the dialog can show it.

- [ ] **Step 3: Update the card's read path**

`types.ts`'s `RuleData` gains `action`, `target`, `data`, `condition`, `replay` and loses `devices`, `settings`, `script`, `variables`, `replay_on_restart`. `ruleBrief` describes a rule as its action plus its target, and `deviceOptions`/`selectableDevices` are deleted along with `<shabbat-device-settings>`'s climate form.

- [ ] **Step 4: Make the dialog honest**

Reduce it to the fields it can still edit correctly — time, name, icon, colour, enabled — plus a read-only display of action, target and data. Delete the device picker and the settings controls.

- [ ] **Step 5: Both suites green**

```bash
uv run pytest -q && npm --prefix frontend test && npm --prefix frontend run typecheck
```

- [ ] **Step 6: Rebuild the bundle and bump both `CARD_VERSION` constants to `0.4.0`**

```bash
npm --prefix frontend run build
```

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "refactor: carry the API and card onto the v2 rule"
```

---

### Task 13: Documentation

**Files:**
- Modify: `README.md`, `docs/known-behaviours.md`

- [ ] **Step 1: Rewrite the README's rule format section** around action/target/data/condition/replay, with a worked example that is **not** about air conditioners — a `notify` and a `scene.turn_on` read better and make the generality obvious.

- [ ] **Step 2: Add to `docs/known-behaviours.md`**

Three entries, each explaining *why*:

- **The one climate shim** — what it does, why it exists, and that the ecosystem's most-used scheduler does the same.
- **Conflicts are coarser than they were** — same target, same moment, regardless of whether the two rules agree. Without understanding the payload, "same" and "opposite" are indistinguishable.
- **Replay is opt-in and bounded** — why the old desired-state computation could not survive a generic action, and what `within` protects against.

- [ ] **Step 3: Commit**

```bash
git add README.md docs/known-behaviours.md
git commit -m "docs: the v2 rule model, and three behaviours worth knowing"
```

---

## Plan Self-Review

**Spec coverage:** action/target/data → Tasks 1, 6. The climate shim → Task 2. HA conditions → Tasks 4, 7. Replay with window and guard → Tasks 1, 8. Conflicts retuned → Task 9. Migration → Task 5. Zmanim configuration and repairs → Task 10. YAML → Task 11. Card carried along → Task 12. Docs → Task 13. Multi-domain execution tests → Task 6.

**Deliberately deferred to Plan 2** (the card) and **Plan 3** (alpha readiness): the action/target/condition/replay editors, HACS metadata, diagnostics, translation completeness. Task 12 only keeps the card honest.

**The spec conflict resolved here:** validation is split across `rule_schema.py` (pure) and `ha_validation.py` (HA-facing), because `tests/test_packaging.py` enforces the purity boundary that the spec's single-layer wording would have broken.

**Two things a reviewer should watch.** Task 6 changes the per-device lock to a per-rule lock, since a target may be an area and there is no single entity to key on — that is a real semantic change and it deserves scrutiny. And Task 9's resolver, though its signature was verified against the installed `helpers/target.py` while writing this plan, still needs a test with a **real area registered** asserting that area's entities come back: a wrong resolver returns an empty set, and an empty set reports *no conflicts* on a genuinely conflicting schedule, which is the quietest possible way to break the one safety feature this plan keeps.

**Task ordering note.** Tasks 1–3 deliberately leave the suite red — `models.py` changes shape before anything else catches up. Only Task 12 returns it to green. An implementer should not "fix" unrelated failing tests along the way; each task's own tests are its gate, and Task 12 owns the reconciliation.
