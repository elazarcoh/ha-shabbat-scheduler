# Shabbat Scheduler v2 — Alpha Design

**Supersedes the rule model of:** Plan 1 (backend), Plan 2a (API), Plan 2b-i/ii (card)
**Target:** an alpha release fit for community users, not just this house

## Why

What exists today works, but it is not what it claims to be. It is a
Shabbat-aware **climate controller** with a script escape hatch, and it cannot
be handed to anyone else:

- `Action` has exactly three values — `on`, `off`, `custom`.
- `_plan_climate` understands exactly three setting keys: `hvac_mode`,
  `temperature`, `fan_mode`.
- `_SIMPLE_DOMAINS = ("switch", "light", "input_boolean", "fan")`. Every other
  domain — `cover`, `media_player`, `humidifier`, `water_heater`, `lock`,
  `vacuum`, `notify`, `scene` — returns `Skip("unsupported domain")`.
- `const.py` contains `FAN_SYNONYMS`, which encodes *two specific air
  conditioner brands in one house* into shared code.
- The card's device picker offers three domains and renders a bespoke
  temperature/mode/fan form.

The goal is the opposite: this integration should decide **when** something
happens and guarantee it happens **once**, and Home Assistant should decide
**what** happens. Everything above is this integration doing Home Assistant's
job, badly and narrowly.

Two findings shaped this design. The most-used third-party scheduler in the
ecosystem (`nielsfaber/scheduler-component`, installed on the target instance)
stores its actions generically as `{action, entity_id, service_data}` and
executes them through `homeassistant.helpers.service.async_call_from_config` —
confirming the generic model is the right primitive. But it *also* hardcodes
the same climate workaround we do, commented "fix for climate integrations
which don't support setting hvac_mode and temperature together". That quirk is
not our special case; it is unavoidable.

It differs from us in exactly the way that matters: `track_conditions` plus
`async_track_state_change_event` means it re-asserts state. That is why it was
abandoned here. **Fire-once is the differentiator**, and it survives untouched.

## Scope

**In:** the v2 rule model (HA action + target + data + condition + replay);
generic execution with one documented climate shim; HA-native conditions;
opt-in replay with a staleness window; conflict detection retuned to overlapping
targets; storage migration; a configurable zmanim source; the card's action,
target, condition and replay editors; and the packaging a community alpha needs.

**Out of alpha:** undo; multi-step action sequences within one rule; a
`variables` editor; a focus trap for the dialogs; blocks longer than three days;
any block source other than the Jewish Calendar integration.

## Global constraints

- **The integration owns *when*; Home Assistant owns *what*.** Any domain
  knowledge in this codebase must justify itself as a compatibility shim, be
  documented as one, and be narrow.
- **Fire once, never re-assert.** Unchanged and non-negotiable.
- **A rule that does not fire must say why.** Blocked by a condition, skipped as
  too stale to replay, or failed — each is visible in the logbook and on the
  card. A rule that silently does nothing is the failure this project exists to
  prevent.
- **Conflicts are warned, never resolved.**
- **No client-side revalidation.** The Python side owns validation.
- The pure modules (`models.py`, `block.py`, `device_ops.py`, `const.py`,
  `rule_schema.py`, `yaml_io.py`) continue to import zero Home Assistant.
- Storage must migrate, not break. An alpha user's rules survive upgrades.
- Home Assistant 2026.8.2 or later.

## What survives, and what goes

**Survives — this is the product.** Nothing else in the ecosystem does it:
block derivation from candle lighting to havdalah with a length in days;
profiles keyed by block length so a 3-day Chag has its own schedule; the
`erev`/day-N vocabulary; fire-once; at-most-once restart catch-up; and
conflict warnings that never auto-resolve.

**Goes:** `Action` (the enum), `device_ops._plan_climate`, `_SIMPLE_DOMAINS`,
`FAN_SYNONYMS`, `resolve_fan_mode`, the `script` and `variables` rule fields,
and the card's climate form.

