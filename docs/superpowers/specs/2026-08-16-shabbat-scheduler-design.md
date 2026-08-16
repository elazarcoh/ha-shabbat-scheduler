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
- Handle 1-, 2-, and 3-day blocks (Shabbat, Chag, and Chag adjacent to Shabbat).
- Never fight the user: a rule acts once and then leaves the device alone.
- Everything explicit. No implicit precedence, no silently-resolved overlaps.

## Non-goals

- Replacing HA's automation engine for anything outside Shabbat/Chag.
- Zmanim-relative rule times (all times are absolute clock times). Revisit later.
- Enforcement / continuous state convergence in v1 — designed for, not built.

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

### Profile

Rules are grouped into a **profile per block length**. The plugin measures the
upcoming block and selects the matching profile.

This exists to remove a real ambiguity: with a single shared rule list, "day 2"
would mean *the last day* of a 2-day block but *a middle day* of a 3-day block.
Per-length profiles make every rule read exactly as it will run.

Each profile contains days: `erev`, then `day_1 … day_N` where N is the profile's
block length. There is no `last_day` role — within a known-length profile the
last day is simply `day_N`.

**If no profile exists for the upcoming block length, nothing fires**, and a
`persistent_notification` is raised as soon as the block is detected — not when
it begins. Silence is the safe failure, but it must be a loud silence.

### Rule

```yaml
id:        uuid
profile:   1 | 2 | 3          # block length this rule belongs to
day:       erev | 1 | 2 | 3   # which day within the block
time:      "11:00:00"         # absolute clock time
name:      "בוקר שבת"          # optional
icon:      mdi:air-conditioner  # optional, defaults per action kind
enabled:   true
action:    on | off | custom
devices:   [climate.a, climate.b]
settings:                     # action == on; merged over defaults
  temperature: 26
  hvac_mode:   cool
  fan_mode:    quiet
script:    script.x           # action == custom only
variables: {}                 # action == custom only
replay_on_restart: false      # action == custom only
color:     "#2e9e5b"          # optional per-rule override
```

Resolution is direct: `erev` → the candle-lighting date; `day_i` →
`candle_lighting.date() + i`.

Two deliberate non-clampings:

- **Erev rules are not clamped to candle lighting.** A rule at erev 17:00 fires
  at 17:00, before Shabbat begins, which allows pre-cooling. The card draws a
  candle-lighting divider so it is visually obvious which side a rule sits on.
- **Last-day rules are not clamped to havdalah.** The production `Sat 23:00 OFF`
  is *after* havdalah and must still fire. A rule is a clock time on a date; the
  block only decides which dates.

All devices in a rule share one action and one settings block. A different
temperature for a different room means a separate rule.

### Defaults

A single `defaults` block is merged under every rule's `settings` and `devices`,
so the common case stays short:

```yaml
defaults:
  temperature: 26
  hvac_mode: cool
  fan_mode: quiet
  devices: [climate.air_conditioner_2]
```

Per-rule values override per key (shallow merge). Nothing else is layered —
there is no profile-level or day-level defaults tier, deliberately, to keep
"where did this value come from" answerable at a glance.

---

## Conflicts

Detected, surfaced, and **never silently resolved**. Overlaps are warnings, not
errors: the user may save and proceed anyway.

| Case | Verdict |
|---|---|
| Same profile+day+time+device, different action | **Conflict** — warn loudly |
| Same profile+day+time+device, identical action | Redundant — info |
| Device missing from the entity registry | Warning |
| Setting unsupported by a device (no synonym match) | Warning |
| Profile missing for a block length that will occur | Warning + notification |

Because there is no precedence rule, a genuine conflict has no defined winner —
which is exactly why it must be visible rather than quietly resolved. Warnings
appear at save time via the websocket API, in `simulate` output, and as a badge
on the card row.

Independently, the engine keeps a **per-device command queue** so two rules
firing at the same instant cannot interleave their multi-call sequences. Without
it, a concurrent ON and OFF on one climate entity can leave the device off but
with a target temperature applied — a half-configured state that matches neither
rule.

---

## Architecture

```
custom_components/shabbat_scheduler/
  block.py          pure logic; zero HA imports; fully unit-testable
  store.py          rule CRUD, persisted in HA .storage
  yaml_io.py        import/export of the whole rule set
  engine.py         timers, idempotent apply, retry, catch-up, dry-run
  switch.py         master switch + one switch per rule
  sensor.py         next-block / next-action / last-run sensors
  websocket_api.py  CRUD + reorder + preview + validation warnings
  config_flow.py    single-instance UI setup
  manifest.json
  const.py

www/  shabbat-scheduler-card.js
```

`block.py` holds every piece of tricky reasoning (block detection, profile
selection, date resolution, desired state, conflict detection) as pure functions
with no HA dependency, so it runs in milliseconds under plain pytest.

### Storage

