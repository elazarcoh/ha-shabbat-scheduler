# Throwaway instance

```bash
docker compose -f dev/docker-compose.yml up -d
# wait for http://127.0.0.1:8124 to answer, then:
uv run python dev/seed.py        # prints a token
```

Port 8124, never 8123. It is the only Home Assistant this plan is allowed to
touch.

`seed.py` is re-runnable: it onboards a fresh instance, and logs in if the
instance is already onboarded.

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

then re-seed. A full `down -v` achieves the same thing more bluntly.

The e2e tests navigate to `/shabbat-scheduler/0`, a dashboard created via
`lovelace/dashboards/create`, not `/lovelace/0`. On this Home Assistant
release the built-in default dashboard's panel is registered with no config
(kept only for backward compatibility) and the frontend redirects any visit
to it to the new built-in `/home` panel instead of rendering the saved
views - confirmed, reproducible, not a bug in this harness.
