# Known behaviours and residual risks

Findings from the reviews of the backend branch that are deliberate, accepted,
or known-and-deferred. Recorded here because the review scratch directory is
not committed and these are things a future maintainer will otherwise
rediscover the hard way.

## The one climate shim

A rule is a single `action` with a `target` and a `data` payload — no
domain-specific knowledge is supposed to live in this integration at all.
`climate.set_temperature` is the one exception, and it splits into up to
three ordered calls (`set_hvac_mode`, `set_temperature`, `set_fan_mode`)
for **three separate reasons**, not one. It matters that they stay
separate: someone later deciding whether this shim can be deleted needs
to know which parts are forced by Home Assistant and which are a
hardware quirk that might outlive any schema change.

Verified directly against the installed
`homeassistant/components/climate/__init__.py`:

```python
SET_TEMPERATURE_SCHEMA = vol.All(
    cv.has_at_least_one_key(ATTR_TEMPERATURE, ATTR_TARGET_TEMP_HIGH, ATTR_TARGET_TEMP_LOW),
    cv.make_entity_service_schema({
        vol.Exclusive(ATTR_TEMPERATURE, "temperature"): vol.Coerce(float),
        vol.Inclusive(ATTR_TARGET_TEMP_HIGH, "temperature"): vol.Coerce(float),
        vol.Inclusive(ATTR_TARGET_TEMP_LOW, "temperature"): vol.Coerce(float),
        vol.Optional(ATTR_HVAC_MODE): vol.Coerce(HVACMode),
    }),
)
```

1. **`fan_mode` is peeled off because the schema genuinely rejects it.**
   `fan_mode` names no key at all in `SET_TEMPERATURE_SCHEMA`, and
   `make_entity_service_schema` defaults to `PREVENT_EXTRA`, so a
   `climate.set_temperature` call carrying `fan_mode` is refused outright
   with "extra keys not allowed" — HA's own validator, not a hardware
   opinion.
2. **`hvac_mode` is peeled off for a hardware reason, not a schema
   one.** `vol.Optional(ATTR_HVAC_MODE)` is right there in the schema —
   `hvac_mode` is an explicitly *permitted* key alongside a temperature,
   and HA would accept the combined call. It is split anyway because
   several climate integrations — the `aux_cloud` units this was built
   for among them — intermittently fail to power on when mode and
   temperature arrive in the same call, schema or no schema. The
   ecosystem's most-used third-party scheduler hardcodes the identical
   split, which is the evidence this is a real, shared hardware quirk
   and not this project's special case.
3. **`set_temperature` is only emitted when something temperature-ish
   remains.** `cv.has_at_least_one_key(temperature, target_temp_high,
   target_temp_low)` means a call with only `hvac_mode` (or only
   `fan_mode`) would leave `set_temperature` an empty `{}`, which HA
   rejects the other way — "must contain at least one of…". So the shim
   drops that call entirely when no temperature-ish key survives the
   split, rather than emitting a call guaranteed to fail.

Because reason 1 is genuinely a schema constraint and reason 2 is not, a
future relaxation of `SET_TEMPERATURE_SCHEMA` (say, if HA ever allowed
`fan_mode` too) would remove the *schema* half of the justification but
leave the *hardware* half standing — the split would still be worth
keeping for `hvac_mode`, even though it would no longer be strictly
required by HA. `expand_action` (`device_ops.py`) is the one place this
integration still knows something about a domain; every other action
passes through untouched, in order `set_hvac_mode` → `set_temperature` →
`set_fan_mode` (v1's order — reversing it can leave a unit briefly at
the wrong setpoint).

This counts as a compatibility shim rather than domain knowledge
creeping back in because two of its three reasons are forced by Home
Assistant's own schema rather than a preference of this project's, and
the one genuinely domain-specific reason (`hvac_mode`+temperature
together) is corroborated by the wider ecosystem's most-used scheduler
making the identical choice for the identical hardware, not invented
here.

## Conflicts are coarser than they were

`block.find_conflicts` warns when two enabled rules resolve to overlapping
targets at the same profile/day/time — full stop. It no longer asks
whether the two rules actually disagree.

