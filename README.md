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
| one switch per rule | named after the rule, so its entity_id follows the rule's name rather than a fixed pattern — find it under Settings → Devices & Services → entities |
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
  devices: [climate.living_room]
  settings:
    temperature: 26
    hvac_mode: cool
    fan_mode: quiet

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
