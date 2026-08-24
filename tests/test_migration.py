from dataclasses import replace
from datetime import datetime, time as dt_time, timedelta
from zoneinfo import ZoneInfo

from custom_components.shabbat_scheduler.block import compute_block, resolve_rules
from custom_components.shabbat_scheduler.migration import migrate_v1, migrate_v1_rule
from custom_components.shabbat_scheduler.models import Replay, Rule
from custom_components.shabbat_scheduler.store import (
    RuleStore,
    replay_from_dict,
    rule_from_dict,
    rule_to_dict,
)

TZ = ZoneInfo("Asia/Jerusalem")

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


# --- Fix round 2 -----------------------------------------------------------

# IMPORTANT: regression - a pre-fix-round-1 store (written by e39449b, which
# serialised `within` as raw seconds) must not have its bound silently
# widened to "unbounded" when read by the fixed code.


def test_replay_from_dict_parses_a_pre_fix_numeric_within_as_seconds():
    """A store written by e39449b has `within` as a raw number of seconds,
    e.g. 3600.0. Treating that as unparsable and dropping it to None would
    silently convert a bounded replay into an unbounded one - the exact
    class of silent widening this project treats as its cardinal sin."""
    replay = replay_from_dict({"enabled": True, "within": 3600.0})
    assert replay.within == timedelta(seconds=3600)


def test_replay_from_dict_raises_rather_than_silently_widening_on_nonsense():
    """A within value that is neither a legacy number of seconds nor a
    valid 'HH:MM:SS' string must not quietly become 'unbounded' either -
    it must raise."""
    import pytest

    from custom_components.shabbat_scheduler.rule_schema import RuleValidationError

    with pytest.raises(RuleValidationError):
        replay_from_dict({"enabled": True, "within": "not-a-duration"})


# IMPORTANT: a malformed (not merely missing) time or profile must not brick
# every subsequent load either - the store is already at version 2 by the
# time the crash happens, so there is no way back.


def test_a_rule_with_an_unparsable_time_cannot_be_migrated():
    raw = {**V1_SIMPLE_ON, "time": "not-a-time"}
    out, reason = migrate_v1_rule(raw)
    assert out is None
    assert "time" in reason.lower()


def test_a_rule_with_a_non_string_time_cannot_be_migrated():
    out, reason = migrate_v1_rule({**V1_SIMPLE_ON, "time": 12345})
    assert out is None
    assert "time" in reason.lower()


def test_a_rule_with_an_unparsable_profile_cannot_be_migrated():
    out, reason = migrate_v1_rule({**V1_SIMPLE_ON, "profile": "not-a-number"})
    assert out is None
    assert "profile" in reason.lower()


def test_a_rule_with_an_unparsable_time_is_kept_disabled_and_does_not_break_the_load():
    """Before this fix the placeholder rule for a *different* failure
    reason could still carry the original malformed `time` straight
    through, crashing the very keep-disable-report record meant to be
    the safe fallback."""
    raw = {**V1_SIMPLE_ON, "time": "not-a-time"}
    out, failed = migrate_v1({"rules": [raw], "defaults": {}})
    assert len(out["rules"]) == 1
    survivor = out["rules"][0]
    assert survivor["enabled"] is False
    rule_from_dict(survivor)  # must not raise
    assert failed == [survivor["id"]]


def test_a_rule_with_an_unparsable_profile_is_kept_disabled_and_does_not_break_the_load():
    raw = {**V1_SIMPLE_ON, "profile": "not-a-number"}
    out, _ = migrate_v1({"rules": [raw], "defaults": {}})
    survivor = out["rules"][0]
    assert survivor["enabled"] is False
    rule_from_dict(survivor)  # must not raise


# IMPORTANT: migration_source must survive a storage round trip - the exact
# gap Important 3 raised for migration_error, reintroduced for this field.


def test_migration_source_survives_a_storage_round_trip():
    raw = {**V1_CUSTOM, "script": None}
    out, _ = migrate_v1({"rules": [raw], "defaults": {}})
    rule = rule_from_dict(out["rules"][0])
    assert rule.migration_source == raw

    round_tripped = rule_from_dict(rule_to_dict(rule))
    assert round_tripped.migration_source == raw


# --- Fix round 3 -----------------------------------------------------------

# IMPORTANT: a v1 rule with `profile` (or, found by the same sweep, `day`)
# entirely absent migrates down the *success* path with that key missing
# altogether, because `_UNCHANGED` only copies keys present in `raw`.
# `rule_from_dict` then does `int(data["profile"])` / `str(data["day"])`
# unconditionally and raises KeyError - after the store is already at
# version 2, so every subsequent start fails identically with no way back.
# Same failure class as the missing id/time (round 1) and malformed
# time/profile (round 2) holes; this closes the last two.


def test_a_rule_with_no_profile_cannot_be_migrated():
    raw = {key: value for key, value in V1_SIMPLE_ON.items() if key != "profile"}
    out, reason = migrate_v1_rule(raw)
    assert out is None
    assert "profile" in reason.lower()


def test_a_rule_with_no_day_cannot_be_migrated():
    raw = {key: value for key, value in V1_SIMPLE_ON.items() if key != "day"}
    out, reason = migrate_v1_rule(raw)
    assert out is None
    assert "day" in reason.lower()


