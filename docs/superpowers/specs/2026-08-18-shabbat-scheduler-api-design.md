# Shabbat Scheduler — API, Lifecycle, Logbook and Packaging (Plan 2a)

**Status:** approved, not yet implemented
**Date:** 2026-08-18
**Follows:** `2026-08-16-shabbat-scheduler-design.md` (backend, merged)
**Precedes:** Plan 2b — the custom Lovelace card

## Problem

The backend is complete and merged: rules resolve against 1-, 2- and 3-day
blocks, fire once, apply idempotently, catch up after a restart, and report
conflicts without inventing precedence. 136 tests pass.

But it is headless. Rules can only be authored by YAML import, and the only
UI is native `entities` cards over one switch per rule. The card that this
project exists to produce cannot be built until there is an API to build it
against — and three known gaps would bite it immediately.

## Goals

- A websocket API the card can read, mutate and subscribe to.
- Entities that appear and disappear as rules are created and deleted, without
  reloading the config entry.
- `Rule` immutable, so websocket CRUD cannot corrupt store state.
- Rule activity visible in Home Assistant's native Logbook ("Activity"),
  including attribution on the affected device's own row.
- Installable and updatable through HACS, with translated UI strings.

## Non-goals

- The Lovelace card itself — that is Plan 2b.
- Enforcement (continuous state convergence). Still deferred; `desired_state_at`
  remains the seam.
- A rule-ordering concept. See "Cut from scope" below.

---

## Websocket API

```
shabbat_scheduler/rules/list      → {defaults, rules[], warnings[]}
shabbat_scheduler/rules/create    → {rule, warnings[]}
shabbat_scheduler/rules/update    → {rule, warnings[]}
shabbat_scheduler/rules/delete    → {ok: true}
shabbat_scheduler/defaults/update → {defaults, warnings[]}
shabbat_scheduler/preview         → {profile, rules[], conflicts[], warnings[]}
shabbat_scheduler/subscribe       → push on every change
```

### Mutations warn, they do not reject

Every mutation returns `warnings[]` alongside its result. Conflicting rules are
reported, never refused — the system deliberately has no precedence rule, so a
conflict has no defined winner and the user is entitled to save anyway. The card
decides how loudly to render them.

Malformed input *is* rejected, with `ServiceValidationError`, matching the YAML
import path. Validation covers: a `day` that is not `erev` or `1..3`, a
`profile` outside `1..3`, an unparseable `time`, an unknown `action`, and a
`custom` action with no `script`.

### Ids are generated server-side

`rules/create` ignores any client-supplied `id` and mints its own, returning the
created rule so the card learns it. Entity identity derives from `rule.id`, so
allowing a client to choose one invites collisions with an existing rule's
entity. `import_yaml` remains the one path that honours an incoming id, because
preserving ids across a round trip is exactly its job.

### `preview` mirrors the existing `simulate` service

Same resolution, same conflict list, no side effects. It exists as a websocket
command so the card can show "what happens this Shabbat" without a service call
round trip.

### `subscribe` exists so the card never polls

Without it the card would have to infer changes by watching entity states. A
YAML import, a second browser tab, or an automation toggling a rule switch all
change the rule set behind the card's back. Subscribers receive the same shape
as `rules/list` on any mutation, and on master-switch and dry-run changes.

### Cut from scope: `reorder`

The earlier backend plan listed a `rules/reorder` command. It is cut. Rules are
displayed sorted by time and the system has no precedence, so a stored manual
order would be a field nothing reads. If per-rule precedence is ever introduced,
ordering comes back with it as one design.

---

## Entity lifecycle

Today rule switches are built once, during platform setup. Creating a rule
therefore produces no switch, and deleting one leaves an orphan until a reload.
The YAML import path currently papers over this by reloading the whole config
entry.

Replace that with the standard Home Assistant pattern:

- The store fires a dispatcher signal after any change to the rule set.
- `switch.py` listens; on a rule it has no entity for, it calls
  `async_add_entities`; for an entity whose rule is gone, it removes the
  registry entry.
- The reload-after-YAML-import is removed, since import becomes just another
  rule-set change.

