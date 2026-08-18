# Shabbat Scheduler Card — Read View (Plan 2b-i) Design

**Follows:** Plan 2a — the websocket rule API (`docs/superpowers/specs/2026-08-18-shabbat-scheduler-api-design.md`)
**Precedes:** Plan 2b-ii — rule authoring (edit dialog, defaults editing, block-length preview)

## Why this exists

Plan 2a built a websocket API with no client. Its rules are visible today only
as one `switch` entity per rule in a plain `entities` card, which shows a name
and a toggle and nothing else — not when a rule fires, not what it does, not
that two rules conflict. The recurring complaint through every earlier attempt
at this system was being unable to tell what was actually configured, and a
list of toggles does not answer that.

This plan builds the read view: one card that shows the coming Shabbat or Chag
as a timeline, grouped by day, with the candle-lighting and havdalah markers in
place, each rule's time and effect legible at a glance, and conflicts called
out where they occur.

Authoring is deliberately **not** in this plan. Splitting at this line means
2b-i ships something that is already better than what is on the dashboard now,
and 2b-ii adds editing on top of a foundation that has been proven against a
running instance.

## Scope

**In:** the build toolchain; serving and registering the card from the
integration; the live subscription; the day-grouped timeline with zmanim
markers; inline conflict warnings; master-switch and dry-run controls; RTL and
Hebrew; the three additive backend payload changes below; tests at three
levels.

**Out (Plan 2b-ii):** the rule edit dialog; create and delete; defaults
editing; the 1/2/3-day block-length preview selector; any new write API.

**Out (later):** replacing the seven production automations. They stay in
charge and the master switch stays off, unchanged by this plan.

## Global constraints

- Home Assistant **2026.8.2** is the target; `hacs.json` declares a
  `2026.8.0` floor.
- The card adds **no new write API**. Its only writes are `switch.turn_on` /
  `switch.turn_off` on the master switch entity and the existing
  `shabbat_scheduler.set_dry_run` service.
- **No optimistic local state.** Every render comes from the last payload the
  server pushed. A control reflects a change only once the server confirms it.
- The Python purity boundary is unchanged: `models.py`, `block.py`,
  `device_ops.py`, `const.py`, `rule_schema.py` and `yaml_io.py` import zero
  Home Assistant, and a test enforces it.
- Fire-once semantics, conflict-warn-never-resolve, and master-defaults-OFF are
  untouched. This plan changes no scheduling behaviour whatsoever.
- All development and testing happens against a **throwaway Home Assistant in
  Docker on the Pi**. Production (`192.168.1.14`) is not touched by this plan.

## Architecture

### The integration serves its own card

HACS treats a repository as exactly one category, and this repository is
already an *integration*. Rather than split the card into a second repository
that must be installed and version-matched separately, the integration serves
the card itself:

- The built bundle is committed at
  `custom_components/shabbat_scheduler/www/shabbat-scheduler-card.js`, so a
  HACS install requires no build step on the user's machine.
- On `async_setup_entry` the integration registers a static path serving that
  directory at `/shabbat_scheduler/`, and registers the Lovelace resource
  `/shabbat_scheduler/shabbat-scheduler-card.js?v=<version>` itself.
- Registration is idempotent: an existing resource with the same path has its
  version bumped rather than being duplicated. The resource is removed on
  unload.

There is direct precedent on the target instance: the `simple_timer`
integration serves `/simple_timer/timer-card.js?v=1.8.0.1786654027` as a
Lovelace resource in exactly this shape.

The implementer must confirm the current API against the installed 2026.8.2 —
the expected entry points are
`hass.http.async_register_static_paths([StaticPathConfig(...)])` for the static
route and the `lovelace` component's resource storage collection for the
resource. `manifest.json` gains `"dependencies": ["http", "lovelace"]` — `http`
for `hass.http`, `lovelace` for the resource collection. If setup fails on a
missing dependency, add what the traceback names rather than guessing wider.

### Source layout

```
frontend/
  src/
    format.ts          pure: grouping, ordering, briefs, colours, warning attachment
    strings.ts         en/he strings, keyed off hass.locale.language
    types.ts           the payload shape, mirroring _state_payload
    card.ts            shabbat-scheduler-card — owns connection and state
    block-header.ts    shabbat-block-header
    day-group.ts       shabbat-day-group
    rule-row.ts        shabbat-rule-row
    warnings.ts        shabbat-warnings
  test/                vitest: unit + component
  package.json  tsconfig.json  rollup.config.js
custom_components/shabbat_scheduler/www/
  shabbat-scheduler-card.js        built bundle, committed
```

