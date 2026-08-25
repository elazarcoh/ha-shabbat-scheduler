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

What this costs a v1 user specifically — a migrated on/off rule loses the
unconditional catch-up it used to have — is its own accepted decision, below:
"v2 does not self-correct after a mid-block restart".

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

If the shared devices span **several domains**, an inheriting rule is split
into one rule per domain, exactly as a rule carrying its own mixed devices is
— see the next section.

## The migration reproduces what v1 DID, not what a v1 rule said

A v1 rule's stored fields are not the same thing as its behaviour. v1 read
some of them, ignored others, and could not act on some at all — so
converting a rule field-for-field produces something that looks right and
does not behave the way the user's schedule behaved. Four cases, each cited
to v1's source at `5192d4c` so the claim can be checked rather than trusted.

**v1 drove five domains, and no others.** `climate`, plus
`device_ops._SIMPLE_DOMAINS = ("switch", "light", "input_boolean", "fan")`
(`5192d4c:device_ops.py:14`). Anything else fell through `plan_calls` and
came back as `Skip("unsupported domain 'x'")` — v1 made **no service call**
for it, ever. So a v1 rule on `lock.front` never did anything, and a blind
`f"{domain}.turn_on"` would either name a service that does not exist
(`lock.turn_on`) or, worse, one that does (`scene.turn_on`, `script.turn_on`)
and quietly start doing something the user never had. Such a rule is kept,
disabled and reported instead, with the domain named. The allow-list lives in
`migration.py` rather than `device_ops.py` because it is a fact about v1, not
about Home Assistant: a rule you author in v2 can name any service you like.

**v1 read exactly three keys out of `settings`:** `hvac_mode`, `temperature`
and `fan_mode`, one branch each in `_plan_climate`
(`5192d4c:device_ops.py:104-183`). A `swing_mode`, a `humidity`, a
`target_temp_high` or a typo was **ignored, and the rule worked**. Carrying
those keys into `climate.set_temperature` breaks a rule that used to work,
because the schema is `PREVENT_EXTRA` and refuses the whole call — so the
temperature stops being set too. Only the three keys are carried; the rest
are logged and dropped, which is precisely what v1 did with them.

**A v1 climate `on` rule with no `hvac_mode`, `temperature` or `fan_mode`
did nothing at all.** `_plan_climate` appended no calls, and the engine
reported `outcome: "ok"` with the state unchanged
(`5192d4c:engine.py:493-500`). Converting it to `climate.turn_on` would make
an air conditioner start up, unattended, on a Shabbat, at whatever
temperature it was last left at. That is inventing behaviour on the user's
behalf, so the rule is kept, disabled and reported instead, and the message
says what to add to make it act. A climate `off` rule with no settings is
unaffected: v1 genuinely called `climate.turn_off` for it.

**A v1 rule spanning two domains worked, so it becomes two v2 rules.** v1
looped `for entity_id in rule.devices` and re-derived the domain per entity
(`5192d4c:engine.py:104`), so one rule could legitimately drive
`climate.salon` and `switch.boiler` together — and the v1 card let you select
several devices for one rule. v2 is one rule, one action, so the only way to
keep that schedule working is one v2 rule per domain. **This is the one place
the migration changes the number of rules you have**, and it is worth knowing
before you open the card after an upgrade:

- Ids are derived and deterministic: `e` becomes `e-climate` and `e-switch`,
  suffixed further only to dodge a collision with an id the store already
  uses. A re-migration of the same store produces the same ids.
- Both parts are renamed, rather than one keeping `e`, so that nothing
  implies one is "the real rule". `e` and `e-switch` would leave a reader
  unable to tell whether `e` had always been climate-only.
- **You are told.** A repair issue (`ISSUE_SPLIT_RULES`, Settings → Repairs)
  names each original rule and what it became: `e → e-climate, e-switch`. It
  is the only report here that is not about something being *wrong* — the
  rules converted correctly and are all enabled — but a rule count changing
  under someone in silence is exactly the shape of thing this project exists
  to prevent, so it gets the same channel as everything else. There is
  nothing to fix, so dismiss it once you have looked at the card; it is
  persistent, so it survives a restart until you do.
- Both parts stash the whole original rule in `migration_source`, so the
  YAML export shows exactly what the single v1 rule was, and the repair issue
  above is derived from it. That field alone renders nothing in the card —
  only `migration_error` does — so it is a paper trail, not a warning. A YAML
  round trip that drops those keys also clears the repair issue, which is the
  other way to acknowledge it.