This keeps entity identity stable: `unique_id` remains
`f"{entry.entry_id}_rule_{rule.id}"`, and YAML round trips preserve `rule.id`,
so an import that keeps a rule keeps its entity, its history and any
customisation.

---

## `Rule` becomes immutable

`RuleStore.rules` currently returns a fresh list containing the *same* mutable
`Rule` objects. No current consumer mutates them, but websocket CRUD is exactly
the consumer that would.

`Rule` becomes a frozen dataclass. All mutation already goes through
`dataclasses.replace` (in `store.async_update` and `block.merge_defaults`), so
this is a small change with a large guarantee. A test asserts that attempting to
mutate a returned rule raises.

`settings` and `variables` remain plain dicts inside the frozen rule; every code
path that alters them already builds a new dict rather than mutating in place,
and `merge_defaults` is the only merger.

---

## Logbook platform

### What appears

For a rule firing at 11:00 across two air conditioners, one needing a change and
one already correct:

```
11:00  שעון שבת
       כלל "בוקר שבת" — מזגן סלון, מזגן חדר בנות

11:00  מזגן סלון → cool
       triggered by שעון שבת: בוקר שבת
```

One summary row naming the rule and its devices; attribution on each device that
actually changed; exact `changed`/`ok`/`failed` counts in
`sensor.…_last_run`; and a second row only when something failed.

### The ordering constraint

Home Assistant attributes a state change to the event that caused it by matching
context, and `logbook/processor.py`'s `augment()` skips attribution entirely for
event types not registered through `async_describe_events`.

So the describing event must both be registered *and* carry the same context as
the service calls. Because service calls happen during rule application, the
event must be fired **before** them — the same pattern automations use with
`automation_triggered`.

The consequence, accepted deliberately: **the summary row cannot contain
changed/ok counts**, because they are not known when it is fired. Firing the
event afterwards would make attribution fragile, which is the worse trade — the
counts are available in the sensor and implied by which device rows appear.

### Events must be self-describing

`EVENT_RULE_APPLIED` currently carries `{"rule_id", "results"}`. The logbook
renders *historical* events, potentially long after a rule was renamed or
deleted, so a describe function cannot look the rule up. The event payload gains
the rule's `name`, `action`, and `devices`, so a row rendered months later still
reads correctly.

### Context

`async_apply_rule` creates one `Context` per application, fires the event with
it, and passes it to every service call for that rule. This supersedes the
current per-device fresh contexts. `is_our_context` and its bounded per-device
history are retained — they exist for future enforcement and remain valid.

---

## Packaging

- `strings.json` — English, the base, as Home Assistant and HACS expect.
- `translations/en.json`, `translations/he.json`.
- `hacs.json` declaring the integration and its minimum HA version.
- `README.md` covering install, rule authoring, the YAML format, and the
  services.
- The `manifest.json` `version` field becomes the release discipline for HACS.

This also fixes a live bug: the config flow's `single_instance_allowed` abort
currently renders as a raw key, because no `strings.json` exists.

Rule names stay in whatever language the user writes them — they are data, not
translations.

---

## Testing

1. **Websocket handlers** — through a real connected test client against real
   `hass.data`, asserting both the returned payload and the resulting store
   state. Not mocks.
2. **Lifecycle** — create a rule and assert its entity appears in the registry;
   delete it and assert the entity is gone; import YAML and assert entities
   match the new set, with surviving rules keeping their entity.
3. **Logbook** — assert the described event renders with the expected name and
   message, and that a device's state row carries our context so attribution
   resolves.
4. **Immutability** — assert mutating a rule returned by the store raises.
5. All 136 existing tests keep passing.

## Rollout

Unchanged from the backend spec: the master switch still defaults off, and the
seven production automations remain in place until the whole thing is proven
across a real Shabbat.

## Open questions

- Whether `defaults/update` needs its own conflict re-validation, or whether
  returning warnings from the next `rules/list` is sufficient.
- Whether the card will want a `rules/duplicate` command for the "clone day"
  affordance, or whether it composes that from `rules/create` client-side.
  Deferred to Plan 2b, where the need will be concrete.
