# Shabbat Scheduler Card — Read View (2b-i) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a Lovelace card that renders the coming Shabbat or Chag as a day-grouped timeline — served and registered by the integration itself — so the configured schedule is legible at a glance instead of being a list of switch toggles.

**Architecture:** The integration serves its own built card bundle over a static path and registers the Lovelace resource on setup. The card opens one websocket subscription and renders entirely from what the server pushes; it holds no optimistic state. All logic that can be decided without a DOM lives in a pure `format.ts`, mirroring the Python purity boundary.

**Tech Stack:** TypeScript, Lit 3, rollup, vitest + happy-dom (frontend); Python 3.14 / Home Assistant 2026.8.2, pytest (backend); Docker + Playwright (end-to-end).

## Global Constraints

- Target Home Assistant is **2026.8.2**; `hacs.json` declares a `2026.8.0` floor.
- The card adds **no new write API**. Its only writes are `switch.turn_on` / `switch.turn_off` on the master switch and the existing `shabbat_scheduler.set_dry_run` service.
- **No optimistic local state.** Every render comes from the last payload the server pushed; a control reflects a change only once the server confirms it.
- The Python purity boundary is unchanged: `models.py`, `block.py`, `device_ops.py`, `const.py`, `rule_schema.py`, `yaml_io.py` import zero Home Assistant. `tests/test_packaging.py::test_the_pure_modules_import_zero_home_assistant` enforces it.
- Fire-once semantics, conflict-warn-never-resolve, and master-defaults-OFF are untouched. **This plan changes no scheduling behaviour.**
- All development and testing runs against a throwaway Home Assistant in Docker on this machine. **Production (192.168.1.14) is never touched by any task in this plan.**
- RTL: logical CSS properties only (`margin-inline-start`, `padding-inline`, `text-align: start`). No `left`/`right` in any stylesheet.
- Every test for a new behaviour must be observed **failing** before the behaviour exists. A test that passes either way is worse than no test.
- Node is installed per-user under `~/.local`. Never `sudo`, never a system package.

## File Structure

**Backend (Python)**

| File | Responsibility |
|---|---|
| `custom_components/shabbat_scheduler/block.py` | +`block_payload(block)` — pure, JSON-able block description |
| `custom_components/shabbat_scheduler/websocket_api.py` | `_state_payload` gains `block` + `master_entity_id`; `ws_subscribe` sends an initial snapshot |
| `custom_components/shabbat_scheduler/frontend.py` | **new** — static path + Lovelace resource registration/removal |
| `custom_components/shabbat_scheduler/__init__.py` | calls frontend setup on entry setup, teardown on unload |
| `custom_components/shabbat_scheduler/manifest.json` | `dependencies: ["http", "lovelace"]` |
| `custom_components/shabbat_scheduler/www/shabbat-scheduler-card.js` | **new** — built bundle, committed |

**Frontend (TypeScript)**

| File | Responsibility |
|---|---|
| `frontend/src/types.ts` | the payload shape, mirroring `_state_payload` |
| `frontend/src/strings.ts` | en/he strings keyed off `hass.locale.language` |
| `frontend/src/format.ts` | pure: grouping, ordering, briefs, colours, warning attachment |
| `frontend/src/rule-row.ts` | `<shabbat-rule-row>` |
| `frontend/src/day-group.ts` | `<shabbat-day-group>` |
| `frontend/src/warnings.ts` | `<shabbat-warnings>` |
| `frontend/src/block-header.ts` | `<shabbat-block-header>` — master + dry-run controls |
| `frontend/src/card.ts` | `<shabbat-scheduler-card>` — connection, state, assembly |

**Dev / e2e**

| File | Responsibility |
|---|---|
| `dev/docker-compose.yml` | throwaway HA container |
| `dev/seed.py` | onboard the container, seed rules + fake zmanim, mount the card |
| `e2e/test_card_e2e.py` | Playwright assertions against the container |

---

### Task 1: Node toolchain and frontend scaffold

**Files:**
- Create: `frontend/package.json`, `frontend/tsconfig.json`, `frontend/rollup.config.js`, `frontend/vitest.config.ts`, `frontend/.gitignore`
- Create: `frontend/src/version.ts`, `frontend/test/version.test.ts`
- Modify: `.gitignore` (repo root)

**Interfaces:**
- Consumes: nothing.
- Produces: `npm --prefix frontend run build` writes `custom_components/shabbat_scheduler/www/shabbat-scheduler-card.js`; `npm --prefix frontend test` runs vitest. `CARD_VERSION: string` exported from `frontend/src/version.ts`.

- [ ] **Step 1: Install Node 22 for this user only**

```bash
mkdir -p ~/.local/node
curl -fsSL https://nodejs.org/dist/v22.11.0/node-v22.11.0-linux-arm64.tar.xz \
  | tar -xJ --strip-components=1 -C ~/.local/node
ln -sf ~/.local/node/bin/node ~/.local/bin/node
ln -sf ~/.local/node/bin/npm  ~/.local/bin/npm
ln -sf ~/.local/node/bin/npx  ~/.local/bin/npx
node --version && npm --version
```

Expected: `v22.11.0` and a matching npm version. `~/.local/bin` is already on PATH. Do **not** use `sudo` or `apt`.

- [ ] **Step 2: Create `frontend/package.json`**

```json
{
  "name": "shabbat-scheduler-card",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "build": "rollup -c",
    "test": "vitest run",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "lit": "^3.2.1"
  },
  "devDependencies": {
    "@rollup/plugin-node-resolve": "^15.3.0",
    "@rollup/plugin-typescript": "^12.1.1",
    "happy-dom": "^15.11.6",
    "rollup": "^4.28.0",
    "tslib": "^2.8.1",
    "typescript": "^5.7.2",
    "vitest": "^2.1.8"
  }
}
```

- [ ] **Step 3: Create `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "es2021",
    "module": "esnext",
    "moduleResolution": "bundler",
    "lib": ["es2021", "dom", "dom.iterable"],
    "strict": true,
    "noUnusedLocals": true,
    "noImplicitOverride": true,
    "experimentalDecorators": true,
    "useDefineForClassFields": false,
    "skipLibCheck": true
  },
  "include": ["src/**/*.ts", "test/**/*.ts"]
}
```

`useDefineForClassFields: false` and `experimentalDecorators: true` are required for Lit's `@property` decorators to work correctly. Do not change them.

- [ ] **Step 4: Create `frontend/rollup.config.js`**

```js
import resolve from '@rollup/plugin-node-resolve';
import typescript from '@rollup/plugin-typescript';

export default {
  input: 'src/card.ts',
  output: {
    file: '../custom_components/shabbat_scheduler/www/shabbat-scheduler-card.js',
    format: 'es',
    sourcemap: false,
  },
  plugins: [resolve(), typescript({ tsconfig: './tsconfig.json' })],
};
```

- [ ] **Step 5: Create `frontend/vitest.config.ts`**

```ts
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'happy-dom',
    include: ['test/**/*.test.ts'],
  },
});
```

- [ ] **Step 6: Create `frontend/.gitignore`**

```
node_modules/
```

- [ ] **Step 7: Write the failing test**

`frontend/test/version.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { CARD_VERSION } from '../src/version';

describe('CARD_VERSION', () => {
  it('is a semver string the resource URL can be stamped with', () => {
    expect(CARD_VERSION).toMatch(/^\d+\.\d+\.\d+$/);
  });
});
```

- [ ] **Step 8: Run it and watch it fail**

```bash
npm --prefix frontend install
npm --prefix frontend test
```

Expected: FAIL — cannot resolve `../src/version`.

- [ ] **Step 9: Create `frontend/src/version.ts`**

```ts
/** Stamped into the Lovelace resource URL so a rebuild busts the cache. */
export const CARD_VERSION = '0.1.0';
```

- [ ] **Step 10: Create a temporary `frontend/src/card.ts` so rollup has an entry point**

```ts
import { CARD_VERSION } from './version';

console.info(`shabbat-scheduler-card ${CARD_VERSION}`);
```

This file is replaced wholesale in Task 11. It exists now only to prove the build pipeline works end to end.

- [ ] **Step 11: Verify test and build both pass**

```bash
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
ls -l custom_components/shabbat_scheduler/www/shabbat-scheduler-card.js
```

Expected: test PASS, typecheck clean, and the bundle exists.

- [ ] **Step 12: Ignore `node_modules` at the repo root too**

Append to the root `.gitignore` (create it if absent):

```
frontend/node_modules/
```

- [ ] **Step 13: Commit**

```bash
git add frontend .gitignore custom_components/shabbat_scheduler/www
git commit -m "build: TypeScript + Lit + rollup toolchain for the card"
```

---

### Task 2: `block_payload` — the pure block description

**Files:**
- Modify: `custom_components/shabbat_scheduler/block.py`
- Test: `tests/test_block.py`

**Interfaces:**
- Consumes: `Block` from `models.py` (fields: `candle_lighting: datetime`, `havdalah: datetime`, `length: int`, `erev_date: date`, `day_dates: tuple[date, ...]`, index 0 is day_1).
- Produces: `block_payload(block: Block | None) -> dict | None`.

**Why:** the card draws day headings with real dates and the candle-lighting / havdalah markers. `_state_payload` currently returns rules carrying only `profile`, `day` and a clock `time` — no dates, no zmanim, no block length — so the card cannot render a timeline or even tell which profile's rules to show. Deriving it client-side from the Jewish Calendar sensors was rejected: it duplicates logic `block.py` owns and lets the card and engine disagree about which Shabbat is which.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_block.py`:

