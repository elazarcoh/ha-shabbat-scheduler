"""End-to-end: a full block driven by real timers, against test booleans.

Time-control technique (deviates from the brief - see task-16-report.md for
the full reasoning): the brief wraps only *setup* in `freeze_time(...)` and
then calls `async_fire_time_changed` *after* that block exits, back on the
real wall clock. That is broken by construction: `async_fire_time_changed`
force-fires a pending timer by comparing how far the requested instant is
from `time.time()` *right now* against how far the timer's own deadline is
from `hass.loop.time()` *right now* - both readings taken at the moment
`async_fire_time_changed` runs. Once real time resumes, `time.time()` jumps
to the actual wall clock, which is now (2026-08-1x onward) *past* the
brief's hardcoded 2026-08-15 literals, making the "jump" negative and the
comparison always false: no timer would ever fire, for a reason having
nothing to do with the code under test.

The fix: use the `freezer` fixture (pytest-freezer, already the convention
in tests/test_engine.py) and never let it expire - one `freezer.move_to(...)`
before setup, then plain `async_fire_time_changed(hass, <target iso time>)`
calls to force each rule's timer, all while still frozen at the original
instant. `async_fire_time_changed`'s own internal "how far is the requested
instant from now" arithmetic then measures forward from a stable, frozen
reference point instead of a drifting real clock, exactly matching how
tests/test_engine.py's `test_enabled_master_lists_upcoming_rules` and the
catch-up tests already use `freezer`/`freeze_time` in this suite.
"""

from datetime import date, time

import pytest
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.shabbat_scheduler.const import (
    CANDLE_SENSOR,
    DOMAIN,
    HAVDALAH_SENSOR,
)
from custom_components.shabbat_scheduler.models import Action, Rule
from custom_components.shabbat_scheduler.store import RuleStore


async def test_full_one_day_block_drives_test_booleans(
    hass, jerusalem, test_booleans, freezer
):
    """Setup, then two real timers fire in sequence and flip a real entity."""
    # Anchor before candle lighting so both rule timers are still pending
    # when the config entry is set up.
    freezer.move_to("2026-08-15T05:00:00+00:00")

    hass.states.async_set(CANDLE_SENSOR, "2026-08-14T15:44:00+00:00")
    hass.states.async_set(HAVDALAH_SENSOR, "2026-08-15T17:01:00+00:00")
    hass.states.async_set("input_boolean.salon", "off")

    store = RuleStore(hass)
    await store.async_load()
    await store.async_replace_all(
        {"devices": ["input_boolean.salon"]},
        [
            Rule(id="on", profile=1, day="1", time=time(11, 0), action=Action.ON),
            Rule(id="off", profile=1, day="1", time=time(18, 0), action=Action.OFF),
        ],
    )
    await store.async_set_enabled(True)

    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    engine = hass.data[DOMAIN][entry.entry_id]["engine"]
    assert [item.rule.id for item in engine.upcoming()] == ["on", "off"]

    # 11:00 Asia/Jerusalem == 08:00 UTC: the "on" rule's moment.
    async_fire_time_changed(hass, dt_util.parse_datetime("2026-08-15T08:00:00+00:00"))
    await hass.async_block_till_done()
    assert hass.states.get("input_boolean.salon").state == "on"

    # 18:00 Asia/Jerusalem == 15:00 UTC: the "off" rule's moment.
    async_fire_time_changed(hass, dt_util.parse_datetime("2026-08-15T15:00:00+00:00"))
    await hass.async_block_till_done()
    assert hass.states.get("input_boolean.salon").state == "off"


