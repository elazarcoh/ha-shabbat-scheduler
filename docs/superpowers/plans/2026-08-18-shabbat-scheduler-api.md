# Shabbat Scheduler — API, Lifecycle, Logbook and Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the merged Shabbat Scheduler backend a websocket API, entities that appear and disappear with their rules, activity visible in Home Assistant's Logbook, and HACS-installable packaging.

**Architecture:** Rules become immutable so websocket CRUD cannot corrupt store state. The store gains a change-notification signal; the switch platform listens and adds/removes entities, replacing the current reload-after-import. Websocket handlers are a thin validating layer over the existing `RuleStore` and pure `block.py` helpers. A `logbook.py` platform describes the integration's own event, and the engine switches to one shared `Context` per rule application so Home Assistant attributes each device's own change back to the rule.

**Tech Stack:** Python 3.14 (uv-managed), Home Assistant 2026.8.x, `pytest` + `pytest-homeassistant-custom-component` + `pytest-asyncio`, `PyYAML`.

## Global Constraints

Every task's requirements implicitly include this section.

- Target Home Assistant **2026.8.x**, Python **3.14** (uv-managed). `requires-python = ">=3.14.2"`.
- Domain string is `shabbat_scheduler` everywhere.
- **Purity boundary:** `models.py`, `block.py`, `device_ops.py`, `const.py`, `yaml_io.py` import **zero** Home Assistant. This is load-bearing — all the tricky logic must stay testable without a running instance.
- **Fire once, never re-assert.** Nothing in this plan may introduce a code path that re-applies device state outside a rule firing. A previous third-party component was abandoned for exactly that.
- **Conflicts are warned, never resolved or rejected.** There is deliberately no precedence rule. Mutations return `warnings[]` and still succeed.
- **Malformed input IS rejected**, with `homeassistant.exceptions.ServiceValidationError`.
- **Rule ids are generated server-side.** `rules/create` ignores any client-supplied id. `import_yaml` is the sole exception — preserving ids across a round trip is its purpose, because entity `unique_id` derives from `rule.id`.
- **The master switch defaults OFF.** Nothing may change that.
- Preserve every existing protection: per-device locking, the stamp-BEFORE-call ordering in `_execute`, retry 3×30s, catch-up at-most-once and off the setup path, conflicts-decline-to-act in `async_catch_up`, the block hold and its release timer, and the persisted active block.
- All **136 existing tests** must keep passing. If a task must change one, say so explicitly and justify it.
- Run tests with `uv run pytest` (bare form works; `pythonpath = ["."]` is configured).

---

## File Structure

```
custom_components/shabbat_scheduler/
  models.py          MODIFY: Rule becomes frozen
  store.py           MODIFY: change-notification signal; validated update
  engine.py          MODIFY: one Context per rule application; self-describing event
  switch.py          MODIFY: dynamic add/remove driven by the store signal
  __init__.py        MODIFY: drop reload-after-import; register websocket handlers
  websocket_api.py   NEW: rule CRUD, defaults, preview, subscribe
  rule_schema.py     NEW: pure validation + dict<->Rule for the API layer
  logbook.py         NEW: async_describe_events for EVENT_RULE_APPLIED
  strings.json       NEW
  translations/en.json  NEW
  translations/he.json  NEW

hacs.json            NEW
README.md            MODIFY (currently empty)

tests/
  test_models.py       MODIFY: immutability
  test_websocket.py    NEW
  test_lifecycle.py    NEW
  test_logbook.py      NEW
```

**Boundary rationale:** `rule_schema.py` is pure (no HA imports) so validation is testable without a running instance and reusable by both the websocket layer and `yaml_io`. `websocket_api.py` holds only transport concerns — parse, call the store, shape the reply.

---

### Task 1: Rule becomes immutable

**Files:**
- Modify: `custom_components/shabbat_scheduler/models.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `Rule` as a frozen dataclass. All mutation must go through `dataclasses.replace`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_models.py`:

```python
import dataclasses

import pytest


def test_rule_is_frozen():
    rule = Rule(id="r1", profile=1, day=EREV, time=time(23, 0), action=Action.OFF)
    with pytest.raises(dataclasses.FrozenInstanceError):
        rule.enabled = False


def test_rule_replace_produces_a_new_rule():
    rule = Rule(id="r1", profile=1, day=EREV, time=time(23, 0), action=Action.OFF)
    updated = dataclasses.replace(rule, enabled=False)
    assert updated.enabled is False
    assert rule.enabled is True
    assert updated is not rule
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_models.py -v`
Expected: FAIL — `test_rule_is_frozen` gets no exception, because `Rule` is currently mutable.

- [ ] **Step 3: Write minimal implementation**

In `custom_components/shabbat_scheduler/models.py`, change the `Rule` decorator:

```python
@dataclass(frozen=True)
class Rule:
```

Leave every field exactly as it is.

- [ ] **Step 4: Run the whole suite**

Run: `uv run pytest -v`
Expected: PASS. All mutation already goes through `dataclasses.replace` (`store.async_update`, `block.merge_defaults`), so nothing else should need changing. **If any test fails because code assigns to a rule attribute, fix that code to use `dataclasses.replace` rather than reverting the freeze** — and report it.

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler/models.py tests/test_models.py
git commit -m "refactor: freeze Rule so CRUD cannot corrupt store state"
```

---

### Task 2: Pure rule validation

**Files:**
- Create: `custom_components/shabbat_scheduler/rule_schema.py`
- Test: `tests/test_rule_schema.py`

**Interfaces:**
- Consumes: `Action`, `EREV`, `Rule` from `.models`.
- Produces:
  - `RuleValidationError(ValueError)` — raised for malformed input.
  - `rule_from_api(data: dict, rule_id: str) -> Rule` — builds a validated `Rule`, using `rule_id` and ignoring any `id` in `data`.
  - `changes_from_api(data: dict) -> dict` — validates a partial update, returning kwargs suitable for `dataclasses.replace`. Rejects `id`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_rule_schema.py`:

```python
from datetime import time

import pytest

from custom_components.shabbat_scheduler.models import Action, EREV
from custom_components.shabbat_scheduler.rule_schema import (
    RuleValidationError,
    changes_from_api,
    rule_from_api,
)

VALID = {
    "profile": 1,
    "day": "1",
    "time": "11:00:00",
    "action": "on",
    "devices": ["climate.a"],
    "settings": {"temperature": 26},
}


def test_builds_a_rule():
    rule = rule_from_api(VALID, "generated-id")
    assert rule.id == "generated-id"
    assert rule.profile == 1
    assert rule.day == "1"
    assert rule.time == time(11, 0)
    assert rule.action is Action.ON
    assert rule.devices == ("climate.a",)


def test_client_supplied_id_is_ignored():
    rule = rule_from_api({**VALID, "id": "client-chosen"}, "generated-id")
    assert rule.id == "generated-id"


def test_erev_is_a_valid_day():
    assert rule_from_api({**VALID, "day": EREV}, "x").day == EREV


@pytest.mark.parametrize(
    "bad",
    [
        {"day": "dya_1"},
        {"day": "0"},
        {"day": "4"},
        {"profile": 0},
        {"profile": 4},
        {"time": "nonsense"},
        {"action": "sideways"},
    ],
)
def test_malformed_input_is_rejected(bad):
    with pytest.raises(RuleValidationError):
        rule_from_api({**VALID, **bad}, "x")


def test_custom_action_requires_a_script():
    with pytest.raises(RuleValidationError):
        rule_from_api({**VALID, "action": "custom"}, "x")


def test_custom_action_with_a_script_is_accepted():
    rule = rule_from_api(
        {**VALID, "action": "custom", "script": "script.demo"}, "x"
    )
    assert rule.action is Action.CUSTOM
    assert rule.script == "script.demo"


def test_changes_validates_only_supplied_keys():
    assert changes_from_api({"enabled": False}) == {"enabled": False}
    assert changes_from_api({"time": "18:00:00"})["time"] == time(18, 0)


def test_changes_rejects_id():
    with pytest.raises(RuleValidationError):
        changes_from_api({"id": "nope"})


def test_changes_rejects_unknown_field():
    with pytest.raises(RuleValidationError):
        changes_from_api({"colour": "red"})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_rule_schema.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'custom_components.shabbat_scheduler.rule_schema'`