```python
def test_block_payload_describes_the_block_for_the_card():
    block = compute_block(
        datetime(2026, 8, 14, 18, 44, tzinfo=UTC),
        datetime(2026, 8, 15, 20, 1, tzinfo=UTC),
    )
    payload = block_payload(block)

    assert payload["length"] == 1
    assert payload["candle_lighting"] == "2026-08-14T18:44:00+00:00"
    assert payload["havdalah"] == "2026-08-15T20:01:00+00:00"
    assert payload["dates"] == {"erev": "2026-08-14", "1": "2026-08-15"}


def test_block_payload_keys_days_the_same_way_rules_do():
    """day_dates[0] is day_1, and rules spell their day '1', not '0'.

    An off-by-one here would silently file every rule under the wrong
    date - the card would render a correct-looking timeline on the wrong
    days, which is worse than rendering nothing.
    """
    block = compute_block(
        datetime(2026, 10, 2, 18, 0, tzinfo=UTC),
        datetime(2026, 10, 4, 19, 0, tzinfo=UTC),
    )
    payload = block_payload(block)

    assert payload["length"] == 2
    assert payload["dates"] == {
        "erev": "2026-10-02",
        "1": "2026-10-03",
        "2": "2026-10-04",
    }


def test_block_payload_is_none_when_there_is_no_block():
    assert block_payload(None) is None


def test_block_payload_is_json_able():
    """It crosses a websocket; a date or datetime object would not survive."""
    block = compute_block(
        datetime(2026, 8, 14, 18, 44, tzinfo=UTC),
        datetime(2026, 8, 15, 20, 1, tzinfo=UTC),
    )
    json.dumps(block_payload(block))
```

The file's existing imports are `from datetime import date, datetime, time` and `from zoneinfo import ZoneInfo` — there is **no** `UTC` import. Add `json` and `UTC`, and add `block_payload` to the existing `from custom_components.shabbat_scheduler.block import (...)` group:

```python
import json
from datetime import UTC, date, datetime, time
```

- [ ] **Step 2: Run the tests and watch them fail**

```bash
uv run pytest tests/test_block.py -q -k block_payload
```

Expected: FAIL — `ImportError: cannot import name 'block_payload'`.

- [ ] **Step 3: Implement it in `block.py`**

Add after `compute_block`:

```python
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
```

- [ ] **Step 4: Run the tests and the purity guard**

```bash
uv run pytest tests/test_block.py tests/test_packaging.py -q
```

Expected: PASS, including `test_the_pure_modules_import_zero_home_assistant`.

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler/block.py tests/test_block.py
git commit -m "feat: block_payload, the block as JSON-able data for the card"
```

---

### Task 3: `block` and `master_entity_id` in the state payload

**Files:**
- Modify: `custom_components/shabbat_scheduler/websocket_api.py`
- Test: `tests/test_websocket.py`

**Interfaces:**
- Consumes: `block_payload(block) -> dict | None` from Task 2; `engine.current_block` (property, returns `Block | None`); the entry data dict `{"store": …, "engine": …}` from `_entry_data(hass)`.
- Produces: `_state_payload(hass, data)` — **note the changed signature**, it now needs `hass` for the registry lookup and the whole entry data, not just the store. Payload gains `block: dict | None` and `master_entity_id: str | None`.

**Why `master_entity_id`:** the card calls `switch.turn_on` on the master switch and cannot construct its `entity_id` — that is slugified from a user-editable name. Resolving a unique_id to an entity_id by guessing has already caused two real bugs in this project; the card will not be a third.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_websocket.py`:

```python
async def test_list_carries_the_block_so_the_card_can_draw_dates(hass, hass_ws_client):
    entry = await _setup(hass)
    client = await hass_ws_client(hass)

    await client.send_json_auto_id({"type": "shabbat_scheduler/rules/list"})
    result = (await client.receive_json())["result"]

    assert result["block"]["length"] == 1
    assert result["block"]["dates"]["erev"] == "2026-08-14"
    assert result["block"]["dates"]["1"] == "2026-08-15"
    assert result["block"]["candle_lighting"].startswith("2026-08-14T")
    assert result["block"]["havdalah"].startswith("2026-08-15T")


async def test_block_is_null_when_the_zmanim_are_missing(hass, hass_ws_client):
    """No Jewish Calendar sensors - the card must render a real message,
    not an empty timeline it cannot explain."""
    await hass.config.async_set_time_zone("Asia/Jerusalem")
    store = RuleStore(hass)
    await store.async_load()
    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "shabbat_scheduler/rules/list"})
    result = (await client.receive_json())["result"]

    assert result["block"] is None


async def test_list_carries_the_master_entity_id(hass, hass_ws_client):
    entry = await _setup(hass)
    client = await hass_ws_client(hass)

    await client.send_json_auto_id({"type": "shabbat_scheduler/rules/list"})
    result = (await client.receive_json())["result"]

    registry = er.async_get(hass)
    expected = registry.async_get_entity_id(
        "switch", DOMAIN, f"{entry.entry_id}_master"
    )
    assert expected is not None
    assert result["master_entity_id"] == expected
    assert hass.states.get(result["master_entity_id"]) is not None
```

Add `from homeassistant.helpers import entity_registry as er` to the imports.

- [ ] **Step 2: Run the tests and watch them fail**

```bash
uv run pytest tests/test_websocket.py -q -k "block or master_entity"
```

Expected: FAIL — `KeyError: 'block'` and `KeyError: 'master_entity_id'`.

- [ ] **Step 3: Change `_state_payload` in `websocket_api.py`**

Replace the existing `_state_payload` with:

```python
def _state_payload(hass: HomeAssistant, data: dict) -> dict:
    """Everything the card renders. One shape, used by list and subscribe."""
    store, engine = data["store"], data["engine"]
    return {
        "defaults": store.defaults,
        "rules": [rule_to_dict(rule) for rule in store.rules],
        "enabled": store.enabled,
        "dry_run": store.dry_run,
        "warnings": _conflict_warnings(store),
        # The card draws dates and the zmanim markers from this, and picks
        # which profile to show from its length. None when the Jewish
        # Calendar sensors give us nothing to derive a block from.
        "block": block_payload(engine.current_block),
        # Resolved here rather than guessed by the card: a rule switch's
        # entity_id is slugified from a user-editable, often-Hebrew name
        # and cannot be constructed from a unique_id. Guessing it has
        # caused two real bugs in this project already.
        "master_entity_id": _master_entity_id(hass, data["entry_id"]),
    }


def _master_entity_id(hass: HomeAssistant, entry_id: str) -> str | None:
    """The master switch's entity_id, or None if it is not registered."""
    return er.async_get(hass).async_get_entity_id(
        "switch", DOMAIN, f"{entry_id}_master"
    )
```

Add these imports:

```python
from homeassistant.helpers import entity_registry as er

from .block import block_payload, conflict_warnings, preview_payload
```

- [ ] **Step 4: Make `entry_id` available in the entry data**

`_state_payload` needs the entry's id for the registry lookup. `__init__.py:64-67` currently builds the dict with two keys; add a third:

```python
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "store": store,
        "engine": engine,
        "entry_id": entry.entry_id,
    }
```

Keep `store` and `engine` exactly as they are — `websocket_api.py`, `switch.py` and `sensor.py` all read them.

- [ ] **Step 5: Update both call sites**

In `ws_list` and in `ws_subscribe`'s `_forward`, change `_state_payload(store)` / `_state_payload(current["store"])` to pass `hass` and the whole entry data:

```python
# ws_list
connection.send_result(msg["id"], _state_payload(hass, data))
```

```python
# _forward, inside ws_subscribe
connection.send_message(
    websocket_api.event_message(msg["id"], _state_payload(hass, current))
)
```

- [ ] **Step 6: Run the whole suite**

```bash
uv run pytest -q
```

Expected: PASS. Every previously passing test must still pass — `_state_payload`'s signature changed, so any missed call site fails loudly here.

- [ ] **Step 7: Commit**

```bash
git add custom_components/shabbat_scheduler/websocket_api.py custom_components/shabbat_scheduler/__init__.py tests/test_websocket.py
git commit -m "feat: the state payload carries the block and the master entity id"
```

---

### Task 4: `subscribe` sends an initial snapshot

**Files:**
- Modify: `custom_components/shabbat_scheduler/websocket_api.py`
- Test: `tests/test_websocket.py`

**Interfaces:**
- Consumes: `_state_payload(hass, data)` from Task 3.
- Produces: after `subscribe` returns its result, the server immediately sends one `event` message carrying the current state.

**Why:** `ws_subscribe` currently sends a bare result and then pushes only on change, so a client needs `rules/list` **and** `subscribe`, with a window between them in which a change is missed entirely and never re-reported. Sending the current state immediately closes that window and removes the card's need to reconcile two responses.

- [ ] **Step 1: Write the failing test**

```python
async def test_subscribe_pushes_the_current_state_immediately(hass, hass_ws_client):
    """Otherwise a client needs list AND subscribe, and a change landing
    between the two is lost silently and never re-reported."""
    await _setup(hass, [
        Rule(id="r1", profile=1, day="1", time=time(11, 0), action=Action.ON),
    ])
    client = await hass_ws_client(hass)

    await client.send_json_auto_id({"type": "shabbat_scheduler/subscribe"})
    assert (await client.receive_json())["success"] is True

    pushed = await client.receive_json()
    assert pushed["type"] == "event"
    assert [rule["id"] for rule in pushed["event"]["rules"]] == ["r1"]
    assert pushed["event"]["block"]["length"] == 1
```

- [ ] **Step 2: Run it and watch it fail**

```bash
uv run pytest tests/test_websocket.py -q -k subscribe_pushes_the_current_state
```

Expected: FAIL — the test times out waiting for a message that never arrives.

- [ ] **Step 3: Send the snapshot in `ws_subscribe`**

Replace the final `connection.send_result(msg["id"])` in `ws_subscribe` with:

```python
    connection.send_result(msg["id"])
    # The current state, before any change happens. Without it a client
    # must also call rules/list, and a change landing between the two
    # calls is missed with nothing to re-report it.
    _forward()
```

`_forward` re-resolves the entry data itself, so it is safe to call directly here.

- [ ] **Step 4: Run the whole suite**

```bash
uv run pytest -q
```