- Each part gets its own rule switch. Both parts share the original's name,
  so Home Assistant dedupes the second entity id.
- The two parts share a profile, day and time but have disjoint targets, so
  they are not reported as conflicting with each other.
- A part on a domain v1 could not drive fails on its own, leaving the
  working part working — which is exactly what v1 did with that rule.

A `custom` (script) rule is never split: `_apply_custom`
(`5192d4c:engine.py:451-470`) used `script` and `variables` and never looked
at `devices`, so a custom rule's devices did nothing in v1 either.

## Accepted decision: v2 does not self-correct after a mid-block restart

v1 did. v2 does not, unless a rule opts into replay. **This is a deliberate
decision by the project owner, not a limitation nobody noticed**, and it is
the one behaviour on the upgrade path a v1 user will actively miss. "Replay
is opt-in and bounded", above, describes the v2 mechanism and why v1's could
not survive the move to a generic action; this is about what the upgrade
itself does to an existing v1 rule.

What v1 did (`5192d4c:engine.py:396-424`): on every restart, catch-up took
every device any rule touched, asked `desired_state_at` what state the most
recent already-passed rule wanted it in, and applied it — with no opt-in of
any kind. `replay_on_restart` gated **only** `custom` (script) rules
(`5192d4c:engine.py:430-437`). So a Home Assistant restart or a power cut at
9pm on Friday re-asserted the air conditioning, and nobody had to know
anything had happened.

What v2 does: catch-up replays only rules whose author set `replay.enabled`,
bounded by `replay.within`. The migration maps `replay_on_restart` →
`replay.enabled` faithfully as a **field**, but that field meant something
narrower in v1 — so a v1 on/off rule left at the default, which is almost all
of them, **is not replayed after a restart any more**. If the last rule of the
day has already passed, the appliance stays as the restart left it for the
rest of Shabbat.

Why it is not simply switched on for every migrated rule, which was
considered and rejected: v1 could afford unconditional catch-up because it
computed a desired state and **compared before acting** — `plan_calls`
returned no calls at all for a device already in the wanted state, so
replaying was free. A v2 rule is an opaque service call with no queryable
desired state, so replay **re-fires** rather than reconciles. Re-firing every
passed rule of the block on every restart, through the unbounded window a
migrated rule would inherit, is worse than not acting. Nothing unexpected
ever firing is the strictest reading of fire-once, and it is the reading this
project takes.

**If you want the old behaviour**, turn it on per rule, on the rules where
re-firing is genuinely safe — a `climate.set_temperature` naming an absolute
temperature usually is; a `script.turn_on` that adds 30 minutes to a timer is
not. Set `replay.enabled` and give it a `within` window, so a restart hours
later does not re-fire something long stale:

```yaml
      - id: b1
        at: "11:00:00"
        action: climate.set_temperature
        target: { entity_id: climate.salon }
        data: { temperature: 24 }
        replay: { enabled: true, within: "02:00:00" }
```

A rule replayed outside its window is reported as `skipped_stale` rather than
dropped in silence.

## v1 resolved fan-mode synonyms against the device; v2 does not

Not a migration defect — a capability v2 dropped. Recorded here because
nothing else in the repo says so, the v1 README's own example config depends
on it, and **this household's own units disagree about the name**: one accepts
`quiet`, the other only `silent`.

v1 carried a `FAN_SYNONYMS` table (`5192d4c:const.py:17-21`, mapping
`quiet`/`silent`/`low` onto each other) and `resolve_fan_mode`
(`5192d4c:device_ops.py:44-51`) picked the first synonym the device actually
listed in its `fan_modes` attribute. If none was supported it emitted a
`Skip`: that one sub-call was dropped and reported, and the rest of the rule
still ran. v2 has neither — `const.py` has no synonym table — so the migrated
rule sends the authored `fan_mode` string verbatim.

So a v1 rule saying `fan_mode: quiet`, aimed at the unit that only takes
`silent`, **worked in v1** — v1 looked at that unit's `fan_modes`, saw
`silent` in the synonym list, and sent it. In v2 the same rule sends `quiet`
verbatim and the unit refuses it.

**The symptom, so it is recognisable when it happens:** the whole
`climate.set_fan_mode` call fails — Home Assistant rejects the mode against
the entity's `fan_modes`, the engine's three retries all fail the same way,
and a persistent notification names the rule. The `set_hvac_mode` and
`set_temperature` calls of the same rule, which the shim splits out
separately, still succeed: so the unit comes on at the right temperature and
**stays on the fan speed it was already using**, which is the part someone is
most likely to notice and least likely to connect to an upgrade. The v1
README's documented example config uses exactly `fan_mode: quiet`, so this is
not a corner case for this install.