The old model could ask that question because a rule's effect was three
hardcoded fields (`on`/`off`/a climate triple), so "opposite" had a
concrete meaning: one rule wants the unit on, the other wants it off. A v2
rule's effect is `action` + arbitrary `data` — an opaque payload for
whatever service `action` names. Two rules pointing `light.turn_on` at the
same area with different `brightness` values are trivially "different",
but so are a `light.turn_on` and a `light.turn_off` on the same target,
and so, for that matter, are two identical `light.turn_on` calls that
would produce no observable disagreement at all. Without understanding
each service's payload — which would mean re-implementing a piece of
every domain's semantics inside this integration — "same" and "opposite"
are indistinguishable, so both must be reported alike: as a conflict.

This means some warnings are now for genuinely harmless overlaps (two
rules that happen to agree), where v1 would have stayed silent on them.
That is the accepted cost of the trade: a rule with no precedence over
another is never silently resolved either way, so an over-eager warning
is the safe direction to err in. See "Two rules on one device at one
instant can interleave" below for why detection, not resolution, is the
whole of what this buys.

## Replay is opt-in and bounded

v1's restart catch-up could ask a device "what state should you be in
right now?" and compare it against what it actually held, because a rule's
effect was a small, fixed, queryable shape (on/off, or a temperature/mode/
fan triple) — the same shape the device itself reports back. That
comparison is what made catch-up idempotent: re-applying an already-true
state was a no-op.

A v2 rule's effect is an opaque Home Assistant service call. There is no
general way to ask "did this notification already go out?" or "was this
scene already applied?" — most services have no queryable desired state
at all, and the ones that do (like `light.turn_on`) do not expose it in a
form this integration could compare against arbitrary `data`. So catch-up
can no longer compute "what should be true" and diff against "what is
true"; the old mechanism could not survive the move to a generic action.

What replaced it is opt-in, author-declared safety: `replay.enabled`
(default `false`) says the rule's effect is safe to repeat at all —
"turn the lights off" is, "start the dishwasher" is not — and
`replay.within` bounds how late a repeat may still happen. `within`
exists because being right about *what* to replay is not enough; being
right about *when* matters just as much. An 11:00 "good morning" scene
replayed at 23:00 because Home Assistant happened to restart late is
actively wrong — worse than not replaying it — even though the same
action at 11:05 would have been exactly correct. A replay older than
`within` is reported as `skipped_stale`, with how late and how wide the
window was, rather than either firing blindly or vanishing without a
trace. Omitting `within` means no bound at all, matching how every rule
behaved before this option existed.

`replay.enabled` and `replay.within` are not the only gate. `async_catch_up`
replays through the same `async_apply_rule` path a normal fire uses
(`engine.py`), which means the rule's own `condition` is evaluated again
and must pass — a replay is not a bypass of the rule's guard, it is the
rule firing late, subject to everything that would have blocked it on
time. So a rule can have `replay.enabled: true`, land well inside
`within`, and still not replay: it is blocked, reported the same way a
blocked on-time fire would be, and this is not visible as `skipped_stale`
at all — that outcome is reserved for staleness specifically. Worth
knowing before assuming a silent non-replay must be a `within` problem.

## Two rules on one device at one instant can interleave

v1 guaranteed that two rules touching one device at the same instant could
never have their service calls interleave — its own spec named the
failure this prevented: "the unit left off with a target temperature
applied — a state matching neither rule." It bought this with an
`asyncio.Lock` keyed on `entity_id`.

v2 no longer can. A target may be an area, a floor or a label rather than
a single device, and some calls (`notify.*`) carry no entity at all — there
is no single entity left to key a lock on. `ShabbatEngine._locks` is now
keyed on `rule.id` instead. What survives: one rule still cannot interleave
with a re-entrant application of itself (a timer racing a restart
catch-up). What is lost: two *different* rules whose resolved targets
overlap can now genuinely interleave their service calls, and the result
can be a device left in a state matching neither rule's `data`.