**`.storage` is the source of truth** — the standard HA mechanism, written by the
UI and websocket API. YAML is an **import/export view**, not the store.

A YAML file is deliberately *not* authoritative: if both a file and the UI can
write, there is no non-confusing reconciliation story, and HA has no file-watch
convention for it. Export/import gives the same practical benefits — version
control, diff review before a Shabbat, backup/restore, and authoring outside the
phone UI — without dual-writer ambiguity.

Canonical storage is a flat rule list (stable ids, simple reorder). YAML export
groups by profile and day for readability:

```yaml
defaults:
  temperature: 26
  hvac_mode: cool
  fan_mode: quiet

profiles:
  1_day:
    erev:
      - { at: "22:30", action: on,  devices: [climate.aux_cloud_e87072dbfee2_ac] }
      - { at: "23:00", action: off, devices: [climate.air_conditioner_2] }
    day_1:
      - { at: "11:00", action: on,  name: בוקר שבת }
      - { at: "18:00", action: off }
      - { at: "23:00", action: off }
  2_day:
    ...
```

### Entities

| Entity | Purpose |
|---|---|
| `switch.shabbat_scheduler` | master; off cancels every pending timer |
| `switch.shabbat_rule_<profile>_<day>_<time>_<action>` | per-rule enable |
| `sensor.shabbat_scheduler_next_block` | state = day count; attrs: start, end, selected profile, resolved dates |
| `sensor.shabbat_scheduler_next_action` | state = next fire time; attrs: rule, action, devices |
| `sensor.shabbat_scheduler_last_run` | state = last fire time; attrs: per-device changed/ok/failed |

Per-rule switch names include the profile so two profiles' rules are never
confused.

### Websocket API

`shabbat_scheduler/rules/{list,create,update,delete,reorder}`,
`shabbat_scheduler/{preview,validate,export_yaml,import_yaml}`.

---

## Behavior

### Idempotent apply

Modelled on Ansible: read current state, compare to desired, act only on what
differs, report per sub-call.

```
11:00  בוקר שבת
  climate.air_conditioner_2   hvac_mode    off → cool    changed
  climate.air_conditioner_2   temperature   26 → 26      ok (skipped)
  climate.air_conditioner_2   fan_mode    auto → quiet   changed
  climate.aux_cloud_…         hvac_mode   cool → cool    ok (skipped)
```

Benefits: far fewer commands to flaky cloud ACs; a real audit trail that
distinguishes "ran and changed nothing" from "never ran"; and catch-up becomes
convergence, therefore safe to repeat.

**Staleness guard:** `unknown`, `unavailable`, or a state last updated before our
most recent command to that device all count as *must apply*, never as "already
correct". The `aux_cloud` units were measured lagging 5–10 s on `fan_mode`, so a
naive read would skip a command that never actually landed.

Each application emits a `shabbat_scheduler_rule_applied` event carrying the
per-device, per-attribute outcome, and updates `sensor.…_last_run`.

### Scheduling

Recompute on: HA start, candle-lighting/havdalah sensor change, any rule edit,
master toggle, and midnight. Each resolved rule gets one
`async_track_point_in_time`.

**Fire once, never re-assert.** At 11:00 the command is sent and the device is
then left alone; turning it off by hand at 11:05 leaves it off. This is the
direct fix for the behavior that made the previous component unusable.

### Desired state

`block.py` exports a first-class pure function:

```python
desired_state_at(rules, block, when, device) -> Action | None
```

It returns the action of the most recent already-passed `on`/`off` rule affecting
that device within the active block's profile, or `None` where undefined (before
the block's first rule, after its last, or when the device is driven only by
`custom` rules). Restart catch-up is one caller; **enforcement would be a second
caller of the same function**. It is exported deliberately rather than living
inside catch-up, so enforcement is an addition rather than a refactor.

Where a conflict makes the answer ambiguous, the function returns the conflict
rather than guessing, and the caller declines to act and logs.

### Restart catch-up

The active block is the one whose span `[candle_lighting … last rule time]`
contains now — deliberately extended past havdalah so post-havdalah rules such as
`23:00 OFF` are covered. For each device, `desired_state_at(now)` is applied once,
idempotently.

`action: custom` rules are **excluded by default** (`replay_on_restart: false`),
because an arbitrary script may not be idempotent — it might notify, toggle, or
start a timed sequence. `on`/`off` rules always replay.

### Command context (required now, enables enforcement later)

Every service call carries an HA `Context` that the engine records. The resulting
`state_changed` event carries that context, which is how a change we caused is
distinguished from a change a human caused. Required in v1 even though nothing
consumes it yet — without it, enforcement can never tell drift from deliberate
override, which is the most likely reason the previous `scheduler` fought the user.

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
   warns, rather than failing the whole rule.

### Error handling

- Device unavailable at fire time → 3 retries, 30 s apart, then log and raise a
  `persistent_notification`.