def test_a_rule_missing_profile_is_kept_disabled_and_does_not_break_the_load():
    """The failing rule loads without raising, disabled and reported, and a
    normal rule alongside it in the same store still migrates and loads
    normally - nothing else in the batch is taken down with it."""
    missing_profile = {key: value for key, value in V1_SIMPLE_ON.items() if key != "profile"}
    out, failed = migrate_v1({"rules": [missing_profile, V1_CLIMATE_ON], "defaults": {}})
    assert len(out["rules"]) == 2

    survivor = next(r for r in out["rules"] if r["id"] == "b")
    assert survivor["enabled"] is False
    rule_from_dict(survivor)  # must not raise
    assert failed == ["b"]

    healthy = next(r for r in out["rules"] if r["id"] == "a")
    assert healthy["enabled"] is True
    healthy_rule = rule_from_dict(healthy)  # must not raise
    assert healthy_rule.action == "climate.set_temperature"


def test_a_rule_missing_day_is_kept_disabled_and_does_not_break_the_load():
    missing_day = {key: value for key, value in V1_SIMPLE_ON.items() if key != "day"}
    out, failed = migrate_v1({"rules": [missing_day], "defaults": {}})
    survivor = out["rules"][0]
    assert survivor["enabled"] is False
    rule_from_dict(survivor)  # must not raise
    assert failed == ["b"]


# --- Fix round 4 -----------------------------------------------------------

# IMPORTANT: round 3's `day` check is presence-only - `str()` never raises,
# so any value passes it. A rule with `day: "tuesday"` therefore migrates
# down the *success* path and loads cleanly, but `block.resolve_rules` does
# `index = int(rule.day)` (block.py:88) inside one loop over all rules, with
# no per-rule isolation and nothing catching `ValueError` between there and
# `engine.async_refresh`. So one bad `day` does not merely disable its own
# rule - it aborts resolving *every* rule and nothing at all is scheduled,
# discovered on Shabbat, after version 2 is already written to disk.
# Same failure class as rounds 1-3: migrates "successfully" into something
# the system cannot then handle.


def _one_day_block():
    return compute_block(
        datetime(2026, 8, 14, 18, 44, tzinfo=TZ),
        datetime(2026, 8, 15, 20, 1, tzinfo=TZ),
    )


def test_a_rule_with_an_out_of_range_day_cannot_be_migrated():
    raw = {**V1_SIMPLE_ON, "day": "tuesday"}
    out, reason = migrate_v1_rule(raw)
    assert out is None
    assert "day" in reason.lower()


def test_a_rule_with_a_non_positive_day_cannot_be_migrated():
    """`int()` accepts these, but a day index below 1 names no day."""
    for value in ("0", "-1"):
        out, reason = migrate_v1_rule({**V1_SIMPLE_ON, "day": value})
        assert out is None, value
        assert "day" in reason.lower()


def test_a_valid_numeric_or_erev_day_still_migrates():
    for value in ("erev", "1", "3", 2):
        out, reason = migrate_v1_rule({**V1_SIMPLE_ON, "day": value})
        assert reason is None, value
        assert out["day"] == value


async def test_a_rule_with_a_bad_day_is_kept_disabled_and_others_still_resolve(
    hass, hass_storage
):
    """The whole point: the bad rule is kept, disabled and reported, and the
    healthy rule alongside it still *resolves* - the step where the crash
    actually happens. A test that only checked loading would miss it."""
    bad_day = {**V1_SIMPLE_ON, "day": "tuesday"}
    hass_storage["shabbat_scheduler.rules"] = {
        "version": 1,
        "minor_version": 1,
        "key": "shabbat_scheduler.rules",
        "data": {"rules": [bad_day, V1_CLIMATE_ON], "defaults": {}},
    }
    store = RuleStore(hass)
    await store.async_load()  # must not raise

    assert len(store.rules) == 2
    assert store.migration_failures == ["b"]

    kept = next(rule for rule in store.rules if rule.id == "b")
    assert kept.enabled is False
    assert kept.migration_error and "day" in kept.migration_error.lower()
    assert kept.migration_source == bad_day

    # The step that used to blow up on `int("tuesday")`, taking every other
    # rule down with it.
    resolved = resolve_rules(store.rules, _one_day_block(), TZ)
    assert [item.rule.id for item in resolved] == ["a"]
    assert resolved[0].when == datetime(2026, 8, 15, 11, 0, tzinfo=TZ)


def test_a_bad_day_cannot_ride_along_into_the_placeholder():
    """Round 2's lesson, applied to `day`: a rule failing for an *unrelated*
    reason must not carry a bad `day` into the supposedly safe record."""
    # No id, so it is rejected by a check that runs *before* the new `day`
    # one - the bad `day` is incidental to why it failed, exactly the shape
    # that slipped through in round 2.
    raw = {key: value for key, value in V1_SIMPLE_ON.items() if key != "id"}
    raw["day"] = "tuesday"
    out, failed = migrate_v1({"rules": [raw], "defaults": {}})
    survivor = out["rules"][0]
    assert failed == ["unmigrated-0"]
    assert survivor["migration_error"] == "a rule with no id cannot be migrated"
    assert survivor["day"] == "erev"

    # And the placeholder is resolvable even if a repair tool re-enables it.
    rule = rule_from_dict(survivor)
    resolve_rules([replace(rule, enabled=True)], _one_day_block(), TZ)  # must not raise
