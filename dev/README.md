# Throwaway instance

```bash
docker compose -f dev/docker-compose.yml up -d
# wait for http://127.0.0.1:8124 to answer, then:
uv run python dev/seed.py        # prints a token
```

Port 8124, never 8123. It is the only Home Assistant this plan is allowed to
touch.

`seed.py` is re-runnable: it onboards a fresh instance, and logs in if the
instance is already onboarded. It also **deletes every existing rule before
seeding**, because `rules/create` only ever appends - there is no upsert - so
without that every re-run stacked another four rules on top of the last run's.
An instance was found holding twenty. That is not cosmetic: e2e's
`test_editing_a_rule_redraws_the_timeline` asserts that after changing the
11:00 rule to 12:15 there is no 11:00 rule left, and with five copies of the
fixture four of them still are - so it fails in a way that reads exactly like a
broken card, and it was misdiagnosed as one. **If e2e shows more failures than
you expect, count the rules before you touch anything.**

**`docker compose down -v` does NOT reset this instance.** `./config` is a bind
mount and the compose file declares no named volumes, so `-v` removes nothing
and every bit of state - onboarding, auth, the config entry, the rules -
survives on the host. This README used to advise `down -v` for a clean slate;
it never worked. The container also writes as root, so the host user cannot
delete the state directly. What does work:

```bash
docker compose -f dev/docker-compose.yml down
docker run --rm -v "$PWD/dev/config:/config" alpine:3 \
  sh -c 'find /config -mindepth 1 -maxdepth 1 \
           ! -name configuration.yaml ! -name custom_components \
           -exec rm -rf {} +'
docker compose -f dev/docker-compose.yml up -d
uv run python dev/seed.py
```

Only `configuration.yaml` is tracked in git under `dev/config/`; everything
else there is generated, so that is the full set worth keeping.

The port mapping is currently `0.0.0.0:8124:8123`, so the instance is
reachable from the LAN for development on other devices. This container ships
seeded, well-known credentials (`dev` / `devdevdev`) and onboards with no
further hardening, so keep it on a trusted network and change the mapping back
to `127.0.0.1:8124:8123` to make it local-only again.

`configuration.yaml` pins `time_zone: Asia/Jerusalem`. Do not remove it.
Onboarding defaults the zone to UTC, and because the engine converts every
zman into Home Assistant's configured zone, an unpinned instance renders
candle lighting three hours early and derives blocks against the wrong local
dates - which silently invalidates every date assertion in `e2e/`.

The two zmanim sensors are fabricated directly via `POST /api/states`, not
backed by a real integration, so they do not survive a container restart
(`docker compose stop && start`, a host reboot, etc.) - only the rules and
dashboard, which live in storage, do. Just re-run `dev/seed.py` after a
restart - it logs in rather than re-onboarding, so it no longer needs a fresh
container to work.

**Restart-based testing needs the template pair, not the fabricated one.**
Because the fabricated sensors vanish on restart, a restart leaves the engine
with no block at all - it logs `no block is known, so nothing is scheduled`
and catch-up correctly does nothing. That is indistinguishable from a replay
bug, and it cost a debugging cycle before it was written down. For anything
that involves restarting the container - replay, catch-up, the
`_caught_up_for` guard - use `sensor.livetest_candle_lighting` /
`sensor.livetest_havdalah` from `configuration.yaml` instead. They are
template sensors, so they survive restarts, and they always bracket `now`:
yesterday 18:44 to today 23:59. The span crosses midnight on purpose - the
engine rejects a same-day pair as an implausible zman pair, since a real
Shabbat runs Friday evening into Saturday night.

**Re-seeding the zmanim does not move the block.** The engine persists the
block in force and holds it, so writing earlier dates into the two sensors on
a running instance changes nothing - `rules/list` keeps reporting the old
block and the card keeps drawing it. That hold is deliberate (it is what stops
a block being lost when the sensors roll forward at havdalah), but it means
the fixture cannot be rewound from the outside. To actually change the block,
clear the persisted one first:

```bash
docker stop shabbat-scheduler-dev
docker run --rm -v "$PWD/dev/config:/config" \
  --entrypoint python3 ghcr.io/home-assistant/home-assistant:2026.8.2 -c \
  "import json; p='/config/.storage/shabbat_scheduler.rules'; \
   d=json.load(open(p)); d['data']['active_block']=None; json.dump(d, open(p,'w'))"
docker start shabbat-scheduler-dev
```

then re-seed. The full reset at the top of this file achieves the same thing
more bluntly.

The e2e tests navigate to `/shabbat-scheduler/0`, a dashboard created via
`lovelace/dashboards/create`, not `/lovelace/0`. On this Home Assistant
release the built-in default dashboard's panel is registered with no config
(kept only for backward compatibility) and the frontend redirects any visit
to it to the new built-in `/home` panel instead of rendering the saved
views - confirmed, reproducible, not a bug in this harness.

## Driving Home Assistant's own elements from Playwright

`e2e/test_card_e2e.py` has to reach inside `<ha-service-control>` and
`<ha-selector>`. These are HA frontend internals with no public API, and they
changed shape in the 2026.x picker rework, so the structure below was found by
dumping shadow roots against this running instance (HA **2026.8.2**) rather
than guessed at. Rediscovering it costs about an hour. Playwright's locators
pierce shadow DOM, so every selector here can be written as one flat CSS
descendant chain - but `document.querySelector` from `page.evaluate` **cannot**,
so start from a Playwright locator (`card.evaluate(...)`) if you need to walk
the tree by hand.

