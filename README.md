<p align="center">
  <img src="brands/icon@2x.png" alt="Shabbat Scheduler" width="160">
</p>

# Shabbat Scheduler

*Alpha. 790 tests passing (443 Python + 15 end-to-end, 332 frontend).*

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=elazarcoh&repository=ha-shabbat-scheduler&category=integration)
[![Add Integration to your Home Assistant instance.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=shabbat_scheduler)

[![CI](https://github.com/elazarcoh/ha-shabbat-scheduler/actions/workflows/ci.yml/badge.svg)](https://github.com/elazarcoh/ha-shabbat-scheduler/actions/workflows/ci.yml)
[![e2e](https://github.com/elazarcoh/ha-shabbat-scheduler/actions/workflows/e2e.yml/badge.svg)](https://github.com/elazarcoh/ha-shabbat-scheduler/actions/workflows/e2e.yml)
[![License: MIT](https://img.shields.io/github/license/elazarcoh/ha-shabbat-scheduler)](LICENSE)
[![Last commit](https://img.shields.io/github/last-commit/elazarcoh/ha-shabbat-scheduler)](https://github.com/elazarcoh/ha-shabbat-scheduler/commits/master)
[![Open issues](https://img.shields.io/github/issues/elazarcoh/ha-shabbat-scheduler)](https://github.com/elazarcoh/ha-shabbat-scheduler/issues)

Shabbat Scheduler schedules Home Assistant to do anything — turn a light
on, run a scene, send a notification, adjust a thermostat — at specific
times across Shabbat and Chag, without you touching a switch.

## ✨ Highlights

- 📅 **Built on the Jewish Calendar integration.** Every schedule is
  derived straight from its candle-lighting and havdalah sensors — a
  1-day Shabbat, a 2- or 3-day Chag, all resolved automatically. No
  manual date math, ever.
- 🔁 **A rule fires once and leaves the device alone.** Not a state to
  keep re-asserting — turn something off by hand five minutes later and
  it stays off. No automation fighting you for control of your own
  switch.
- ⚡ **Set up in minutes.** Install via HACS, point it at two sensors you
  probably already have, and the card is already on your dashboard —
  nothing to add to Lovelace resources by hand.
- 🎛️ **Schedule *anything*, not just climate.** Any `domain.service` Home
  Assistant can call — lights, scenes, notifications, thermostats — with
  Home Assistant's own target selector (entity, device, area, or label)
  and its own condition schema. No fixed vocabulary, no allow-list.
- 🧪 **Prove it before you trust it.** Run any rule, or a whole day's
  schedule, right now — simulated or for real — instead of waiting for
  the next actual Shabbat to find out if you set it up correctly.
- 🧬 **Clone a day or a whole profile.** Building a 3-day Chag from a
  Shabbat you already trust is a couple of taps, not retyping every rule.
- ⚠️ **Conflicts are reported, never silently resolved.** Two rules
  targeting the same device at the same time get flagged — there's no
  hidden winner, the choice stays yours.

![The card showing a real, resolved schedule](docs/images/card-screenshot.png)

## Quick start

1. **Install the [Jewish Calendar][jewish-calendar] integration first, if
   you don't already have it.** This isn't optional — every block this
   scheduler runs is derived from its candle-lighting and havdalah
   sensors, and setup can't complete without two sensors to point at.
2. **Check your Home Assistant version.** This needs `2026.8.0` or newer;
   HACS will refuse the install otherwise.
3. **Install via HACS.** Use the button above, or add this repository as
   a custom repository of type *Integration* by hand, then restart Home
   Assistant.
4. **Add the integration.** Use the button above, or go to Settings →
   Devices & Services → Add Integration → **Shabbat Scheduler**. Jewish
   Calendar's candle-lighting and havdalah sensors are offered as the
   defaults — accept them unless you have a reason not to.
5. **The master switch starts off.** Nothing can happen yet: installing
   (and even authoring rules) cannot touch a single appliance until you
   deliberately turn `switch.shabbat_scheduler` on. This is deliberate —
   safe by default — so you can set everything up at your own pace before
   anything is live.
6. **Open the card.** It's a Lovelace card and it registers itself the
   moment the integration is added — there is nothing to add to your
   dashboard's resources (unless your Lovelace is in YAML resource mode,
   in which case check the log for the one line to add). Add it to a
   dashboard:

   ```yaml
   type: custom:shabbat-scheduler-card
   title: שעון שבת
   ```

   Tap **+ Add rule** under a day and author your first one. A safe first
   rule to try: action `input_boolean.turn_on`, target one `input_boolean`
   entity — nothing about getting this wrong is dangerous, since it's just
   a toggle. Give the **action** (which service to call — `domain.service`,
   e.g. `input_boolean.turn_on`), a **target** (which entity, area, device
   or label it acts on), a **time**, and save.
7. **Prove it works before you trust it.** Open the rule you just wrote
   and tap **Run now** — see "Testing your rules" below for what that does
   and how to test a whole day at once, so you're never waiting for the
   next real Shabbat to find out whether you set something up correctly.
8. **Turn the master switch on when you're ready.** Everything you've
   authored starts running on the next Shabbat or Chag it applies to.

[jewish-calendar]: https://www.home-assistant.io/integrations/jewish_calendar/

### Testing your rules

You do not have to wait for a real Shabbat to find out whether a rule
works. Open any rule and press **Run now** for an inline choice: Simulate
(reports what would happen, calls nothing) or Run for real, each a
deliberate second step rather than a single click. To test a whole day's
schedule at once — in order, exactly as it would really run — use the ▶
icon in the header, which also lets you force every condition to pass so
you can see past a guard that is currently blocking; running that whole
day for real asks the same kind of explicit confirmation, since it is a
bigger action than running one rule. Neither path changes any real timer:
they run the exact same `resolve_rules()` → `async_apply_rule()` path a
real fire uses, on demand, any day of the week. Run Now is disabled while
a rule has unsaved edits, so it can never report on a version of the rule
that is not the one on screen.

## Terminology

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
- **Reports what happened, honestly.** A rule is an opaque service call, not
  a state to compare against — there is nothing to read back and check. Each
  call reports `called`, `would_call`, `failed`, `blocked`, or skipped (as
  stale, or as never opted into replay), plus two diagnostics for a call
  that succeeded but reached nothing real:
  `unknown_targets` (a typo) and `no_live_targets` (a target that resolved
  to nothing that exists). The integration hands the call to Home Assistant
  and tells you exactly what happened — it does not pretend to know what
  changed.
- **No precedence.** Overlapping rules are reported as conflicts, never
  silently resolved — there is no defined winner, so the choice stays yours.
- **Safe by default.** The master switch is **off** on a fresh install, so
  installing cannot touch an appliance until you deliberately enable it.
- **Replay is opt-in, off by default.** After a restart, a rule that already
  passed does **not** re-fire — even one that was due minutes before the
  restart — unless you explicitly opt it in per rule (a `replay` block
  with `enabled: true`), with an optional staleness window past which it
  is skipped rather than replayed late. Nothing unexpected fires just
  because Home Assistant restarted.
- **Testable on demand, without waiting for Shabbat.** Every rule has a
  Run Now button (Simulate, or run for real); every day's whole resolved
  schedule can be run the same way from the header's ▶ icon — running a
  whole day for real asks for an explicit inline confirmation first, the
  same way a single rule's Run for real already does. Both reuse the exact
  code path a real fire uses — `resolve_rules()` then `async_apply_rule()`
  — so what you see is what would really happen, not a separate
  approximation of it. A simulated run is never recorded or logged, and
  never moves `sensor.shabbat_scheduler_last_run` either — it is a
  live-only answer to "would this actually work?", visible only in the
  dialog that asked the question.

## Entities

| Entity | Purpose |
|---|---|
| `switch.shabbat_scheduler` | master on/off; off cancels every pending timer |
| one switch per rule | named after the rule, so its entity_id follows the rule's name rather than a fixed pattern — find it under Settings → Devices & Services → entities |
| `sensor.shabbat_scheduler_next_block` | day count, with the resolved dates |
| `sensor.shabbat_scheduler_next_action` | when the next rule fires |
| `sensor.shabbat_scheduler_last_run` | when a rule last ran, and what it did |

## The card

Installing the integration also installs a Lovelace card. It is registered
automatically — there is nothing to add to your resources.

```yaml
type: custom:shabbat-scheduler-card
title: שעון שבת
```

It shows the coming block as a timeline: one group per day with its date,
the candle-lighting and havdalah markers, and each rule's time, action,
target and data. Every rule has its own quick on/off toggle right on the
row — no need to open it just to disable it for a week — and a disabled
rule dims so the schedule still reads correctly at a glance. Conflicts
appear on the rows they affect; a conflict whose rules are not currently on
screen appears in the banner instead, so it cannot go unseen. Conflicts are
only ever warned about, never auto-resolved — the same "no precedence"
commitment above applies here too. The header carries the master switch,
the shared-defaults gear, and a ▶ icon that opens a dialog for testing a
whole day's schedule at once. All three are admin-only: the master switch
is shown but disabled for a non-admin user, while the gear and the ▶ icon
are not rendered for one at all — a non-admin can still read the whole
schedule either way.

The card shows only the rules matching the coming block's length, because
rules are authored per profile — a 3-day chag's rules are not shown on a
plain Shabbat.

Tap any rule to edit it, or use the **+ add** button under a day to create
one there — the day and block length are taken from where you tapped. The
dialog has a full editor for every field: **action** (a service picker),
**target** (Home Assistant's own target selector — entity, device, area or
label), **data** (the service's own payload form), **condition** (a
guard the rule must pass to fire), and **replay** (whether it re-fires
after a restart), alongside time, name, icon, color and the enabled flag —
nothing is shown read-only. Both are detailed in full under "Rule format"
below. YAML export/import (see Services, below) is still there too, for
bulk edits across the whole rule set at once; either path writes the same
rule shape, so use whichever is faster for what you're doing.

The **1d / 2d / 3d** chips switch which block length you are looking at, so a
3-day Chag can be set up long before one arrives. Any length other than the
coming one is shown as a preview: no dates, no candle-lighting or havdalah
markers, and a banner saying so. Editing works exactly the same there.

The gear opens the **shared defaults** — the target and data every rule
inherits unless it sets its own — with the same target and data editors the
rule dialog uses.

### Cloning a day or a whole profile

Setting up a 3-day Chag from scratch when you already have a working
Shabbat profile is exactly the kind of thing that shouldn't require
retyping every rule. The **⋮** menu next to each day's heading clones that
one day onto another day (in the same or a different profile); the **⋮**
next to the 1d/2d/3d chips clones the whole profile — every day it has —
onto another profile, matching day names across profiles and leaving any
day the source doesn't have untouched. Either way you choose **extend**
(add the cloned rules alongside whatever's already on the target day) or
**overwrite** (replace the target day's rules with the clone). Cloned
rules get their own fresh identity — editing one never touches the rule it
was cloned from.

## Services

- `shabbat_scheduler.simulate` — resolve a block with no side effects. Answers
  "what happens this Shabbat?" and "what happens on a 3-day chag?".
- `shabbat_scheduler.export_yaml` — dump the whole rule set.
- `shabbat_scheduler.import_yaml` — replace the whole rule set.

## Rule format

A rule **is** a Home Assistant service call: which one (`action`), what it
acts on (`target`), and what it carries (`data`) — the same three things
you'd fill in from Developer Tools → Actions. If Home Assistant can do it,
a rule can schedule it; nothing about the rule format is specific to
climate, lighting, or any other domain.

```yaml
profiles:
  1_day:
    erev:
      - id: a1
        at: "17:30:00"
        action: notify.mobile_app_phone
        data:
          message: Candle lighting in 30 minutes
      - id: a2
        at: "23:00:00"
        action: scene.turn_on
        target:
          entity_id: scene.shabbat_off
    day_1:
      - id: b1
        at: "11:00:00"
        name: Shabbat morning
        action: scene.turn_on
        target:
          area_id: living_room
```

- **`action`** is `domain.service` — any registered Home Assistant service,
  not a fixed on/off/custom vocabulary. `notify.mobile_app_phone`,
  `scene.turn_on`, `light.turn_on`, `script.boiler` are all equally rules;
  there is no allow-list.
- **`target`** is Home Assistant's own target selector: `entity_id`,
  `device_id`, `area_id`, or `label_id`, singly or as lists. Areas and
  labels are new in this format and are the ones worth using — target a
  label like `label_id: winter_lights` once, and every entity you tag with
  it later is covered without touching the rule again; target an area and
  a device added to that area later is covered too. A rule with no
  meaningful target (a `notify.*` call, for instance) simply omits it.
- **`data`** is the service's own payload, passed through untouched —
  whatever fields that `action` accepts, verbatim.
- **`condition`** (optional) is a list of Home Assistant's own condition
  configs — the same schema you'd write in an automation's `condition:`
  block (`state`, `numeric_state`, `sun`, `zone`, `and`/`or`/`not`, …). All
  conditions must pass at fire time or the rule is blocked, reported, and
  left alone:

  ```yaml
      - id: c1
        at: "18:00:00"
        action: light.turn_on
        target:
          area_id: living_room
        condition:
          - condition: sun
            after: sunset
  ```

- **`replay`** (optional, off by default) controls whether a rule is
  re-applied after a Home Assistant restart lands after the rule's moment
  but before the block ends. It is opt-in per rule because only the
  author knows what is safe to repeat — replaying "turn the lights off"
  is harmless, replaying "start the dishwasher" is not:

  ```yaml
        replay:
          enabled: true
          within: "02:00:00"
  ```

  `enabled` turns replay on at all. `within` bounds how late a replay may
  still happen — an 11:00 rule replayed at 23:00 does more harm than
  skipping it, so a replay older than `within` is reported as
  `skipped_stale` rather than fired. Omitting `within` means no bound,
  matching how every rule behaved before this option existed. A replay
  still passes through the rule's own `condition` before firing, exactly
  like a normal fire — so a rule can pass `enabled` and `within` and still
  not replay, blocked the same way it would be blocked at its original
  moment.

One authored action can still become more than one actual service call:
see [`docs/known-behaviours.md`](docs/known-behaviours.md) for the one
compatibility shim this integration keeps, and for how conflicts and replay
behave in more detail than fits here.

Rule ids are preserved across an export/import round trip, so re-importing
an edited file keeps each rule's entity, history and customisation.

## Known behaviours

Non-obvious behaviours and accepted trade-offs — the havdalah sensor rollover,
refresh serialisation, and what restart catch-up does across havdalah — are
documented in [docs/known-behaviours.md](docs/known-behaviours.md).
