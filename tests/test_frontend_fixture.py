"""Keeps the card's test fixtures honest.

The frontend suite was 168/168 green through the entire period in which
the card rendered every conflict as an empty string: its fixtures were
hand-written and used a `device` key the backend had stopped sending, so
the tests agreed with each other and with nothing else. This test is the
only thing that makes a frontend fixture answerable to the server.

Regenerate with:

    REGEN_FRONTEND_FIXTURE=1 uv run pytest tests/test_frontend_fixture.py
"""

import json
import os
from datetime import time
from pathlib import Path

from custom_components.shabbat_scheduler.models import Replay, Rule

FIXTURE = (
    Path(__file__).parent.parent / "frontend" / "test" / "fixtures" / "state-payload.json"
)

REGEN = "REGEN_FRONTEND_FIXTURE=1 uv run pytest tests/test_frontend_fixture.py"

# Every value here is deliberately NOT a default of anything on either
# side. A fixture that happens to equal the card's own property defaults
# proves nothing about the binding, and `enabled`/`dry_run` left False
# would be indistinguishable from a card that never read them at all.
DEFAULTS = {
    "target": {"entity_id": ["climate.salon"]},
    "data": {"temperature": 24},
}

RULES = (
    # An ordinary rule, carrying every optional field a rule can carry, so
    # the card's row rendering is exercised against real serialisation
    # (`replay.within` as 'HH:MM:SS', a colour, an icon, a name).
    Rule(
        id="erev-salon",
        profile=1,
        day="erev",
        time=time(18, 50),
        action="climate.set_temperature",
        target={"entity_id": ["climate.salon"]},
        data={"temperature": 26},
        replay=Replay(enabled=True),
        name="Salon AC",
        icon="mdi:snowflake",
        color="#4caf50",
    ),
    # The conflict that matters most: both of these rules are DISPLAYED
    # (profile 1 is the coming block's length), so `unattachedWarnings`
    # keeps this warning out of the banner and the only place its text can
    # appear is the rule rows themselves.
    Rule(
        id="day1-mamad-on",
        profile=1,
        day="1",
        time=time(11, 0),
        action="climate.turn_on",
        target={"entity_id": ["climate.mamad"]},
    ),
    Rule(
        id="day1-mamad-off",
        profile=1,
        day="1",
        time=time(11, 0),
        action="climate.turn_off",
        # Overlaps the rule above on climate.mamad only, so the conflict's
        # `targets` is a genuine intersection rather than a whole selector.
        target={"entity_id": ["climate.mamad", "climate.boiler"]},
    ),
    # Disabled, and takes its target from the defaults. Two things at once:
    # a disabled rule must not conflict with anything, and `ruleBrief` must
    # fall back to `defaults.target` for a rule that names none.
    Rule(
        id="day1-disabled",
        profile=1,
        day="1",
        time=time(13, 0),
        action="switch.turn_off",
        enabled=False,
    ),
    # A conflict in a profile that is NOT on screen (the coming block is 1
    # day long). It names no displayed rule, so the banner is the only
    # place it can appear - the case that tells `displayedRuleIds` apart
    # from "every rule id", and the one where a conflict would otherwise
    # render nowhere at all.
    Rule(
        id="p3-day2-on",
        profile=3,
        day="2",
        time=time(9, 0),
        action="climate.turn_on",
        target={"entity_id": ["climate.mamad"]},
    ),
    Rule(
        id="p3-day2-off",
        profile=3,
        day="2",
        time=time(9, 0),
        action="switch.turn_off",
        target={"entity_id": ["climate.mamad"]},
    ),
)


async def test_the_committed_frontend_fixture_matches_a_real_payload(
    hass, hass_ws_client, setup_scheduler
):
    """The card's fixture is the server's payload, or the suite is lying."""
    # The client is minted before the entry loads, exactly as the other
    # websocket tests do it.
    await setup_scheduler(RULES, defaults=DEFAULTS, enabled=True, dry_run=True)
    client = await hass_ws_client(hass)

    # A real round trip over the socket, not a call to `_state_payload`:
    # what the card receives is the WIRE shape, and only the round trip
    # proves that is what this fixture holds.
    await client.send_json({"id": 1, "type": "shabbat_scheduler/rules/list"})
    msg = await client.receive_json()
    assert msg["success"], msg
    payload = msg["result"]

    assert payload["warnings"], (
        "this fixture is only worth having if it carries a conflict - that "
        "is the field the silent bug lived in"
    )
    # Both halves of the warning story, or the frontend contract test can
    # only ever cover one of the two places a conflict is rendered.
    by_profile = {warning["profile"]: warning for warning in payload["warnings"]}
    assert set(by_profile) == {1, 3}, (
        "the fixture needs one conflict on displayed rules (rendered on the "
        f"rows) and one on a hidden profile (rendered in the banner); got {payload['warnings']}"
    )
    for warning in payload["warnings"]:
        assert warning["targets"], f"a conflict with no targets renders as nothing: {warning}"
        # The exact regression: the backend renamed `device` -> `targets`
        # and every hand-written fixture kept the old key. `in` rather than
        # a dict comparison so an explicit `device: None` cannot pass.
        assert "device" not in warning, (
            "`device` is v1's key and the card no longer reads it; a payload "
            "carrying it means the rename has been reverted"
        )
    assert by_profile[1]["targets"] == ["climate.mamad"], (
        "the displayed conflict must be the INTERSECTION of the two rules' "
        "resolved targets, not either rule's whole selector"
    )
    # Guards against a fixture that would still pass while proving nothing
    # about the card's own bindings, per this plan's testing standards.
    assert payload["enabled"] is True and payload["dry_run"] is True
    assert payload["master_entity_id"], (
        "the card cannot toggle the master switch without this, and every "
        "hand-written fixture guessed it"
    )
    assert payload["block"] is not None

    current = json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"

    if os.environ.get("REGEN_FRONTEND_FIXTURE"):
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE.write_text(current)

    assert FIXTURE.exists(), f"{FIXTURE} is missing; regenerate with {REGEN}"
    assert FIXTURE.read_text() == current, (
        "the card's committed fixture no longer matches what the server "
        "sends. `frontend/test/payload-contract.test.ts` is now rendering a "
        "payload shape that does not exist, and it will stay green while it "
        f"does. Regenerate with `{REGEN}`, read the diff, and fix whatever "
        "in the card stopped reading the field that changed."
    )