Expected: PASS, including the existing subscription tests — check none of them assumed the first message after subscribing was a change notification.

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler/websocket_api.py tests/test_websocket.py
git commit -m "feat: subscribe delivers the current state as its first message"
```

---

### Task 5: Serve the card and register the Lovelace resource

**Files:**
- Create: `custom_components/shabbat_scheduler/frontend.py`
- Modify: `custom_components/shabbat_scheduler/__init__.py`, `custom_components/shabbat_scheduler/manifest.json`
- Test: `tests/test_frontend.py`

**Interfaces:**
- Consumes: `CARD_VERSION` is *not* imported by Python — the version stamped into the URL is `manifest.json`'s `version` field, read via `hass.data`/the entry, or the module constant below.
- Produces: `async_register_frontend(hass) -> None` and `async_unregister_frontend(hass) -> None`.

**Why here and not a second repo:** HACS treats a repository as exactly one category, and this repository is already an *integration*. Serving the card from the integration means one install and no manual resource registration. `simple_timer` on the target instance serves `/simple_timer/timer-card.js` in exactly this shape.

**Verified APIs (do not substitute):**
- `from homeassistant.components.http import StaticPathConfig` and `await hass.http.async_register_static_paths([StaticPathConfig(url_path, path, cache_headers)])`.
- `from homeassistant.components.lovelace.const import LOVELACE_DATA`; `hass.data[LOVELACE_DATA]` is a `LovelaceData` with `.resource_mode` (`"storage"` or `"yaml"`) and `.resources`, a collection exposing `async_items() -> list[dict]`, `async_create_item(data) -> dict` and `async_update_item(item_id, updates) -> dict`. Create/update take `{"res_type": "module", "url": …}`.

- [ ] **Step 1: Write the failing tests**

`tests/test_frontend.py`:

```python
"""The integration serves and registers its own card."""

from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shabbat_scheduler.const import DOMAIN
from custom_components.shabbat_scheduler.frontend import CARD_URL


async def _setup(hass):
    await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_the_card_is_registered_as_a_lovelace_resource(hass):
    await _setup(hass)

    urls = [
        item["url"] for item in hass.data[LOVELACE_DATA].resources.async_items()
    ]
    assert any(url.startswith(CARD_URL) for url in urls)


async def test_registering_twice_does_not_duplicate_the_resource(hass):
    """A reload must not leave the user with two copies of the card,
    which load twice and fight over the custom element name."""
    entry = await _setup(hass)
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    matching = [
        item
        for item in hass.data[LOVELACE_DATA].resources.async_items()
        if item["url"].startswith(CARD_URL)
    ]
    assert len(matching) == 1


async def test_the_resource_url_is_version_stamped(hass):
    """Otherwise a browser serves the old bundle from cache after an update."""
    await _setup(hass)

    url = next(
        item["url"]
        for item in hass.data[LOVELACE_DATA].resources.async_items()
        if item["url"].startswith(CARD_URL)
    )
    assert "?v=" in url


async def test_setup_survives_yaml_resource_mode(hass):
    """In YAML mode resources cannot be created programmatically. That must
    degrade to a log line, not a failed setup that takes the scheduler down
    with it."""
    await async_setup_component(hass, "lovelace", {})
    hass.data[LOVELACE_DATA].resource_mode = "yaml"

    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state.recoverable is False or entry.state.name == "LOADED"
```

- [ ] **Step 2: Run them and watch them fail**

```bash
uv run pytest tests/test_frontend.py -q
```

Expected: FAIL — `ModuleNotFoundError: custom_components.shabbat_scheduler.frontend`.

- [ ] **Step 3: Create `frontend.py`**

```python
"""Serving and registering the Lovelace card.

HACS treats a repository as exactly one category and this one is an
integration, so the card ships inside it rather than as a second
repository the user must install and version-match by hand.
"""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CARD_FILENAME = "shabbat-scheduler-card.js"
CARD_URL = f"/{DOMAIN}/{CARD_FILENAME}"
CARD_VERSION = "0.1.0"

