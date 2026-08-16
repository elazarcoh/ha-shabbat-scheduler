# Shabbat Scheduler — Design

**Status:** approved, not yet implemented
**Date:** 2026-08-16

## Problem

Appliances (initially air conditioners) must follow a fixed schedule across
Shabbat and Chag, when they cannot be operated by hand. Three earlier attempts
each failed for a different reason:

1. **`scheduler` (nielsfaber) + `scheduler-card`** — the card only renders
   single-action timeslots, and the component mutated its own stored timeslots
   (a configured `18:00→23:00` slot silently became `18:00→22:59` +
   `22:59→23:00`). It also re-asserted state, repeatedly switching an AC back on.
2. **Native `schedule` helper** — a real weekly grid, but blocks cannot cross
   midnight and static clock times drift against candle lighting through the year.
3. **Plain automations** (current production setup) — reliable and predictable,
   but no grouped/sorted UI, one device per automation, and no concept of a
   multi-day Chag. Eight were created and individually verified; **seven exist
   today** — `automation.shabbat_ac_living_room_sat_23_00_off` disappeared from
   storage between 2026-08-14 and 2026-08-15 by an unknown mechanism, and has
   deliberately not been recreated pending a decision.

Those seven automations remain in production and are **not** replaced until this
plugin is proven.

## Goals

- A sorted, grouped, colored list of rules that is readable at a glance.
- Enable/disable the whole flow, or any single rule.
- One rule may target **several devices**.
- Handle 1-, 2-, and 3-day blocks (Shabbat, Chag, and Chag adjacent to Shabbat)
  from one rule list, with no duplication.
- Never fight the user: a rule acts once and then leaves the device alone.

## Non-goals

- Replacing HA's automation engine for anything outside Shabbat/Chag.
- Zmanim-relative rule times (all times are absolute clock times). Revisit later.
- Covering a Chag that falls on a weekday for the *legacy* automations — that
  gap already exists in production and is out of scope here.

---

## Domain model

### Block

A **block** is one contiguous Shabbat/Chag period, derived entirely from
`sensor.jewish_calendar_upcoming_candle_lighting` and
`sensor.jewish_calendar_upcoming_havdalah`. Nothing is hand-maintained.

```
length_in_days = havdalah.date() - candle_lighting.date()
```

| Case | Candle lighting | Havdalah | Length | Erev | Full days |
|---|---|---|---|---|---|
| Regular Shabbat | Fri | Sat | 1 | Fri | Sat |
| Chag + Shabbat | Thu | Sat | 2 | Thu | Fri, Sat |
| Chag + Chag + Shabbat | Wed | Sat | 3 | Wed | Thu, Fri, Sat |

Verified against live sensors: `2026-08-14 18:44` → `2026-08-15 20:01` = 1 day.

### Rule

```yaml
id:        uuid
name:      "בוקר שבת"        # optional
icon:      mdi:air-conditioner  # optional, defaults per action kind
enabled:   true
day_role:  erev | every_day | last_day | day_n
day_index: 2                  # only when day_role == day_n, 1-based over full days
time:      "11:00:00"         # absolute clock time
action:    on | off | custom
devices:   [climate.a, climate.b]
settings:                     # action == on only
  temperature: 26
  hvac_mode:   cool
  fan_mode:    quiet
script:    script.x           # action == custom only
variables: {}                 # action == custom only
replay_on_restart: false      # action == custom only; see Catch-up
color:     "#2e9e5b"          # optional per-rule override
```

### Day-role resolution

```
"every_day, 11:00, ON"
  1-day block → Sat 11:00
  3-day block → Thu, Fri, Sat 11:00     (no extra rules)

"erev, 23:00, OFF"  → always the candle-lighting date
"last_day, 20:30"   → always the havdalah date
"day_n(2), 09:00"   → 2nd full day; no-op if the block is shorter
```

Two deliberate non-clampings:

- **Erev rules are not clamped to candle lighting.** A rule at erev 17:00 fires
  at 17:00, before Shabbat begins, which allows pre-cooling. The card draws a
  candle-lighting divider so it is visually obvious which side a rule sits on.
- **Last-day rules are not clamped to havdalah.** The production `Sat 23:00 OFF`
  is *after* havdalah and must still fire. A rule is a clock time on a date; the
  block only decides which dates.

All devices in a rule share one action and one settings block. A different
temperature for a different room means a separate rule.

---

## Architecture

```
custom_components/shabbat_scheduler/
  block.py          pure logic; zero HA imports; fully unit-testable
  store.py          rule CRUD, persisted in HA .storage
  engine.py         timers, firing, retry, restart catch-up, dry-run
  switch.py         master switch + one switch per rule
  sensor.py         next-block / next-action sensors
  websocket_api.py  list/create/update/delete/reorder + schedule preview
  config_flow.py    single-instance UI setup
  manifest.json
  const.py

www/ (or HACS frontend section)
  shabbat-scheduler-card.js
```

`block.py` holds every piece of tricky reasoning (which dates are in a block,
how `every_day` expands, what `day_n` resolves to, catch-up selection) as pure
functions with no HA dependency, so it runs in milliseconds under plain pytest.

### Entities

| Entity | Purpose |
|---|---|
| `switch.shabbat_scheduler` | master; off cancels every pending timer |
| `switch.shabbat_rule_<slug>` | per-rule enable |
| `sensor.shabbat_scheduler_next_block` | state = day count; attrs: start, end, resolved dates + weekday names |
| `sensor.shabbat_scheduler_next_action` | state = next fire time; attrs: rule, action, devices |

Per-rule switches exist so the integration is fully usable with native
`entities`/`tile` cards before the custom card ships.

