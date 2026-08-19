# Known behaviours and residual risks

Findings from the reviews of the backend branch that are deliberate, accepted,
or known-and-deferred. Recorded here because the review scratch directory is
not committed and these are things a future maintainer will otherwise
rediscover the hard way.

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
restarts before the block's tail, restart catch-up re-applies the most recent
already-passed rule — so a device switched off by hand at 20:30 comes back on
after a 21:00 restart, until the 23:00 rule turns it off.

This is the same trade-off already accepted for any mid-block restart. It
stays at one rule per device and is idempotent (no service call if the device
is already in the desired state). The alternative — not restoring the block —
loses the 23:00 rule entirely, which is worse.

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
- **Static switch entities.** Rule switches are built once at platform setup.
  `import_yaml` schedules a config-entry reload so they are rebuilt, but there
  is no dynamic add/remove. **The planned Lovelace card creates and deletes
  rules over a websocket API and will need this**, most likely via a
  dispatcher signal.
- **`RuleStore.rules` hands out shared mutable `Rule` objects.** No current
  consumer mutates them, but websocket CRUD in the follow-up plan must not
  either — consider making `Rule` frozen before that lands.

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

## Deployment note

Nothing here has been installed on the live instance. The integration ships
with its master switch defaulting **off**, so installing it cannot drive any
appliance until deliberately enabled. The rollout sequence is in the design
spec; the existing plain automations remain in production until it is proven.