- [ ] **Step 3: Write minimal implementation**

Create `custom_components/shabbat_scheduler/rule_schema.py`:

```python
"""Validation for rules arriving from the API. No Home Assistant imports.

Kept pure so it is testable without a running instance and usable from both
the websocket layer and YAML import.
"""

from __future__ import annotations

from datetime import time

from .models import Action, EREV, Rule

_FIELDS = {
    "profile", "day", "time", "action", "devices", "settings", "name",
    "icon", "enabled", "script", "variables", "replay_on_restart", "color",
}


class RuleValidationError(ValueError):
    """A rule as supplied cannot be built."""


def _day(value) -> str:
    text = str(value)
    if text == EREV:
        return text
    if text.isdigit() and 1 <= int(text) <= 3:
        return text
    raise RuleValidationError(
        f"day must be {EREV!r} or '1'..'3', got {value!r}"
    )


def _profile(value) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as err:
        raise RuleValidationError(f"profile must be 1..3, got {value!r}") from err
    if not 1 <= number <= 3:
        raise RuleValidationError(f"profile must be 1..3, got {value!r}")
    return number


def _time(value) -> time:
    try:
        return time.fromisoformat(str(value))
    except ValueError as err:
        raise RuleValidationError(f"time is not a valid clock time: {value!r}") from err


def _action(value) -> Action:
    try:
        return Action(value)
    except ValueError as err:
        raise RuleValidationError(
            f"action must be one of on/off/custom, got {value!r}"
        ) from err


def _coerce(field: str, value):
    if field == "day":
        return _day(value)
    if field == "profile":
        return _profile(value)
    if field == "time":
        return _time(value)
    if field == "action":
        return _action(value)
    if field == "devices":
        return tuple(value or ())
    if field in ("settings", "variables"):
        return dict(value or {})
    return value


def changes_from_api(data: dict) -> dict:
    """Validate a partial update into kwargs for dataclasses.replace."""
    if "id" in data:
        raise RuleValidationError("id cannot be changed")
    unknown = set(data) - _FIELDS
    if unknown:
        raise RuleValidationError(f"unknown field(s): {sorted(unknown)}")
    return {field: _coerce(field, value) for field, value in data.items()}


def rule_from_api(data: dict, rule_id: str) -> Rule:
    """Build a validated Rule. Any client-supplied id is ignored."""
    payload = {key: value for key, value in data.items() if key != "id"}
    unknown = set(payload) - _FIELDS
    if unknown:
        raise RuleValidationError(f"unknown field(s): {sorted(unknown)}")

    for required in ("profile", "day", "time", "action"):
        if required not in payload:
            raise RuleValidationError(f"missing required field: {required}")

    kwargs = {field: _coerce(field, value) for field, value in payload.items()}
    rule = Rule(id=rule_id, **kwargs)

    if rule.action is Action.CUSTOM and not rule.script:
        raise RuleValidationError("a custom action requires a script")
    return rule
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_rule_schema.py -v`
Expected: PASS, 11 tests

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler/rule_schema.py tests/test_rule_schema.py
git commit -m "feat: pure validation for rules arriving from the API"
```

---

### Task 3: Store change signal and validated update

**Files:**
- Modify: `custom_components/shabbat_scheduler/store.py`
- Modify: `custom_components/shabbat_scheduler/const.py`
- Test: `tests/test_store.py`

**Interfaces:**
- Consumes: `RuleStore`.
- Produces:
  - `SIGNAL_RULES_CHANGED = "shabbat_scheduler_rules_changed"` in `const.py`.
  - `RuleStore.async_set_change_listener(callback)` — registers one callback invoked after any change to the rule set. Store stays HA-free of dispatcher specifics; the caller decides what to do.
  - `RuleStore.async_update(rule_id, **changes)` raises `KeyError` when no such rule exists.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_store.py`:

```python
import pytest


async def test_change_listener_fires_on_add_update_delete(hass):
    store = RuleStore(hass)
    await store.async_load()
    calls = []
    store.async_set_change_listener(lambda: calls.append(1))

    rule = Rule(id="r1", profile=1, day="1", time=time(11, 0), action=Action.ON)
    await store.async_add(rule)
    await store.async_update("r1", enabled=False)
    await store.async_delete("r1")
    await store.async_replace_all({}, [rule])

    assert len(calls) == 4


async def test_change_listener_fires_for_enabled_and_dry_run(hass):
    """The card renders both, so both must push."""
    store = RuleStore(hass)
    await store.async_load()
    calls = []
    store.async_set_change_listener(lambda: calls.append(1))

    await store.async_set_enabled(True)
    await store.async_set_dry_run(True)
    assert len(calls) == 2


async def test_change_listener_does_not_fire_for_active_block(hass):
    """The block in force is engine bookkeeping, not user-visible state."""
    store = RuleStore(hass)
    await store.async_load()
    calls = []
    store.async_set_change_listener(lambda: calls.append(1))

    await store.async_set_active_block(
        datetime(2026, 8, 14, 18, 44, tzinfo=UTC),
        datetime(2026, 8, 15, 20, 1, tzinfo=UTC),
    )
    assert calls == []


async def test_update_of_unknown_rule_raises(hass):
    store = RuleStore(hass)
    await store.async_load()
    with pytest.raises(KeyError):
        await store.async_update("nope", enabled=False)
```

Add these imports at the top of the file if absent:

```python
from datetime import UTC, datetime
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_store.py -v`
Expected: FAIL with `AttributeError: 'RuleStore' object has no attribute 'async_set_change_listener'`

- [ ] **Step 3: Write minimal implementation**

Add to `custom_components/shabbat_scheduler/const.py`:

```python
SIGNAL_RULES_CHANGED = "shabbat_scheduler_rules_changed"
```

In `custom_components/shabbat_scheduler/store.py`, add to `__init__`:

```python
        self._on_change: Callable[[], None] | None = None
```

with `from collections.abc import Callable` at the top, and add:

```python
    def async_set_change_listener(self, listener: Callable[[], None]) -> None:
        """Register the one callback fired after any rule-set change.

        The store deliberately does not know about dispatchers or entities -
        the caller decides what a change means.
        """
        self._on_change = listener

    def _notify_change(self) -> None:
        if self._on_change is not None:
            self._on_change()
```

Then call `self._notify_change()` at the end of `async_add`, `async_update`,
`async_delete`, `async_replace_all`, `async_set_enabled` and
`async_set_dry_run` — everything the card renders.

Do **not** call it in `async_set_active_block` or `async_clear_active_block`:
the block in force is engine bookkeeping, invisible to the card, and those run
on every refresh.

Change `async_update` to raise when the rule is absent:

```python
    async def async_update(self, rule_id: str, **changes) -> None:
        if not any(rule.id == rule_id for rule in self._rules):
            raise KeyError(rule_id)
        self._rules = [
            replace(rule, **changes) if rule.id == rule_id else rule
            for rule in self._rules
        ]
        await self.async_save()
        self._notify_change()
```

- [ ] **Step 4: Run the whole suite**

Run: `uv run pytest -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler/store.py custom_components/shabbat_scheduler/const.py tests/test_store.py
git commit -m "feat: store change-notification signal and validated update"
```

---

### Task 4: Dynamic switch entity lifecycle