What protects the household now is detection, not prevention:
`block.find_conflicts` is what surfaces this to the user (see "Conflicts
are coarser than they were", above) — the engine no longer refuses to run
either rule on their behalf, it warns and lets both proceed. The full
account, including the characterisation tests that pin the bad ending
deterministically and how to get the guarantee back (a lock keyed on the
*resolved* target set, costed but not scheduled), is in the ledger entry
headed "A GUARANTEE v2 GAVE UP" in
`.superpowers/sdd/2026-08-24-shabbat-scheduler-v2-model/progress.md`.

## A rule that could not be migrated is kept, disabled, and reported

A v1 store can contain a rule shape the v1→v2 migration cannot translate
into a `target`/`data` pair — a hand-edited `.storage` file, or a v1 field
combination nobody anticipated. That rule is never dropped. It is kept in
the store with `enabled: false` and `action: shabbat_scheduler.unmigrated`
so it cannot fire in a shape nothing understands, `migration_error` names
why it could not convert, and `migration_source` stashes the entire
original v1 rule dict verbatim — including anything the migration *did*
manage to salvage into `target`/`data` along the way.

The user is told through a repair issue (Settings → Repairs), not a log
line during the one week nobody reads logs: `ISSUE_UNMIGRATED_RULES` names
every affected rule id so they do not have to hunt through the whole rule
set to find them. What to do with one: open it in the card, which renders
the migration error inline, then re-author it by hand as a v2
`action`/`target`/`data` rule and re-enable it — nothing does this
automatically, because a migration confident enough to invent a `target`
on your behalf is exactly the kind of silent guess this project exists to
avoid. Preserving `migration_source` whole in storage is what makes that
reconstruction possible instead of a rewrite from memory.

The YAML export is the other way to inspect one, and it is now safe. Both
`migration_error` and `migration_source` are written by `export_yaml` and
preserved by `import_yaml`, so a round trip shows you the original v1 rule
verbatim and leaves an untouched stub exactly as it was — still disabled,
still carrying its error, still named in the repair issue. To repair one
this way, replace the stub's `action`/`target`/`data` with the v2 rule you
want, delete its two `migration_*` keys and set `enabled: true`; the warning
clears itself once no rule carries a `migration_error` any more.

This was not always true, and the earlier behaviour was destructive: the
export omitted both fields, so the documented inspection route could not
work, and the import stripped them, so a round trip permanently deleted the
stashed v1 payload *and* cleared the flag the repair issue is derived from —
leaving a disabled stub pointing at a service that does not exist with
nothing anywhere saying why.

Note the asymmetry this creates, deliberately. A **websocket client** still
cannot set either field: `rule_schema._READ_ONLY_FIELDS` drops them from
every create and update, because a client payload is an *edit* that echoes
back fields it did not author, and a forged `migration_error` would put a
healthy rule in the repair issue and make the card claim a migration failed.
A **YAML document** is a serialised store rather than an edit, so it opts in
(`rule_from_api(..., keep_server_fields=True)`). Forging one there is
pointless rather than dangerous: the shape is still validated, and the only
thing it achieves is listing your own rule as unmigrated.

## The shared defaults are domain-blind, and v1's were not

`block.merge_defaults` folds `defaults["data"]` into **every** rule, whatever
domain it targets, and `defaults["target"]` into every rule that has none of
its own. There is no per-domain defaults concept and no filtering: a
`data` of `{hvac_mode, temperature}` reaches a `switch.turn_on` rule
untouched, and Home Assistant then refuses the call outright —
`make_entity_service_schema` defaults to `PREVENT_EXTRA`, so the error is
`extra keys not allowed @ data['hvac_mode']`, after three retries and a
notification. This is worth knowing before you author a `light.turn_on` rule
in a rule set whose defaults were written for an air conditioner.

v1 was different: it read its global `settings` for the **climate** domain
and nowhere else, so a mixed v1 rule set was safe by accident. The v1 → v2
migration therefore does **not** copy `defaults.settings` into
`defaults.data`. It inlines them onto each migrated climate rule's own `data`
instead, merged per key with the rule's own settings and in the same order
`merge_defaults` uses — so the effective payload of every rule is byte for
byte what v1 fired, and no non-climate rule inherits anything. Dropping them
instead would have been lossy in the other direction: a v1 climate rule with
no settings of its own *did* read the global ones, and would have become a
bare `climate.turn_on` — the unit coming on at whatever temperature it was
last left at, reported nowhere.

The cost is stated where the code is (`migration.migrate_v1_defaults`): the
values are **materialised per rule**, so editing the shared defaults
afterwards no longer changes them. That is unavoidable — "climate only" is a
v1 concept v2 cannot express — and copying it is honest where reinterpreting
it is not.

`defaults.devices` is resolved per rule for the same reason, and it matters
even more. v1's `merge_defaults` was, verbatim:

```python
devices = rule.devices or tuple(defaults.get("devices", ()))
```

So **a v1 rule with no `devices` of its own inherited the global ones** —
which is what `defaults.devices` was for, and the shape the v1 README
documented as the common case. The migration therefore resolves that
fallback per rule, `or` not merge (a rule's own devices win outright), and
writes the result into the rule's **own** `target`. It has to be written
rather than left to v2's `defaults.target` inheritance, because the migrated
*action* (`switch.turn_on` vs `climate.set_temperature`) is derived from
those same devices and is frozen into the rule: a target left floating could
later be repointed at a domain the frozen action does not belong to. A
migrated rule describes itself. `defaults.devices` still becomes a shared
`defaults.target` as well, for rules authored later.

If the shared devices span **several domains**, an inheriting rule cannot
become one action, and it is kept-disabled-reported like any other — but the
reason names the *defaults*, because in that case every inheriting rule
fails at once and the user needs pointing at the one thing that is wrong,
not at ten rules that are not.

## `migrate_v1` never raises, by construction

The whole migration is total. Anything it raised escaped
`_MigratingStore._async_migrate_func` → `Store.async_load` →
`RuleStore.async_load` → `async_setup_entry`, which failed with
`ConfigEntryState.SETUP_ERROR` — and because the store was then still at
version 1, **every subsequent restart failed identically**. No entities, no
engine, nothing scheduled, and the only trace a setup traceback nobody reads
during the one week they cannot. Two live instances of that were closed
(a `settings` or a `defaults` that was a truthy non-mapping, e.g. `'hot'`),
along with the same shape in `devices` and `variables`.

Two rules follow from it, and both are load-bearing:

- Every coercion is guarded, and a field the migration cannot parse routes
  the rule through keep-disable-report — the same path as any other
  unconvertible rule, with the whole raw v1 rule stashed in
  `migration_source`, so being told costs one field to fix.
- The per-rule conversion is additionally wrapped in a catch-all, so the
  *ninth* instance of that failure class becomes one kept, disabled and
  reported rule rather than a permanently unbootable install. The trade: a
  genuine bug in `migrate_v1_rule` shows up as a disabled rule naming the
  exception rather than as a crash. For the one function whose crash costs
  the user every rule they have, that is the right way round.

A malformed **`defaults`** is the one case with nothing to disable — it is
not a rule — so it drops to empty and logs a warning. Inventing a phantom
rule to carry the report would put something in the store the user never
wrote, which is a worse violation than a log line.

That is not free, and the section above says why: a rule with no `devices` of
its own inherits the shared ones, so a `defaults` that cannot be read costs
every such rule its target. Those rules are **not** silent about it — each
one is kept, disabled, and named in the repair issue, with a reason pointing
at the defaults. The log line is the only trace of the *defaults* being
unreadable; the consequence for each affected rule is reported through the
channel the user actually looks at.

## The zmanim sensors roll forward at havdalah

`sensor.jewish_calendar_upcoming_candle_lighting` and
`sensor.jewish_calendar_upcoming_havdalah` advance to the **next** occurrence
the moment `now >= havdalah`. Verified live on 2026-08-17: the preceding
Shabbat was 14–15 Aug and the sensors already read 21–22 Aug.

This matters because rules are deliberately **not** clamped to the zmanim — a
last-day `23:00 turn off` is a supported configuration, and it sits *after*
havdalah. Two defects came out of this and are now closed:

- The engine originally replaced its cached block on every sensor change, so
  at havdalah every still-pending timer of the current block was cancelled and
  the 23:00 rule never fired. The engine now **holds** the current block while
  any of its own resolved rules are still pending.
- The hold then needed releasing: nothing else would have triggered it,
  because mid-week the sensors republish identical values, which Home
  Assistant delivers as `EVENT_STATE_REPORTED`, not `state_changed`. Without a
  release the next block was never armed and **alternate Shabbatot were
  silently skipped**. A timer at `tail + 1s` now releases the hold.

The active block's `(candle_lighting, havdalah)` pair is persisted, so a
restart between havdalah and the tail restores the held block rather than
adopting next week's.

## `async_refresh` is serialised

Persisting the block introduced an `await` mid-refresh, which had previously
been atomic. Two overlapping refreshes then each rebuilt the timer list and
each appended to it, **firing every rule twice**. A refresh lock closes this.

The reachable path is the boot race: a late `jewish_calendar` publish racing
the start-up refresh. Reproduced with the lock removed (`TIMERS: 2, FIRED: 2`)
and with it restored (`TIMERS: 1, FIRED: 1`).

Note for anyone writing tests here: `pytest_homeassistant_custom_component`'s
`mock_storage` replaces `_async_write_data` with a plain dict assignment that
never awaits, so a concurrency test against mocked storage **cannot** observe
this interleaving and will pass either way. The covering test injects the
executor hop that a real `Store.async_save` performs.

## Accepted behaviour: catch-up reaches across havdalah

If the user manually switches a device off after havdalah and Home Assistant
restarts before the block's tail, restart catch-up re-applies every
already-passed rule that opted in to replay — so a device switched off by hand
at 20:30 comes back on after a 21:00 restart, until the 23:00 rule turns it
off.

This is the same trade-off already accepted for any mid-block restart. The
alternative — not restoring the block — loses the 23:00 rule entirely, which
is worse.

**This paragraph used to claim catch-up "stays at one rule per device and is
idempotent (no service call if the device is already in the desired state)".
Both halves are v1 claims that v2 falsified, and it matters more than ordinary
doc rot: "fire once, never re-assert" is a binding constraint, and a
maintainer reasoning from the old wording would conclude a repeat is
harmless. It is not.**

- **Not idempotent.** Application goes through `async_call_from_config`,
  which has no "already in that state" check; v1's device comparison, which
  did, could not survive the move to an opaque service call (see "Replay is
  opt-in and bounded" above). A repeat re-issues the call.
- **Not one rule per device.** Catch-up replays *every* opted-in rule whose
  time has already passed, in time order — `engine.async_catch_up` walks the
  whole resolved list. `tests/test_replay.py` pins that ordering, and
  `test_catch_up_declines_to_act_on_a_conflicting_pair` was re-aimed at
  exactly this behaviour.
- What bounds repeats now is `engine._caught_up_for`, which compares the
  current `Block` by value and so runs catch-up at most once per block, and at
  most once per Home Assistant session. That is a per-*block* bound, not a
  per-device one.

The three author-declared guards are what make this safe instead:
`replay.enabled` (default `false`), `replay.within`, and the rule's own
condition, all evaluated through the normal apply path. A replay declined as
too stale reports `skipped_stale` and now fires its own
`shabbat_scheduler_rule_completed` event, so the skip is a logbook row rather
than an entry in an aggregate `last_run` that the next rule overwrites.

## Residual risks (accepted, not fixed)

- **Delayed missing-zmanim notification.** A restart landing inside the hold
  window *while the zmanim entities are simultaneously renamed or removed*
  restores the cached block and stays quiet, so the "cannot read zmanim"
  notification is delayed until the next restart. Requires two faults at once
  plus a restart in a ~3 hour window. The pending rule still fires correctly
  in this case.
- **Unload racing an in-flight refresh.** Because `async_refresh` now awaits
  mid-way, a refresh suspended in the storage write could in principle resume
  after `async_shutdown` and arm timers on a dead engine. Not reproducible —
  `async_unload_platforms` awaits first and lets the refresh drain. Taking the
  refresh lock in `async_shutdown` would close it definitively.
Two entries that used to sit in this list have been **done** since, and are
recorded here so nobody plans against the stale version:

- ~~**Static switch entities.**~~ Rule switches are now added and removed
  dynamically: `switch.py`'s `_sync`, subscribed to `SIGNAL_RULES_CHANGED`,
  creates a switch for a new rule and removes the entity (and its registry
  entry) for a deleted one. The websocket CRUD the card uses goes through
  that same signal, so the "the planned Lovelace card will need this"
  dependency is satisfied, not pending.
- ~~**`RuleStore.rules` hands out shared mutable `Rule` objects.**~~ `Rule`
  is `@dataclass(frozen=True)` (`models.py`), as are `Replay`, `Block`,
  `ResolvedRule` and `Conflict`. Mutation is a `FrozenInstanceError` rather
  than a convention, and `Block` being frozen is also what makes
  `engine._caught_up_for`'s value comparison sound.

## The card's static path outlives a reload

Home Assistant offers no way to unregister a static path, so
`/shabbat_scheduler/` stays served after the config entry is unloaded. The
Lovelace *resource* is removed, so nothing references it. Re-registering the
same static path does not actually raise on current Home Assistant (the http
component patches `app._router.freeze` to a no-op at startup for exactly
this kind of late/duplicate registration) — but that is not a contract this
integration wants to depend on across versions, so it still guards against
repeating the registration. The guard exists to skip pointless repeat work
on every reload, not to dodge an exception. A served file nobody loads costs
nothing either way.

## The card is silent in YAML resource mode

Lovelace in YAML resource mode owns its resource list and cannot be written
to programmatically. In that mode the integration logs the line to add and
carries on rather than failing setup — the scheduler must keep running even
when its card cannot register itself.

## A broken card can never take the scheduler down

Frontend registration — serving the bundle, and adding the Lovelace
resource — is wrapped in its own broad exception handler, separate from
everything else `async_setup_entry` does. Any failure there, expected
(no Lovelace, YAML resource mode) or not, is logged and swallowed; the
config entry still loads and the engine still schedules. The card is a
convenience for reading the schedule. The schedule itself drives real air
conditioners on days nobody can operate them by hand, and nothing about
rendering a Lovelace card is allowed to be the reason that stops.

## The card cannot tell a dropped connection from a live one

The spec's error table says a lost connection shows "the last known state,
visibly marked stale, **with controls disabled**". Neither half is
implemented, and they share one root cause: **nothing detects a connection
lost after a successful subscribe.**

What is implemented is the *first* subscribe failing — that sets the stale
notice, and the next `hass` assignment retries. Once a subscription is
established, the card has no liveness signal at all: `subscribeMessage`
pushes when there is something to push, and silence is indistinguishable
from a healthy week with no changes. So the card cannot mark itself stale,
and since it does not know it is stale it has nothing to disable controls
on. Disabling them on a *timer* would be worse — a quiet Tuesday is not a
fault, and greying out the master switch because nothing has happened for
an hour is a lie in the other direction.

What limits the exposure:

- `home-assistant-js-websocket` reconnects and re-subscribes on its own, and
  `ws_subscribe` now sends a full snapshot immediately on subscribe, so a
  reconnect self-heals the display. The window is the disconnect itself.
- A control pressed while the socket is down rejects, and that now renders
  a distinct "that did not go through" notice (it used to claim the
  connection was lost, which was the wrong diagnosis in the far more common
  case where the server was reachable and simply refused the call).
- Nothing the card shows can make an appliance do the wrong thing. The
  engine runs entirely server-side from its own block.

Closing this properly means a heartbeat or a `connection.connected` /
`ready`/`disconnected` listener on the HA websocket object, plus a disabled
state threaded through `<shabbat-block-header>`. Deferred to 2b-ii.

## The card does not re-subscribe when `hass.connection` is replaced

The spec says the card "re-subscribes if the connection object is replaced".
`set hass` compares only the language and the admin flag; it never compares
`hass.connection` identity, so a genuinely new connection object leaves the
old subscription attached to a dead socket and the card frozen on its last
payload, with nothing marking it stale.

Reachability is low: Home Assistant's frontend creates one connection object
per page load and reconnects *inside* it, so the object identity is stable
for the life of the page. Replacement would mean a frontend change or an
embedder that rebuilds `hass`. Fixing it is a small change (`if
(hass.connection !== previous.connection) resubscribe`), but it is untested
against any real path that triggers it, and an unexercised teardown/re-setup
path in the one component a wall tablet leaves running for weeks is its own
risk. Recorded rather than guessed at; it belongs with the liveness work
above, which needs the same teardown path.

## `block: null` hides the rule set — a deliberate deviation from the spec

The spec's error table promises "the rule set, plus a clear note that no
upcoming Shabbat could be derived". The card renders the note and **not** the
rule set (`card.ts`'s `_groups` returns `[]` when `block` is null).

This is deliberate. Rules are authored per profile — 1-day, 2-day, 3-day —
and per day within the block. Without a block there is no length to select a
profile by and no dates to hang days on, so "the rule set" could only mean
every profile's rules at once, undifferentiated. That is precisely the
confidently-wrong display this card exists to eliminate: a screen full of
rules with no honest way to say which of them apply.

It would also be wrong on the facts. With no block the engine returns from
`_async_refresh` before building a single timer — nothing is scheduled at
all. A timeline of rules under those conditions implies a schedule that does
not exist. The note says the true thing: the Jewish Calendar sensors are not
readable, so there is nothing upcoming.

The rules remain fully visible either way — every rule has its own switch
entity, and the `simulate` service and `preview` command both take an
explicit `block_length`.

## Deleting a rule is immediate, with no confirmation

Delete lives inside the edit dialog and acts at once. There is no confirmation
step and no undo: the rule and its switch entity are gone.

This was chosen deliberately rather than overlooked. Reaching delete already
takes two intentional actions — open the row, then tap delete — and a
confirmation modal on a wall tablet becomes muscle memory within a week, which
buys nothing. Recovering a deleted rule means adding it again, or re-importing
a YAML export.

## Deployment note

Nothing here has been installed on the live instance. The integration ships
with its master switch defaulting **off**, so installing it cannot drive any
appliance until deliberately enabled. The rollout sequence is in the design
spec; the existing plain automations remain in production until it is proven.
