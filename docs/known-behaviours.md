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

## Deployment note

Nothing here has been installed on the live instance. The integration ships
with its master switch defaulting **off**, so installing it cannot drive any
appliance until deliberately enabled. The rollout sequence is in the design
spec; the existing plain automations remain in production until it is proven.