_STATIC_REGISTERED = f"{DOMAIN}_static_registered"


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Serve the bundle and make Lovelace load it."""
    if not hass.data.get(_STATIC_REGISTERED):
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    f"/{DOMAIN}",
                    str(Path(__file__).parent / "www"),
                    # The URL is version-stamped, so caching is safe and
                    # keeps the bundle out of every page load.
                    True,
                )
            ]
        )
        # A static path cannot be unregistered, so this survives a reload
        # deliberately - registering it twice raises.
        hass.data[_STATIC_REGISTERED] = True

    await _async_register_resource(hass)


async def _async_register_resource(hass: HomeAssistant) -> None:
    """Add or update our Lovelace resource, never duplicating it."""
    data = hass.data.get(LOVELACE_DATA)
    if data is None:
        _LOGGER.warning("Lovelace is not set up; the card was not registered")
        return

    if data.resource_mode != "storage":
        # YAML mode owns its own resource list and cannot be written to.
        _LOGGER.warning(
            "Lovelace is in YAML resource mode. Add this line to your "
            "resources yourself:\n  - url: %s?v=%s\n    type: module",
            CARD_URL,
            CARD_VERSION,
        )
        return

    wanted = f"{CARD_URL}?v={CARD_VERSION}"
    for item in data.resources.async_items():
        if item["url"].startswith(CARD_URL):
            if item["url"] != wanted:
                await data.resources.async_update_item(
                    item["id"], {"url": wanted}
                )
            return

    await data.resources.async_create_item({"res_type": "module", "url": wanted})


async def async_unregister_frontend(hass: HomeAssistant) -> None:
    """Remove the Lovelace resource on unload.

    The static path stays: Home Assistant has no way to unregister one,
    and serving a file nobody references is harmless.
    """
    data = hass.data.get(LOVELACE_DATA)
    if data is None or data.resource_mode != "storage":
        return
    for item in data.resources.async_items():
        if item["url"].startswith(CARD_URL):
            await data.resources.async_delete_item(item["id"])
            return
```

- [ ] **Step 4: Wire it into `__init__.py`**

In `async_setup_entry`, after the store and engine are set up and before returning `True`:

```python
    await async_register_frontend(hass)
```

In `async_unload_entry`, alongside the existing teardown:

```python
    await async_unregister_frontend(hass)
```

Import both at the top:

```python
from .frontend import async_register_frontend, async_unregister_frontend
```

- [ ] **Step 5: Declare the dependencies in `manifest.json`**

Add the key, keeping every existing key unchanged:

```json
  "dependencies": ["http", "lovelace"],
```

`http` for `hass.http`, `lovelace` for the resource collection. If setup fails on a missing dependency, add what the traceback names — do not guess wider.

- [ ] **Step 6: Run the tests**

```bash
uv run pytest tests/test_frontend.py -q && uv run pytest -q
```

Expected: PASS, whole suite green.

- [ ] **Step 7: Commit**

```bash
git add custom_components/shabbat_scheduler/frontend.py custom_components/shabbat_scheduler/__init__.py custom_components/shabbat_scheduler/manifest.json tests/test_frontend.py
git commit -m "feat: the integration serves and registers its own card"
```

---

### Task 6: The pure core — `types.ts`, `strings.ts`, `format.ts`

**Files:**
- Create: `frontend/src/types.ts`, `frontend/src/strings.ts`, `frontend/src/format.ts`
- Test: `frontend/test/format.test.ts`

**Interfaces:**
- Consumes: the payload shape produced by Tasks 3 and 4.
- Produces:
  - `interface CardState { defaults; rules: RuleData[]; enabled: boolean; dry_run: boolean; warnings: WarningData[]; block: BlockData | null; master_entity_id: string | null }`
  - `buildGroups(state: CardState): DayGroup[]`
  - `ruleBrief(rule: RuleData, defaults: Defaults): string`
  - `actionColour(action: string): string`
  - `warningsForRule(ruleId: string, warnings: WarningData[]): WarningData[]`
  - `unattachedWarnings(warnings: WarningData[]): WarningData[]`

**Why this file exists:** it is the frontend's purity boundary, mirroring `block.py`. Everything decidable without a DOM lives here and is tested without one. The Lit elements below hold no logic beyond presentation.

- [ ] **Step 1: Create `frontend/src/types.ts`**

```ts
/** Mirrors _state_payload in websocket_api.py. Keep the two in step. */

export interface RuleData {
  id: string;
  profile: number;
  day: string;            // 'erev' | '1' | '2' | '3'
  time: string;           // 'HH:MM:SS'
  action: string;         // 'on' | 'off' | 'custom'
  devices: string[];
  settings: Record<string, unknown>;
  name: string | null;
  icon: string | null;
  enabled: boolean;
  script: string | null;
  variables: Record<string, unknown>;
  replay_on_restart: boolean;
  color: string | null;
}

export interface Defaults {
  devices?: string[];
  settings?: Record<string, unknown>;
}

export interface WarningData {
  kind: string;                 // 'conflict' | 'no_profile' | 'no_block'
  message: string;
  rule_ids?: string[];
  profile?: number;
}

export interface BlockData {
  length: number;
  candle_lighting: string;      // ISO 8601
  havdalah: string;             // ISO 8601
  dates: Record<string, string>; // 'erev' | '1'.. -> 'YYYY-MM-DD'
}

export interface CardState {
  defaults: Defaults;
  rules: RuleData[];
  enabled: boolean;
  dry_run: boolean;
  warnings: WarningData[];
  block: BlockData | null;
  master_entity_id: string | null;
}

export interface DayGroup {
  day: string;                  // 'erev' | '1'..
  date: string | null;          // 'YYYY-MM-DD'
  rules: RuleData[];
  marker: { kind: 'candle_lighting' | 'havdalah'; at: string } | null;
}
```

- [ ] **Step 2: Write the failing tests**

`frontend/test/format.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import {
  actionColour,
  buildGroups,
  ruleBrief,
  unattachedWarnings,
  warningsForRule,
} from '../src/format';
import type { CardState, RuleData } from '../src/types';

const rule = (over: Partial<RuleData>): RuleData => ({
  id: 'r', profile: 1, day: '1', time: '11:00:00', action: 'on',
  devices: [], settings: {}, name: null, icon: null, enabled: true,
  script: null, variables: {}, replay_on_restart: false, color: null,
  ...over,
});

const state = (over: Partial<CardState>): CardState => ({
  defaults: {}, rules: [], enabled: true, dry_run: false, warnings: [],
  master_entity_id: 'switch.master',
  block: {
    length: 1,
    candle_lighting: '2026-08-14T18:44:00+03:00',
    havdalah: '2026-08-15T20:01:00+03:00',
    dates: { erev: '2026-08-14', '1': '2026-08-15' },
  },
  ...over,
});

describe('buildGroups', () => {
  it('puts erev before day 1', () => {
    const groups = buildGroups(state({
      rules: [rule({ id: 'a', day: '1' }), rule({ id: 'b', day: 'erev' })],
    }));
    expect(groups.map((g) => g.day)).toEqual(['erev', '1']);
  });

  it('orders rules within a day by time', () => {
    const groups = buildGroups(state({
      rules: [
        rule({ id: 'late', day: '1', time: '18:00:00' }),
        rule({ id: 'early', day: '1', time: '11:00:00' }),
      ],
    }));
    expect(groups[0].rules.map((r) => r.id)).toEqual(['early', 'late']);
  });

  it('shows only rules for the current block length', () => {
    const groups = buildGroups(state({
      rules: [rule({ id: 'one', profile: 1 }), rule({ id: 'three', profile: 3 })],
    }));
    const ids = groups.flatMap((g) => g.rules.map((r) => r.id));
    expect(ids).toEqual(['one']);
  });

  it('attaches candle lighting to erev and havdalah to the last day', () => {
    const groups = buildGroups(state({
      rules: [rule({ day: 'erev' }), rule({ day: '1' })],
    }));
    expect(groups[0].marker?.kind).toBe('candle_lighting');
    expect(groups[1].marker?.kind).toBe('havdalah');
  });

  it('gives every day of the block a group, even with no rules', () => {
    const groups = buildGroups(state({ rules: [] }));
    expect(groups.map((g) => g.day)).toEqual(['erev', '1']);
  });

  it('returns nothing when there is no block', () => {
    expect(buildGroups(state({ block: null }))).toEqual([]);
  });
});

describe('ruleBrief', () => {
  it('falls back to the defaults devices when the rule has none', () => {
    const brief = ruleBrief(rule({ devices: [] }), { devices: ['climate.salon'] });
    expect(brief).toContain('climate.salon');
  });

  it('prefers the rule devices over the defaults', () => {
    const brief = ruleBrief(rule({ devices: ['climate.kids'] }), {
      devices: ['climate.salon'],
    });
    expect(brief).toContain('climate.kids');
    expect(brief).not.toContain('climate.salon');
  });

  it('merges settings over the defaults settings', () => {
    const brief = ruleBrief(
      rule({ devices: ['climate.a'], settings: { temperature: 24 } }),
      { settings: { temperature: 26, fan_mode: 'quiet' } },
    );
    expect(brief).toContain('24');
    expect(brief).toContain('quiet');
    expect(brief).not.toContain('26');
  });

  it('names the script for a custom action', () => {
    const brief = ruleBrief(
      rule({ action: 'custom', script: 'script.boiler' }), {},
    );
    expect(brief).toContain('script.boiler');
  });
});

describe('actionColour', () => {
  it('gives on, off and custom three distinguishable colours', () => {
    const colours = new Set(['on', 'off', 'custom'].map(actionColour));
    expect(colours.size).toBe(3);
  });

  it('does not throw on an action it has never seen', () => {
    expect(typeof actionColour('something-new')).toBe('string');
  });
});

describe('warning attachment', () => {
  const conflict = { kind: 'conflict', message: 'clash', rule_ids: ['a', 'b'] };
  const noProfile = { kind: 'no_profile', message: 'nothing enabled' };

  it('attaches a conflict to each rule it names', () => {
    expect(warningsForRule('a', [conflict, noProfile])).toEqual([conflict]);
    expect(warningsForRule('b', [conflict, noProfile])).toEqual([conflict]);
  });

  it('attaches nothing to an unnamed rule', () => {
    expect(warningsForRule('c', [conflict, noProfile])).toEqual([]);
  });

  it('leaves warnings naming no rule for the banner', () => {
    expect(unattachedWarnings([conflict, noProfile])).toEqual([noProfile]);
  });
});
```

- [ ] **Step 3: Run them and watch them fail**

```bash
npm --prefix frontend test
```

Expected: FAIL — cannot resolve `../src/format`.

- [ ] **Step 4: Create `frontend/src/strings.ts`**

```ts
/** Mirrors the integration's own en/he translations. */

const STRINGS = {
  en: {
    erev: 'Erev',
    day: 'Day',
    candle_lighting: 'Candle lighting',
    havdalah: 'Havdalah',
    master: 'Shabbat Scheduler',
    dry_run: 'Dry run',
    no_block: 'No upcoming Shabbat could be derived from the Jewish Calendar sensors.',
    not_set_up: 'Shabbat Scheduler is not configured.',
    stale: 'Connection lost — showing the last known state.',
    no_rules: 'No rules for this block.',
    disabled_rule: 'disabled',
    runs_script: 'runs',
  },
  he: {
    erev: 'ערב',
    day: 'יום',
    candle_lighting: 'הדלקת נרות',
    havdalah: 'הבדלה',
    master: 'שעון שבת',
    dry_run: 'הרצה יבשה',
    no_block: 'לא ניתן לגזור שבת קרובה מחיישני לוח השנה העברי.',
    not_set_up: 'שעון שבת אינו מוגדר.',
    stale: 'החיבור אבד — מוצג המצב האחרון הידוע.',
    no_rules: 'אין כללים לבלוק הזה.',
    disabled_rule: 'מושבת',
    runs_script: 'מריץ',
  },
} as const;

export type StringKey = keyof (typeof STRINGS)['en'];

export function t(language: string | undefined, key: StringKey): string {
  const table = language === 'he' ? STRINGS.he : STRINGS.en;
  return table[key];
}
```

- [ ] **Step 5: Create `frontend/src/format.ts`**

```ts
import type {
  BlockData,
  CardState,
  DayGroup,
  Defaults,
  RuleData,
  WarningData,
} from './types';

/** Erev sorts before day 1, then days ascend numerically. */
function dayRank(day: string): number {
  return day === 'erev' ? -1 : Number(day);
}

function dayKeys(block: BlockData): string[] {
  const days = ['erev'];
  for (let i = 1; i <= block.length; i += 1) days.push(String(i));
  return days;
}

/**
 * The timeline: one group per day of the block, in order, each carrying
 * its date, its rules ordered by time, and its zmanim marker if one
 * falls at its end.
 *
 * Only rules matching the block's length are shown - rules are authored
 * per profile, and a 3-day chag's rules must not appear on a plain
 * Shabbat.
 */
export function buildGroups(state: CardState): DayGroup[] {
  const { block } = state;
  if (block === null) return [];

  const lastDay = String(block.length);
  return dayKeys(block).map((day) => {
    const rules = state.rules
      .filter((rule) => rule.profile === block.length && rule.day === day)
      .sort((a, b) => a.time.localeCompare(b.time));

    let marker: DayGroup['marker'] = null;
    if (day === 'erev') {
      marker = { kind: 'candle_lighting', at: block.candle_lighting };
    } else if (day === lastDay) {
      marker = { kind: 'havdalah', at: block.havdalah };
    }

    return { day, date: block.dates[day] ?? null, rules, marker };
  }).sort((a, b) => dayRank(a.day) - dayRank(b.day));
}

/**
 * One line describing what a rule does, resolved exactly the way the
 * engine resolves it: the rule's own devices and settings win, and
 * anything it omits falls back to the defaults.
 */
export function ruleBrief(rule: RuleData, defaults: Defaults): string {
  if (rule.action === 'custom') {
    return rule.script ?? '';
  }

  const devices = rule.devices.length ? rule.devices : (defaults.devices ?? []);
  const settings = { ...(defaults.settings ?? {}), ...rule.settings };

  const parts = [devices.join(', ')];
  if (rule.action === 'on') {
    for (const value of Object.values(settings)) {
      if (value !== undefined && value !== null) parts.push(String(value));
    }
  }
  return parts.filter((part) => part !== '').join(' · ');
}

const COLOURS: Record<string, string> = {
  on: 'var(--success-color, #2e9e5b)',
  off: 'var(--error-color, #d64545)',
  custom: 'var(--info-color, #3b7ddd)',
};

export function actionColour(action: string): string {
  return COLOURS[action] ?? 'var(--secondary-text-color, #888)';
}

/** Warnings naming this rule, so a conflict shows where it happens. */
export function warningsForRule(
  ruleId: string,
  warnings: WarningData[],
): WarningData[] {
  return warnings.filter((warning) => warning.rule_ids?.includes(ruleId));
}

/** Warnings naming no rule at all, for the banner. */
export function unattachedWarnings(warnings: WarningData[]): WarningData[] {
  return warnings.filter((warning) => !warning.rule_ids?.length);
}
```

- [ ] **Step 6: Run the tests and the typecheck**

```bash
npm --prefix frontend test && npm --prefix frontend run typecheck
```

Expected: PASS, typecheck clean.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/types.ts frontend/src/strings.ts frontend/src/format.ts frontend/test/format.test.ts
git commit -m "feat: the card's pure core - types, strings and formatting"
```

---

### Task 7: `<shabbat-rule-row>`

**Files:**
- Create: `frontend/src/rule-row.ts`
- Test: `frontend/test/rule-row.test.ts`

**Interfaces:**
- Consumes: `RuleData`, `Defaults`, `WarningData` from `types.ts`; `ruleBrief`, `actionColour` from `format.ts`; `t` from `strings.ts`.
- Produces: `<shabbat-rule-row>` with properties `rule: RuleData`, `defaults: Defaults`, `warnings: WarningData[]`, `language: string`.

- [ ] **Step 1: Write the failing test**

`frontend/test/rule-row.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import '../src/rule-row';
import type { RuleData } from '../src/types';

const rule = (over: Partial<RuleData>): RuleData => ({
  id: 'r', profile: 1, day: '1', time: '11:00:00', action: 'on',
  devices: ['climate.salon'], settings: {}, name: null, icon: null,
  enabled: true, script: null, variables: {}, replay_on_restart: false,
  color: null, ...over,
});

async function render(props: Record<string, unknown>) {
  const el = document.createElement('shabbat-rule-row') as HTMLElement &
    Record<string, unknown>;
  Object.assign(el, { defaults: {}, warnings: [], language: 'en', ...props });
  document.body.appendChild(el);
  await (el as unknown as { updateComplete: Promise<unknown> }).updateComplete;
  return el;
}

describe('shabbat-rule-row', () => {
  it('shows the time and the brief', async () => {
    const el = await render({ rule: rule({}) });
    const text = el.shadowRoot!.textContent!;
    expect(text).toContain('11:00');
    expect(text).toContain('climate.salon');
  });

  it('shows the name when there is one', async () => {
    const el = await render({ rule: rule({ name: 'Shabbat morning' }) });
    expect(el.shadowRoot!.textContent).toContain('Shabbat morning');
  });

  it('marks a disabled rule as disabled, not merely dim', async () => {
    const el = await render({ rule: rule({ enabled: false }) });
    expect(el.shadowRoot!.querySelector('.row')!.classList).toContain('disabled');
    expect(el.shadowRoot!.textContent).toContain('disabled');
  });

  it('shows a conflict badge when a warning names this rule', async () => {
    const el = await render({
      rule: rule({ id: 'a' }),
      warnings: [{ kind: 'conflict', message: 'clash', rule_ids: ['a'] }],
    });
    expect(el.shadowRoot!.querySelector('.conflict')).not.toBeNull();
  });

  it('shows no conflict badge when no warning names it', async () => {
    const el = await render({
      rule: rule({ id: 'a' }),
      warnings: [{ kind: 'conflict', message: 'clash', rule_ids: ['b'] }],
    });
    expect(el.shadowRoot!.querySelector('.conflict')).toBeNull();
  });
});
```

- [ ] **Step 2: Run it and watch it fail**

```bash
npm --prefix frontend test rule-row
```

Expected: FAIL — cannot resolve `../src/rule-row`.

- [ ] **Step 3: Create `frontend/src/rule-row.ts`**

```ts
import { LitElement, css, html, nothing } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { actionColour, ruleBrief, warningsForRule } from './format';
import { t } from './strings';
import type { Defaults, RuleData, WarningData } from './types';

@customElement('shabbat-rule-row')
export class ShabbatRuleRow extends LitElement {
  @property({ attribute: false }) rule!: RuleData;
  @property({ attribute: false }) defaults: Defaults = {};
  @property({ attribute: false }) warnings: WarningData[] = [];
  @property() language = 'en';

  static styles = css`
    .row {
      display: flex;
      align-items: center;
      gap: 12px;
      padding-block: 8px;
      padding-inline: 4px;
      border-block-end: 1px solid var(--divider-color, #e0e0e0);
    }
    .row.disabled { opacity: 0.5; }
    .dot { inline-size: 10px; block-size: 10px; border-radius: 50%; flex: none; }
    .time { font-variant-numeric: tabular-nums; min-inline-size: 3.5em; }
    .body { flex: 1; min-inline-size: 0; }
    .title { font-weight: 500; }
    .brief {
      color: var(--secondary-text-color, #666);
      font-size: 0.9em;
      overflow-wrap: anywhere;
    }
    .conflict { color: var(--warning-color, #d9822b); flex: none; }
    .tag { font-size: 0.8em; color: var(--secondary-text-color, #666); }
  `;

  render() {
    const conflicts = warningsForRule(this.rule.id, this.warnings);
    const title = this.rule.name;
    return html`
      <div class="row ${this.rule.enabled ? '' : 'disabled'}">
        <span class="dot" style="background:${actionColour(this.rule.action)}"></span>
        <span class="time">${this.rule.time.slice(0, 5)}</span>
        <div class="body">
          ${title ? html`<div class="title">${title}</div>` : nothing}
          <div class="brief">${ruleBrief(this.rule, this.defaults)}</div>
        </div>
        ${this.rule.enabled
          ? nothing
          : html`<span class="tag">${t(this.language, 'disabled_rule')}</span>`}
        ${conflicts.length
          ? html`<span class="conflict" title=${conflicts[0].message}>⚠</span>`
          : nothing}
      </div>
    `;
  }
}
```

- [ ] **Step 4: Run the tests**

```bash
npm --prefix frontend test && npm --prefix frontend run typecheck
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/rule-row.ts frontend/test/rule-row.test.ts
git commit -m "feat: the rule row"
```

---

### Task 8: `<shabbat-day-group>` and `<shabbat-warnings>`

**Files:**
- Create: `frontend/src/day-group.ts`, `frontend/src/warnings.ts`
- Test: `frontend/test/day-group.test.ts`, `frontend/test/warnings.test.ts`

**Interfaces:**
- Consumes: `DayGroup`, `Defaults`, `WarningData` from `types.ts`; `<shabbat-rule-row>` from Task 7; `t` from `strings.ts`.
- Produces: `<shabbat-day-group>` with properties `group: DayGroup`, `defaults: Defaults`, `warnings: WarningData[]`, `language: string`; `<shabbat-warnings>` with properties `warnings: WarningData[]`, `language: string`.

- [ ] **Step 1: Write the failing tests**

`frontend/test/day-group.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import '../src/day-group';
import type { DayGroup } from '../src/types';

const group = (over: Partial<DayGroup>): DayGroup => ({
  day: '1', date: '2026-08-15', rules: [], marker: null, ...over,
});

async function render(props: Record<string, unknown>) {
  const el = document.createElement('shabbat-day-group') as HTMLElement &
    Record<string, unknown>;
  Object.assign(el, { defaults: {}, warnings: [], language: 'en', ...props });
  document.body.appendChild(el);
  await (el as unknown as { updateComplete: Promise<unknown> }).updateComplete;
  return el;
}

describe('shabbat-day-group', () => {
  it('shows the date in its heading', async () => {
    const el = await render({ group: group({}) });
    expect(el.shadowRoot!.textContent).toContain('2026-08-15');
  });

  it('renders a row per rule', async () => {
    const el = await render({
      group: group({
        rules: [
          { id: 'a', profile: 1, day: '1', time: '11:00:00', action: 'on',
            devices: [], settings: {}, name: null, icon: null, enabled: true,
            script: null, variables: {}, replay_on_restart: false, color: null },
          { id: 'b', profile: 1, day: '1', time: '18:00:00', action: 'off',
            devices: [], settings: {}, name: null, icon: null, enabled: true,
            script: null, variables: {}, replay_on_restart: false, color: null },
        ],
      }),
    });
    expect(el.shadowRoot!.querySelectorAll('shabbat-rule-row').length).toBe(2);
  });

  it('says so when a day has no rules rather than rendering nothing', async () => {
    const el = await render({ group: group({ rules: [] }) });
    expect(el.shadowRoot!.textContent).toContain('No rules');
  });

  it('shows the havdalah marker with its time', async () => {
    const el = await render({
      group: group({ marker: { kind: 'havdalah', at: '2026-08-15T20:01:00+03:00' } }),
    });
    const text = el.shadowRoot!.textContent!;
    expect(text).toContain('Havdalah');
    expect(text).toContain('20:01');
  });
});
```

`frontend/test/warnings.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import '../src/warnings';

async function render(warnings: unknown[]) {
  const el = document.createElement('shabbat-warnings') as HTMLElement &
    Record<string, unknown>;
  Object.assign(el, { warnings, language: 'en' });
  document.body.appendChild(el);
  await (el as unknown as { updateComplete: Promise<unknown> }).updateComplete;
  return el;
}

describe('shabbat-warnings', () => {
  it('renders nothing at all when there are none', async () => {
    const el = await render([]);
    expect(el.shadowRoot!.querySelector('.banner')).toBeNull();
  });

  it('shows only warnings that name no rule', async () => {
    const el = await render([
      { kind: 'no_profile', message: 'nothing enabled' },
      { kind: 'conflict', message: 'clash', rule_ids: ['a'] },
    ]);
    const text = el.shadowRoot!.textContent!;
    expect(text).toContain('nothing enabled');
    expect(text).not.toContain('clash');
  });
});
```

- [ ] **Step 2: Run them and watch them fail**

```bash
npm --prefix frontend test
```

Expected: FAIL — cannot resolve the two new modules.

- [ ] **Step 3: Create `frontend/src/day-group.ts`**

```ts
import { LitElement, css, html, nothing } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import './rule-row';
import { t } from './strings';
import type { DayGroup, Defaults, WarningData } from './types';

/** '2026-08-15T20:01:00+03:00' -> '20:01', without a timezone library. */
function clock(iso: string): string {
  const match = /T(\d{2}:\d{2})/.exec(iso);
  return match ? match[1] : '';
}

@customElement('shabbat-day-group')
export class ShabbatDayGroup extends LitElement {
  @property({ attribute: false }) group!: DayGroup;
  @property({ attribute: false }) defaults: Defaults = {};
  @property({ attribute: false }) warnings: WarningData[] = [];
  @property() language = 'en';

  static styles = css`
    .heading {
      display: flex;
      align-items: baseline;
      gap: 8px;
      margin-block: 16px 4px;
      font-weight: 600;
    }
    .date { color: var(--secondary-text-color, #666); font-weight: 400; }
    .empty {
      color: var(--secondary-text-color, #666);
      padding-block: 8px;
      padding-inline: 4px;
      font-size: 0.9em;
    }
    .marker {
      display: flex;
      align-items: center;
      gap: 8px;
      padding-block: 6px;
      padding-inline: 4px;
      color: var(--secondary-text-color, #666);
      font-size: 0.9em;
    }
  `;

  private label(): string {
    const { day } = this.group;
    return day === 'erev'
      ? t(this.language, 'erev')
      : `${t(this.language, 'day')} ${day}`;
  }

  render() {
    const { marker, rules } = this.group;
    return html`
      <div class="heading">
        <span>${this.label()}</span>
        <span class="date">${this.group.date ?? ''}</span>
      </div>
      ${rules.length
        ? rules.map(
            (rule) => html`
              <shabbat-rule-row
                .rule=${rule}
                .defaults=${this.defaults}
                .warnings=${this.warnings}
                .language=${this.language}
              ></shabbat-rule-row>
            `,
          )
        : html`<div class="empty">${t(this.language, 'no_rules')}</div>`}
      ${marker
        ? html`
            <div class="marker">
              <span>${marker.kind === 'havdalah' ? '✨' : '🕯️'}</span>
              <span>${t(this.language, marker.kind)}</span>
              <span>${clock(marker.at)}</span>
            </div>
          `
        : nothing}
    `;
  }
}
```

- [ ] **Step 4: Create `frontend/src/warnings.ts`**

```ts
import { LitElement, css, html, nothing } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { unattachedWarnings } from './format';
import type { WarningData } from './types';

@customElement('shabbat-warnings')
export class ShabbatWarnings extends LitElement {
  @property({ attribute: false }) warnings: WarningData[] = [];
  @property() language = 'en';

  static styles = css`
    .banner {
      display: flex;
      flex-direction: column;
      gap: 4px;
      padding: 8px 12px;
      margin-block-end: 8px;
      border-inline-start: 3px solid var(--warning-color, #d9822b);
      background: var(--secondary-background-color, #f4f4f4);
      font-size: 0.9em;
    }
  `;

  render() {
    // Warnings naming a rule are shown on that row instead, so the banner
    // carries only what has nowhere else to go.
    const shown = unattachedWarnings(this.warnings);
    if (!shown.length) return nothing;
    return html`
      <div class="banner">
        ${shown.map((warning) => html`<span>${warning.message}</span>`)}
      </div>
    `;
  }
}
```

- [ ] **Step 5: Run the tests**

```bash
npm --prefix frontend test && npm --prefix frontend run typecheck
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/day-group.ts frontend/src/warnings.ts frontend/test/day-group.test.ts frontend/test/warnings.test.ts
git commit -m "feat: the day group and the warnings banner"
```

---

### Task 9: `<shabbat-block-header>` — master switch and dry run

**Files:**
- Create: `frontend/src/block-header.ts`
- Test: `frontend/test/block-header.test.ts`

**Interfaces:**
- Consumes: `BlockData` from `types.ts`; `t` from `strings.ts`.
- Produces: `<shabbat-block-header>` with properties `block: BlockData | null`, `enabled: boolean`, `dryRun: boolean`, `canWrite: boolean`, `masterEntityId: string | null`, `language: string`. Fires `shabbat-master-toggle` (detail `{ enabled: boolean }`) and `shabbat-dry-run-toggle` (detail `{ dryRun: boolean }`) — the card performs the service calls, this element only reports intent.

**Why `canWrite`:** Plan 2a made reads open and every mutator `require_admin`. A read-only user must see the whole timeline but must not be offered a control that will fail.

- [ ] **Step 1: Write the failing test**

`frontend/test/block-header.test.ts`:

```ts
import { describe, expect, it, vi } from 'vitest';
import '../src/block-header';
import type { BlockData } from '../src/types';

const block: BlockData = {
  length: 1,
  candle_lighting: '2026-08-14T18:44:00+03:00',
  havdalah: '2026-08-15T20:01:00+03:00',
  dates: { erev: '2026-08-14', '1': '2026-08-15' },
};

async function render(props: Record<string, unknown>) {
  const el = document.createElement('shabbat-block-header') as HTMLElement &
    Record<string, unknown>;
  Object.assign(el, {
    block, enabled: false, dryRun: false, canWrite: true,
    masterEntityId: 'switch.master', language: 'en', ...props,
  });
  document.body.appendChild(el);
  await (el as unknown as { updateComplete: Promise<unknown> }).updateComplete;
  return el;
}

describe('shabbat-block-header', () => {
  it('shows the block length and its dates', async () => {
    const el = await render({});
    const text = el.shadowRoot!.textContent!;
    expect(text).toContain('2026-08-15');
  });

  it('says so when there is no block instead of rendering an empty header', async () => {
    const el = await render({ block: null });
    expect(el.shadowRoot!.textContent).toContain('No upcoming Shabbat');
  });

  it('fires an event rather than mutating its own state', async () => {
    const el = await render({ enabled: false });
    const listener = vi.fn();
    el.addEventListener('shabbat-master-toggle', listener);

    (el.shadowRoot!.querySelector('.master') as HTMLElement).click();

    expect(listener).toHaveBeenCalledOnce();
    expect((listener.mock.calls[0][0] as CustomEvent).detail).toEqual({
      enabled: true,
    });
    // No optimistic update: the control still reads the pushed state.
    expect((el as unknown as { enabled: boolean }).enabled).toBe(false);
  });

  it('disables both controls for a read-only user', async () => {
    const el = await render({ canWrite: false });
    const master = el.shadowRoot!.querySelector('.master') as HTMLButtonElement;
    const dryRun = el.shadowRoot!.querySelector('.dry-run') as HTMLButtonElement;
    expect(master.disabled).toBe(true);
    expect(dryRun.disabled).toBe(true);
  });

  it('disables the master control when the entity is unknown', async () => {
    const el = await render({ masterEntityId: null });
    const master = el.shadowRoot!.querySelector('.master') as HTMLButtonElement;
    expect(master.disabled).toBe(true);
  });
});
```

- [ ] **Step 2: Run it and watch it fail**

```bash
npm --prefix frontend test block-header
```

Expected: FAIL — cannot resolve `../src/block-header`.

- [ ] **Step 3: Create `frontend/src/block-header.ts`**

```ts
import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { t } from './strings';
import type { BlockData } from './types';

@customElement('shabbat-block-header')
export class ShabbatBlockHeader extends LitElement {
  @property({ attribute: false }) block: BlockData | null = null;
  @property({ type: Boolean }) enabled = false;
  @property({ type: Boolean }) dryRun = false;
  @property({ type: Boolean }) canWrite = false;
  @property() masterEntityId: string | null = null;
  @property() language = 'en';

  static styles = css`
    .header {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
      padding-block-end: 8px;
      border-block-end: 1px solid var(--divider-color, #e0e0e0);
    }
    .label { flex: 1; min-inline-size: 0; font-weight: 600; }
    .dates { color: var(--secondary-text-color, #666); font-weight: 400; }
    button {
      font: inherit;
      padding: 4px 10px;
      border-radius: 14px;
      border: 1px solid var(--divider-color, #e0e0e0);
      background: var(--card-background-color, #fff);
      color: inherit;
      cursor: pointer;
    }
    button[disabled] { opacity: 0.5; cursor: not-allowed; }
    button.active {
      background: var(--primary-color, #03a9f4);
      color: var(--text-primary-color, #fff);
      border-color: transparent;
    }
    .none { color: var(--secondary-text-color, #666); }
  `;

  private _dates(): string {
    if (this.block === null) return '';
    const values = Object.values(this.block.dates);
    return values.join(' → ');
  }

  // No optimistic update anywhere here: the control reports intent and
  // keeps rendering the pushed state until the server confirms.
  private _toggleMaster() {
    this.dispatchEvent(
      new CustomEvent('shabbat-master-toggle', {
        detail: { enabled: !this.enabled },
      }),
    );
  }

  private _toggleDryRun() {
    this.dispatchEvent(
      new CustomEvent('shabbat-dry-run-toggle', {
        detail: { dryRun: !this.dryRun },
      }),
    );
  }

  render() {
    return html`
      <div class="header">
        <div class="label">
          ${this.block === null
            ? html`<span class="none">${t(this.language, 'no_block')}</span>`
            : html`
                <span>${t(this.language, 'day')} ×${this.block.length}</span>
                <span class="dates">${this._dates()}</span>
              `}
        </div>
        <button
          class="master ${this.enabled ? 'active' : ''}"
          ?disabled=${!this.canWrite || this.masterEntityId === null}
          @click=${this._toggleMaster}
        >
          ${t(this.language, 'master')}
        </button>
        <button
          class="dry-run ${this.dryRun ? 'active' : ''}"
          ?disabled=${!this.canWrite}
          @click=${this._toggleDryRun}
        >
          ${t(this.language, 'dry_run')}
        </button>
      </div>
    `;
  }
}
```

- [ ] **Step 4: Run the tests**

```bash
npm --prefix frontend test && npm --prefix frontend run typecheck
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/block-header.ts frontend/test/block-header.test.ts
git commit -m "feat: the block header with the master and dry-run controls"
```

---

### Task 10: `<shabbat-scheduler-card>` — connection, state and assembly

**Files:**
- Modify: `frontend/src/card.ts` (replacing the Task 1 placeholder entirely)
- Test: `frontend/test/card.test.ts`

**Interfaces:**
- Consumes: everything from Tasks 6–9.
- Produces: the `shabbat-scheduler-card` custom element, registered in `window.customCards`.

**Connection contract:** `hass.connection.subscribeMessage(callback, { type: 'shabbat_scheduler/subscribe' })` returns `Promise<() => Promise<void>>` — an unsubscribe function. Because of Task 4 the first callback carries the current state, so the card never calls `rules/list`.

**Writes:** master → `hass.callService('switch', enabled ? 'turn_on' : 'turn_off', { entity_id: masterEntityId })`. Dry run → `hass.callService('shabbat_scheduler', 'set_dry_run', { enabled: dryRun })`. The field is `enabled` and is `required: true` — verified against `services.yaml`.

- [ ] **Step 1: Write the failing test**

`frontend/test/card.test.ts`:

```ts
import { describe, expect, it, vi } from 'vitest';
import '../src/card';
import type { CardState } from '../src/types';

const state = (over: Partial<CardState> = {}): CardState => ({
  defaults: {}, rules: [], enabled: false, dry_run: false, warnings: [],
  master_entity_id: 'switch.master',
  block: {
    length: 1,
    candle_lighting: '2026-08-14T18:44:00+03:00',
    havdalah: '2026-08-15T20:01:00+03:00',
    dates: { erev: '2026-08-14', '1': '2026-08-15' },
  },
  ...over,
});

/** A fake hass whose subscription we drive by hand. */
function fakeHass(over: Record<string, unknown> = {}) {
  let push: ((s: CardState) => void) | null = null;
  const unsubscribe = vi.fn(async () => {});
  const callService = vi.fn(async () => {});
  const hass = {
    locale: { language: 'en' },
    user: { is_admin: true },
    callService,
    connection: {
      subscribeMessage: vi.fn(async (cb: (s: CardState) => void) => {
        push = cb;
        return unsubscribe;
      }),
    },
    ...over,
  };
  return { hass, send: (s: CardState) => push!(s), unsubscribe, callService };
}

async function mount(hass: unknown) {
  const el = document.createElement('shabbat-scheduler-card') as HTMLElement &
    Record<string, any>;
  el.setConfig({});
  document.body.appendChild(el);
  el.hass = hass;
  await el.updateComplete;
  return el;
}

describe('shabbat-scheduler-card', () => {
  it('subscribes once even when hass is reassigned repeatedly', async () => {
    const { hass } = fakeHass();
    const el = await mount(hass);
    el.hass = { ...hass };
    el.hass = { ...hass };
    await el.updateComplete;
    expect(hass.connection.subscribeMessage).toHaveBeenCalledOnce();
  });

  it('renders a day group per day once the state arrives', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(state());
    await el.updateComplete;
    expect(el.shadowRoot!.querySelectorAll('shabbat-day-group').length).toBe(2);
  });

  it('unsubscribes when removed from the document', async () => {
    const { hass, unsubscribe } = fakeHass();
    const el = await mount(hass);
    el.remove();
    await Promise.resolve();
    expect(unsubscribe).toHaveBeenCalledOnce();
  });

  it('calls switch.turn_on when the master control asks to enable', async () => {
    const { hass, send, callService } = fakeHass();
    const el = await mount(hass);
    send(state({ enabled: false }));
    await el.updateComplete;

    el.shadowRoot!
      .querySelector('shabbat-block-header')!
      .dispatchEvent(
        new CustomEvent('shabbat-master-toggle', { detail: { enabled: true } }),
      );

    expect(callService).toHaveBeenCalledWith('switch', 'turn_on', {
      entity_id: 'switch.master',
    });
  });

  it('does not update its own state from a control - only the push does', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(state({ enabled: false }));
    await el.updateComplete;

    el.shadowRoot!
      .querySelector('shabbat-block-header')!
      .dispatchEvent(
        new CustomEvent('shabbat-master-toggle', { detail: { enabled: true } }),
      );
    await el.updateComplete;

    const header = el.shadowRoot!.querySelector('shabbat-block-header') as any;
    expect(header.enabled).toBe(false);
  });

  it('renders the not-configured message when the subscription is refused', async () => {
    const { hass } = fakeHass();
    hass.connection.subscribeMessage = vi.fn(async () => {
      throw new Error('not_set_up');
    });
    const el = await mount(hass);
    await el.updateComplete;
    expect(el.shadowRoot!.textContent).toContain('not configured');
  });

  it('tells a read-only user it cannot write', async () => {
    const { hass, send } = fakeHass({ user: { is_admin: false } });
    const el = await mount(hass);
    send(state());
    await el.updateComplete;
    const header = el.shadowRoot!.querySelector('shabbat-block-header') as any;
    expect(header.canWrite).toBe(false);
  });
});
```

- [ ] **Step 2: Run it and watch it fail**

```bash
npm --prefix frontend test card
```

Expected: FAIL — `setConfig is not a function` (the Task 1 placeholder defines no element).

- [ ] **Step 3: Replace `frontend/src/card.ts` entirely**

```ts
import { LitElement, css, html, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import './block-header';
import './day-group';
import './warnings';
import { buildGroups } from './format';
import { t } from './strings';
import type { CardState } from './types';
import { CARD_VERSION } from './version';

interface CardConfig {
  type?: string;
  title?: string;
}

@customElement('shabbat-scheduler-card')
export class ShabbatSchedulerCard extends LitElement {
  @state() private _state: CardState | null = null;
  @state() private _error: string | null = null;
  @property({ attribute: false }) private _config: CardConfig = {};

  private _hass: any;
  private _unsubscribe: (() => Promise<void>) | null = null;
  private _subscribed = false;

  static styles = css`
    ha-card { padding: 16px; }
    .title { font-size: 1.1em; font-weight: 600; margin-block-end: 8px; }
    .message { color: var(--secondary-text-color, #666); padding-block: 8px; }
  `;

  setConfig(config: CardConfig) {
    this._config = config ?? {};
  }

  getCardSize() {
    return 3 + (this._state?.rules.length ?? 0);
  }

  static getStubConfig() {
    return { type: 'custom:shabbat-scheduler-card' };
  }

  set hass(hass: any) {
    this._hass = hass;
    // Subscribe exactly once. Home Assistant reassigns `hass` on every
    // state change in the whole system; subscribing per assignment would
    // open a subscription per tick.
    if (!this._subscribed) {
      this._subscribed = true;
      void this._subscribe();
    }
  }

  get hass() {
    return this._hass;
  }

  private async _subscribe() {
    try {
      this._unsubscribe = await this._hass.connection.subscribeMessage(
        (payload: CardState) => {
          this._state = payload;
          this._error = null;
        },
        { type: 'shabbat_scheduler/subscribe' },
      );
    } catch (err) {
      this._error = String(err);
    }
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    void this._unsubscribe?.();
    this._unsubscribe = null;
    this._subscribed = false;
  }

  private get _language(): string {
    return this._hass?.locale?.language ?? 'en';
  }

  private get _canWrite(): boolean {
    // 2a made reads open and every mutator require_admin. Offering a
    // control that is certain to fail is worse than not offering it.
    return this._hass?.user?.is_admin === true;
  }

  private _onMaster = (event: Event) => {
    const { enabled } = (event as CustomEvent).detail;
    const entityId = this._state?.master_entity_id;
    if (!entityId) return;
    void this._hass.callService(
      'switch',
      enabled ? 'turn_on' : 'turn_off',
      { entity_id: entityId },
    );
  };

  private _onDryRun = (event: Event) => {
    const { dryRun } = (event as CustomEvent).detail;
    void this._hass.callService('shabbat_scheduler', 'set_dry_run', {
      enabled: dryRun,
    });
  };

  render() {
    if (this._error !== null) {
      return html`
        <ha-card>
          <div class="message">${t(this._language, 'not_set_up')}</div>
        </ha-card>
      `;
    }
    if (this._state === null) {
      return html`<ha-card><div class="message">…</div></ha-card>`;
    }

    const groups = buildGroups(this._state);
    return html`
      <ha-card>
        ${this._config.title
          ? html`<div class="title">${this._config.title}</div>`
          : nothing}
        <shabbat-block-header
          .block=${this._state.block}
          .enabled=${this._state.enabled}
          .dryRun=${this._state.dry_run}
          .canWrite=${this._canWrite}
          .masterEntityId=${this._state.master_entity_id}
          .language=${this._language}
          @shabbat-master-toggle=${this._onMaster}
          @shabbat-dry-run-toggle=${this._onDryRun}
        ></shabbat-block-header>
        <shabbat-warnings
          .warnings=${this._state.warnings}
          .language=${this._language}
        ></shabbat-warnings>
        ${groups.map(
          (group) => html`
            <shabbat-day-group
              .group=${group}
              .defaults=${this._state!.defaults}
              .warnings=${this._state!.warnings}
              .language=${this._language}
            ></shabbat-day-group>
          `,
        )}
      </ha-card>
    `;
  }
}

(window as any).customCards = (window as any).customCards ?? [];
(window as any).customCards.push({
  type: 'shabbat-scheduler-card',
  name: 'Shabbat Scheduler',
  description: 'The coming Shabbat or Chag as a timeline.',
});

console.info(`shabbat-scheduler-card ${CARD_VERSION}`);
```

- [ ] **Step 4: Run everything**

```bash
npm --prefix frontend test && npm --prefix frontend run typecheck && npm --prefix frontend run build
```

Expected: all PASS, and the bundle rebuilt.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/card.ts frontend/test/card.test.ts
git commit -m "feat: the card - connection, state and assembly"
```

---

### Task 11: Commit the built bundle and prove the integration serves it

**Files:**
- Modify: `custom_components/shabbat_scheduler/www/shabbat-scheduler-card.js` (rebuilt)
- Test: `tests/test_frontend.py`

**Interfaces:**
- Consumes: the rollup build from Task 1; `CARD_URL`, `CARD_VERSION` from `frontend.py` (Task 5).
- Produces: a committed bundle that a HACS install serves with no build step.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_frontend.py`:

```python
from pathlib import Path

from custom_components.shabbat_scheduler.frontend import (
    CARD_FILENAME,
    CARD_VERSION,
)

WWW = Path("custom_components/shabbat_scheduler/www")


def test_the_built_bundle_is_committed():
    """A HACS user has no Node. The bundle must be in the repository."""
    bundle = WWW / CARD_FILENAME
    assert bundle.is_file()
    assert bundle.stat().st_size > 1000


def test_the_bundle_defines_the_card_element():
    text = (WWW / CARD_FILENAME).read_text(encoding="utf-8")
    assert "shabbat-scheduler-card" in text


def test_the_bundle_version_matches_the_url_stamp():
    """Otherwise the resource URL never changes and browsers keep serving
    a stale card out of cache after an update."""
    text = (WWW / CARD_FILENAME).read_text(encoding="utf-8")
    assert CARD_VERSION in text
```

- [ ] **Step 2: Run them**

```bash
uv run pytest tests/test_frontend.py -q
```

Expected: the first two PASS (Task 1 left a bundle, Task 10 rebuilt it); the third FAILS if `frontend/src/version.ts` and `frontend.py`'s `CARD_VERSION` have drifted.

- [ ] **Step 3: Make the two versions agree**

Both `frontend/src/version.ts` and `custom_components/shabbat_scheduler/frontend.py` declare `0.1.0`. If they differ, set both to `0.1.0` and rebuild:

```bash
npm --prefix frontend run build
```

Add this note above `CARD_VERSION` in `frontend.py`:

```python
# Must match frontend/src/version.ts. The bundle carries it, and
# tests/test_frontend.py fails if the two ever drift apart.
```

- [ ] **Step 4: Run the whole suite**

```bash
uv run pytest -q && npm --prefix frontend test
```

Expected: both green.

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler/www custom_components/shabbat_scheduler/frontend.py tests/test_frontend.py
git commit -m "build: commit the card bundle so a HACS install needs no Node"
```

---

### Task 12: Throwaway Home Assistant and the end-to-end test

**Files:**
- Create: `dev/docker-compose.yml`, `dev/seed.py`, `dev/README.md`
- Create: `e2e/test_card_e2e.py`, `e2e/conftest.py`
- Modify: `pyproject.toml` (adds a `playwright` dev dependency; `testpaths` already excludes `e2e/`)

**Interfaces:**
- Consumes: the integration and the built bundle.
- Produces: `dev/seed.py` prints a long-lived token and the base URL; `e2e/` is runnable with `uv run pytest e2e/ -q` and skips cleanly when the container is not up.

**Why:** happy-dom proves the elements render in a fake DOM. It cannot prove they render inside Home Assistant, which is exactly what went wrong with an earlier markdown card on this instance that looked right and was not. Fabricating the zmanim here also makes a 3-day chag and a missing block reachable in seconds instead of months.

**Production is not involved.** Nothing in this task may address `192.168.1.14`.

- [ ] **Step 1: Create `dev/docker-compose.yml`**

```yaml
services:
  ha:
    image: ghcr.io/home-assistant/home-assistant:2026.8.2
    container_name: shabbat-scheduler-dev
    ports:
      - "8124:8123"
    volumes:
      - ./config:/config
      - ../custom_components/shabbat_scheduler:/config/custom_components/shabbat_scheduler:ro
    environment:
      TZ: Asia/Jerusalem
```

Port **8124** deliberately: the production instance answers on 8123 and the two must never be confused.

- [ ] **Step 2: Create `dev/config/configuration.yaml`**

```yaml
default_config:

input_boolean:
  salon:
    name: Salon AC stand-in
  kids:
    name: Kids AC stand-in

logger:
  default: info
  logs:
    custom_components.shabbat_scheduler: debug
```

- [ ] **Step 3: Create `dev/seed.py`**

```python
"""Bring the throwaway instance up to a testable state.

