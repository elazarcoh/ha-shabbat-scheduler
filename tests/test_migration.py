from datetime import time as dt_time, timedelta

from custom_components.shabbat_scheduler.migration import migrate_v1, migrate_v1_rule
from custom_components.shabbat_scheduler.models import Replay, Rule
from custom_components.shabbat_scheduler.store import RuleStore, rule_from_dict, rule_to_dict

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


# --- IMPORTANT 2: a kept-disabled rule must stay repairable ---------------


def test_a_kept_disabled_rule_preserves_target_and_data_where_derivable():
    """"Kept" has to mean repairable: a rule whose devices are known but
    whose action is ambiguous must not lose its target on the way to
    disabled-and-reported."""
    multi_domain = {
        "id": "e", "profile": 1, "day": "1", "time": "12:00:00", "action": "on",
        "devices": ["climate.salon", "switch.boiler"],
        "settings": {"temperature": 26},
    }
    out, failed = migrate_v1({"rules": [multi_domain], "defaults": {}})
    survivor = out["rules"][0]
    assert survivor["target"] == {"entity_id": ["climate.salon", "switch.boiler"]}
    assert survivor["data"] == {"temperature": 26}
    assert survivor["migration_source"] == multi_domain
    assert failed == ["e"]


def test_a_kept_disabled_rule_stashes_the_raw_v1_rule_even_when_nothing_is_derivable():
    """Nothing derivable (no devices at all) is still not nothing lost -
    the whole original rule is stashed for a future repair tool."""
    raw = {**V1_CUSTOM, "script": None}
    out, _ = migrate_v1({"rules": [raw], "defaults": {}})
    survivor = out["rules"][0]
    assert survivor["target"] == {}
    assert survivor["migration_source"] == raw


# --- IMPORTANT 3: the "reported" half must be proven, not just green ------


def test_migration_error_survives_a_storage_round_trip():
    from custom_components.shabbat_scheduler.store import rule_from_dict, rule_to_dict

    raw = {**V1_CUSTOM, "script": None}
    out, _ = migrate_v1({"rules": [raw], "defaults": {}})
    rule = rule_from_dict(out["rules"][0])
    assert rule.migration_error == "a custom rule with no script has nothing to call"
    assert rule.enabled is False

    round_tripped = rule_from_dict(rule_to_dict(rule))
    assert round_tripped.migration_error == rule.migration_error
    assert round_tripped.enabled is False


async def test_migration_failures_are_populated_on_the_store_after_load(hass, hass_storage):
    hass_storage["shabbat_scheduler.rules"] = {
        "version": 1,
        "minor_version": 1,
        "key": "shabbat_scheduler.rules",
        "data": {
            "rules": [V1_SIMPLE_ON, {**V1_CUSTOM, "script": None}],
            "defaults": {},
        },
    }
    store = RuleStore(hass)
    await store.async_load()

    assert store.migration_failures == ["d"]


# --- IMPORTANT 5: a success-path rule missing id/time must not brick load -


def test_a_rule_with_no_id_cannot_be_migrated():
    raw = {key: value for key, value in V1_SIMPLE_ON.items() if key != "id"}
    out, reason = migrate_v1_rule(raw)
    assert out is None
    assert "id" in reason.lower()


def test_a_rule_with_no_time_cannot_be_migrated():
    raw = {key: value for key, value in V1_SIMPLE_ON.items() if key != "time"}
    out, reason = migrate_v1_rule(raw)
    assert out is None
    assert "time" in reason.lower()


def test_a_rule_missing_id_is_kept_disabled_and_does_not_break_the_load():
    """Before this fix, a v1 rule missing id/time 'succeeded' into a dict
    rule_from_dict raises KeyError on, aborting the load of every rule."""
    from custom_components.shabbat_scheduler.store import rule_from_dict

    raw = {key: value for key, value in V1_SIMPLE_ON.items() if key != "id"}
    out, failed = migrate_v1({"rules": [raw], "defaults": {}})
    assert len(out["rules"]) == 1
    assert out["rules"][0]["enabled"] is False
    rule_from_dict(out["rules"][0])  # must not raise
    assert failed == [out["rules"][0]["id"]]
    assert failed[0]  # not the empty string


# --- Minors, folded in -----------------------------------------------------


def test_non_climate_on_settings_are_dropped_not_passed_through():
    """v1 ignored settings for non-climate domains; carrying them through
    now gets the call rejected at fire time (switch.turn_on does not take
    a "temperature" key)."""
    raw = {**V1_CLIMATE_ON, "devices": ["switch.boiler"]}
    out, reason = migrate_v1_rule(raw)
    assert reason is None
    assert out["action"] == "switch.turn_on"
    assert out["data"] == {}


def test_migrate_v1_tolerates_a_null_rules_list():
    out, failed = migrate_v1({"rules": None, "defaults": {}})
    assert out["rules"] == []
    assert failed == []


def test_migrate_v1_tolerates_a_non_dict_rule_element():
    out, failed = migrate_v1({"rules": ["not-a-rule"], "defaults": {}})
    assert len(out["rules"]) == 1
    assert out["rules"][0]["enabled"] is False
    assert failed == [out["rules"][0]["id"]]
    assert failed[0]  # not the empty string


def test_failed_ids_are_unique_even_when_source_rules_have_no_id():
    """An empty-string id repeated for every unnamed failure gives a
    future repair tool nothing to address a rule by."""
    no_id_a = {key: value for key, value in V1_SIMPLE_ON.items() if key != "id"}
    no_id_b = {key: value for key, value in {**V1_CUSTOM, "script": None}.items() if key != "id"}
    out, failed = migrate_v1({"rules": [no_id_a, no_id_b], "defaults": {}})
    assert len(failed) == 2
    assert failed[0] != failed[1]
    assert all(failed)


# --- IMPORTANT 4: replay.within must serialise as "HH:MM:SS" --------------


def test_replay_within_serialises_as_hh_mm_ss_not_seconds():
    """rule_schema._duration - what every client-written rule is validated
    against - accepts only 'HH:MM:SS'. rule_to_dict is what every
    websocket response returns, so writing seconds back would make a
    client that reads a rule and writes it back rejected."""
    rule = Rule(
        id="x", profile=1, day="1", time=dt_time(11, 0),
        action="climate.turn_off", target={}, data={},
        replay=Replay(enabled=True, within=timedelta(hours=1)),
    )
    out = rule_to_dict(rule)
    assert out["replay"]["within"] == "01:00:00"


def test_replay_within_round_trips_through_hh_mm_ss():
    rule = Rule(
        id="x", profile=1, day="1", time=dt_time(11, 0),
        action="climate.turn_off", target={}, data={},
        replay=Replay(enabled=True, within=timedelta(hours=1, minutes=30, seconds=5)),
    )
    round_tripped = rule_from_dict(rule_to_dict(rule))
    assert round_tripped.replay.within == timedelta(hours=1, minutes=30, seconds=5)
