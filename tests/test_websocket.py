from datetime import time

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shabbat_scheduler.const import DOMAIN
from custom_components.shabbat_scheduler.models import Action, Rule
from custom_components.shabbat_scheduler.store import RuleStore

ZMANIM = {
    "sensor.jewish_calendar_upcoming_candle_lighting": "2026-08-14T15:44:00+00:00",
    "sensor.jewish_calendar_upcoming_havdalah": "2026-08-15T17:01:00+00:00",
}


async def _setup(hass, rules=(), defaults=None):
    await hass.config.async_set_time_zone("Asia/Jerusalem")
    for entity_id, state in ZMANIM.items():
        hass.states.async_set(entity_id, state)
    store = RuleStore(hass)
    await store.async_load()
    await store.async_replace_all(defaults or {}, list(rules))
    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_rules_list_returns_rules_and_defaults(hass, hass_ws_client):
    await _setup(
        hass,
        [Rule(id="r1", profile=1, day="1", time=time(11, 0), action=Action.ON,
              devices=("climate.a",))],
        defaults={"temperature": 26},
    )
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "shabbat_scheduler/rules/list"})
    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"]["defaults"] == {"temperature": 26}
    assert [r["id"] for r in msg["result"]["rules"]] == ["r1"]
    assert msg["result"]["warnings"] == []


async def test_rules_list_reports_conflicts_as_warnings(hass, hass_ws_client):
    await _setup(hass, [
        Rule(id="a", profile=1, day="1", time=time(18, 0), action=Action.ON,
             devices=("climate.a",)),
        Rule(id="b", profile=1, day="1", time=time(18, 0), action=Action.OFF,
             devices=("climate.a",)),
    ])
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "shabbat_scheduler/rules/list"})
    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"]["warnings"]


async def test_preview_resolves_the_upcoming_block(hass, hass_ws_client):
    await _setup(hass, [
        Rule(id="r1", profile=1, day="1", time=time(11, 0), action=Action.ON,
             devices=("climate.a",)),
    ])
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "shabbat_scheduler/preview"})
    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"]["profile"] == 1
    assert len(msg["result"]["rules"]) == 1
    assert msg["result"]["rules"][0]["action"] == "on"


async def test_preview_with_block_length_resolves_a_hypothetical_block(
    hass, hass_ws_client
):
    """block_length re-derives a hypothetical block, mirroring the `simulate` service."""
    await _setup(hass, [
        Rule(id="r1", profile=1, day="1", time=time(11, 0), action=Action.ON,
             devices=("climate.a",)),
        Rule(id="r3", profile=3, day="1", time=time(11, 0), action=Action.ON,
             devices=("climate.b",)),
    ])
    client = await hass_ws_client(hass)
    await client.send_json(
        {"id": 1, "type": "shabbat_scheduler/preview", "block_length": 3}
    )
    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"]["profile"] == 3
    assert [r["rule_id"] for r in msg["result"]["rules"]] == ["r3"]


async def test_preview_without_block_length_uses_the_real_upcoming_block(
    hass, hass_ws_client
):
    await _setup(hass, [
        Rule(id="r1", profile=1, day="1", time=time(11, 0), action=Action.ON,
             devices=("climate.a",)),
        Rule(id="r3", profile=3, day="1", time=time(11, 0), action=Action.ON,
             devices=("climate.b",)),
    ])
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "shabbat_scheduler/preview"})
    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"]["profile"] == 1
    assert [r["rule_id"] for r in msg["result"]["rules"]] == ["r1"]


async def test_rules_list_reports_not_set_up_after_unload(hass, hass_ws_client):
    entry = await _setup(hass)
    client = await hass_ws_client(hass)

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    await client.send_json({"id": 1, "type": "shabbat_scheduler/rules/list"})
    msg = await client.receive_json()

    assert not msg["success"]
    assert msg["error"]["code"] == "not_set_up"


async def test_preview_reports_not_set_up_after_unload(hass, hass_ws_client):
    entry = await _setup(hass)
    client = await hass_ws_client(hass)

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    await client.send_json({"id": 1, "type": "shabbat_scheduler/preview"})
    msg = await client.receive_json()

    assert not msg["success"]
    assert msg["error"]["code"] == "not_set_up"


async def test_preview_reports_no_block_when_zmanim_missing(hass, hass_ws_client):
    await hass.config.async_set_time_zone("Asia/Jerusalem")
    store = RuleStore(hass)
    await store.async_load()
    await store.async_replace_all({}, [
        Rule(id="r1", profile=1, day="1", time=time(11, 0), action=Action.ON,
             devices=("climate.a",)),
    ])
    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "shabbat_scheduler/preview"})
    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"]["profile"] is None
    assert msg["result"]["warnings"] == [
        {
            "kind": "no_block",
            "message": "No block could be derived from the Jewish Calendar sensors.",
        }
    ]