Onboards a fresh container, fabricates the Jewish Calendar sensors the
engine reads, seeds a rule set, and prints a token for the e2e tests.

Points at localhost:8124 only. It must never be aimed at a real instance.
"""

import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8124"


def _post(path: str, payload: dict, token: str | None = None) -> dict:
    request = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode()
    return json.loads(body) if body else {}


def onboard() -> str:
    """Create the owner and exchange the auth code for a token."""
    result = _post(
        "/api/onboarding/users",
        {
            "client_id": BASE,
            "name": "Dev",
            "username": "dev",
            "password": "devdevdev",
            "language": "en",
        },
    )
    code = result["auth_code"]

    request = urllib.request.Request(
        f"{BASE}/auth/token",
        data=(
            f"grant_type=authorization_code&code={code}&client_id={BASE}"
        ).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode())["access_token"]


def seed_zmanim(token: str) -> None:
    """Fabricate the two sensors the engine derives its block from."""
    for entity_id, state in (
        ("sensor.jewish_calendar_upcoming_candle_lighting",
         "2026-08-14T18:44:00+03:00"),
        ("sensor.jewish_calendar_upcoming_havdalah",
         "2026-08-15T20:01:00+03:00"),
    ):
        _post(f"/api/states/{entity_id}", {"state": state}, token)


if __name__ == "__main__":
    access_token = onboard()
    seed_zmanim(access_token)
    print(access_token)
    sys.exit(0)
```

- [ ] **Step 4: Create `dev/README.md`**

````markdown
# Throwaway instance

```bash
docker compose -f dev/docker-compose.yml up -d
# wait for http://127.0.0.1:8124 to answer, then:
uv run python dev/seed.py        # prints a token
```

Port 8124, never 8123. This instance is disposable — `docker compose down -v`
and re-seed whenever it gets confusing. It is the only Home Assistant this
plan is allowed to touch.
````

- [ ] **Step 5: Add the Playwright dependency**

```bash
uv add --dev playwright
uv run playwright install chromium
```

`pyproject.toml` already sets `testpaths = ["tests"]`, so `e2e/` is excluded from the default run with **no change needed**. Do not edit that table; Step 9 verifies the exclusion holds.

- [ ] **Step 6: Create `e2e/conftest.py`**

```python
"""End-to-end fixtures. Skips entirely when the dev container is down."""

import os
import urllib.error
import urllib.request

import pytest

BASE = "http://127.0.0.1:8124"


def _up() -> bool:
    try:
        urllib.request.urlopen(f"{BASE}/", timeout=3)
    except (urllib.error.URLError, OSError):
        return False
    return True


@pytest.fixture(scope="session")
def base_url() -> str:
    if not _up():
        pytest.skip("dev container is not running; see dev/README.md")
    return BASE


@pytest.fixture(scope="session")
def token() -> str:
    value = os.environ.get("HA_DEV_TOKEN")
    if not value:
        pytest.skip("HA_DEV_TOKEN is not set; run dev/seed.py")
    return value


@pytest.fixture
def page(base_url, token):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context()
        # The token must be injected BEFORE any page script runs. Setting
        # it after a goto is too late: the frontend has already redirected
        # to /auth/authorize by then.
        context.add_init_script(
            f"""
            localStorage.setItem('hassTokens', JSON.stringify({{
              access_token: '{token}',
              token_type: 'Bearer',
              expires_in: 1800,
              hassUrl: '{base_url}',
              clientId: '{base_url}',
              expires: 9999999999999,
              refresh_token: ''
            }}));
            """
        )
        yield context.new_page()
        browser.close()
```

- [ ] **Step 7: Write the end-to-end test**

`e2e/test_card_e2e.py`:

```python
"""The card inside a real Home Assistant.