**Files:**
- Modify: `custom_components/shabbat_scheduler/switch.py`
- Modify: `custom_components/shabbat_scheduler/__init__.py`
- Test: `tests/test_lifecycle.py`

**Interfaces:**
- Consumes: `SIGNAL_RULES_CHANGED`, `RuleStore.async_set_change_listener`.
- Produces: switch entities that appear when a rule is added and disappear when it is deleted, with no config-entry reload. The `async_schedule_reload` call in `_import_yaml` is removed.

- [ ] **Step 1: Write the failing test**

Create `tests/test_lifecycle.py`:

```python
from datetime import time

from homeassistant.helpers import entity_registry as er
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


def _switch_for(hass, entry, rule_id):
    return er.async_get(hass).async_get_entity_id(
        "switch", DOMAIN, f"{entry.entry_id}_rule_{rule_id}"
    )


async def test_adding_a_rule_creates_its_switch(hass):
    entry = await _setup(hass)
    store = hass.data[DOMAIN][entry.entry_id]["store"]
    assert _switch_for(hass, entry, "new") is None

    await store.async_add(
        Rule(id="new", profile=1, day="1", time=time(11, 0), action=Action.ON)
    )
    await hass.async_block_till_done()

    entity_id = _switch_for(hass, entry, "new")
    assert entity_id is not None
    assert hass.states.get(entity_id) is not None


async def test_deleting_a_rule_removes_its_switch(hass):
    entry = await _setup(hass, [
        Rule(id="gone", profile=1, day="1", time=time(11, 0), action=Action.ON),
    ])
    assert _switch_for(hass, entry, "gone") is not None

    store = hass.data[DOMAIN][entry.entry_id]["store"]
    await store.async_delete("gone")
    await hass.async_block_till_done()

    assert _switch_for(hass, entry, "gone") is None


async def test_surviving_rule_keeps_its_entity_across_replace_all(hass):
    keep = Rule(id="keep", profile=1, day="1", time=time(11, 0), action=Action.ON)
    entry = await _setup(hass, [keep])
    before = _switch_for(hass, entry, "keep")

    store = hass.data[DOMAIN][entry.entry_id]["store"]
    await store.async_replace_all({}, [
        keep,
        Rule(id="added", profile=1, day="1", time=time(18, 0), action=Action.OFF),
    ])
    await hass.async_block_till_done()

    assert _switch_for(hass, entry, "keep") == before
    assert _switch_for(hass, entry, "added") is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_lifecycle.py -v`
Expected: FAIL — `test_adding_a_rule_creates_its_switch` finds no entity, because switches are only built at platform setup.

- [ ] **Step 3: Write minimal implementation**

In `custom_components/shabbat_scheduler/switch.py`, replace the body of `async_setup_entry` after the entities list is first created with a version that tracks known rule ids and syncs on the signal:

```python
    known: set[str] = set()

    @callback
    def _sync() -> None:
        """Add entities for new rules, remove those whose rule is gone."""
        current = {rule.id for rule in store.rules}

        new = [
            RuleSwitch(entry, store, engine, rule)
            for rule in store.rules
            if rule.id not in known
        ]
        if new:
            async_add_entities(new)
        known.update(current)

        registry = er.async_get(hass)
        for rule_id in known - current:
            unique_id = f"{entry.entry_id}_rule_{rule_id}"
            entity_id = registry.async_get_entity_id("switch", DOMAIN, unique_id)
            if entity_id:
                registry.async_remove(entity_id)
        known.intersection_update(current)

    async_add_entities([MasterSwitch(entry, store, engine)])
    _sync()
    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_RULES_CHANGED, _sync)
    )
```

Add these imports to `switch.py` if not already present:

```python
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import SIGNAL_RULES_CHANGED
```

The store holds only one change listener, and more than one consumer needs to
react, so the store's listener drives a dispatcher signal and everything else
connects to that. In `custom_components/shabbat_scheduler/__init__.py`, inside
`async_setup_entry` just after the store is created:

```python
    @callback
    def _rules_changed() -> None:
        async_dispatcher_send(hass, SIGNAL_RULES_CHANGED)

    store.async_set_change_listener(_rules_changed)
```

with these imports added:

```python
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import SIGNAL_RULES_CHANGED
```

Then delete the `hass.config_entries.async_schedule_reload(entry.entry_id)`
line from `_import_yaml` — the signal now handles it — leaving the
`store.async_replace_all(...)` and `engine.async_refresh()` calls in place.

- [ ] **Step 4: Run the whole suite**

Run: `uv run pytest -v`
Expected: PASS, including the existing `test_import_yaml_rebuilds_the_rule_switches`.

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler/switch.py custom_components/shabbat_scheduler/__init__.py tests/test_lifecycle.py
git commit -m "feat: add and remove rule switches without reloading the entry"
```

---

### Task 5: Websocket read commands

**Files:**
- Create: `custom_components/shabbat_scheduler/websocket_api.py`
- Modify: `custom_components/shabbat_scheduler/__init__.py`
- Test: `tests/test_websocket.py`

**Interfaces:**
- Consumes: `RuleStore`, `ShabbatEngine`, `block.find_conflicts`, `block.merge_defaults`, `block.has_profile`, `block.resolve_rules`, `store.rule_to_dict`.
- Produces:
  - `async_register(hass)` — registers every websocket command for this integration.
  - `shabbat_scheduler/rules/list` → `{defaults, rules, warnings}`
  - `shabbat_scheduler/preview` → `{profile, rules, conflicts, warnings}`

- [ ] **Step 1: Write the failing test**

Create `tests/test_websocket.py`:

```python
from datetime import time

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shabbat_scheduler.const import DOMAIN
from custom_components.shabbat_scheduler.models import Action, Rule
from custom_components.shabbat_scheduler.store import RuleStore

ZMANIM = {
    "sensor.jewish_calendar_upcoming_candle_lighting": "2026-08-14T15:44:00+00:00",
    "sensor.jewish_calendar_upcoming_havdalah": "2026-08-15T17:01:00+00:00",
}


async def _setup(hass, rules=(), defaults=None):
    await hass.config.async_set_time_zone("Asia/Jerusalem")
    for entity_id, state in ZMANIM.items():
        hass.states.async_set(entity_id, state)
    store = RuleStore(hass)
    await store.async_load()
    await store.async_replace_all(defaults or {}, list(rules))
    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_rules_list_returns_rules_and_defaults(hass, hass_ws_client):
    await _setup(
        hass,
        [Rule(id="r1", profile=1, day="1", time=time(11, 0), action=Action.ON,
              devices=("climate.a",))],
        defaults={"temperature": 26},
    )
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "shabbat_scheduler/rules/list"})
    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"]["defaults"] == {"temperature": 26}
    assert [r["id"] for r in msg["result"]["rules"]] == ["r1"]
    assert msg["result"]["warnings"] == []


async def test_rules_list_reports_conflicts_as_warnings(hass, hass_ws_client):
    await _setup(hass, [
        Rule(id="a", profile=1, day="1", time=time(18, 0), action=Action.ON,
             devices=("climate.a",)),
        Rule(id="b", profile=1, day="1", time=time(18, 0), action=Action.OFF,
             devices=("climate.a",)),
    ])
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "shabbat_scheduler/rules/list"})
    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"]["warnings"]


async def test_preview_resolves_the_upcoming_block(hass, hass_ws_client):
    await _setup(hass, [
        Rule(id="r1", profile=1, day="1", time=time(11, 0), action=Action.ON,
             devices=("climate.a",)),
    ])
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "shabbat_scheduler/preview"})
    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"]["profile"] == 1
    assert len(msg["result"]["rules"]) == 1
    assert msg["result"]["rules"][0]["action"] == "on"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_websocket.py -v`
Expected: FAIL — the commands are not registered, so each reply has `success: False` with `unknown_command`.

- [ ] **Step 3: Write minimal implementation**

Create `custom_components/shabbat_scheduler/websocket_api.py`:

```python
"""Websocket commands. Transport only - logic lives in block.py/store.py."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util

from .block import find_conflicts, has_profile, merge_defaults, resolve_rules
from .const import DOMAIN
from .store import rule_to_dict


def _entry_data(hass: HomeAssistant) -> dict | None:
    """The single config entry's data, or None when not set up."""
    entries = list(hass.data.get(DOMAIN, {}).values())
    return entries[0] if entries else None