It cannot be fixed in the migration: choosing a synonym needs the device's
`fan_modes` attribute, which needs a running instance, and `migration.py`
imports no Home Assistant. The honest fix is to restore the resolution at
fire time in the engine, which already reads each entity's state and
attributes, together with v1's `Skip` behaviour so an unsupported mode drops
one sub-call and reports it rather than failing the whole rule. That is a
change to the fire path, not to the upgrade path, so it is recorded rather
than smuggled into a migration fix.

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

## A mode-only null payload still emits a call Home Assistant refuses

`expand_action("climate.set_temperature", {"hvac_mode": None})` — a null mode
and nothing else — drops the null (correctly, per the reasoning in
`device_ops.py`) and is then left with an empty payload, so it emits
`climate.set_temperature {}`. Home Assistant refuses that: the schema requires
at least one of `temperature`, `target_temp_high`, `target_temp_low`. The rule
retries three times and raises a persistent notification.

That contradicts the letter of `test_hvac_mode_only_does_not_emit_an_empty_
set_temperature_call`, which holds for a *non-null* mode-only payload. The
inconsistency is real and is recorded here rather than fixed, for two reasons.

The migration cannot produce this shape — v1's own three settings keys are
value-gated in `migration.py`, so a null never reaches storage from an upgrade.
It is reachable only from a rule authored directly against the v2 API with an
explicit null mode and no temperature, which is a nonsense rule, and for such a
rule a loud refusal naming the problem beats silence.

The apparent fix — return no calls at all — is worse as things stand. The
engine records `last_run` from what `expand_action` yields, so an empty
expansion would log the rule as fired having done nothing, with no row
explaining why. That is the silent no-op shape this project treats as its
primary defect class, and closing it properly means giving the engine and the
logbook a way to say "fired, no call was possible" — engine work, not a guard
in the shim.

**Revisit when the card starts authoring arbitrary service data** (the
`ha-service-control` work). Until then the shape is unreachable in practice;
after then it is one selector click away, and the honest empty-expansion path
should land with it.

A sibling of the same key-versus-value gating survives in
`migrate_v1_defaults`: a null in `defaults.settings` is dropped silently, while
an unrecognised key there is reported. The behaviour is right — v1 dropped it
too — and only the reporting is inconsistent.

## The defaults dialog's service picker is blank on reopen

`<shabbat-defaults-dialog>` composes the same `<shabbat-service-editor>` the
rule dialog does, and `<ha-service-control>` needs an `action`
(`domain.service`) to know which service's schema to render its `data` form
against. `Defaults` (`types.ts`) has no `action` field — only `target` and
`data`, the two keys `validate_defaults` accepts — because a rule's action is
always its own; the shared defaults contribute only a target and a payload,
never a service. So on open the dialog seeds a scratch `_action = ''` that
lives only in the component's own state, never in `_draft`, and is never sent.

The visible cost: reopening the dialog after saving, say, `{temperature: 26}`
shows an **empty** service picker, with the saved `data` sitting underneath it
unlabelled by any service schema — not a blank form, but not obviously the
temperature you set either, until you re-pick `climate.set_temperature` (or
whichever service the data was shaped for) and the existing `{temperature:
26}` becomes visible and editable again under that service's own fields. A
user who set a default and comes back later may reasonably read the blank
picker as "my default was lost" when it was not: `hass.callWS` round-tripped
it, the server has it, and the next rule that inherits `defaults.data` still
gets it.

The alternative — persisting the picked action into `Defaults` so the picker
remembers it — is worse than the symptom: it would mean storing a field
`validate_defaults` neither accepts nor uses, purely to make a UI widget's
memory outlive the dialog, and would need a schema change and a migration
story for a value the server has no use for. **What to do:** re-pick the
service the data belongs to; the stored `data` reappears under it, editable,
exactly as saved.

## The card's payload fixture is generated, and regenerating it is one command

`frontend/test/fixtures/state-payload.json` is **not hand-written**. It is a
real `shabbat_scheduler/rules/list` result, captured over an actual websocket
round trip by `tests/test_frontend_fixture.py` and committed.
`frontend/test/payload-contract.test.ts` renders the card from it, and that
Python test fails whenever the committed copy differs from what the server now
sends. Regenerate with:

```
REGEN_FRONTEND_FIXTURE=1 uv run pytest tests/test_frontend_fixture.py
```

