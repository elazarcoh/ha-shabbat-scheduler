"""Bring the throwaway instance up to a testable state.

Onboards a fresh container, creates the integration's config entry,
fabricates the Jewish Calendar sensors the engine reads, seeds a rule set,
and prints a token for the e2e tests.

Points at localhost:8124 only. It must never be aimed at a real instance.
"""

import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8124"


def _post(path: str, payload: dict, token: str | None = None) -> dict:
    request = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode()
    return json.loads(body) if body else {}


def onboard() -> str:
    """Create the owner, exchange the auth code for a token, and finish
    the remaining onboarding steps.

    A token alone is not enough: as long as any of the four onboarding
    steps (user, core_config, analytics, integration) is unfinished, the
    frontend redirects every page - including /lovelace/0 - to
    /onboarding.html, so the e2e browser never reaches the card. The
    HA-owned onboarding UI would normally walk a human through the rest;
    scripting them here is what makes the container usable headlessly.
    """
    result = _post(
        "/api/onboarding/users",
        {
            "client_id": BASE,
            "name": "Dev",
            "username": "dev",
            "password": "devdevdev",
            "language": "en",
        },
    )
    code = result["auth_code"]

    request = urllib.request.Request(
        f"{BASE}/auth/token",
        data=(
            f"grant_type=authorization_code&code={code}&client_id={BASE}"
        ).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        token = json.loads(response.read().decode())["access_token"]

    _post("/api/onboarding/core_config", {}, token)
    _post("/api/onboarding/analytics", {}, token)
    _post(
        "/api/onboarding/integration",
        {"client_id": BASE, "redirect_uri": f"{BASE}/"},
        token,
    )
    return token


def create_config_entry(token: str) -> None:
    """Drive the integration's config flow so a config entry exists.

    seed_rules() writes through the websocket API, which requires the
    integration to already be configured. The flow has no fields - it
    creates the entry on the first step - so a single POST is enough.
    Fails loudly if the entry cannot be created (e.g. it already exists
    for a reason other than "single instance already set up").
    """
    result = _post(
        "/api/config/config_entries/flow",
        {"handler": "shabbat_scheduler", "show_advanced_options": False},
        token,
    )
    if result.get("type") == "create_entry":
        return
    if result.get("type") == "abort" and result.get("reason") == "single_instance_allowed":
        return
    raise SystemExit(f"creating the config entry failed: {result}")


def seed_zmanim(token: str) -> None:
    """Fabricate the two sensors the engine derives its block from."""
    for entity_id, state in (
        ("sensor.jewish_calendar_upcoming_candle_lighting",
         "2026-08-14T18:44:00+03:00"),
        ("sensor.jewish_calendar_upcoming_havdalah",
         "2026-08-15T20:01:00+03:00"),
    ):
        _post(f"/api/states/{entity_id}", {"state": state}, token)


def seed_rules(token: str) -> None:
    """Two rules on erev and two on day 1, via the websocket API.

    Uses the same websocket pattern as /home/rpi4/ha-claude-utils, pointed
    at this container. Written through the API rather than into .storage so
    the seed exercises the same validation a user would hit.

    RuleStore.rules (custom_components/shabbat_scheduler/store.py) returns
    rules in insertion order - async_add() appends, nothing sorts before
    the websocket API hands them to the card - so the order these are
    *created* in is exactly the order `state.rules` arrives in on the
    frontend, before format.ts's buildGroups() sorts by time. The day-1
    pair is therefore deliberately authored 18:00-before-11:00 (out of
    time order): if buildGroups()'s `.sort((a, b) =>
    a.time.localeCompare(b.time))` were ever removed, day 1 would render
    18:00 above 11:00 and e2e/test_card_e2e.py's
    test_the_card_shows_its_rules_in_time_order would catch it. With
    erev's two rules already ascending (22:30, 23:00) and untouched, that
    group alone would NOT have caught a missing sort - the day-1 order is
    what makes the test adversarial rather than incidentally-passing.
    """
    import asyncio

    import websockets  # provided by the playwright dev dependency chain

    rules = [
        {"profile": 1, "day": "erev", "time": "22:30:00", "action": "on",
         "devices": ["input_boolean.kids"], "name": "Kids night"},
        {"profile": 1, "day": "erev", "time": "23:00:00", "action": "off",
         "devices": ["input_boolean.salon"]},
        {"profile": 1, "day": "1", "time": "18:00:00", "action": "off",
         "devices": ["input_boolean.salon"]},
        {"profile": 1, "day": "1", "time": "11:00:00", "action": "on",
         "devices": ["input_boolean.salon"], "name": "Shabbat morning"},
    ]

    async def _send() -> None:
        uri = BASE.replace("http://", "ws://") + "/api/websocket"
        async with websockets.connect(uri) as socket:
            await socket.recv()  # auth_required
            await socket.send(json.dumps({"type": "auth", "access_token": token}))
            await socket.recv()  # auth_ok
            for index, rule in enumerate(rules, start=1):
                await socket.send(json.dumps({
                    "id": index,
                    "type": "shabbat_scheduler/rules/create",
                    "rule": rule,
                }))
                reply = json.loads(await socket.recv())
                if not reply.get("success"):
                    raise SystemExit(f"seeding rule {index} failed: {reply}")

    asyncio.run(_send())


DASHBOARD_URL_PATH = "shabbat-scheduler"


def seed_dashboard(token: str) -> None:
    """A single-view dashboard holding nothing but the card.

    Deliberately NOT the default `lovelace/config/save` (no url_path)
    target. As of Home Assistant 2026.8 the built-in default dashboard is
    registered purely for backward compatibility with a null panel
    config (`lovelace/__init__.py`'s `_async_ensure_default_panel` calls
    `async_register_built_in_panel(hass, DOMAIN)` with no config), and the
    frontend now treats a null-config "lovelace" panel as unconfigured -
    any navigation to it, including a direct link to /lovelace/0, gets
    client-side redirected to the new built-in /home panel instead of
    showing the saved views. That is a real, confirmed behavior of this
    HA release, not a harness bug. A dashboard created explicitly via
    lovelace/dashboards/create (as any real user would do to add a
    custom card) gets a real panel config and is not affected, so that
    is what this seeds and what e2e/test_card_e2e.py points at.
    """
    import asyncio

    import websockets

    config = {
        "views": [
            {
                "title": "Card",
                "cards": [{"type": "custom:shabbat-scheduler-card"}],
            }
        ]
    }

    async def _send() -> None:
        uri = BASE.replace("http://", "ws://") + "/api/websocket"
        async with websockets.connect(uri) as socket:
            await socket.recv()
            await socket.send(json.dumps({"type": "auth", "access_token": token}))
            await socket.recv()
            await socket.send(json.dumps({
                "id": 1,
                "type": "lovelace/dashboards/create",
                "url_path": DASHBOARD_URL_PATH,
                "title": "Shabbat Scheduler",
                "mode": "storage",
                "show_in_sidebar": True,
            }))
            reply = json.loads(await socket.recv())
            if not reply.get("success"):
                raise SystemExit(f"creating the dashboard failed: {reply}")

            await socket.send(json.dumps({
                "id": 2,
                "type": "lovelace/config/save",
                "url_path": DASHBOARD_URL_PATH,
                "config": config,
            }))
            reply = json.loads(await socket.recv())
            if not reply.get("success"):
                raise SystemExit(f"saving the dashboard failed: {reply}")

    asyncio.run(_send())


if __name__ == "__main__":
    access_token = onboard()
    create_config_entry(access_token)
    seed_zmanim(access_token)
    seed_rules(access_token)
    seed_dashboard(access_token)
    print(access_token)
    sys.exit(0)