### Websocket API

`shabbat_scheduler/rules/{list,create,update,delete,reorder}` and
`shabbat_scheduler/preview` (resolved schedule for a given or upcoming block).

---

## Behavior

### Scheduling

Recompute on: HA start, candle-lighting/havdalah sensor change, any rule edit,
master toggle, and midnight. Each resolved rule gets one
`async_track_point_in_time`.

**Fire once, never re-assert.** At 11:00 the command is sent and the device is
then left alone; turning it off by hand at 11:05 leaves it off. This is the
direct fix for the behavior that made the previous component unusable.

### Restart catch-up

The active block is the one whose span `[candle_lighting … last rule time]`
contains now — deliberately extended past havdalah so post-havdalah rules such
as `23:00 OFF` are covered. For each device, only the single most recent
already-passed rule is applied.

`action: custom` rules are **excluded from catch-up by default**
(`replay_on_restart: false`), because an arbitrary script may not be idempotent —
it might notify, toggle, or start a timed sequence. `on`/`off` rules are
idempotent and always replay.

### Applying actions per device

Dispatch by device domain. Two behaviors are required by hardware already in
production:

1. **Climate ON is three separate calls** — `set_hvac_mode` → `set_temperature`
   → `set_fan_mode`. The combined `set_temperature(hvac_mode=…)` form was
   observed to silently fail to power on the `aux_cloud` units.
2. **Fan-mode names differ per device** — `climate.air_conditioner_2` exposes
   `quiet`; `climate.aux_cloud_*` expose `silent`. The engine reads the device's
   actual `fan_modes`, falls back through a synonym table
   (`quiet ↔ silent ↔ low`), and if nothing matches skips only that sub-call and
   logs, rather than failing the whole rule.

### Error handling

- Device unavailable at fire time → 3 retries, 30 s apart (the cloud ACs do go
  briefly unavailable), then log and raise a `persistent_notification`.
- `jewish_calendar` unavailable → the last computed block stays cached, so an
  outage cannot silently wipe the schedule.
- A single device failing does not abort the remaining devices in the rule.

### Diagnostics

- **`shabbat_scheduler.simulate` service** — given any date, returns the fully
  resolved list of what would fire and when, with no side effects. Answers "what
  happens this Shabbat?" and "what happens on a 3-day chag?" without waiting.
- **`dry_run` option** — rules log and emit events but call no services.

---

## Card

Single-column, time-sorted list grouped by day (layout A), with zmanim shown as
inline dividers positioned by time.

```
│▌│ 22:30 │(icon)│ קירור לילה לבנות          │ ON │ ⬤ │
│ │       │      │ מזגן חדר בנות · 26° · שקט │    │   │
 ↑    ↑      ↑     ↑ optional title            ↑    ↑
color time  icon   brief underneath          tag  switch
```

- **Optional title.** When absent, the auto-generated brief is promoted to the
  main line and the row collapses to one line.
- **Brief** is generated from the rule: devices, and settings when `action: on`.
- **Icon** is per-rule and user-chosen, defaulting by action kind.
- **Switch** toggles that rule's `switch.shabbat_rule_<slug>`.
- **Disabled rules** render greyed with the switch off.
- **Master switch** in the card header, alongside next-block summary.

Card options: `colors` (per action kind, any hex), `show_tags` (the ON/OFF/SCRIPT
pill is arguably redundant against the color bar and icon tint, so it is
toggleable), `title`.

Constraints discovered while prototyping, which justify a custom card:

- HA's `markdown` card strips all `style` attributes (DOMPurify) — colored
  layouts are impossible there.
- `tile` cards cannot express one rule targeting several devices; an
  `18:00 OFF סלון + חדר בנות` rule had to be split into two rows.
- Native cards offer no master switch, no inline zmanim divider, and no
  add/reorder affordance.

---

## Testing

1. **Pure unit tests on `block.py`** — 1/2/3-day blocks, day-role expansion,
   catch-up selection, DST transitions, year boundaries. No HA, no network.
2. **Engine tests** with `pytest-homeassistant-custom-component` — fake the
   clock, assert exactly which service calls fire and when.
3. **Live verification against `input_boolean` test devices** before any real AC
   is involved. Card verified via `ha-shot` screenshots.

## Rollout

The current seven automations stay in production throughout.

```
1. Install integration; master switch defaults OFF → cannot act
2. Rules target input_boolean test devices → simulate 1/2/3-day blocks
3. Repoint rules at real ACs; master ON, dry_run ON → observe one real Shabbat
4. dry_run OFF; the legacy automations remain enabled as backup
5. Disable (not delete) the legacy automations → one clean Shabbat
6. Delete the legacy automations
```

Steps 4→5 briefly arm both systems. They issue identical commands, so the worst
case is a duplicate `turn_off`, which is harmless — preferable to a gap.

## Deployment

Development uses direct file access to `/config` over `ssh ha`, which requires
`id_ed25519_ha_deploy` to be copied to the Pi (not yet done as of 2026-08-16).

Card development does **not** need `/config`: Lovelace resources are fetched by
the browser, so the card is served over HTTP from the Pi (`192.168.1.50:8899`,
CORS header required) and registered via `lovelace/resources/create`. This is
already working and was used to prototype the card.

Final distribution is a HACS custom repository.

## Open questions

- Zmanim-relative rule times — deferred, revisit once absolute times are proven.
- Whether a Chag falling on a weekday needs coverage beyond the block model
  (the block model already handles it; only the legacy automations do not).
- Whether `day_n` is needed at all in practice, or whether
  `erev`/`every_day`/`last_day` suffice. Ship it; drop it if unused.
