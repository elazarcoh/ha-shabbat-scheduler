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


async def test_adding_a_rule_creates_its_switch(hass, rule_switch_entity_id):
    entry = await _setup(hass)
    store = hass.data[DOMAIN][entry.entry_id]["store"]
    assert rule_switch_entity_id(entry, "new") is None

    await store.async_add(
        Rule(id="new", profile=1, day="1", time=time(11, 0), action=Action.ON)
    )
    await hass.async_block_till_done()

    entity_id = rule_switch_entity_id(entry, "new")
    assert entity_id is not None
    assert hass.states.get(entity_id) is not None


async def test_deleting_a_rule_removes_its_switch(hass, rule_switch_entity_id):
    entry = await _setup(hass, [
        Rule(id="gone", profile=1, day="1", time=time(11, 0), action=Action.ON),
    ])
    assert rule_switch_entity_id(entry, "gone") is not None

    store = hass.data[DOMAIN][entry.entry_id]["store"]
    await store.async_delete("gone")
    await hass.async_block_till_done()

    assert rule_switch_entity_id(entry, "gone") is None


async def test_surviving_rule_keeps_its_entity_across_replace_all(
    hass, rule_switch_entity_id
):
    keep = Rule(id="keep", profile=1, day="1", time=time(11, 0), action=Action.ON)
    entry = await _setup(hass, [keep])
    before = rule_switch_entity_id(entry, "keep")

    store = hass.data[DOMAIN][entry.entry_id]["store"]
    await store.async_replace_all({}, [
        keep,
        Rule(id="added", profile=1, day="1", time=time(18, 0), action=Action.OFF),
    ])
    await hass.async_block_till_done()

    assert rule_switch_entity_id(entry, "keep") == before
    assert rule_switch_entity_id(entry, "added") is not None


async def test_stale_registry_entry_from_before_the_session_is_purged(
    hass, rule_switch_entity_id
):
    """A registry entry can be orphaned before this session even starts -
    e.g. the store file was edited, or a rule removed, while HA was
    stopped. The first `_sync()` call, made during setup, must still purge
    it: a `known - current` diff cannot see it, because `known` is seeded
    from `current` before that first diff is ever computed, so nothing
    ever appears on the "known but no longer current" side for an entity
    that was never added in this session to begin with.
    """
    await hass.config.async_set_time_zone("Asia/Jerusalem")
    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)

    registry = er.async_get(hass)
    registry.async_get_or_create(
        "switch", DOMAIN, f"{entry.entry_id}_rule_ghost", config_entry=entry
    )
    assert rule_switch_entity_id(entry, "ghost") is not None

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert rule_switch_entity_id(entry, "ghost") is None


async def test_renaming_a_rule_reaches_its_switch_without_a_restart(
    hass, rule_switch_entity_id
):
    """Final review I7: RuleSwitch used to snapshot its name in __init__.

    `_sync` only added and removed, so after `rules/update {"name": ...}`
    the friendly name and the registry's original_name stayed stale until
    a restart - and renaming is the card's primary affordance.
    """
    entry = await _setup(hass, [
        Rule(id="r1", profile=1, day="1", time=time(11, 0), action=Action.ON,
             name="בוקר שבת", icon="mdi:candle"),
    ])
    entity_id = rule_switch_entity_id(entry, "r1")
    assert hass.states.get(entity_id).attributes["friendly_name"] == "בוקר שבת"
    assert hass.states.get(entity_id).attributes["icon"] == "mdi:candle"

    store = hass.data[DOMAIN][entry.entry_id]["store"]
    await store.async_update("r1", name="ערב שבת", icon="mdi:weather-night")
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state.attributes["friendly_name"] == "ערב שבת"
    assert state.attributes["icon"] == "mdi:weather-night"
    # The registry's own copy follows too, so the entity list is not stale.
    assert er.async_get(hass).async_get(entity_id).original_name == "ערב שבת"
    # The entity_id itself deliberately does NOT move: it is the user's
    # stable handle, and unique_id is what keeps it attached to the rule.
    assert rule_switch_entity_id(entry, "r1") == entity_id


async def test_an_unnamed_rule_falls_back_to_a_derived_name(
    hass, rule_switch_entity_id
):
    entry = await _setup(hass, [
        Rule(id="r1", profile=1, day="1", time=time(11, 0), action=Action.ON),
    ])
    entity_id = rule_switch_entity_id(entry, "r1")
    assert hass.states.get(entity_id).attributes["friendly_name"] == "1d 1 11:00 on"

    store = hass.data[DOMAIN][entry.entry_id]["store"]
    await store.async_update("r1", time=time(20, 0))
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).attributes["friendly_name"] == "1d 1 20:00 on"


async def test_a_rule_change_refreshes_the_engine_exactly_once(hass):
    """The reschedule-on-change listener must not feed itself.

    `engine.async_refresh` writes the active block back to the store, and
    if those writes ever start notifying, this listener refreshes, which
    writes, which notifies... The store's async_set_active_block and
    async_clear_active_block deliberately do not call _notify_change, and
    this is what says so out loud.
    """
    entry = await _setup(hass)
    engine = hass.data[DOMAIN][entry.entry_id]["engine"]
    store = hass.data[DOMAIN][entry.entry_id]["store"]

    calls = []
    original = engine.async_refresh

    async def _counting_refresh():
        calls.append(1)
        await original()

    engine.async_refresh = _counting_refresh

    await store.async_add(
        Rule(id="one", profile=1, day="1", time=time(11, 0), action=Action.ON)
    )
    await hass.async_block_till_done()

    assert calls == [1]
