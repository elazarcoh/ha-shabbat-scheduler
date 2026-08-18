from datetime import time

from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shabbat_scheduler.const import DOMAIN
from custom_components.shabbat_scheduler.models import Action, Rule
from custom_components.shabbat_scheduler.store import RuleStore


async def _setup(hass, rules=()):
    await hass.config.async_set_time_zone("Asia/Jerusalem")
    store = RuleStore(hass)
    await store.async_load()
    if rules:
        await store.async_replace_all({}, list(rules))
    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _switch_for(hass, entry, rule_id):
    return er.async_get(hass).async_get_entity_id(
        "switch", DOMAIN, f"{entry.entry_id}_rule_{rule_id}"
    )


async def test_adding_a_rule_creates_its_switch(hass):
    entry = await _setup(hass)
    store = hass.data[DOMAIN][entry.entry_id]["store"]
    assert _switch_for(hass, entry, "new") is None

    await store.async_add(
        Rule(id="new", profile=1, day="1", time=time(11, 0), action=Action.ON)
    )
    await hass.async_block_till_done()

    entity_id = _switch_for(hass, entry, "new")
    assert entity_id is not None
    assert hass.states.get(entity_id) is not None


async def test_deleting_a_rule_removes_its_switch(hass):
    entry = await _setup(hass, [
        Rule(id="gone", profile=1, day="1", time=time(11, 0), action=Action.ON),
    ])
    assert _switch_for(hass, entry, "gone") is not None

    store = hass.data[DOMAIN][entry.entry_id]["store"]
    await store.async_delete("gone")
    await hass.async_block_till_done()

    assert _switch_for(hass, entry, "gone") is None


async def test_surviving_rule_keeps_its_entity_across_replace_all(hass):
    keep = Rule(id="keep", profile=1, day="1", time=time(11, 0), action=Action.ON)
    entry = await _setup(hass, [keep])
    before = _switch_for(hass, entry, "keep")

    store = hass.data[DOMAIN][entry.entry_id]["store"]
    await store.async_replace_all({}, [
        keep,
        Rule(id="added", profile=1, day="1", time=time(18, 0), action=Action.OFF),
    ])
    await hass.async_block_till_done()

    assert _switch_for(hass, entry, "keep") == before
    assert _switch_for(hass, entry, "added") is not None