async def test_manual_change_is_not_reverted(hass, jerusalem, test_booleans, freezer):
    """Fire-once means the plugin must never fight a manual override.

    This is the property the whole project exists to guarantee: the user's
    previous scheduler re-asserted state and fought them - an AC turned off
    by hand switched back on within minutes. Here the rule fires once, the
    user flips the boolean off by hand, and time keeps moving; the boolean
    must stay off because nothing re-asserts it.
    """
    freezer.move_to("2026-08-15T05:00:00+00:00")

    hass.states.async_set(CANDLE_SENSOR, "2026-08-14T15:44:00+00:00")
    hass.states.async_set(HAVDALAH_SENSOR, "2026-08-15T17:01:00+00:00")
    hass.states.async_set("input_boolean.salon", "off")

    store = RuleStore(hass)
    await store.async_load()
    await store.async_replace_all(
        {"devices": ["input_boolean.salon"]},
        [Rule(id="on", profile=1, day="1", time=time(11, 0), action=Action.ON)],
    )
    await store.async_set_enabled(True)

    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    async_fire_time_changed(hass, dt_util.parse_datetime("2026-08-15T08:00:00+00:00"))
    await hass.async_block_till_done()
    assert hass.states.get("input_boolean.salon").state == "on"

    # The user turns it off by hand five minutes later.
    hass.states.async_set("input_boolean.salon", "off")

    # Time keeps moving; nothing else is scheduled for this block, so
    # nothing should touch the entity again.
    async_fire_time_changed(hass, dt_util.parse_datetime("2026-08-15T08:30:00+00:00"))
    await hass.async_block_till_done()
    assert hass.states.get("input_boolean.salon").state == "off"


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_a_restart_between_havdalah_and_the_tail_still_fires_it(
    hass, jerusalem, test_booleans, freezer
):
    """The whole restart path, through real config entries.

    Havdalah rolls the jewish_calendar sensors to next week while a last-day
    "23:00 off" is still pending. Home Assistant then restarts at 21:00.
    Everything in memory is lost, the sensors read next week, and catch-up
    against a wholly-future block does nothing - so the air conditioner used
    to run the night with nothing in the log. The block in force has to come
    back out of .storage.
    """
    freezer.move_to("2026-08-15T05:00:00+00:00")

    hass.states.async_set(CANDLE_SENSOR, "2026-08-14T15:44:00+00:00")
    hass.states.async_set(HAVDALAH_SENSOR, "2026-08-15T17:01:00+00:00")
    hass.states.async_set("input_boolean.salon", "on")

    store = RuleStore(hass)
    await store.async_load()
    await store.async_replace_all(
        {"devices": ["input_boolean.salon"]},
        [Rule(id="late-off", profile=1, day="1", time=time(23, 0),
              action=Action.OFF)],
    )
    await store.async_set_enabled(True)

    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # 20:01:30 local - havdalah passes and both sensors roll forward.
    freezer.move_to("2026-08-15T17:01:30+00:00")
    hass.states.async_set(CANDLE_SENSOR, "2026-08-21T15:36:00+00:00")
    hass.states.async_set(HAVDALAH_SENSOR, "2026-08-22T16:53:00+00:00")
    await hass.async_block_till_done()

    # 21:00 local - the restart, inside the hold's own window.
    freezer.move_to("2026-08-15T18:00:00+00:00")
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    engine = hass.data[DOMAIN][entry.entry_id]["engine"]
    assert engine.current_block.erev_date == date(2026, 8, 14)
    assert [item.rule.id for item in engine.upcoming()] == ["late-off"]

    # 23:00 local - the rule the restart used to eat.
    freezer.move_to("2026-08-15T20:00:00+00:00")
    async_fire_time_changed(hass, dt_util.parse_datetime("2026-08-15T20:00:00+00:00"))
    await hass.async_block_till_done()
    assert hass.states.get("input_boolean.salon").state == "off"


async def test_a_card_can_drive_the_whole_loop(
    hass, hass_ws_client, jerusalem, rule_switch_entity_id
):
    """Subscribe, create, see the push and the entity, delete, see both go."""
    hass.states.async_set(
        "sensor.jewish_calendar_upcoming_candle_lighting",
        "2026-08-14T15:44:00+00:00",
    )
    hass.states.async_set(
        "sensor.jewish_calendar_upcoming_havdalah", "2026-08-15T17:01:00+00:00"
    )
    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "shabbat_scheduler/subscribe"})
    assert (await client.receive_json())["success"]

    await client.send_json(
        {
            "id": 2,
            "type": "shabbat_scheduler/rules/create",
            "rule": {
                "profile": 1,
                "day": "1",
                "time": "11:00:00",
                "action": "on",
                "devices": ["input_boolean.salon"],
                "name": "בוקר שבת",
            },
        }
    )

    pushed = await client.receive_json()
    created = await client.receive_json()
    if pushed["type"] != "event":  # ordering is not guaranteed
        pushed, created = created, pushed

    assert created["success"]
    rule_id = created["result"]["rule"]["id"]
    assert [r["id"] for r in pushed["event"]["rules"]] == [rule_id]

    await hass.async_block_till_done()
    assert rule_switch_entity_id(entry, rule_id) is not None

    await client.send_json(
        {"id": 3, "type": "shabbat_scheduler/rules/delete", "rule_id": rule_id}
    )
    while True:
        msg = await client.receive_json()
        if msg.get("id") == 3 and msg["type"] == "result":
            assert msg["success"]
            break

    await hass.async_block_till_done()
    assert rule_switch_entity_id(entry, rule_id) is None
