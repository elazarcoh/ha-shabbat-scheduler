from datetime import time

from custom_components.shabbat_scheduler.models import Action, EREV, Rule
from custom_components.shabbat_scheduler.store import (
    RuleStore,
    rule_from_dict,
    rule_to_dict,
)


def test_rule_dict_round_trip():
    rule = Rule(
        id="r1", profile=2, day=EREV, time=time(22, 30), action=Action.ON,
        devices=("climate.a",), settings={"temperature": 26}, name="test",
    )
    restored = rule_from_dict(rule_to_dict(rule))
    assert restored == rule
    assert isinstance(restored.action, Action)
    assert isinstance(restored.devices, tuple)
    assert isinstance(restored.time, time)


async def test_store_starts_empty_and_disabled(hass):
    store = RuleStore(hass)
    await store.async_load()
    assert store.rules == []
    assert store.enabled is False  # master switch defaults OFF
    assert store.dry_run is False


async def test_add_and_persist(hass):
    store = RuleStore(hass)
    await store.async_load()
    rule = Rule(id="r1", profile=1, day="1", time=time(11, 0), action=Action.ON)
    await store.async_add(rule)

    reloaded = RuleStore(hass)
    await reloaded.async_load()
    assert [r.id for r in reloaded.rules] == ["r1"]


async def test_update_changes_only_named_fields(hass):
    store = RuleStore(hass)
    await store.async_load()
    await store.async_add(
        Rule(id="r1", profile=1, day="1", time=time(11, 0), action=Action.ON)
    )
    await store.async_update("r1", enabled=False)
    assert store.rules[0].enabled is False
    assert store.rules[0].time == time(11, 0)


async def test_delete(hass):
    store = RuleStore(hass)
    await store.async_load()
    await store.async_add(
        Rule(id="r1", profile=1, day="1", time=time(11, 0), action=Action.ON)
    )
    await store.async_delete("r1")
    assert store.rules == []


async def test_replace_all_swaps_defaults_and_rules(hass):
    store = RuleStore(hass)
    await store.async_load()
    await store.async_replace_all(
        {"temperature": 26},
        [Rule(id="x", profile=3, day="2", time=time(9, 0), action=Action.OFF)],
    )
    assert store.defaults == {"temperature": 26}
    assert [r.id for r in store.rules] == ["x"]