happy-dom proves the elements render in a fake DOM. Only this proves they
render in Home Assistant - which is where an earlier card on this project
looked correct and was not.
"""


def test_the_card_renders_the_timeline(page, base_url):
    page.goto(f"{base_url}/lovelace/0")
    card = page.locator("shabbat-scheduler-card")
    card.wait_for(state="attached", timeout=30_000)

    groups = card.locator("shabbat-day-group")
    assert groups.count() == 2, "expected an erev group and a day-1 group"

    text = card.inner_text()
    assert "2026-08-15" in text
    assert "Havdalah" in text


def test_the_card_shows_its_rules_in_time_order(page, base_url):
    page.goto(f"{base_url}/lovelace/0")
    card = page.locator("shabbat-scheduler-card")
    card.wait_for(state="attached", timeout=30_000)

    times = card.locator("shabbat-rule-row .time").all_inner_texts()
    assert times == sorted(times)


def test_the_card_lays_out_right_to_left_in_hebrew(page, base_url):
    """Hebrew is the language this household actually uses. A card that
    only works in English is a card that does not work."""
    page.goto(f"{base_url}/profile")
    page.evaluate(
        "document.querySelector('home-assistant').hass"
        ".callWS({type:'frontend/set_user_data',key:'language',value:'he'})"
    )
    page.goto(f"{base_url}/lovelace/0")
    card = page.locator("shabbat-scheduler-card")
    card.wait_for(state="attached", timeout=30_000)

    direction = card.evaluate("el => getComputedStyle(el).direction")
    assert direction == "rtl"
```

- [ ] **Step 8: Run it**

```bash
docker compose -f dev/docker-compose.yml up -d
sleep 60
export HA_DEV_TOKEN=$(uv run python dev/seed.py)
# Add a dashboard view holding the card, then:
uv run pytest e2e/ -q
```

If a rule set is needed first, create it over the websocket API using the same
tooling pattern as `/home/rpi4/ha-claude-utils` — pointed at **127.0.0.1:8124**.

Expected: PASS. If the card does not appear, check that the Lovelace resource
was registered (`lovelace/resources` over the websocket) before debugging the
card itself.

- [ ] **Step 9: Confirm the fast suite is unaffected**

```bash
uv run pytest -q
```

Expected: PASS, and `e2e/` is not collected.

- [ ] **Step 10: Commit**

```bash
git add dev e2e pyproject.toml uv.lock
git commit -m "test: throwaway instance and the end-to-end card tests"
```

---

### Task 13: Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/known-behaviours.md`

**Interfaces:**
- Consumes: everything above.
- Produces: no code.

- [ ] **Step 1: Add a Card section to `README.md`**

Insert after the Entities table:

````markdown
## The card

Installing the integration also installs a Lovelace card. It is registered
automatically — there is nothing to add to your resources.

```yaml
type: custom:shabbat-scheduler-card
title: שעון שבת
```

It shows the coming block as a timeline: one group per day with its date,
the candle-lighting and havdalah markers, and each rule's time, effect and
devices. Conflicts appear on the rows they affect. The header carries the
master switch and the dry-run toggle; both are disabled for non-admin users,
who can still read the whole schedule.

The card shows only the rules matching the coming block's length, because
rules are authored per profile — a 3-day chag's rules are not shown on a
plain Shabbat. Editing rules from the card comes in a later release; for now
use the switch entities, or `import_yaml`.
````

- [ ] **Step 2: Add the two non-obvious behaviours to `docs/known-behaviours.md`**

````markdown
## The card's static path outlives a reload

Home Assistant offers no way to unregister a static path, so
`/shabbat_scheduler/` stays served after the config entry is unloaded. The
Lovelace *resource* is removed, so nothing references it. This is deliberate:
re-registering the same static path raises, and a served file nobody loads
costs nothing.

## The card is silent in YAML resource mode

Lovelace in YAML resource mode owns its resource list and cannot be written
to programmatically. In that mode the integration logs the line to add and
carries on rather than failing setup — the scheduler must keep running even
when its card cannot register itself.
````

- [ ] **Step 3: Commit**

```bash
git add README.md docs/known-behaviours.md
git commit -m "docs: the card, and two non-obvious behaviours it introduces"
```

---

## Plan Self-Review

**Spec coverage:** toolchain → Task 1. `block` → Tasks 2–3. `master_entity_id` → Task 3. Initial snapshot → Task 4. Serving and registering → Task 5. `format.ts` purity boundary → Task 6. The five elements → Tasks 7–10. Committed bundle → Task 11. Error, empty and permission states → Tasks 9 and 10 (`block: null`, `not_set_up`, non-admin) and Task 8 (empty day). RTL → Task 12's Hebrew test, plus the logical-properties constraint binding every stylesheet. Testing at three levels plus backend → Tasks 2–12. Dev container → Task 12. Rollout → out of scope by design; the card is mounted on the production dashboard only after this plan is reviewed and green, as its own decision.

**Deliberately not covered, matching the spec's "Out" list:** the edit dialog, create/delete, defaults editing, and the block-length preview selector, all of which are Plan 2b-ii. `getConfigElement` is not shipped — with only `title` to configure, `getStubConfig` plus YAML is enough, and this is the resolution of the spec's second open question.

**Connection-lost state:** the spec's table lists it, and `strings.ts` carries the `stale` string, but no task renders it. This is a deliberate deferral, not an oversight: Home Assistant's own `subscribeMessage` re-subscribes across a reconnect, so the card would show a stale banner only in the window before that resolves. Left for 2b-ii, when the behaviour can be observed against the dev container rather than guessed at.