## The rule model

An action becomes a Home Assistant service call. Several fields collapse as a
consequence: a script is just `action: script.turn_on`, so `script` and
`variables` disappear; `devices` and `settings` become HA's own `target` and
`data`.

```yaml
defaults:
  target: { entity_id: [climate.salon] }
  data: { temperature: 26 }

profiles:
  1_day:
    erev:
      - id: a1
        at: "23:00:00"
        name: Salon off
        action: climate.turn_off
        target: { entity_id: climate.salon }
    day_1:
      - id: b1
        at: "11:00:00"
        name: Shabbat morning
        action: climate.set_temperature
        target: { area_id: salon }
        data: { temperature: 26, hvac_mode: cool, fan_mode: quiet }
        condition:
          - condition: state
            entity_id: binary_sensor.jewish_calendar_issur_melacha_in_effect
            state: "on"
        replay:
          enabled: true
          within: "02:00:00"
```

Field by field:

| Field | Meaning |
|---|---|
| `action` | any HA service, `"domain.service"` |
| `target` | HA's target selector — `entity_id`, `device_id`, `area_id`, `label_id`, `floor_id` |
| `data` | the service's own data, validated by HA against that service's schema |
| `condition` | optional, HA's native condition config |
| `replay` | optional — `enabled`, `within`, and the rule's `condition` as its guard |
| unchanged | `id`, `profile`, `day`, `time`, `name`, `icon`, `color`, `enabled` |

`target` support means areas and labels work, which `scheduler-component`
cannot do — it only ever handles `entity_id`.

Validation reuses HA's own schemas rather than reimplementing them:
`cv.TARGET_SERVICE_FIELDS` (`config_validation.py:1338`) for the target and
`cv.CONDITION_SCHEMA` (`:1787`) for conditions, with
`condition.async_validate_condition_config` for the deeper check.

## Execution

One path, and it is short: build the config dict and hand it to
`homeassistant.helpers.service.async_call_from_config` (`helpers/service.py:239`).
That helper accepts a `context`, so the Context-based attribution already built
for distinguishing "we did this" from "a human did this" survives intact.

**The one shim.** A `climate.set_temperature` call carrying `hvac_mode` is split
into `climate.set_hvac_mode`, a short gap, then `climate.set_temperature`
without the mode. Everything else passes through untouched. This exists because
several climate integrations — including the `aux_cloud` units on the target
instance — intermittently fail to power on when both are sent together, and
because the ecosystem's most-used scheduler independently concluded the same.
It is documented as a compatibility shim in `known-behaviours.md`, not as a
feature.

**What is lost, deliberately.** The current executor diffs desired state against
current and reports `changed`/`ok`/`failed` per attribute. An opaque service call
has no queryable desired state, so that becomes `called`/`failed`. This is an
acceptable loss: fire-once already means each rule acts once, so the
re-assertion the diff guarded against cannot arise. Retry (3 × 30s) and
per-device locking are unchanged.

## Conditions

Evaluated by HA's condition engine — `condition.async_from_config`
(`helpers/condition.py:1330`) — at fire time and again before a replay. Every
condition type comes free: `state`, `numeric_state`, `template`, `time`, `sun`,
`zone`, `and`/`or`/`not`.

A rule blocked by its condition **must be reported**, not silently dropped: a
logbook entry saying it was blocked, and a visible marker on the card's row.
This is the single largest new way for a rule to do nothing, and the constraint
above applies with full force.

## Replay

Opt-in per rule. On a restart mid-block, the passed rules with
`replay.enabled` are re-run in time order, each subject to two guards:

- **`within`** — a staleness window. A rule whose time passed longer ago than
  this is skipped and the skip is reported. Re-running an 11:00 rule at 23:00 is
  worse than not running it.
- **the rule's own `condition`** — re-evaluated before replaying.