Node is installed **per-user** under `~/.local` from the official
linux-arm64 tarball — no `sudo`, nothing installed system-wide. `frontend/`
carries its own `package.json`; `node_modules/` is git-ignored.

### `format.ts` is the purity boundary

Everything that can be decided without a DOM lives here and is unit-tested
without one: grouping rules into days, ordering days (erev before day 1),
ordering rules within a day by time, composing each row's one-line brief from
its devices and settings, mapping an action to its colour, and deciding which
warnings attach to which row. This mirrors the Python side's separation and is
where the logic that could actually be *wrong* is tested.

The Lit elements below it render what `format.ts` returns and hold no logic of
their own beyond presentation.

## Backend changes

Three additions, all additive, all things the server already knows and the card
cannot correctly derive on its own. Each ships with tests.

### 1. `block` in the state payload

`_state_payload` returns raw rules — `profile`, `day` (`erev`/`1`/`2`/`3`) and a
clock `time` — with no dates and no zmanim. The card cannot draw the timeline
from that: it has no dates for the day headings, no candle-lighting or havdalah
times for the markers, and no block length, so it cannot even tell which
profile's rules to show.

```
"block": {
  "length": 1,
  "candle_lighting": "2026-08-14T18:44:00+03:00",
  "havdalah": "2026-08-15T20:01:00+03:00",
  "dates": {"erev": "2026-08-14", "1": "2026-08-15"}
}
```

`null` when no block can be derived from the Jewish Calendar sensors — the same
condition `preview_payload` already reports as its `no_block` warning.

The alternative — having the card read the Jewish Calendar sensors and compute
dates itself — was rejected: it duplicates the block derivation that `block.py`
owns and tests, and lets the card and the engine disagree about which Shabbat
is which.

### 2. `master_entity_id` in the state payload

The card must call `switch.turn_on` on the master switch and cannot construct
its `entity_id`. Resolved server-side from unique_id `<entry_id>_master` via
`registry.async_get_entity_id("switch", DOMAIN, ...)` — the same sanctioned
lookup the tests use. Guessing an entity_id from a unique_id has already caused
two real bugs in this project; the card will not be a third.

`null` if the entity is not registered, in which case the card renders the
master control disabled rather than offering a toggle that cannot work.

### 3. `subscribe` sends an initial snapshot

`ws_subscribe` currently sends a bare result and then pushes only on change, so
a client needs `rules/list` *and* `subscribe`, with a window between them in
which a change is missed entirely. Sending the current state immediately after
the subscription result closes that window and removes the card's need to
reconcile two responses.

This changes an existing command's behaviour. It is additive for any client
that ignores unexpected pushes, and this integration's only client is the card
being written here, but the change must be covered by a test asserting the
first message after subscribing carries the current state.

## Components

### `shabbat-scheduler-card`

Owns the connection and the state. On the first `set hass` it opens one
subscription via `hass.connection.subscribeMessage`; `disconnectedCallback`
closes it. Re-subscribes if the connection object is replaced. Renders the
header, the day groups and the warnings from the last pushed payload.

Implements `setConfig(config)` (accepting an optional `title`),
`getCardSize()`, and `static getStubConfig()`. Whether it also ships
`getConfigElement` — a GUI editor for the card's own Lovelace config — is
decided in the plan; with only a `title` to configure, hand-editing YAML is not
obviously worse than a form.

### `shabbat-block-header`

The block label (e.g. "שבת · 15/08" with its day count), the master switch, and
the dry-run control. Renders the block's absence as an explicit message rather
than an empty header.

### `shabbat-day-group`

One day: its heading with the resolved date, its zmanim marker where one falls
(🕯️ candle lighting at the end of erev, ✨ havdalah at the end of the last
day), and its rule rows.

### `shabbat-rule-row`

Time, an action-coloured marker, the device icon, the rule's name (or a
generated description when unnamed), the one-line brief of devices and
settings, its enabled state, and a conflict badge where one attaches. A
disabled rule is visibly disabled rather than merely dimmed.

### `shabbat-warnings`