### `ha-service-control` - the action editor

```
shabbat-service-editor
  ha-service-control                         (already registered on a dashboard)
    ha-service-picker                        <- the action combo box
      ha-generic-picker
        div.container > div#picker > slot[name=field]
          ha-picker-field                    <- CLICK THIS to open it
        wa-popover                           (appears only once open)
          ha-picker-combo-box#combo-box
            ha-input-search > wa-input > input   <- TYPE THE QUERY HERE
            lit-virtualizer
              div.combo-box-row              <- the results; CLICK one
    div.description                          (a link to the service's docs)
    ha-selector.target-selector              <- HA's OWN target UI; see below
    ha-settings-row                          <- one per data field in the schema
      ha-selector                            (the field's typed selector)
```

- A result row's text is `"<service>\n<domain>"`, e.g. `"turn_on\nswitch"`.
  Searching is fuzzy and crosses domains: `set_temperature` returns both
  `climate`'s and `water_heater`'s, and `turn_on` returns `siren`'s. Narrow
  with two chained text filters (service, then domain) and assert exactly one
  row survives - `.first` silently authors a rule against the wrong
  integration.
- Data fields are `ha-settings-row` elements and there is one per field HA's
  schema declares, so their count and text are a real schema assertion:
  `switch.turn_on` renders zero, `climate.set_temperature` renders one
  (`hvac_mode`).
- **`temperature` never appears here.** `climate.set_temperature` declares it
  behind a `supported_features` filter, and `ha-service-control` renders a
  filtered field only once its own internal target names an entity with that
  feature. This card deliberately does not pass a target down (see
  `service-editor.ts`), so the filtered fields stay hidden. `hvac_mode` is the
  unfiltered field of the same service and proves the same point.
- **`ha-service-control` renders its own target picker anyway**, as
  `ha-selector.target-selector`, as soon as an action is set - and its
  `elementProperties` offer `hidePicker` and `hideDescription` but **no**
  `hideTarget`, so it cannot be turned off. That means a dialog with an action
  set contains **two** `ha-target-picker`s, and the card discards the value of
  HA's one. Scope every target locator to `shabbat-target-editor`, never to the
  dialog, or the test drives the picker whose value is thrown away.

### `ha-selector` with `{target: {}}` - the target editor

```
shabbat-target-editor
  ha-selector                                (always registered)
    ha-selector-target#selector              (dynamically imported)
      ha-target-picker                       (dynamically imported)
        div.item-groups                      (present only once something is chosen)
          ha-target-picker-item-group[type=entity]
        div.add-target-wrapper
          ha-generic-picker
            div.container > div#picker > slot[name=field]
              ha-button                      <- "Add target"; CLICK THIS
            wa-popover
              ha-picker-combo-box#combo-box
                ha-input-search > wa-input > input
                div.combo-box-row
```

- **The two pickers have different triggers.** `ha-service-picker` slots an
  `ha-picker-field`; `ha-target-picker` slots an `ha-button` labelled "Add
  target". There is no single selector that opens both. Clicking the
  `ha-generic-picker` itself does nothing - click the trigger.
- `customElements.get('ha-target-picker')` is **undefined** on a freshly loaded
  dashboard and becomes defined once a `{target: {}}` selector is rendered.
  That dynamic import is the entire reason the card uses `ha-selector` rather
  than the picker directly, and
  `test_the_target_selector_causes_ha_target_picker_to_be_defined` guards it.
  Assert it in a **create** dialog: in an edit dialog the rule already has an
  action, so `ha-service-control`'s own target selector imports the picker and
  the test would pass with the card's target editor deleted.
- An entity row's text is `"<friendly name>\n<domain>"`, e.g.
  `"Dev salon\nclimate"`. Searching `dev_salon` also returns the
  generic_thermostat's backing `input_boolean` ("Thermostat output (salon)"),
  so narrow by domain here too.
- Picking one entity yields `{entity_id: 'climate.dev_salon'}` - a bare
  **string**, not a list. `rule_schema` accepts either.

### Not registered on a dashboard

Confirmed absent both before and after the dialog opens, which is why the
replay and condition editors use plain `<input>` and `<textarea>`:
`ha-textfield`, `ha-combo-box`. `ha-selector`, `ha-service-control` and
`ha-entity-picker` are all present from the start.

### Running e2e, and the one way it can still go unnoticed

```bash
export HA_DEV_TOKEN=$(uv run python dev/seed.py | tail -1)
uv run pytest e2e/ -v
```

Tokens last **30 minutes**. A run that dies part-way with 30-second Playwright
timeouts is far more often an expired token than a broken card - the `token`
fixture checks for that up front and skips with a plain-language reason, so
trust it over your own reading of the timeout.

When every e2e test skips, `pytest_terminal_summary` in `e2e/conftest.py`
prints a red `e2e: ALL TESTS SKIPPED` banner with the reason. A silent skip is
how this suite stayed red, unnoticed, through a whole plan.

**But the banner only fires when e2e is actually collected.** `pyproject.toml`
sets `testpaths = ["tests"]`, so a plain `uv run pytest` does not collect
`e2e/` at all and says nothing about it either way - "496 passed" is a
statement about the Python suite only, and nothing about the card in a real
browser. Run `uv run pytest e2e/` as a separate, deliberate step. Adding `e2e`
to `testpaths` would make the banner unmissable, at the cost of making the
default command need a container and a token; that trade has not been made.
