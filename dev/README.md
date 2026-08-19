# Throwaway instance

```bash
docker compose -f dev/docker-compose.yml up -d
# wait for http://127.0.0.1:8124 to answer, then:
uv run python dev/seed.py        # prints a token
```

Port 8124, never 8123. This instance is disposable - `docker compose down -v`
and re-seed whenever it gets confusing. It is the only Home Assistant this
plan is allowed to touch.

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
dashboard, which live in storage, do. Re-run `dev/seed.py` after any restart
that was not a full `down -v`; running it against a container that still has
its onboarding user will fail on the user-creation step, so tear down with
`down -v` first if the container was only stopped rather than removed.

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