Catch-up remains at-most-once per block and stays off the setup path. It no
longer computes a desired state, so it works identically for scripts, scenes and
notifications. `desired_state_at` and its use in catch-up are deleted.

## Conflicts, retuned

Today a conflict means two enabled rules disagree about `hvac_mode` for one
device at one moment. That is unknowable for an opaque payload, so it becomes:

> two enabled rules, in the same profile and day, at the same time, whose
> **resolved targets overlap**.

Weaker than before — two rules setting the same device to the same value now
count as a conflict — but domain-agnostic and still worth having. Warn, never
resolve, unchanged.

Resolving `area_id` or `label_id` to entities needs the registries, via
`homeassistant.helpers.target.async_extract_referenced_entity_ids`
(`helpers/target.py:158`). To keep `block.py` free of Home Assistant,
`find_conflicts` takes a resolver callable; the HA-facing layer supplies one.

## The zmanim source becomes configuration

`const.py` currently hardcodes
`CANDLE_SENSOR = "sensor.jewish_calendar_upcoming_candle_lighting"`. That entity
id derives from the Jewish Calendar config entry's *title*, so anyone who named
theirs differently — or runs two, for different locations or candle-lighting
offsets — gets an integration that silently derives no block at all. It is the
first thing an alpha user hits.

The config flow gains a step selecting the two sensors, defaulting to the
current names when they exist. If they are missing or become unavailable, a
**repair issue** is raised telling the user what to fix — rather than the
current behaviour of logging a warning and scheduling nothing.

## Migration

`STORAGE_VERSION` goes to 2 with a real migration, because an alpha user's rules
must survive an upgrade:

- `action: "on"` + `devices` + `settings` → the equivalent service call. For a
  climate target that is `climate.set_temperature` with the settings as `data`;
  for a simple domain, `<domain>.turn_on`.
- `action: "off"` → `<domain>.turn_off`.
- `action: "custom"` + `script` + `variables` → `action: script.turn_on` with
  the script as target and the variables as `data`.
- `replay_on_restart: true` → `replay: {enabled: true}` with no `within`,
  preserving today's unbounded behaviour rather than silently tightening it.

A rule that cannot be migrated is **kept, disabled, and reported** via a repair
issue naming it. Dropping a rule silently would be the worst possible outcome of
an upgrade.

## The card

The bespoke climate form is deleted. In its place:

- an **action editor** on `<ha-service-control>` for the action and its data, so
  the form for every service comes from HA's own schemas rather than being
  hand-written per domain;
- a **target picker** as `<ha-selector>` with a `{target: {}}` selector,
  covering entities, devices, areas, labels and floors;
- a **condition editor**;
- a **replay editor** (`enabled` plus `within`).

### Frontend availability — verified, not assumed

These are frontend internals rather than a public API, so all of the below was
checked in real Chromium against 2026.8.2, with the elements instantiated
inside a custom element's own shadow root to match how the card will use them.

**`<ha-service-control>` works.** Given
`{action: 'climate.set_temperature', target: {...}, data: {...}}` it rendered,
read that service's real schema — producing `temperature` and `hvac_mode` rows,
not a hand-written guess — and emitted `value-changed` carrying the full
`{action, target, data}`.

**It does not render its own target row on a dashboard.** It has the internal
logic (`_targetChanged`, `_entityPicked`) but the UI depends on
`ha-target-picker`, which is *not* pre-registered outside the automation
editor. Do not wait for it to appear.