- `jewish_calendar` unavailable → the last computed block stays cached, so an
  outage cannot silently wipe the schedule.
- A single device failing does not abort the remaining devices in the rule.

### Diagnostics

- **`shabbat_scheduler.simulate`** — given any date, returns the resolved
  schedule, the selected profile, and all validation warnings, with no side
  effects. Answers "what happens this Shabbat?" and "what happens on a 3-day
  chag?" without waiting for one.
- **`dry_run` option** — Ansible's `--check`: reports exactly what *would* change,
  per device and attribute, calling no services.

---

## Card

Single-column, time-sorted list grouped by day, with zmanim as inline dividers
positioned by time. A profile selector shows which rule set is being viewed;
it defaults to the profile of the upcoming block.

```
│▌│ 22:30 │(icon)│ קירור לילה לבנות          │ ON │ ⬤ │
│ │       │      │ מזגן חדר בנות · 26° · שקט │    │   │
 ↑    ↑      ↑     ↑ optional title            ↑    ↑
color time  icon   brief underneath          tag  switch
```

- **Optional title.** When absent, the generated brief is promoted to the main
  line and the row collapses to one line.
- **Brief** is generated from the rule: devices, and settings when `action: on`.
- **Icon** is per-rule and user-chosen, defaulting by action kind.
- **Switch** toggles that rule's switch entity.
- **Disabled rules** render greyed with the switch off.
- **Conflicting rules** render with a warning badge, still saved and still shown.
- **Master switch** in the header, alongside the next-block summary.

Authoring affordances, since profiles are explicit rather than inferred:

- **Clone day** — copy a day's rules to another day, or to another profile.
- **Convert generic ↔ specific** — an "every day" authoring action materializes
  explicit per-day rules; collapsing back to a single day is offered only when
  the days are identical, so nothing is silently lost.

Card options: `colors` (per action kind, any hex), `show_tags`, `title`.

Constraints discovered while prototyping, which justify a custom card:

- HA's `markdown` card strips all `style` attributes (DOMPurify) — colored
  layouts are impossible there.
- `tile` cards cannot express one rule targeting several devices; an
  `18:00 OFF סלון + חדר בנות` rule had to be split into two rows.
- Native cards offer no master switch, no inline zmanim divider, and no
  add/reorder affordance.

---

## Testing

1. **Pure unit tests on `block.py`** — block detection, profile selection, date
   resolution, desired state, conflict detection, DST transitions, year
   boundaries. No HA, no network.
2. **Engine tests** with `pytest-homeassistant-custom-component` — fake the
   clock, assert exactly which service calls fire, and assert that already-correct
   state produces *no* call.
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

Steps 4→5 briefly arm both systems. They issue identical commands, and idempotent
apply means the second one is a no-op — preferable to a gap.

## Deployment

Development uses direct file access to `/config` over `ssh ha`, which requires
`id_ed25519_ha_deploy` to be copied to the Pi (not yet done as of 2026-08-16).

Card development does **not** need `/config`: Lovelace resources are fetched by
the browser, so the card is served over HTTP from the Pi (`192.168.1.50:8899`,
CORS header required) and registered via `lovelace/resources/create`. Already
working, and used to prototype the card.

Final distribution is a HACS custom repository.

## Future: enforcement (designed for, not built in v1)

v1 is strictly fire-once. Enforcement is deferred because discrete events are far
easier to reason about and verify than a continuously evaluated state function —
but the design keeps the door open at near-zero cost.

When added, enforcement becomes a **second caller of `desired_state_at`**,
reacting to `state_changed` instead of a timer:

```yaml
enforce: none | window | until_next   # per rule, default none
enforce_minutes: 15                   # when enforce == window
```

- **`none`** — pure fire-once (v1 behavior; the only legal value for `custom`).
- **`window(N)`** — re-assert only for N minutes after the rule fires. Targets the
  observed failure mode (cloud AC offline or command dropped at the moment of
  firing), then goes quiet. Expected default choice.
- **`until_next`** — re-assert until the next rule for that device.

**All modes yield permanently to a manual override** until the next rule fires,
detected via the recorded command context. The plugin must never fight the user.

Two definitional limits, not implementation shortcuts:

- **`custom` rules can never be enforced.** A script's effect is opaque, so no
  desired state is derivable.
- **Enforcement is scoped to an active block**, between its first and last rule.
  Outside that, desired state is undefined and enforcement must not run.

Idempotent apply is the natural stepping stone: it already answers "is the device
in the desired state?", which is the question enforcement asks continuously.

## Open questions

- Zmanim-relative rule times — deferred, revisit once absolute times are proven.
- Whether `until_next` enforcement is worth building, or `window(N)` covers every
  real case.
- Whether profiles should key on anything beyond block length (e.g. Chag vs
  Shabbat of the same length). Not needed for AC; may matter for other appliances.
