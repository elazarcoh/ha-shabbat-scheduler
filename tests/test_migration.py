from custom_components.shabbat_scheduler.migration import migrate_v1, migrate_v1_rule
from custom_components.shabbat_scheduler.store import RuleStore

V1_CLIMATE_ON = {
    "id": "a", "profile": 1, "day": "1", "time": "11:00:00", "action": "on",
    "devices": ["climate.salon"], "settings": {"temperature": 26, "hvac_mode": "cool"},
    "name": "Morning", "enabled": True, "replay_on_restart": True,
}
V1_SIMPLE_ON = {
    "id": "b", "profile": 1, "day": "erev", "time": "22:00:00", "action": "on",
    "devices": ["switch.boiler"], "settings": {},
}
V1_OFF = {
    "id": "c", "profile": 1, "day": "1", "time": "18:00:00", "action": "off",
    "devices": ["climate.salon"], "settings": {},
}
V1_CUSTOM = {
    "id": "d", "profile": 1, "day": "1", "time": "17:00:00", "action": "custom",
    "script": "script.boiler", "variables": {"minutes": 30},
}


def test_a_climate_on_rule_becomes_set_temperature():
    out, reason = migrate_v1_rule(V1_CLIMATE_ON)
    assert reason is None
    assert out["action"] == "climate.set_temperature"
    assert out["target"] == {"entity_id": ["climate.salon"]}
    assert out["data"] == {"temperature": 26, "hvac_mode": "cool"}
    assert out["name"] == "Morning"


def test_a_simple_on_rule_becomes_turn_on():
    out, reason = migrate_v1_rule(V1_SIMPLE_ON)
    assert reason is None
    assert out["action"] == "switch.turn_on"
    assert out["target"] == {"entity_id": ["switch.boiler"]}


def test_an_off_rule_becomes_turn_off():
    out, _ = migrate_v1_rule(V1_OFF)
    assert out["action"] == "climate.turn_off"


def test_a_custom_rule_becomes_a_script_call():
    out, reason = migrate_v1_rule(V1_CUSTOM)
    assert reason is None
    assert out["action"] == "script.turn_on"
    assert out["target"] == {"entity_id": ["script.boiler"]}
    assert out["data"] == {"variables": {"minutes": 30}}


def test_replay_on_restart_becomes_replay_with_no_window():
    """v1 replayed however late it was; tightening that silently would
    change behaviour the user never asked to change."""
    out, _ = migrate_v1_rule(V1_CLIMATE_ON)
    assert out["replay"] == {"enabled": True}
    out2, _ = migrate_v1_rule(V1_SIMPLE_ON)
    assert out2["replay"] == {"enabled": False}


def test_a_rule_with_no_devices_cannot_be_migrated():
    out, reason = migrate_v1_rule({**V1_SIMPLE_ON, "devices": []})
    assert out is None
    assert "device" in reason.lower()


def test_a_custom_rule_with_no_script_cannot_be_migrated():
    out, reason = migrate_v1_rule({**V1_CUSTOM, "script": None})
    assert out is None
    assert "script" in reason.lower()


def test_an_unmigratable_rule_is_kept_and_disabled_not_dropped():
    data = {"rules": [V1_SIMPLE_ON, {**V1_CUSTOM, "script": None}], "defaults": {}}
    out, failed = migrate_v1(data)
    assert len(out["rules"]) == 2, "a dropped rule is the worst upgrade outcome"
    survivor = next(r for r in out["rules"] if r["id"] == "d")
    assert survivor["enabled"] is False
    assert failed == ["d"]


def test_defaults_migrate_too():
    data = {"rules": [], "defaults": {"devices": ["climate.a"], "settings": {"temperature": 26}}}
    out, _ = migrate_v1(data)
    assert out["defaults"] == {
        "target": {"entity_id": ["climate.a"]},
        "data": {"temperature": 26},
    }


def test_the_other_store_keys_survive():
    data = {"rules": [], "defaults": {}, "enabled": True, "dry_run": True,
            "active_block": {"candle_lighting": "x", "havdalah": "y"}}
    out, _ = migrate_v1(data)
    assert out["enabled"] is True
    assert out["dry_run"] is True
    assert out["active_block"] == {"candle_lighting": "x", "havdalah": "y"}


async def test_a_v1_store_on_disk_migrates_on_load(hass, hass_storage):
    hass_storage["shabbat_scheduler.rules"] = {
        "version": 1,
        "minor_version": 1,
        "key": "shabbat_scheduler.rules",
        "data": {"rules": [V1_CLIMATE_ON], "defaults": {}, "enabled": True},
    }
    store = RuleStore(hass)
    await store.async_load()

    assert len(store.rules) == 1
    assert store.rules[0].action == "climate.set_temperature"
    assert store.enabled is True
    # And it was written back, so the conversion happens once.
    assert hass_storage["shabbat_scheduler.rules"]["version"] == 2