Why it exists: the frontend suite was **168/168 green for the whole period in
which the card rendered every conflict warning as an empty string**. Every
fixture was hand-written and read `warning.device`, a key the backend had
renamed to `targets` — so the tests agreed with each other and with nothing at
all. One generated fixture is what makes any part of that suite answerable to
the server.

A `_state_payload` change (a new field, a renamed one) is therefore **expected**
to fail that Python test. That is the guard working: read the diff, regenerate,
and check whether the card actually reads the field that moved. Do not silence
it by editing the JSON — `payload-contract.test.ts` would then be rendering a
shape the server does not send, which is the original failure exactly.

**Its clock is frozen, and that is not incidental.** The generator runs with
`enabled=True, dry_run=True`, so restart catch-up really runs and the one
replay-enabled rule in the fixture really records a `last_outcome`. That
outcome carries `at`, and a stale skip's `detail` says *how late* the rule was
— both read from the clock. Against the real clock the regenerated fixture
therefore differs on every run, down to the microsecond, and a guard that fails
at random is a guard the next frustrated developer switches off. So
`tests/test_frontend_fixture.py` freezes time around the **setup call only**,
to an instant inside the block its ZMANIM describe. `hass_ws_client`'s auth
refuses a frozen clock outright (`auth_invalid`), so the socket is opened
afterwards, in real time — harmless, because everything the payload reports was
already decided and recorded during setup. The frozen instant is also chosen so
every rule is already past, leaving no timer armed across the un-freeze.

## Each rule remembers its own last outcome; `last_run` remembers only one

`engine.last_run` is a single value for the whole integration, overwritten by
the next rule to act. It can say what happened most recently; it can never say
what happened to *this* rule. Half of "a rule that does not fire must say why"
therefore held only in the logbook, and the card — the thing on the wall — had
nothing to show.

`RuleStore` now keeps a `last_outcomes` map keyed by rule id, persisted beside
the rules, and `_state_payload` attaches each rule's own entry as
`last_outcome`. The record is
`{outcome, at, detail, unknown_targets?, no_live_targets?}`, and it has **two
axes on purpose**:

- `outcome` — `called` | `would_call` | `failed` | `blocked` | `skipped_stale`.
  Did the call happen, and if not, why not.
- `unknown_targets` / `no_live_targets` — did it *reach* anything. A different
  question, and one whose answer can be "no" while the call genuinely was made.
  `called` **plus** `no_live_targets` is a real, common combination (an
  existing group whose members are all unavailable); collapsing it into
  `failed` would blame a misspelling that is not there, which is the mistake
  Gap B's first fix made in both directions. Both keys are **absent** rather
  than `[]`/`false` when they do not apply, so a healthy rule cannot render a
  warning-shaped nothing.

Four things worth knowing about it:

- **`detail` is the server's own wording, reused verbatim.**
  `_condition_block_reason` already writes "condition 1 of 1 (state on
  input_boolean.kids) not met" for the logbook. The card showing the same words
  is the point: two renderings of one verdict, never two different stories
  about the same rule. `OUTCOME_PRECEDENCE` lives in `const.py` for the same
  reason — a multi-call rule's row and its logbook line must agree on which of
  its calls decides the verdict.
- **Recording does not notify the store's change listener.** That listener is
  `_rules_changed`, which reschedules the engine, so notifying would refresh
  from inside a rule's own application — a re-evaluation, on the one day nobody
  can intervene. The engine sends `SIGNAL_RULES_CHANGED` itself instead, whose
  only subscribers are `switch.py`'s `_sync` and the websocket `_forward`;
  neither writes to the store or refreshes, so nothing comes back round. Fire
  once, never re-assert — and an open card still sees the outcome as it lands.
- **No `STORAGE_VERSION` bump.** The key is absent on every store written
  before it and `last_outcomes_from_dict` never raises, so an alpha user's
  rules load unchanged; it is written only once there is something to write, so
  a store that has never fired keeps exactly the shape it always had.
  `test_a_store_written_before_last_outcome_existed_still_loads` is the proof
  rather than the claim.
- **Outcomes are pruned for deleted rules on every save**, so the map is
  bounded by the rule set rather than by uptime. `last_outcome` is also
  server-owned: `rule_schema.py` drops it on the way in (unconditionally, not
  under `keep_server_fields`), so a client can echo a rule it read without
  being refused and still cannot forge a verdict.

## Deployment note

Nothing here has been installed on the live instance. The integration ships
with its master switch defaulting **off**, so installing it cannot drive any
appliance until deliberately enabled. The rollout sequence is in the design
spec; the existing plain automations remain in production until it is proven.
