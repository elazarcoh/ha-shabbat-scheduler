# Clone rules + rule-testing rework — Design

**Goal:** Two independent-but-related additions. (1) Let an author copy an
already-authored day's or profile's rules onto another day/profile, with
extend or overwrite semantics. (2) Replace the global, persistent `dry_run`
flag — confirmed not useful in practice, since it only ever exercised a real
Shabbat and produced no visible proof anything worked — with an on-demand way
to prove a rule, and a whole day's schedule, actually fire correctly: reusing
the exact code path a real fire uses, triggered manually, any day of the
week.

**Architecture:** Both features are thin orchestration on top of machinery
that already exists and is already tested: `rules/create` + `rules/delete`
(clone), and `resolve_rules()` + `async_apply_rule()` (the verification
story). No new domain knowledge, no new persisted state for verification, no
change to how or when the real scheduler sets real timers.

**Tech stack:** No new dependencies. Backend: `websocket_api.py`,
`engine.py`, `block.py`, `store.py`. Frontend: `card.ts`, plus new files
`clone-dialog.ts` and `simulate-dialog.ts`.

## Global Constraints

- `custom_components/shabbat_scheduler/{models,block,device_ops,const,
  rule_schema,yaml_io,migration}.py` import zero Home Assistant
  (`tests/test_packaging.py` enforces this) — nothing in this plan adds an HA
  import to those files.
- The climate shim (`device_ops.expand_action`) stays the only domain-aware
  code. Neither feature in this spec adds a second one.
- No feature here changes when or whether a REAL scheduled timer fires. The
  master switch (`store.enabled`) and the real schedule (`async_refresh`,
  `_make_callback`) are untouched by this plan.
- Every websocket write command in this plan follows the existing pattern in
  `websocket_api.py`: `@websocket_api.require_admin`, a `vol.Schema`, a
  `not_set_up` guard via `_entry_data`, `RuleValidationError` ->
  `connection.send_error`.
- Card writes stay non-optimistic: a control reflects only what the server
  pushed back, matching every existing write in `card.ts` (`_send`, `_call`).
- Both `en` and `he` entries are required for every new string in
  `frontend/src/strings.ts`.
- `<ha-selector>` with the selector type wanted, never a specific picker
  element (`ha-switch`, `ha-textfield`, `ha-code-editor`) — dashboard
  availability differs picker-by-picker; `ha-selector` itself is always
  registered. See `frontend/src/target-editor.ts`'s existing comment for why.

---

## Part 1 — Clone rules

### Data model

No new persisted shape. A clone is composed client-side from the existing
`rules/create` and `rules/delete` websocket commands — the server already
assigns a fresh id on create, so there is no id-collision case to handle and
no new backend command.

### Client-side composition (`card.ts`)

A new private method, `_cloneRules(sourceRuleIds: string[], targetProfile:
number, targetDay: string, mode: 'extend' | 'overwrite')`:

1. **Overwrite mode only:** collect every rule currently in
   `{profile: targetProfile, day: targetDay}` and `await this._send({type:
   'shabbat_scheduler/rules/delete', rule_id})` for each, sequentially,
   before doing anything else. If any delete is rejected, stop and report —
   do not proceed to create with a partially-cleared target.
2. For each source rule (in `sourceRuleIds` order): build the create payload
   from the rule's own `formToCreate`-equivalent shape (action, target,
   data, condition, replay, name, icon, color, enabled — everything but
   `id`), with `day` and `profile` rewritten to the target, and `await
   this._send({type: 'shabbat_scheduler/rules/create', rule: ...})`.
3. Track per-rule success/failure. If any create fails, stop issuing further
   creates and report exactly which source rules landed and which did not,
   by name — never a bare "something failed". This mirrors the existing
   `_dialogError` discipline: nothing here is optimistic, and a partial
   result is reported, not hidden.

### Day-name matching (profile-to-profile clone)