def _conflict_warnings(rules) -> list[dict]:
    return [
        {
            "kind": "conflict",
            "device": conflict.device,
            "profile": conflict.profile,
            "day": conflict.day,
            "time": conflict.time.isoformat(),
            "rule_ids": list(conflict.rule_ids),
        }
        for conflict in find_conflicts(rules)
    ]


def _state_payload(store) -> dict:
    """Everything the card renders. One shape, used by list and subscribe."""
    return {
        "defaults": store.defaults,
        "rules": [rule_to_dict(rule) for rule in store.rules],
        "enabled": store.enabled,
        "dry_run": store.dry_run,
        "warnings": _conflict_warnings(store.rules),
    }


@callback
@websocket_api.websocket_command({vol.Required("type"): "shabbat_scheduler/rules/list"})
def ws_list(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    data = _entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_set_up", "Integration is not set up")
        return
    connection.send_result(msg["id"], _state_payload(data["store"]))


@callback
@websocket_api.websocket_command(
    {
        vol.Required("type"): "shabbat_scheduler/preview",
        vol.Optional("block_length"): vol.All(int, vol.Range(1, 3)),
    }
)
def ws_preview(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    data = _entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_set_up", "Integration is not set up")
        return
    store, engine = data["store"], data["engine"]
    block = engine.current_block

    if block is None:
        connection.send_result(
            msg["id"],
            {
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
            },
        )
        return

    rules = [merge_defaults(store.defaults, rule) for rule in store.rules]
    warnings: list[dict] = []
    if not has_profile(rules, block.length):
        warnings.append(
            {
                "kind": "no_profile",
                "message": f"No enabled rules for a {block.length}-day block.",
            }
        )

    tz = dt_util.get_time_zone(hass.config.time_zone)
    connection.send_result(
        msg["id"],
        {
            "profile": block.length,
            "rules": [
                {
                    "when": item.when.isoformat(),
                    "rule_id": item.rule.id,
                    "name": item.rule.name,
                    "action": item.rule.action.value,
                    "devices": list(item.rule.devices),
                }
                for item in resolve_rules(rules, block, tz)
            ],
            "conflicts": _conflict_warnings(rules),
            "warnings": warnings,
        },
    )


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register every websocket command for this integration."""
    websocket_api.async_register_command(hass, ws_list)
    websocket_api.async_register_command(hass, ws_preview)
```

In `custom_components/shabbat_scheduler/__init__.py`, import it and call it once in `async_setup_entry`, before forwarding platforms:

```python
from . import websocket_api

    websocket_api.async_register(hass)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_websocket.py -v`
Expected: PASS, 3 tests

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler/websocket_api.py custom_components/shabbat_scheduler/__init__.py tests/test_websocket.py
git commit -m "feat: websocket rules/list and preview"
```

---

### Task 6: Websocket mutation commands

**Files:**
- Modify: `custom_components/shabbat_scheduler/websocket_api.py`
- Test: `tests/test_websocket.py`

**Interfaces:**
- Consumes: `rule_schema.rule_from_api`, `rule_schema.changes_from_api`, `rule_schema.RuleValidationError`.
- Produces:
  - `shabbat_scheduler/rules/create` → `{rule, warnings}`
  - `shabbat_scheduler/rules/update` → `{rule, warnings}`
  - `shabbat_scheduler/rules/delete` → `{ok: True}`
  - `shabbat_scheduler/defaults/update` → `{defaults, warnings}`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_websocket.py`:

```python
NEW_RULE = {
    "profile": 1,
    "day": "1",
    "time": "11:00:00",
    "action": "on",
    "devices": ["climate.a"],
}


async def test_create_generates_an_id_and_persists(hass, hass_ws_client):
    await _setup(hass)
    client = await hass_ws_client(hass)
    await client.send_json(
        {"id": 1, "type": "shabbat_scheduler/rules/create", "rule": NEW_RULE}
    )
    msg = await client.receive_json()
    assert msg["success"]
    rule_id = msg["result"]["rule"]["id"]
    assert rule_id

    reloaded = RuleStore(hass)
    await reloaded.async_load()
    assert [r.id for r in reloaded.rules] == [rule_id]


async def test_create_ignores_a_client_supplied_id(hass, hass_ws_client):
    await _setup(hass)
    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 1,
            "type": "shabbat_scheduler/rules/create",
            "rule": {**NEW_RULE, "id": "client-chosen"},
        }
    )
    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"]["rule"]["id"] != "client-chosen"


async def test_create_rejects_malformed_input(hass, hass_ws_client):
    await _setup(hass)
    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 1,
            "type": "shabbat_scheduler/rules/create",
            "rule": {**NEW_RULE, "day": "dya_1"},
        }
    )
    msg = await client.receive_json()
    assert not msg["success"]

    reloaded = RuleStore(hass)
    await reloaded.async_load()
    assert reloaded.rules == []


async def test_create_succeeds_but_warns_on_a_conflict(hass, hass_ws_client):
    await _setup(hass, [
        Rule(id="a", profile=1, day="1", time=time(11, 0), action=Action.OFF,
             devices=("climate.a",)),
    ])
    client = await hass_ws_client(hass)
    await client.send_json(
        {"id": 1, "type": "shabbat_scheduler/rules/create", "rule": NEW_RULE}
    )
    msg = await client.receive_json()

    assert msg["success"]  # conflicts warn, they never reject
    assert msg["result"]["warnings"]


async def test_update_changes_only_supplied_fields(hass, hass_ws_client):
    await _setup(hass, [
        Rule(id="r1", profile=1, day="1", time=time(11, 0), action=Action.ON,
             devices=("climate.a",)),
    ])
    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 1,
            "type": "shabbat_scheduler/rules/update",
            "rule_id": "r1",
            "changes": {"enabled": False},
        }
    )
    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"]["rule"]["enabled"] is False
    assert msg["result"]["rule"]["time"] == "11:00:00"


async def test_update_of_unknown_rule_errors(hass, hass_ws_client):
    await _setup(hass)
    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 1,
            "type": "shabbat_scheduler/rules/update",
            "rule_id": "nope",
            "changes": {"enabled": False},
        }
    )
    msg = await client.receive_json()
    assert not msg["success"]


async def test_delete_removes_the_rule(hass, hass_ws_client):
    await _setup(hass, [
        Rule(id="r1", profile=1, day="1", time=time(11, 0), action=Action.ON),
    ])
    client = await hass_ws_client(hass)
    await client.send_json(
        {"id": 1, "type": "shabbat_scheduler/rules/delete", "rule_id": "r1"}
    )
    msg = await client.receive_json()
    assert msg["success"]

    reloaded = RuleStore(hass)
    await reloaded.async_load()
    assert reloaded.rules == []


async def test_defaults_update_persists(hass, hass_ws_client):
    await _setup(hass)
    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 1,
            "type": "shabbat_scheduler/defaults/update",
            "defaults": {"temperature": 24},
        }
    )
    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"]["defaults"] == {"temperature": 24}

    reloaded = RuleStore(hass)
    await reloaded.async_load()
    assert reloaded.defaults == {"temperature": 24}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_websocket.py -v`
Expected: FAIL — the mutation commands are not registered.

- [ ] **Step 3: Write minimal implementation**

Add to `custom_components/shabbat_scheduler/websocket_api.py`:

```python
import uuid

from dataclasses import replace

from .rule_schema import RuleValidationError, changes_from_api, rule_from_api


@websocket_api.websocket_command(
    {
        vol.Required("type"): "shabbat_scheduler/rules/create",
        vol.Required("rule"): dict,
    }
)
@websocket_api.async_response
async def ws_create(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    data = _entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_set_up", "Integration is not set up")
        return
    store = data["store"]
    try:
        rule = rule_from_api(msg["rule"], uuid.uuid4().hex)
    except RuleValidationError as err:
        connection.send_error(msg["id"], "invalid_rule", str(err))
        return

    await store.async_add(rule)
    connection.send_result(
        msg["id"],
        {"rule": rule_to_dict(rule), "warnings": _conflict_warnings(store.rules)},
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "shabbat_scheduler/rules/update",
        vol.Required("rule_id"): str,
        vol.Required("changes"): dict,
    }
)
@websocket_api.async_response
async def ws_update(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    data = _entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_set_up", "Integration is not set up")
        return
    store = data["store"]
    try:
        changes = changes_from_api(msg["changes"])
    except RuleValidationError as err:
        connection.send_error(msg["id"], "invalid_rule", str(err))
        return

    try:
        await store.async_update(msg["rule_id"], **changes)
    except KeyError:
        connection.send_error(msg["id"], "not_found", f"No rule {msg['rule_id']}")
        return

    updated = next(r for r in store.rules if r.id == msg["rule_id"])
    connection.send_result(
        msg["id"],
        {"rule": rule_to_dict(updated), "warnings": _conflict_warnings(store.rules)},
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "shabbat_scheduler/rules/delete",
        vol.Required("rule_id"): str,
    }
)
@websocket_api.async_response
async def ws_delete(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    data = _entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_set_up", "Integration is not set up")
        return
    await data["store"].async_delete(msg["rule_id"])
    connection.send_result(msg["id"], {"ok": True})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "shabbat_scheduler/defaults/update",
        vol.Required("defaults"): dict,
    }
)
@websocket_api.async_response
async def ws_defaults(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    data = _entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_set_up", "Integration is not set up")
        return
    store = data["store"]
    await store.async_replace_all(msg["defaults"], store.rules)
    connection.send_result(
        msg["id"],
        {"defaults": store.defaults, "warnings": _conflict_warnings(store.rules)},
    )
```

And extend `async_register`:

```python
    websocket_api.async_register_command(hass, ws_create)
    websocket_api.async_register_command(hass, ws_update)
    websocket_api.async_register_command(hass, ws_delete)
    websocket_api.async_register_command(hass, ws_defaults)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_websocket.py -v`
Expected: PASS, 11 tests

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler/websocket_api.py tests/test_websocket.py
git commit -m "feat: websocket rule create, update, delete and defaults"
```

---

### Task 7: Websocket subscription

**Files:**
- Modify: `custom_components/shabbat_scheduler/websocket_api.py`
- Test: `tests/test_websocket.py`

**Interfaces:**
- Consumes: `SIGNAL_RULES_CHANGED`, `homeassistant.helpers.dispatcher`.
- Produces: `shabbat_scheduler/subscribe` — sends the same shape as `rules/list` on every rule-set change, so the card never polls.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_websocket.py`:

```python
async def test_subscribe_pushes_on_change(hass, hass_ws_client):
    await _setup(hass)
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "shabbat_scheduler/subscribe"})

    ack = await client.receive_json()
    assert ack["success"]

    store = RuleStore(hass)
    await store.async_load()
    entry_store = list(hass.data[DOMAIN].values())[0]["store"]
    await entry_store.async_add(
        Rule(id="pushed", profile=1, day="1", time=time(11, 0), action=Action.ON)
    )
    await hass.async_block_till_done()

    event = await client.receive_json()
    assert event["type"] == "event"
    assert [r["id"] for r in event["event"]["rules"]] == ["pushed"]


async def test_subscribe_stops_pushing_after_unsubscribe(hass, hass_ws_client):
    await _setup(hass)
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "shabbat_scheduler/subscribe"})
    assert (await client.receive_json())["success"]

    await client.send_json({"id": 2, "type": "unsubscribe_events", "subscription": 1})
    assert (await client.receive_json())["success"]

    entry_store = list(hass.data[DOMAIN].values())[0]["store"]
    await entry_store.async_add(
        Rule(id="quiet", profile=1, day="1", time=time(11, 0), action=Action.ON)
    )
    await hass.async_block_till_done()

    await client.send_json({"id": 3, "type": "shabbat_scheduler/rules/list"})
    msg = await client.receive_json()
    assert msg["id"] == 3  # no pushed event arrived in between
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_websocket.py -k subscribe -v`
Expected: FAIL — `shabbat_scheduler/subscribe` is not a known command.

- [ ] **Step 3: Write minimal implementation**

The dispatcher signal already exists from Task 4 — this task only adds a second
consumer of it. Add the subscription command to `websocket_api.py`:

```python
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import SIGNAL_RULES_CHANGED


@callback
@websocket_api.websocket_command({vol.Required("type"): "shabbat_scheduler/subscribe"})
def ws_subscribe(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    data = _entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_set_up", "Integration is not set up")
        return
    store = data["store"]

    @callback
    def _forward() -> None:
        connection.send_message(
            websocket_api.event_message(msg["id"], _state_payload(store))
        )

    connection.subscriptions[msg["id"]] = async_dispatcher_connect(
        hass, SIGNAL_RULES_CHANGED, _forward
    )
    connection.send_result(msg["id"])
```

and register it in `async_register`:

```python
    websocket_api.async_register_command(hass, ws_subscribe)
```

- [ ] **Step 4: Run the whole suite**

Run: `uv run pytest -v`
Expected: PASS, including `tests/test_lifecycle.py`, which now runs through the dispatcher.

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler tests/test_websocket.py
git commit -m "feat: websocket subscription so the card never polls"
```

---

### Task 8: Self-describing event and shared context

**Files:**
- Modify: `custom_components/shabbat_scheduler/engine.py`
- Modify: `custom_components/shabbat_scheduler/const.py`
- Modify: `custom_components/shabbat_scheduler/sensor.py`
- Test: `tests/test_engine.py`

**Why `sensor.py` changes here.** `LastRunSensor` is push-based: it listens for
`EVENT_RULE_APPLIED` and snapshots `engine.last_run` / `last_run_at`
synchronously inside that callback. That worked only because the event used to
fire *after* the results existed. Moving it before the calls — which logbook
attribution requires — would leave that snapshot permanently stale.

Both requirements are legitimate, so they get **two** signals:
`EVENT_RULE_APPLIED` fires **before** (self-describing, for attribution and the
logbook row), and a new `EVENT_RULE_COMPLETED` fires **after** (carrying the
results, for the sensor). Only the former is described to the logbook, so no
duplicate row appears.

This also closes a latent gap: `async_catch_up` sets `last_run` but fired no
event at all, so the sensor never reflected a restart catch-up. It now fires
`EVENT_RULE_COMPLETED` too.

**Interfaces:**
- Consumes: `EVENT_RULE_APPLIED`.
- Produces:
  - `EVENT_RULE_COMPLETED = "shabbat_scheduler_rule_completed"` in `const.py`.
  - `EVENT_RULE_APPLIED` is fired **before** the service calls, carrying `{rule_id, name, action, devices, dry_run}`.
  - `EVENT_RULE_COMPLETED` is fired **after**, carrying `{rule_id, results}`; `LastRunSensor` listens for this instead.
  - One `Context` per rule application, passed to every service call for that rule, so Home Assistant can attribute each device's change back to the rule.
  - `is_our_context(entity_id, context)` keeps working.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_engine.py`:

```python
async def test_event_is_self_describing_and_fires_before_the_calls(hass, engine):
    """The logbook renders historical events, so the payload must stand alone."""
    hass.states.async_set("input_boolean.t", "off")
    order: list[str] = []
    events: list = []

    @callback
    def _event(event):
        events.append(event)
        order.append("event")

    hass.bus.async_listen(EVENT_RULE_APPLIED, _event)

    @callback
    def _call(event):
        order.append("call")

    hass.bus.async_listen(EVENT_CALL_SERVICE, _call)

    rule = _rule(action=Action.ON, devices=("input_boolean.t",))
    rule = dataclasses.replace(rule, name="בוקר שבת")
    await engine.async_apply_rule(rule)
    await hass.async_block_till_done()

    assert events[0].data["rule_id"] == rule.id
    assert events[0].data["name"] == "בוקר שבת"
    assert events[0].data["action"] == "on"
    assert events[0].data["devices"] == ["input_boolean.t"]
    assert order[0] == "event"  # must precede the calls, or attribution breaks


async def test_all_calls_of_one_rule_share_the_events_context(hass, engine):
    hass.states.async_set("input_boolean.t", "off")
    hass.states.async_set("input_boolean.salon", "off")
    contexts: list[str] = []
    event_context: list[str] = []

    @callback
    def _event(event):
        event_context.append(event.context.id)

    hass.bus.async_listen(EVENT_RULE_APPLIED, _event)

    @callback
    def _call(event):
        contexts.append(event.context.id)

    hass.bus.async_listen(EVENT_CALL_SERVICE, _call)

    await engine.async_apply_rule(
        _rule(action=Action.ON, devices=("input_boolean.t", "input_boolean.salon"))
    )
    await hass.async_block_till_done()

    assert len(set(contexts)) == 1
    assert contexts[0] == event_context[0]


async def test_concurrent_rules_get_distinct_contexts(hass, engine):
    """Two rules applied at once must not share or overwrite each other's."""
    hass.states.async_set("input_boolean.t", "off")
    hass.states.async_set("input_boolean.salon", "off")
    seen: list[str] = []

    @callback
    def _event(event):
        seen.append(event.context.id)

    hass.bus.async_listen(EVENT_RULE_APPLIED, _event)

    await asyncio.gather(
        engine.async_apply_rule(
            dataclasses.replace(
                _rule(action=Action.ON, devices=("input_boolean.t",)), id="one"
            )
        ),
        engine.async_apply_rule(
            dataclasses.replace(
                _rule(action=Action.OFF, devices=("input_boolean.salon",)), id="two"
            )
        ),
    )
    await hass.async_block_till_done()

    assert len(seen) == 2
    assert len(set(seen)) == 2
```

Add `import asyncio` to the test file's imports if absent.

Add these imports to the top of `tests/test_engine.py` if absent:

```python
import dataclasses

from homeassistant.const import EVENT_CALL_SERVICE
from homeassistant.core import callback

from custom_components.shabbat_scheduler.const import EVENT_RULE_APPLIED
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_engine.py -k "self_describing or share" -v`
Expected: FAIL — the event fires after the calls and carries no `name`, and each device call has its own context.

- [ ] **Step 3: Write minimal implementation**

In `custom_components/shabbat_scheduler/engine.py`, rewrite `async_apply_rule`:

```python
    async def async_apply_rule(self, rule: Rule, force: bool = False) -> list[dict]:
        """Apply one rule, returning a per-attribute outcome report.

        The event is fired BEFORE the calls and carries everything needed to
        describe itself. The logbook renders historical events, so a describe
        function cannot look the rule up - it may have been renamed or deleted
        by then. Firing first is also what lets Home Assistant attribute each
        device's own change back to this rule, the same way automations do.
        """
        context = Context()

        self.hass.bus.async_fire(
            EVENT_RULE_APPLIED,
            {
                "rule_id": rule.id,
                "name": rule.name,
                "action": rule.action.value,
                "devices": list(rule.devices),
                "dry_run": self.store.dry_run,
            },
            context=context,
        )

        if rule.action is Action.CUSTOM:
            results = await self._apply_custom(rule, context)
        else:
            results = []
            for entity_id in rule.devices:
                results.extend(
                    await self._apply_device(rule, entity_id, force, context)
                )

        self.last_run = results
        self.last_run_at = dt_util.utcnow()
        # Fired after the results exist, for consumers that need them.
        # EVENT_RULE_APPLIED cannot carry them: it must precede the calls so
        # Home Assistant can attribute each device's change back to this rule.
        self.hass.bus.async_fire(
            EVENT_RULE_COMPLETED, {"rule_id": rule.id, "results": results}
        )
        return results
```

Add `EVENT_RULE_COMPLETED = "shabbat_scheduler_rule_completed"` to `const.py`
and import it in `engine.py`.

In `async_catch_up`, after it sets `self.last_run` and `self.last_run_at`, fire
the same event with `rule_id=None` — the sensor previously never reflected a
restart catch-up at all:

```python
        self.hass.bus.async_fire(
            EVENT_RULE_COMPLETED, {"rule_id": None, "results": results}
        )
```

In `sensor.py`, change `LastRunSensor.async_added_to_hass` to listen for
`EVENT_RULE_COMPLETED` instead of `EVENT_RULE_APPLIED`, leaving everything else
about that entity — `_attr_should_poll = False`, the `async_on_remove`
teardown, `native_value`, `extra_state_attributes` — exactly as it is.

The context is threaded through as a parameter rather than held on the engine.
Two rules can be applied concurrently — the suite already exercises exactly
that — and a single instance attribute would let one overwrite the other's
context mid-flight, misattributing a device change to the wrong rule.

Change the three signatures to carry it, and replace `_new_context` with a
recorder:

```python
    async def _apply_custom(self, rule: Rule, context: Context) -> list[dict]:
```

```python
    async def _apply_device(
        self, rule: Rule, entity_id: str, force: bool, context: Context
    ) -> list[dict]:
```

```python
    async def _execute(self, entity_id: str, call, context: Context) -> dict:
```

```python
    def _record_context(self, entity_id: str, context: Context) -> Context:
        """Remember a context as ours, for the given entity.

        Retaining our own context ids is what lets a future enforcement
        feature tell "we changed it" from "a human changed it" when looking
        at a state_changed event.
        """
        self._our_contexts[entity_id].append(context.id)
        return context
```

At each `hass.services.async_call` site inside `_execute` and `_apply_custom`,
pass `context=self._record_context(entity_id, context)` — for `_apply_custom`
use `rule.script` as the key, matching what it does today. Delete
`_new_context`; `is_our_context` is unchanged.

- [ ] **Step 4: Run the whole suite**

Run: `uv run pytest -v`
Expected: PASS. The existing `test_engine_recognises_its_own_context` still holds, because ids are still recorded per device.

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler/engine.py tests/test_engine.py
git commit -m "feat: self-describing rule event fired before its calls, one shared context"
```

---

### Task 9: Logbook platform

**Files:**
- Create: `custom_components/shabbat_scheduler/logbook.py`
- Test: `tests/test_logbook.py`

**Interfaces:**
- Consumes: `EVENT_RULE_APPLIED`, `DOMAIN`.
- Produces: `async_describe_events(hass, async_describe_event)` — renders `EVENT_RULE_APPLIED` as a logbook row.

- [ ] **Step 1: Write the failing test**

Create `tests/test_logbook.py`:

```python
from homeassistant.components.logbook import DOMAIN as LOGBOOK_DOMAIN
from homeassistant.core import Event
from homeassistant.setup import async_setup_component

from custom_components.shabbat_scheduler.const import DOMAIN, EVENT_RULE_APPLIED
from custom_components.shabbat_scheduler.logbook import async_describe_events


async def test_describe_renders_a_named_rule(hass):
    described = {}

    def _capture(domain, event_type, describe):
        described[event_type] = describe

    async_describe_events(hass, _capture)
    assert EVENT_RULE_APPLIED in described

    event = Event(
        EVENT_RULE_APPLIED,
        {
            "rule_id": "r1",
            "name": "בוקר שבת",
            "action": "on",
            "devices": ["climate.a", "climate.b"],
            "dry_run": False,
        },
    )
    result = described[EVENT_RULE_APPLIED](event)

    assert "בוקר שבת" in result["message"]
    assert "climate.a" in result["message"]
    assert result["name"]


async def test_describe_handles_an_unnamed_rule(hass):
    described = {}
    async_describe_events(hass, lambda d, e, f: described.__setitem__(e, f))

    event = Event(
        EVENT_RULE_APPLIED,
        {
            "rule_id": "r1",
            "name": None,
            "action": "off",
            "devices": ["climate.a"],
            "dry_run": False,
        },
    )
    result = described[EVENT_RULE_APPLIED](event)
    assert result["message"]


async def test_describe_marks_a_dry_run(hass):
    described = {}
    async_describe_events(hass, lambda d, e, f: described.__setitem__(e, f))

    event = Event(
        EVENT_RULE_APPLIED,
        {
            "rule_id": "r1",
            "name": "בוקר שבת",
            "action": "on",
            "devices": ["climate.a"],
            "dry_run": True,
        },
    )
    result = described[EVENT_RULE_APPLIED](event)
    assert "dry run" in result["message"].lower()


async def test_logbook_component_picks_up_the_platform(hass):
    """The platform must be discoverable, not merely importable."""
    assert await async_setup_component(hass, LOGBOOK_DOMAIN, {LOGBOOK_DOMAIN: {}})
    await hass.async_block_till_done()
    assert LOGBOOK_DOMAIN in hass.config.components
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_logbook.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'custom_components.shabbat_scheduler.logbook'`

- [ ] **Step 3: Write minimal implementation**

Create `custom_components/shabbat_scheduler/logbook.py`:

```python
"""Render this integration's own events in Home Assistant's Logbook.

Registering here is also what lets Home Assistant attribute a device's own
state change back to the rule that caused it: logbook's processor skips
attribution entirely for event types nothing describes.
"""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.core import Event, HomeAssistant, callback

from .const import DOMAIN, EVENT_RULE_APPLIED


@callback
def async_describe_events(
    hass: HomeAssistant,
    async_describe_event: Callable[[str, str, Callable[[Event], dict]], None],
) -> None:
    """Describe the events this integration fires."""

    @callback
    def async_describe_rule_applied(event: Event) -> dict:
        data = event.data
        rule = data.get("name") or data.get("rule_id", "")
        devices = ", ".join(data.get("devices") or [])
        action = data.get("action", "")

        message = f"rule {rule} ({action})"
        if devices:
            message = f"{message} — {devices}"
        if data.get("dry_run"):
            message = f"{message} [dry run]"

        return {
            "name": "Shabbat Scheduler",
            "message": message,
            "icon": "mdi:candle",
        }

    async_describe_event(DOMAIN, EVENT_RULE_APPLIED, async_describe_rule_applied)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_logbook.py -v`
Expected: PASS, 4 tests

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler/logbook.py tests/test_logbook.py
git commit -m "feat: describe rule events in the logbook"
```

---

### Task 10: Translations and strings

**Files:**
- Create: `custom_components/shabbat_scheduler/strings.json`
- Create: `custom_components/shabbat_scheduler/translations/en.json`
- Create: `custom_components/shabbat_scheduler/translations/he.json`
- Test: `tests/test_translations.py`

**Interfaces:**
- Consumes: the config flow's `single_instance_allowed` abort reason and the four service names.
- Produces: translated strings, so the abort renders as prose rather than a raw key.

- [ ] **Step 1: Write the failing test**

Create `tests/test_translations.py`:

```python
import json
from pathlib import Path

COMPONENT = Path("custom_components/shabbat_scheduler")
SERVICES = ("simulate", "set_dry_run", "export_yaml", "import_yaml")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_strings_covers_the_abort_reason():
    strings = _load(COMPONENT / "strings.json")
    assert "single_instance_allowed" in strings["config"]["abort"]


def test_strings_covers_every_service():
    strings = _load(COMPONENT / "strings.json")
    assert set(strings["services"]) == set(SERVICES)


def test_english_translation_matches_strings():
    assert _load(COMPONENT / "strings.json") == _load(
        COMPONENT / "translations/en.json"
    )


def test_hebrew_translation_has_the_same_shape():
    strings = _load(COMPONENT / "strings.json")
    hebrew = _load(COMPONENT / "translations/he.json")
    assert set(hebrew["config"]["abort"]) == set(strings["config"]["abort"])
    assert set(hebrew["services"]) == set(strings["services"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_translations.py -v`
Expected: FAIL with `FileNotFoundError` for `strings.json`

- [ ] **Step 3: Write minimal implementation**

Create `custom_components/shabbat_scheduler/strings.json`:

```json
{
  "config": {
    "abort": {
      "single_instance_allowed": "Shabbat Scheduler is already set up. Only one instance is supported."
    }
  },
  "services": {
    "simulate": {
      "name": "Simulate",
      "description": "Resolve the schedule for a block without side effects.",
      "fields": {
        "block_length": {
          "name": "Block length",
          "description": "Days to simulate. Defaults to the upcoming block."
        }
      }
    },
    "set_dry_run": {
      "name": "Set dry run",
      "description": "When enabled, rules report what they would change but call no services.",
      "fields": {
        "enabled": { "name": "Enabled", "description": "Whether dry run is on." }
      }
    },
    "export_yaml": {
      "name": "Export YAML",
      "description": "Return the whole rule set as YAML."
    },
    "import_yaml": {
      "name": "Import YAML",
      "description": "Replace the whole rule set from YAML.",
      "fields": {
        "yaml": { "name": "YAML", "description": "The rule set to import." }
      }
    }
  }
}
```

Copy it verbatim to `custom_components/shabbat_scheduler/translations/en.json`.

Create `custom_components/shabbat_scheduler/translations/he.json`:

```json
{
  "config": {
    "abort": {
      "single_instance_allowed": "שעון שבת כבר מוגדר. נתמך מופע אחד בלבד."
    }
  },
  "services": {
    "simulate": {
      "name": "סימולציה",
      "description": "חישוב לוח הזמנים לבלוק ללא ביצוע בפועל.",
      "fields": {
        "block_length": {
          "name": "אורך הבלוק",
          "description": "מספר הימים לסימולציה. ברירת המחדל היא הבלוק הקרוב."
        }
      }
    },
    "set_dry_run": {
      "name": "הרצה יבשה",
      "description": "כשמופעל, הכללים מדווחים מה היו משנים אך אינם מבצעים דבר.",
      "fields": {
        "enabled": { "name": "מופעל", "description": "האם הרצה יבשה פעילה." }
      }
    },
    "export_yaml": {
      "name": "ייצוא YAML",
      "description": "מחזיר את כל מערך הכללים כ-YAML."
    },
    "import_yaml": {
      "name": "ייבוא YAML",
      "description": "מחליף את כל מערך הכללים מתוך YAML.",
      "fields": {
        "yaml": { "name": "YAML", "description": "מערך הכללים לייבוא." }
      }
    }
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_translations.py -v`
Expected: PASS, 4 tests

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler/strings.json custom_components/shabbat_scheduler/translations tests/test_translations.py
git commit -m "feat: English and Hebrew strings"
```

---

### Task 11: HACS packaging and README

**Files:**
- Create: `hacs.json`
- Modify: `README.md`
- Test: `tests/test_packaging.py`

**Interfaces:**
- Consumes: `manifest.json`.
- Produces: a repository HACS can install as a custom repository.

- [ ] **Step 1: Write the failing test**

Create `tests/test_packaging.py`:

```python
import json
from pathlib import Path

MANIFEST = Path("custom_components/shabbat_scheduler/manifest.json")


def test_hacs_json_declares_the_integration():
    hacs = json.loads(Path("hacs.json").read_text(encoding="utf-8"))
    assert hacs["name"]
    assert hacs["homeassistant"]


def test_manifest_has_a_version_for_hacs():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["version"]
    assert manifest["domain"] == "shabbat_scheduler"


def test_readme_is_not_empty():
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "Shabbat Scheduler" in readme
    assert len(readme.splitlines()) > 20
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_packaging.py -v`
Expected: FAIL with `FileNotFoundError` for `hacs.json`

- [ ] **Step 3: Write minimal implementation**

Create `hacs.json`:

```json
{
  "name": "Shabbat Scheduler",
  "homeassistant": "2026.8.0",
  "render_readme": true
}
```

Replace `README.md` with exactly this:

````markdown
# Shabbat Scheduler

A Home Assistant integration that drives appliances across Shabbat and Chag,
when they cannot be operated by hand.

## What it does

A **block** is one contiguous Shabbat/Chag period, derived entirely from the
Jewish Calendar integration's candle-lighting and havdalah sensors. Its length
in days — 1 for a regular Shabbat, 2 or 3 when a Chag abuts one — selects which
**profile** of rules applies. Rules are authored explicitly per block length,
so a rule always reads exactly as it will run.

Rules are deliberately **not** clamped to the zmanim: an erev rule at 17:00
fires before Shabbat begins, which is how you pre-cool; a last-day rule at
23:00 fires after havdalah. A rule is a clock time on a resolved date.

## Design commitments

- **Fire once, never re-assert.** A rule acts at its moment and then leaves the
  device alone. Turn something off by hand afterwards and it stays off.
- **Idempotent.** Each rule compares current state to desired and sends only
  what genuinely differs, reporting `changed` / `ok` / `failed` per attribute.
- **No precedence.** Overlapping rules are reported as conflicts, never
  silently resolved — there is no defined winner, so the choice stays yours.
- **Safe by default.** The master switch is **off** on a fresh install, so
  installing cannot touch an appliance until you deliberately enable it.
- **Restart-aware.** A restart part-way through a block re-applies the current
  desired state once, rather than losing the rules that already passed.

## Installation

Add this repository to HACS as a custom repository of type *Integration*,
download it, restart Home Assistant, then add **Shabbat Scheduler** from
Settings → Devices & Services.

## Entities

| Entity | Purpose |
|---|---|
| `switch.shabbat_scheduler` | master on/off; off cancels every pending timer |
| `switch.shabbat_rule_*` | one per rule |
| `sensor.shabbat_scheduler_next_block` | day count, with the resolved dates |
| `sensor.shabbat_scheduler_next_action` | when the next rule fires |
| `sensor.shabbat_scheduler_last_run` | when a rule last ran, and what it did |

## Services

- `shabbat_scheduler.simulate` — resolve a block with no side effects. Answers
  "what happens this Shabbat?" and "what happens on a 3-day chag?".
- `shabbat_scheduler.set_dry_run` — report what would change, call nothing.
- `shabbat_scheduler.export_yaml` — dump the whole rule set.
- `shabbat_scheduler.import_yaml` — replace the whole rule set.

## Rule format

```yaml
defaults:
  temperature: 26
  hvac_mode: cool
  fan_mode: quiet
  devices: [climate.living_room]

profiles:
  1_day:
    erev:
      - { id: a1, at: "23:00:00", action: "off" }
    day_1:
      - { id: b1, at: "11:00:00", action: "on", name: Shabbat morning }
      - { id: b2, at: "18:00:00", action: "off" }
```

`action` is `on`, `off`, or `custom`. A `custom` rule runs a script, for
appliances whose control does not fit the simple on/off model:

```yaml
      - { id: c1, at: "17:30:00", action: custom, script: script.boiler }
```

Rule ids are preserved across an export/import round trip, so re-importing an
edited file keeps each rule's entity, history and customisation.

## Known behaviours

Non-obvious behaviours and accepted trade-offs — the havdalah sensor rollover,
refresh serialisation, and what restart catch-up does across havdalah — are
documented in [docs/known-behaviours.md](docs/known-behaviours.md).
````

- [ ] **Step 4: Run the whole suite**

Run: `uv run pytest -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add hacs.json README.md tests/test_packaging.py
git commit -m "feat: HACS packaging and README"
```

---

### Task 12: End-to-end — card-shaped workflow

**Files:**
- Test: `tests/test_end_to_end.py`

**Interfaces:**
- Consumes: everything above.
- Produces: no production code. One test proving the whole loop a card would drive.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_end_to_end.py`:

```python
async def test_a_card_can_drive_the_whole_loop(hass, hass_ws_client, jerusalem):
    """Subscribe, create, see the push and the entity, delete, see both go."""
    hass.states.async_set(
        "sensor.jewish_calendar_upcoming_candle_lighting",
        "2026-08-14T15:44:00+00:00",
    )
    hass.states.async_set(
        "sensor.jewish_calendar_upcoming_havdalah", "2026-08-15T17:01:00+00:00"
    )
    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "shabbat_scheduler/subscribe"})
    assert (await client.receive_json())["success"]

    await client.send_json(
        {
            "id": 2,
            "type": "shabbat_scheduler/rules/create",
            "rule": {
                "profile": 1,
                "day": "1",
                "time": "11:00:00",
                "action": "on",
                "devices": ["input_boolean.salon"],
                "name": "בוקר שבת",
            },
        }
    )

    pushed = await client.receive_json()
    created = await client.receive_json()
    if pushed["type"] != "event":  # ordering is not guaranteed
        pushed, created = created, pushed

    assert created["success"]
    rule_id = created["result"]["rule"]["id"]
    assert [r["id"] for r in pushed["event"]["rules"]] == [rule_id]

    await hass.async_block_till_done()
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        "switch", DOMAIN, f"{entry.entry_id}_rule_{rule_id}"
    )
    assert entity_id is not None

    await client.send_json(
        {"id": 3, "type": "shabbat_scheduler/rules/delete", "rule_id": rule_id}
    )
    while True:
        msg = await client.receive_json()
        if msg.get("id") == 3 and msg["type"] == "result":
            assert msg["success"]
            break

    await hass.async_block_till_done()
    assert registry.async_get_entity_id(
        "switch", DOMAIN, f"{entry.entry_id}_rule_{rule_id}"
    ) is None
```

Add to the top of `tests/test_end_to_end.py` if absent:

```python
from homeassistant.helpers import entity_registry as er
```

- [ ] **Step 2: Run test to verify it passes**

Run: `uv run pytest tests/test_end_to_end.py -v`
Expected: PASS if every earlier task is correct. If it fails, the failure identifies which layer is wrong — fix that layer's own test first, not this one.

- [ ] **Step 3: Run the whole suite**

Run: `uv run pytest -v`
Expected: PASS, all tests

- [ ] **Step 4: Commit**

```bash
git add tests/test_end_to_end.py
git commit -m "test: a card-shaped end-to-end loop over the websocket API"
```

---

## Deferred to Plan 2b

- The custom Lovelace card and its visual editor.
- `rules/duplicate` for the "clone day" affordance, if the card wants it
  server-side rather than composing it from `rules/create`.

## Deployment notes

Deployment is **not** part of this plan. All work runs locally under `pytest`.

When it is time to install: `ssh ha` now works as `elazar` with passwordless
sudo, but there is **no SFTP/SCP subsystem**, so files must be pushed with
`cat local | ssh ha "sudo tee /config/custom_components/... >/dev/null"`. The
master switch defaults off, so installing cannot drive any appliance.
