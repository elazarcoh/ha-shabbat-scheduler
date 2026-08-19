# Throwaway instance

```bash
docker compose -f dev/docker-compose.yml up -d
# wait for http://127.0.0.1:8124 to answer, then:
uv run python dev/seed.py        # prints a token
```

Port 8124, never 8123. This instance is disposable - `docker compose down -v`
and re-seed whenever it gets confusing. It is the only Home Assistant this
plan is allowed to touch.

The two zmanim sensors are fabricated directly via `POST /api/states`, not
backed by a real integration, so they do not survive a container restart
(`docker compose stop && start`, a host reboot, etc.) - only the rules and
dashboard, which live in storage, do. Re-run `dev/seed.py` after any restart
that was not a full `down -v`; running it against a container that still has
its onboarding user will fail on the user-creation step, so tear down with
`down -v` first if the container was only stopped rather than removed.

The e2e tests navigate to `/shabbat-scheduler/0`, a dashboard created via
`lovelace/dashboards/create`, not `/lovelace/0`. On this Home Assistant
release the built-in default dashboard's panel is registered with no config
(kept only for backward compatibility) and the frontend redirects any visit
to it to the new built-in `/home` panel instead of rendering the saved
views - confirmed, reproducible, not a bug in this harness.