Days are `'erev'` plus `'1'..'n'` where `n` is the profile length
(`block.py`'s `compute_block`). A profile-to-profile clone matches by day
name and skips days the source profile does not have: cloning a 1-day
profile (days `erev`, `1`) onto a 3-day profile touches only `erev` and `1`
in the target; days `2` and `3` in the target are untouched — not cleared,
not created, not read. This applies in both overwrite and extend mode: the
day-by-day scope is the same, only what happens *within* each touched day
differs.

### UI

**`day-group.ts`** gets a small `⋮` menu button next to its `.heading`
(visible only when `canWrite`), for day-to-day clone: dispatches a
`clone-open` event carrying `{scope: 'day', profile: this.group.day's
profile, day: this.group.day}`.

**`block-header.ts`** gets a matching `⋮` next to the 1d/2d/3d chips, for
whole-profile clone: dispatches `clone-open` with `{scope: 'profile',
profile: this.selectedProfile}`.

**New `clone-dialog.ts`**, opened by `card.ts` on `clone-open`, mirrors the
existing dialog styling (`rule-dialog.ts`'s `.sheet`/`.panel` pattern):

- Header names the source (read from the event detail, not editable —
  "Clone day Erev" / "Clone the 1-day profile").
- Target picker: a profile selector (1d/2d/3d) plus, for day-scope clones
  only, a day selector scoped to that profile's valid days (`erev`, `1`..`n`)
  — for profile-scope clones every valid day of the target profile is
  included automatically, so no day picker is shown.
- Extend/overwrite: two radio-style buttons, extend selected by default
  (the non-destructive choice).
- A warning line, shown only when the target already has rules: "The
  target has N existing rule(s)." — worded identically regardless of mode,
  so overwrite's destructiveness reads from the mode selection itself, not
  from separate copy.
- Confirm button disabled while a source has zero rules (nothing to clone).
- On confirm: calls `_cloneRules`, shows a spinner/busy state (reusing
  `card.ts`'s existing `_busy`), and on completion either closes (full
  success) or stays open showing exactly which rules failed (partial
  failure) with a retry-the-remainder option that only re-attempts the rules
  still missing from the target.

### Testing

- `frontend/test/clone.test.ts` (new): day-name matching (skip-missing
  behaviour, both directions: narrow→wide and wide→narrow profile), extend
  vs overwrite call ordering (delete-before-create, never interleaved),
  partial-failure reporting (mock a `rules/create` rejection mid-sequence,
  assert the report names exactly which rules landed).
- `frontend/test/clone-dialog.test.ts` (new): day-scope vs profile-scope
  target picker rendering, confirm-disabled-when-source-empty, the
  existing-target-rules warning line.
- `e2e/test_card_e2e.py`: one new test cloning a day with a real rule onto
  an empty day in the dev container, asserting the cloned rule appears with
  a new id and the source rule is untouched.

---

## Part 2 — Replace dry-run with on-demand verification

### What is removed

- `store.dry_run` (persisted boolean) and every read of it: `engine.py`'s
  `_call` (`if self.store.dry_run: result["outcome"] = "would_call"`),
  `store.py`'s persistence of the field, `websocket_api.py`'s inclusion of
  `dry_run` in `_state_payload`.
- The `shabbat_scheduler.set_dry_run` service (`services.py`, `services.yaml`).
- The "Dry run" toggle button in `block-header.ts`, its `dryRun`/`_toggleDryRun`
  wiring, and `card.ts`'s `_onDryRun` handler.
- `types.ts`: `CardState.dry_run`.
- `strings.ts`: the `dry_run` key (both languages).
- README's mention of the dry-run toggle in the screenshot caption and the
  "Design commitments" bullet — replaced per the docs updates below, not
  deleted outright (the capability moves, the sentence describing it must
  move with it).

**What stays:** the `would_call` outcome *value* — `build_outcome`,
`OUTCOME_PRECEDENCE`, and every place that renders it (`format.ts`,
`rule-row.ts`, the logbook) are unchanged. Only what *triggers* it changes:
instead of a standing flag read by every real scheduled fire, it is the
result of an explicit "Simulate" choice made per invocation of the two new
features below. A simulated run is never recorded to `last_outcome`, never
pushed to the logbook, and never persisted — it is a live-only report shown
in the dialog that triggered it and nowhere else, since it did not really
happen and the rest of the system must not be told otherwise.

### `engine.async_apply_rule` gets one new optional parameter

```python
async def async_apply_rule(
    self, rule: Rule, *, simulate: bool = False, at: datetime | None = None,
    force_conditions: bool = False,
) -> list[dict]:
```

- `force_conditions`: when true, `_condition_block_reason` is skipped
  entirely and every condition is treated as passed — this is the ONLY
  effect it has; it does not interact with `at` (forcing pass is "ignore
  conditions", evaluating against `at` is "evaluate conditions honestly
  against a different moment" — a caller sets one or the other, or neither,
  never expects both to combine into some third meaning). Defaults false,
  so both real call sites (`_make_callback`, `async_catch_up`) are
  unaffected.
- `simulate`: when true, behaves exactly as `store.dry_run` used to at the
  point of the real service call (`_call` returns `would_call` instead of
  calling), but — unlike the old flag — does **not** call
  `self._async_record_outcome` and does **not** fire `SIGNAL_RULES_CHANGED`.
  The event bus fires (`EVENT_RULE_APPLIED`/`EVENT_RULE_COMPLETED`) still
  fire, carrying the same `dry_run`-named key for backward compatibility
  with anything listening (renamed `simulate` in the payload is a breaking
  change to an external contract the codebase doesn't control the readers
  of; keep the key name `dry_run` in the event payload specifically, and
  say so in a comment, even though the internal flag is gone).
- `at`: when given, `_condition_block_reason`'s condition evaluation is
  asked to treat `at` as "now" for any condition that reads the clock
  (`sun`, `time`, `numeric_state` with a time-based template are out of
  scope — HA's own condition helpers read `dt_util.utcnow()` internally and
  cannot be parameterised; scope `at` to exactly what this plan can honestly
  deliver: **conditions of type `sun` and `time`**, evaluated against `at`
  by constructing the condition check with an explicit `datetime` argument
  where HA's helper supports one, and documented as a named limitation —
  not silently pretended to be universal — for any condition type HA's
  helper does not accept a `now` override for). This is additive and
  optional; omitted, behaviour is identical to today.
- Both default to today's behaviour when omitted, so `_make_callback`'s real
  callback and `async_catch_up`'s replay path — the two real call sites —
  are unchanged and untested-differently.

### New websocket command: `rules/run_now`

```python
vol.Required("type"): "shabbat_scheduler/rules/run_now",
vol.Required("rule_id"): str,
vol.Optional("simulate", default=True): bool,
vol.Optional("at"): str,  # ISO 8601, optional
```

Looks the rule up in `store`, calls `await engine.async_apply_rule(rule,
simulate=msg["simulate"], at=parsed_at)`, and returns the per-call results
list verbatim — the same list `async_apply_rule` already returns and
`outcome_from_results` already knows how to summarise; the card renders it
with the same `formatOutcome`/`formatWarning` helpers `rule-row.ts` already
has, no new formatting code. `simulate` defaults to `True` so an
accidental/malformed call from a future client version cannot silently make
a real call.

### New websocket command: `rules/run_day`

```python
vol.Required("type"): "shabbat_scheduler/rules/run_day",
vol.Required("profile"): int,
vol.Required("day"): str,
vol.Optional("simulate", default=True): bool,
vol.Optional("force_conditions", default=False): bool,
```

This is "run this day's schedule now." Implementation, in full:

```python
merged = engine._merged_rules()  # same call async_refresh already makes
block = <the real current block if it matches `profile`, else a
         hypothetical block of that length anchored on real candle
         lighting via compute_block — exactly preview_payload's existing
         block_length branch>
resolved = resolve_rules(merged, block, engine._tz())
day_items = [item for item in resolved if item.rule.day == day]
results = []
for item in day_items:  # in resolve_rules' own order — unchanged
    result = await engine.async_apply_rule(
        item.rule, simulate=simulate, force_conditions=force_conditions,
    )
    results.append({"rule_id": item.rule.id, "results": result})
return results
```

This is `resolve_rules()` — the exact function `async_refresh` calls to
build the real schedule — followed by a loop over `async_apply_rule()` —
the exact function `_make_callback`'s real timer closure calls. No
parallel implementation of either decision. The only thing this command
owns is *what decides when to call `async_apply_rule`*: a plain sequential
loop, right now, instead of HA's real point-in-time timer waiting for the
real clock. Nothing about real scheduling, real timers, or the persisted
block is touched.

### UI

**`rule-dialog.ts`**: a "▶ Run now" button next to Save/Delete (visible only
when editing an existing rule, i.e. `this.rule !== null`, and `canWrite`).
Clicking opens a small inline confirm, not a separate dialog: two buttons,
"Simulate" and "Run for real", each sending `rules/run_now` with `simulate`
set accordingly. The result (per-call outcome list) renders inline in the
dialog using the same `formatOutcome`/`formatWarning` helpers `rule-row.ts`
uses, so a real user recognises the shape immediately.

**New `simulate-dialog.ts`**, opened from a new icon in `block-header.ts`
next to the existing gear:

- A day/profile picker — reuses the same profile+day selector as
  `clone-dialog.ts`'s target picker (shared as a small internal
  sub-component if that turns out cleaner in implementation; not mandated
  here).
- Calls `shabbat_scheduler/preview` (existing) for the chosen day/profile
  to render the full ordered rule list with resolved times — this is
  **read-only, already-existing, zero-risk** and needs no new backend code.
  This alone satisfies "see the full schedule for a day that isn't coming
  yet" — no markers/dates limitation applies here since the dialog is
  explicitly a testing surface, not the card's live day view; it is fine
  and expected for it to show resolved times for a hypothetical day.
- "Simulate this day" / "Run this day for real" buttons call
  `rules/run_day` with the matching `simulate` value, plus a "Conditions:
  respect real state / force pass" toggle wired to `force_conditions`,
  defaulting to respect-real-state per the earlier decision.
- Results render as a list, one row per rule, in schedule order, each
  showing its outcome the same way `rule-row.ts` does.

### Docs

- README: replace the dry-run screenshot caption and the "Design
  commitments" bullet about dry-run with a short paragraph on Run Now /
  Simulate, and add a "Testing your rules" subsection under Quick Start
  pointing at it.
- `docs/known-behaviours.md`: add an entry recording that dry-run was
  removed in favour of on-demand verification, and why (the two reasons
  given in this spec's Goal — no visible proof, only exercised a real
  Shabbat) — matching this file's own established practice of recording
  what changed and why rather than deleting history silently.

### Testing

- `tests/test_engine.py`: `async_apply_rule(rule, simulate=True)` does not
  call `_async_record_outcome` or send `SIGNAL_RULES_CHANGED` (ablate: make
  it call them, confirm a test goes red); `at`-scoped condition evaluation
  for `sun`/`time` conditions; every existing `store.dry_run`-driven test
  ported to call `async_apply_rule(..., simulate=True)` directly instead of
  toggling a store flag that no longer exists.
- `tests/test_websocket.py`: `rules/run_now` — simulate defaults true,
  explicit `simulate: false` really calls (via the existing
  `async_mock_service` fixture), unknown `rule_id` errors cleanly.
  `rules/run_day` — day-name filtering, `resolve_rules` ordering preserved,
  `force_conditions` bypasses a normally-blocking condition, results shape
  matches `async_apply_rule`'s per-rule results.
- `tests/test_store.py`, `tests/test_migration.py`: remove/port every
  `dry_run`-field test; confirm a store persisted with an old `dry_run` key
  from a pre-upgrade version loads without error (the key is simply
  ignored, not migrated — it carried no information worth preserving).
- `frontend/test/rule-dialog.test.ts`: Run Now button visibility
  (existing-rule only, `canWrite` only), Simulate vs Real dispatching the
  right `simulate` value, inline result rendering.
- `frontend/test/simulate-dialog.test.ts` (new): day/profile picker,
  preview rendering, force-conditions toggle, result-per-rule rendering.
- `e2e/test_card_e2e.py`: one new test running a day's schedule for real in
  the dev container (using the existing `input_boolean` fixtures already in
  that suite, matching the project's own "test with input_boolean first"
  guidance) and asserting the resulting states.

---

## Sequencing note for the implementation plan

Part 2's removal of `store.dry_run` and Part 1's clone feature do not share
files in a way that creates ordering dependencies — they can be planned as
two independent task sequences. Within Part 2, the backend
(`async_apply_rule` parameter, `run_now`, `run_day`) must land before the
frontend pieces that call them; within Part 1, `_cloneRules` composition
logic (pure, testable without a dialog) should land before `clone-dialog.ts`
so the dialog's tests can exercise real composition logic rather than a
stub.
