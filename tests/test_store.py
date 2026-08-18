from datetime import datetime, time, timezone

from custom_components.shabbat_scheduler.const import STORAGE_KEY, STORAGE_VERSION
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


def _stored(hass_storage) -> dict:
    return hass_storage[STORAGE_KEY]["data"]


async def test_active_block_round_trips(hass):
    store = RuleStore(hass)
    await store.async_load()
    assert store.active_block is None

    candle = datetime(2026, 8, 14, 18, 44, tzinfo=timezone.utc)
    havdalah = datetime(2026, 8, 15, 20, 1, tzinfo=timezone.utc)
    await store.async_set_active_block(candle, havdalah)

    reloaded = RuleStore(hass)
    await reloaded.async_load()
    assert reloaded.active_block == (candle, havdalah)

    await reloaded.async_clear_active_block()
    again = RuleStore(hass)
    await again.async_load()
    assert again.active_block is None


async def test_a_store_without_an_active_block_keeps_its_old_shape(
    hass, hass_storage
):
    """The key is additive: absent before this existed, absent when unset."""
    store = RuleStore(hass)
    await store.async_load()
    await store.async_add(
        Rule(id="r1", profile=1, day="1", time=time(11, 0), action=Action.ON)
    )
    assert set(_stored(hass_storage)) == {
        "rules", "defaults", "enabled", "dry_run"
    }


async def test_load_tolerates_storage_written_before_active_block_existed(
    hass, hass_storage
):
    """A .storage file from the shipped v1 schema must still load."""
    hass_storage[STORAGE_KEY] = {
        "version": STORAGE_VERSION,
        "key": STORAGE_KEY,
        "data": {
            "rules": [
                rule_to_dict(
                    Rule(id="r1", profile=1, day="1", time=time(11, 0),
                         action=Action.ON)
                )
            ],
            "defaults": {"temperature": 26},
            "enabled": True,
            "dry_run": False,
        },
    }
    store = RuleStore(hass)
    await store.async_load()

    assert [r.id for r in store.rules] == ["r1"]
    assert store.defaults == {"temperature": 26}
    assert store.enabled is True
    assert store.active_block is None


async def test_a_malformed_active_block_is_ignored_not_fatal(hass, hass_storage):
    hass_storage[STORAGE_KEY] = {
        "version": STORAGE_VERSION,
        "key": STORAGE_KEY,
        "data": {
            "rules": [],
            "defaults": {},
            "enabled": True,
            "dry_run": False,
            "active_block": {"candle_lighting": "not-a-datetime"},
        },
    }
    store = RuleStore(hass)
    await store.async_load()
    assert store.active_block is None
    assert store.enabled is True


async def test_replace_all_swaps_defaults_and_rules(hass):
    store = RuleStore(hass)
    await store.async_load()
    await store.async_replace_all(
        {"temperature": 26},
        [Rule(id="x", profile=3, day="2", time=time(9, 0), action=Action.OFF)],
    )
    assert store.defaults == {"temperature": 26}
    assert [r.id for r in store.rules] == ["x"]
