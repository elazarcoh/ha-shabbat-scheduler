from datetime import time

from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shabbat_scheduler.const import DOMAIN
from custom_components.shabbat_scheduler.models import Action, Rule
from custom_components.shabbat_scheduler.store import RuleStore


async def _setup(hass, rules=()):
    await hass.config.async_set_time_zone("Asia/Jerusalem")
    store = RuleStore(hass)
    await store.async_load()
    for rule in rules:
        await store.async_add(rule)

    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_entry_sets_up_and_unloads(hass):
    entry = await _setup(hass)
    assert entry.entry_id in hass.data[DOMAIN]

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.entry_id not in hass.data[DOMAIN]


async def test_only_one_instance_allowed(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == "create_entry"

    second = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert second["type"] == "abort"
    assert second["reason"] == "single_instance_allowed"


async def test_master_switch_defaults_off(hass):
    await _setup(hass)
    state = hass.states.get("switch.shabbat_scheduler")
    assert state is not None
    assert state.state == STATE_OFF


async def test_master_switch_turns_on_and_persists(hass):
    await _setup(hass)
    await hass.services.async_call(
        "switch", "turn_on",
        {"entity_id": "switch.shabbat_scheduler"}, blocking=True,
    )
    assert hass.states.get("switch.shabbat_scheduler").state == STATE_ON

    reloaded = RuleStore(hass)
    await reloaded.async_load()
    assert reloaded.enabled is True


async def test_one_switch_per_rule(hass):
    entry = await _setup(hass, [
        Rule(id="r1", profile=1, day="1", time=time(11, 0),
             action=Action.ON, name="בוקר שבת"),
    ])
    registry = er.async_get(hass)
    unique_id = f"{entry.entry_id}_rule_r1"
    entity_id = registry.async_get_entity_id("switch", DOMAIN, unique_id)
    assert entity_id is not None
    assert hass.states.get(entity_id) is not None

    entry_reg = registry.async_get(entity_id)
    assert entry_reg.unique_id == unique_id


async def test_rule_switch_toggle_persists(hass):
    entry = await _setup(hass, [
        Rule(id="r1", profile=1, day="1", time=time(11, 0), action=Action.ON),
    ])
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        "switch", DOMAIN, f"{entry.entry_id}_rule_r1"
    )
    assert entity_id is not None
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": entity_id}, blocking=True
    )

    reloaded = RuleStore(hass)
    await reloaded.async_load()
    assert reloaded.rules[0].enabled is False