The summary banner for warnings that are not attached to a specific row —
`no_profile`, `no_block`, and conflicts spanning rules.

## Data flow

```
integration store ──SIGNAL_RULES_CHANGED──> ws_subscribe ──push──> card._state
                                                                      │
                                                            format.ts │
                                                                      v
                                                              rendered timeline

card ──switch.turn_on / set_dry_run──> HA services ──> store ──> push ──> re-render
```

Writes never touch local state. The master and dry-run controls call their
service and wait; the resulting push is what moves the UI. This is the same
discipline the backend follows — one source of truth, and a control that
reports what *is* rather than what was asked for.

## Error, empty and permission states

Every one of these renders something explicit. A blank card is a bug.

| Condition | Rendered as |
|---|---|
| Integration not set up (`not_set_up`) | "Shabbat Scheduler is not configured", with no controls |
| No block derivable (`block: null`) | The rule set, plus a clear note that no upcoming Shabbat could be derived from the Jewish Calendar sensors |
| No rules for this block length | The `no_profile` warning, stated plainly, not an empty list |
| Connection lost | The last known state, visibly marked stale, with controls disabled |
| Non-admin user | Full timeline, with master and dry-run controls disabled |

The non-admin case is a direct consequence of 2a: reads (`rules/list`,
`preview`, `subscribe`) are open, and writes are `require_admin`. The card
disables what a read-only user cannot do rather than offering a control that
fails.

## RTL and language

The target household reads Hebrew, and every existing dashboard card here is
Hebrew. The card inherits `dir` from Home Assistant and uses **only** logical
CSS properties (`margin-inline-start`, `padding-inline`, `text-align: start`) —
no `left`/`right` anywhere. Strings live in `strings.ts` with `en` and `he`,
selected by `hass.locale.language`, mirroring the `en`/`he` translations the
integration already ships.

## Testing

Three layers on the card, each catching a class the others cannot, plus the
backend tests for the payload changes.

**1. Vitest, pure.** `format.ts` against fixture payloads: erev sorts before
day 1; rules order by time within a day; a rule inheriting devices from
`defaults` still renders its devices; the brief composes from devices and
settings; conflicts attach to the right rows; `block: null` produces the empty
state rather than throwing.

**2. Vitest + happy-dom, component.** Each element rendered against fixture
payloads, asserting the DOM: a disabled rule renders as disabled, a conflicted
row carries its badge, the non-admin state disables the controls, the
not-set-up state renders its message and no controls.

**3. Python + Playwright, end-to-end.** Against the throwaway Docker Home
Assistant: install the integration, seed a rule set and fake Jewish Calendar
sensors, mount the card on a dashboard, and assert the rendered DOM — including
one Hebrew RTL pass. This is the layer that catches "renders under happy-dom but
not inside Home Assistant", which is precisely what went wrong with an earlier
markdown card that looked correct and was not.

**Backend, pytest.** The three new payload keys: `block` present and correctly shaped,
`block: null` when the zmanim are missing, `master_entity_id` resolving through
the registry, and `subscribe` delivering the current state as its first message.

A test that asserts something trivially true is worse than no test. Every test
for a new behaviour must be observed failing before the behaviour exists.

## Development environment

A disposable Home Assistant container on the Pi, defined by a committed
`dev/docker-compose.yml`, with a seeded config: the integration
installed, `input_boolean` helpers standing in for appliances, and fabricated
candle-lighting/havdalah sensor values. Fabricating the zmanim is the point —
it makes a 2-day or 3-day chag, a missing block, and a conflicting rule set all
reachable in seconds rather than waiting months for one to occur.

Production is not part of this plan's test path. The final confirmation pass on
`192.168.1.14` happens after 2b-i is reviewed and green, as its own decision.

## Rollout

The card is added to the שעון שבת view *alongside* the existing `entities`
card, not in place of it. The seven production automations remain in charge and
the master switch stays off. Nothing about what controls the air conditioners
changes in this plan.

## Open questions

- Whether the Lovelace resource should be registered automatically by the
  integration or left to HACS's own frontend handling. The design assumes
  automatic registration, matching `simple_timer`'s behaviour on the target
  instance; if HACS registers it too, the idempotency requirement above is what
  prevents a duplicate.
- Whether `getConfigElement` is worth shipping in 2b-i at all, given the card
  has only a `title` to configure. Deferred to the plan, where the cost is
  concrete.