> **CORRECTED BY PLAN 2 — the paragraph above is what was believed, and it is
> false in this card.** It was measured honestly: with `ha-service-control`
> alone in a bare shadow root, `ha-target-picker` really is undefined and the
> row really does not appear. What the measurement missed is that HA's target
> row is itself an `<ha-selector>` carrying a `{target: …}` selector, and
> `ha-selector` *dynamically imports whatever it is handed* — the very property
> the next paragraph relies on. So the moment this card renders its own
> `ha-selector{target:{}}` in the same dialog, `ha-target-picker` becomes
> defined and HA's row loads its own picker. The two findings were never
> independent: **acting on the second one is what falsifies the first.**
> Re-verified in real Chromium against 2026.8.2 / frontend 20260729.7,
> including with the card's own target editor removed entirely — HA's row
> still self-loads. The consequence for Plan 2 was the reverse of "do not wait
> for it": two target pickers per dialog, one of them silently discarded, so
> the card now has to *suppress* HA's row by hand (matched on `'target' in
> selector`, plus a `MutationObserver`, with the count reflected onto
> `data-target-rows-suppressed`). `ha-service-control` exposes no `hideTarget`
> in this version. See `frontend/src/service-editor.ts` for the mechanism and
> `docs/known-behaviours.md` for the trade-off. Anything Plan 3 builds on
> `ha-service-control` must assume the target row **is** rendered.

**`<ha-selector>` is the reliable way in.** It is always pre-registered, and it
dynamically imports whatever sub-selector it is handed — given `{target: {}}`
it rendered a working picker *and* caused `ha-target-picker` to become defined,
which it had not been a moment earlier.

So the standing rule for this card: **reach for `ha-selector` with the selector
you want, never for a specific picker element.** Availability differs
element-by-element on a dashboard — `ha-entity-picker`, `ha-area-picker`,
`ha-label-picker`, `ha-form` and `ha-icon-picker` are present, while
`ha-device-picker`, `ha-floor-picker`, `ha-target-picker` and `ha-textfield`
are not — and that list is not something to depend on.

No fallback is needed, and the YAML-data fallback previously contemplated here
is withdrawn.

Everything else the card does — the day-grouped timeline, zmanim markers,
profile chips and preview, per-day add, duplicate, delete, defaults, warnings,
master and dry-run — is unchanged.

## Alpha readiness

Distinct from the feature work, and genuinely required before anyone else
installs this:

- README rewritten for someone who has never seen it, with the rule model
  documented and a worked example that is not about air conditioners.
- HACS metadata and a brands entry.
- A diagnostics platform (config entry, rule count, resolved block, last run).
- Repair issues for the two cases above: zmanim sensors missing, and a rule that
  failed migration.
- Translation completeness for `en` and `he`, including the config flow.
- Upgrade notes describing the v1 → v2 change.

## Sub-plans

One spec, three plans, in order:

1. **The v2 model.** Schema, generic executor plus the shim, conditions, replay,
   retuned conflicts, storage migration, the zmanim config flow and repair
   issue, YAML round-trip. The card is carried along minimally so nothing
   breaks — it need not expose the new fields yet, but it must not lie about
   them.
2. **The v2 card.** The four editors above, and the climate form deleted.
3. **Alpha readiness.** The packaging list above.

Alpha ships after 3.

## Testing

The existing three-layer approach continues: pure-module unit tests, `pytest`
with `pytest-homeassistant-custom-component` for the HA-facing layer, Vitest
plus happy-dom for the card, and Playwright against the throwaway Docker
instance for anything a real browser must prove.

Two additions this design makes necessary:

- **Migration tests** with real v1 payloads for every action shape, including
  one deliberately unmigratable rule, asserting it is disabled and reported
  rather than dropped.
- **Execution tests across several domains** — at minimum `climate`, `switch`,
  `scene`, `script` and `notify` — proving the executor is genuinely generic and
  not climate-shaped. The dev fixture needs entities for these; it currently has
  only booleans and two thermostats.

Every test for a new behaviour must be observed failing before the behaviour
exists.

## Open questions

None. The one risk this design originally carried — whether HA's
service-control component can be driven from a custom card — was settled
empirically before the spec was finalised; see *Frontend availability* above.

Plan 2 should still re-check the availability list against whatever Home
Assistant version it targets, since none of these elements is a public API and
the pre-registered set can change between releases. The rule that survives a
change is the one stated above: go through `ha-selector`.
