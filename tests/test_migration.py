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
    """RE-AIMED (I3). This asserted `settings` became `defaults["data"]`,
    which is the defect, not the behaviour: v2's defaults are domain-blind,
    so `block.merge_defaults` then handed `{temperature: 26}` to every
    `switch.turn_on` in the store and Home Assistant refused the call at
    fire time. The settings half now lands on the climate rules that would
    have read it in v1, pinned by the I3 tests below.

    RE-CHECKED after I5, when both defaults fields started being resolved
    per rule. Both halves of this assertion are still what we WANT, not what
    the code happens to do:

    - `target` is still emitted, even though no migrated rule needs it any
      more (they all carry their own now). It is what the user set, the
      card's defaults dialog reads it, and a rule authored later inherits it
      exactly as a v1 rule would have. Unlike a shared `data`, a shared
      `target` cannot break a rule of the wrong domain: it is only ever
      consulted for a rule that has none.
    - no `data` key, for the I3 reason above. Asserted by equality, not by
      membership, so a `data` creeping back in fails here.
    """
    data = {"rules": [], "defaults": {"devices": ["climate.a"], "settings": {"temperature": 26}}}
    out, _ = migrate_v1(data)
    assert out["defaults"] == {"target": {"entity_id": ["climate.a"]}}


def test_the_other_store_keys_survive():
    data = {"rules": [], "defaults": {}, "enabled": True,
            "active_block": {"candle_lighting": "x", "havdalah": "y"}}
    out, _ = migrate_v1(data)
    assert out["enabled"] is True
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
    which cannot be converted must not lose its target on the way to
    disabled-and-reported.

    EXAMPLE CHANGED in fix round 3, assertions untouched. This used to use a
    mixed-domain rule, which round 3 makes migratable (it splits - see the
    I6 section, which now pins that case). The property here is about the
    SALVAGE, not about that rule shape, so it moved to a shape that still
    cannot convert: a domain v1 never drove.
    """
    unsupported = {
        "id": "e", "profile": 1, "day": "1", "time": "12:00:00", "action": "on",
        "devices": ["lock.front", "lock.back"],
        "settings": {"temperature": 26},
    }
    out, failed = migrate_v1({"rules": [unsupported], "defaults": {}})
    survivor = out["rules"][0]
    assert survivor["target"] == {"entity_id": ["lock.front", "lock.back"]}
    assert survivor["data"] == {"temperature": 26}
    assert survivor["migration_source"] == unsupported
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


# --- Fix round 5 -----------------------------------------------------------

# IMPORTANT: round 4 bounded `day` to "erev or any positive integer", on the
# reasoning that a longer Chag block might legitimately use a higher index.
# That reasoning was wrong, and the looser bound is itself an instance of
# this task's failure class - a silent no-op rather than a crash:
#
#   * `rule_schema._profile` hard-caps `profile` to 1..3.
#   * `resolve_rules` skips any rule whose `profile != block.length`.
#   * so a rule can only fire when block.length == its profile, max 3,
#     and `resolve_rules` then `continue`s whenever `index > block.length`.
#
# A `day: "7"` rule therefore migrates clean and enabled, is never
# reported, shows healthy in the UI, and hits that `continue` for every
# block that can ever exist. It never fires, and nobody is told.


async def test_a_day_beyond_the_cap_is_kept_disabled_not_a_silent_no_op(
    hass, hass_storage
):
    """`day: "7"` can never fire (profile caps at 3, and resolve_rules skips
    index > block.length), so migrating it clean is a permanent silent
    no-op. It must be kept-disabled-and-reported like any other rule this
    code cannot convert - and the healthy rule beside it must still
    resolve."""
    bad_day = {**V1_SIMPLE_ON, "day": "7"}
    hass_storage["shabbat_scheduler.rules"] = {
        "version": 1,
        "minor_version": 1,
        "key": "shabbat_scheduler.rules",
        "data": {"rules": [bad_day, V1_CLIMATE_ON], "defaults": {}},
    }
    store = RuleStore(hass)
    await store.async_load()

    assert len(store.rules) == 2
    assert store.migration_failures == ["b"]

    kept = next(rule for rule in store.rules if rule.id == "b")
    assert kept.enabled is False
    assert kept.migration_error and "day" in kept.migration_error.lower()

    resolved = resolve_rules(store.rules, _one_day_block(), TZ)
    assert [item.rule.id for item in resolved] == ["a"]


def test_a_day_above_three_cannot_be_migrated():
    for value in ("4", "7", 9):
        out, reason = migrate_v1_rule({**V1_SIMPLE_ON, "day": value})
        assert out is None, value
        assert "day" in reason.lower()


def test_a_day_beyond_the_cap_cannot_ride_into_the_placeholder():
    raw = {key: value for key, value in V1_SIMPLE_ON.items() if key != "id"}
    raw["day"] = "7"
    out, failed = migrate_v1({"rules": [raw], "defaults": {}})
    survivor = out["rules"][0]
    assert failed == ["unmigrated-0"]
    assert survivor["day"] == "erev"


# The same trace applied to `profile`, which `migrate_v1_rule` only ever
# checked with a bare `int()`. A migrated rule never passes through
# `rule_schema._profile`, so `profile: 7` survives migration clean and
# enabled - and then `resolve_rules` skips it for every block that can
# exist, because no block is 7 days long. Identical silent no-op.


async def test_a_profile_beyond_the_cap_is_kept_disabled_not_a_silent_no_op(
    hass, hass_storage
):
    bad_profile = {**V1_SIMPLE_ON, "profile": 7}
    hass_storage["shabbat_scheduler.rules"] = {
        "version": 1,
        "minor_version": 1,
        "key": "shabbat_scheduler.rules",
        "data": {"rules": [bad_profile, V1_CLIMATE_ON], "defaults": {}},
    }
    store = RuleStore(hass)
    await store.async_load()

    assert store.migration_failures == ["b"]
    kept = next(rule for rule in store.rules if rule.id == "b")
    assert kept.enabled is False
    assert kept.migration_error and "profile" in kept.migration_error.lower()

    resolved = resolve_rules(store.rules, _one_day_block(), TZ)
    assert [item.rule.id for item in resolved] == ["a"]


def test_a_profile_outside_one_to_three_cannot_be_migrated():
    for value in (0, 4, 7, -1):
        out, reason = migrate_v1_rule({**V1_SIMPLE_ON, "profile": value})
        assert out is None, value
        assert "profile" in reason.lower()


def test_a_profile_beyond_the_cap_cannot_ride_into_the_placeholder():
    raw = {key: value for key, value in V1_SIMPLE_ON.items() if key != "id"}
    raw["profile"] = 7
    out, _ = migrate_v1({"rules": [raw], "defaults": {}})
    assert out["rules"][0]["profile"] == 1


def test_every_in_range_profile_and_day_still_migrates():
    """The bound must not be so tight it rejects what v1 legitimately wrote."""
    for profile in (1, 2, 3):
        for day in ("erev", "1", "2", "3"):
            out, reason = migrate_v1_rule(
                {**V1_SIMPLE_ON, "profile": profile, "day": day}
            )
            assert reason is None, (profile, day)
            assert out["profile"] == profile
            assert out["day"] == day


# --- I1: migrate_v1 must be TOTAL - it is the one function that cannot ----
#     raise. A raise here escapes _async_migrate_func -> Store.async_load ->
#     async_setup_entry, the store STAYS at version 1, and every subsequent
#     restart fails identically. The seventh and eighth instances of the
#     Task-5 class, in the two fields nobody swept. `yaml_io.py:172-175`
#     already closed exactly this hole at the YAML door.


def test_a_malformed_settings_is_kept_disabled_and_reported():
    """`dict("hot")` raised ValueError on the SUCCESS path, so one corrupt
    field took down the whole load rather than one rule.

    Looped rather than parametrised, matching the shape sweeps already in
    this file - `enable_custom_integrations` is autouse, so every test case
    in this suite costs a fixture round trip whether it needs one or not.
    """
    for bad in ("hot", ["hot"], 5, 26.5, True):
        raw = {**V1_CLIMATE_ON, "id": "bad", "settings": bad}
        out, failed = migrate_v1({"rules": [raw, V1_SIMPLE_ON], "defaults": {}})

        assert failed == ["bad"], bad
        kept = next(rule for rule in out["rules"] if rule["id"] == "bad")
        assert kept["enabled"] is False, bad
        assert kept["migration_error"] and "settings" in kept["migration_error"]
        assert kept["migration_source"] == raw
        # ...and the OTHER rule in the same store is untouched and schedulable.
        survivor = next(rule for rule in out["rules"] if rule["id"] == "b")
        assert survivor["action"] == "switch.turn_on", bad
        assert survivor.get("migration_error") is None


async def test_a_malformed_store_still_loads_and_the_rest_still_resolves(
    hass, hass_storage
):
    """One store, both malformed fields, through the real `Store` - which is
    where the raise actually escaped from. The SHAPES are swept by the pure
    tests either side of this one; a second `hass` fixture per shape buys
    nothing but seconds off the gate.
    """
    hass_storage["shabbat_scheduler.rules"] = {
        "version": 1, "minor_version": 1, "key": "shabbat_scheduler.rules",
        "data": {
            "rules": [{**V1_CLIMATE_ON, "id": "bad", "settings": "hot"}, V1_SIMPLE_ON],
            "defaults": "everything",
        },
    }
    store = RuleStore(hass)
    await store.async_load()  # used to raise, permanently

    assert store.migration_failures == ["bad"]
    assert {rule.id for rule in store.rules} == {"bad", "b"}
    assert store.defaults == {}
    resolved = resolve_rules(store.rules, _one_day_block(), TZ)
    assert [item.rule.id for item in resolved] == ["b"]


def test_a_malformed_defaults_drops_to_empty_rather_than_refusing_to_start():
    """A truthy non-mapping `defaults` sailed past `or {}` and then
    AttributeError'd inside migrate_v1_defaults.

    There is no rule to disable here, so keep-disable-report has nothing to
    attach to: the defaults drop to empty and the discard is logged. Every
    rule a v1 store could migrate carries its own target already (a v1 rule
    with no devices cannot be migrated at all), so nothing that fires is
    lost - and refusing to start forever is strictly worse.
    """
    for bad in ("everything", ["climate.a"], 5, True, {"devices": 5}):
        out, failed = migrate_v1({"rules": [V1_SIMPLE_ON], "defaults": bad})

        assert out["defaults"] == {}, bad
        assert failed == [], bad
        assert out["rules"][0]["action"] == "switch.turn_on", bad


async def test_a_malformed_v1_store_still_sets_the_config_entry_up(
    hass, hass_storage, jerusalem
):
    """The failure the reviewer actually observed was ConfigEntryState.
    SETUP_ERROR with the store left at version 1 - so no entities, no
    engine, nothing scheduled, on every restart forever."""
    from homeassistant.config_entries import ConfigEntryState
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.shabbat_scheduler.const import DOMAIN

    hass_storage["shabbat_scheduler.rules"] = {
        "version": 1, "minor_version": 1, "key": "shabbat_scheduler.rules",
        "data": {
            "rules": [{**V1_CLIMATE_ON, "settings": "hot"}, V1_SIMPLE_ON],
            "defaults": "everything",
        },
    }
    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert hass_storage["shabbat_scheduler.rules"]["version"] == 2


def test_every_other_coercion_in_the_migration_is_also_total():
    """The same sweep, applied to the remaining `list(...)`/`dict(...)`
    coercions rather than only to the two the review named.

    `script: 5` is the one here that did NOT raise: it migrated
    "successfully" into a target of `{"entity_id": [5]}` and failed at fire
    time instead - the quieter half of the same class."""
    cases = [
        ("devices", 5),
        ("devices", "climate.salon"),
        ("devices", {"climate.salon": True}),
        ("devices", [None]),
        ("variables", "thirty"),
        ("variables", 30),
        ("script", 5),
    ]
    for field, bad in cases:
        source = V1_CUSTOM if field in ("variables", "script") else V1_SIMPLE_ON
        raw = {**source, "id": "bad", field: bad}
        out, failed = migrate_v1({"rules": [raw, V1_OFF], "defaults": {}})

        assert failed == ["bad"], (field, bad)
        kept = next(rule for rule in out["rules"] if rule["id"] == "bad")
        assert kept["enabled"] is False, (field, bad)
        assert kept["migration_source"] == raw
        survivor = next(r for r in out["rules"] if r["id"] == "c")
        assert survivor["action"] == "climate.turn_off", (field, bad)


def test_migrate_v1_survives_a_store_whose_shape_is_nonsense():
    """Belt and braces: whatever else is wrong, this must return."""
    for data in ({"rules": 5}, {"rules": "abc"}, {"defaults": {"devices": 5}}):
        out, failed = migrate_v1(data)
        assert isinstance(out["rules"], list)
        assert isinstance(out["defaults"], dict)


# --- I3: v1's global `settings` were climate-only; v2 defaults are --------
#     domain-blind. Carrying them into `defaults.data` makes block.py's
#     merge_defaults hand `{hvac_mode, temperature}` to switch.turn_on,
#     which Home Assistant rejects at fire time. So they are inlined onto
#     the climate rules that would have read them in v1 instead.


V1_DEFAULTS_CLIMATE = {
    "devices": ["climate.salon"],
    "settings": {"hvac_mode": "cool", "temperature": 24},
}


def test_the_v1_global_settings_do_not_become_domain_blind_v2_defaults():
    out, _ = migrate_v1({"rules": [], "defaults": V1_DEFAULTS_CLIMATE})
    assert out["defaults"] == {"target": {"entity_id": ["climate.salon"]}}
    assert "data" not in out["defaults"]


def test_a_climate_rule_inherits_the_v1_global_settings_onto_its_own_data():
    """v1 read `settings` for climate, so a climate rule with none of its
    own still got the global temperature. Dropping them outright would
    silently turn a set_temperature into a bare turn_on."""
    bare_climate = {
        "id": "x", "profile": 1, "day": "1", "time": "18:00:00", "action": "on",
        "devices": ["climate.salon"],
    }
    out, _ = migrate_v1(
        {"rules": [bare_climate], "defaults": V1_DEFAULTS_CLIMATE}
    )
    assert out["rules"][0]["action"] == "climate.set_temperature"
    assert out["rules"][0]["data"] == {"hvac_mode": "cool", "temperature": 24}


def test_a_rules_own_settings_win_key_by_key_over_the_global_ones():
    out, _ = migrate_v1(
        {"rules": [V1_CLIMATE_ON], "defaults": V1_DEFAULTS_CLIMATE}
    )
    # v1 merged per key, exactly as block.merge_defaults does for `data`.
    assert out["rules"][0]["data"] == {"temperature": 26, "hvac_mode": "cool"}


def test_a_non_climate_rule_never_inherits_the_v1_global_settings():
    out, _ = migrate_v1(
        {"rules": [V1_SIMPLE_ON, V1_OFF, V1_CUSTOM], "defaults": V1_DEFAULTS_CLIMATE}
    )
    by_id = {rule["id"]: rule for rule in out["rules"]}
    assert by_id["b"]["data"] == {}          # switch.turn_on
    assert by_id["c"]["data"] == {}          # climate.turn_off - v1 ignored settings
    assert by_id["d"]["data"] == {"variables": {"minutes": 30}}  # script.turn_on


def test_a_mixed_v1_rule_set_migrates_into_calls_home_assistant_accepts():
    """The reviewer's exact repro, driven through the real schemas Home
    Assistant registers: `switch.turn_on` registers `None`, which becomes
    `cv.make_entity_service_schema(None)` with PREVENT_EXTRA, so an
    inherited `temperature` key is refused outright."""
    import voluptuous as vol
    from homeassistant.components.climate import SET_TEMPERATURE_SCHEMA
    from homeassistant.helpers import config_validation as cv

    from custom_components.shabbat_scheduler.block import merge_defaults
    from custom_components.shabbat_scheduler.device_ops import expand_action

    entity_service = cv.make_entity_service_schema(None)
    schemas = {
        "switch.turn_on": entity_service,
        "switch.turn_off": entity_service,
        "climate.turn_off": entity_service,
        "script.turn_on": cv.make_entity_service_schema({vol.Optional("variables"): dict}),
        "climate.set_temperature": SET_TEMPERATURE_SCHEMA,
        "climate.set_hvac_mode": cv.make_entity_service_schema(
            {vol.Required("hvac_mode"): cv.string}
        ),
        "climate.set_fan_mode": cv.make_entity_service_schema(
            {vol.Required("fan_mode"): cv.string}
        ),
    }

    out, failed = migrate_v1(
        {
            "rules": [V1_CLIMATE_ON, V1_SIMPLE_ON, V1_OFF, V1_CUSTOM],
            "defaults": V1_DEFAULTS_CLIMATE,
        }
    )
    assert failed == []

    for stored in out["rules"]:
        rule = merge_defaults(out["defaults"], rule_from_dict(stored))
        for action, data in expand_action(rule.action, dict(rule.data)):
            payload = {**data, **rule.target}
            # Raises vol.Invalid if HA would refuse the call at fire time.
            schemas[action](payload)


# --- I5: the most consequential case in this migration -------------------
#     v1's own merge_defaults (5192d4c:block.py:61) was
#         devices = rule.devices or tuple(defaults.get("devices", ()))
#     so a v1 rule with no `devices` of its own INHERITED the global ones -
#     and `defaults.devices` existed for exactly that, the shape the v1
#     README documented as the common case. Migrating such a rule as
#     "a rule with no devices has nothing to target" disables THE WHOLE
#     SCHEDULE of anyone who wrote their config the documented way. Not one
#     rule: every rule. Reachable without a hand edit, and far more likely
#     than any malformed input.


V1_DEFAULTS_SWITCH = {"devices": ["switch.boiler"]}
V1_NO_DEVICES_ON = {
    "id": "n1", "profile": 1, "day": "erev", "time": "18:00:00", "action": "on",
}
V1_NO_DEVICES_OFF = {
    "id": "n2", "profile": 1, "day": "1", "time": "23:00:00", "action": "off",
}


def test_a_v1_store_that_kept_its_devices_in_the_defaults_migrates_whole():
    """Every rule ENABLED and schedulable, not one disabled stub."""
    out, failed = migrate_v1(
        {
            "rules": [V1_NO_DEVICES_ON, V1_NO_DEVICES_OFF],
            "defaults": V1_DEFAULTS_SWITCH,
        }
    )

    assert failed == [], "the whole schedule was disabled, silently"
    by_id = {rule["id"]: rule for rule in out["rules"]}
    assert by_id["n1"]["enabled"] is True
    assert by_id["n2"]["enabled"] is True
    assert by_id["n1"]["action"] == "switch.turn_on"
    assert by_id["n2"]["action"] == "switch.turn_off"
    # Explicit, not left to v2's defaults inheritance - see the report.
    assert by_id["n1"]["target"] == {"entity_id": ["switch.boiler"]}
    assert by_id["n2"]["target"] == {"entity_id": ["switch.boiler"]}
    # ...and they actually resolve, which is the thing that failed.
    rules = [rule_from_dict(item) for item in out["rules"]]
    resolved = resolve_rules(rules, _one_day_block(), TZ)
    assert [item.rule.id for item in resolved] == ["n1", "n2"]


def test_a_rules_own_devices_still_win_over_the_shared_ones():
    """v1's `rule.devices or defaults.devices`, per rule, not merged."""
    out, failed = migrate_v1(
        {"rules": [V1_SIMPLE_ON], "defaults": {"devices": ["climate.salon"]}}
    )
    assert failed == []
    assert out["rules"][0]["target"] == {"entity_id": ["switch.boiler"]}
    assert out["rules"][0]["action"] == "switch.turn_on"


def test_an_inherited_climate_default_carries_the_global_settings_too():
    """The I3 rule, applied to the inherited case: v1 read `settings` for a
    climate entity whether the entity came from the rule or the defaults."""
    out, failed = migrate_v1(
        {"rules": [V1_NO_DEVICES_ON], "defaults": V1_DEFAULTS_CLIMATE}
    )
    assert failed == []
    assert out["rules"][0]["action"] == "climate.set_temperature"
    assert out["rules"][0]["target"] == {"entity_id": ["climate.salon"]}
    assert out["rules"][0]["data"] == {"hvac_mode": "cool", "temperature": 24}


def test_an_inherited_default_produces_calls_home_assistant_accepts():
    import voluptuous as vol
    from homeassistant.components.climate import SET_TEMPERATURE_SCHEMA
    from homeassistant.helpers import config_validation as cv

    from custom_components.shabbat_scheduler.block import merge_defaults
    from custom_components.shabbat_scheduler.device_ops import expand_action

    entity_service = cv.make_entity_service_schema(None)
    schemas = {
        "switch.turn_on": entity_service,
        "switch.turn_off": entity_service,
        "climate.turn_off": entity_service,
        "climate.set_temperature": SET_TEMPERATURE_SCHEMA,
        "climate.set_hvac_mode": cv.make_entity_service_schema(
            {vol.Required("hvac_mode"): cv.string}
        ),
    }
    for defaults in (V1_DEFAULTS_SWITCH, V1_DEFAULTS_CLIMATE):
        out, failed = migrate_v1(
            {"rules": [V1_NO_DEVICES_ON, V1_NO_DEVICES_OFF], "defaults": defaults}
        )
        assert failed == [], defaults
        for stored in out["rules"]:
            rule = merge_defaults(out["defaults"], rule_from_dict(stored))
            for action, data in expand_action(rule.action, dict(rule.data)):
                # Raises vol.Invalid if HA would refuse it at fire time.
                schemas[action]({**data, **rule.target})


def test_a_rule_with_neither_its_own_devices_nor_shared_ones_is_still_kept():
    """The fallback is a fallback, not a licence to invent a target."""
    for defaults in ({}, {"devices": []}, {"settings": {"temperature": 24}}):
        out, failed = migrate_v1({"rules": [V1_NO_DEVICES_ON], "defaults": defaults})
        assert failed == ["n1"], defaults
        kept = out["rules"][0]
        assert kept["enabled"] is False
        assert kept["action"] == "shabbat_scheduler.unmigrated"
        assert kept["migration_error"] and "device" in kept["migration_error"]
        assert kept["migration_source"] == V1_NO_DEVICES_ON


def test_shared_default_devices_spanning_several_domains_are_split_too():
    """RE-AIMED in fix round 3, from disabled-with-a-good-message to working.

    Round 2 made this keep-disable-report and pinned that the reason named
    the DEFAULTS rather than the rule, since it hits every inheriting rule
    at once. Round 3 removes the case entirely: v1 drove inherited devices
    through the same per-entity loop as any others (5192d4c:engine.py:104),
    so an inheriting rule spanning two domains WORKED in v1 and now splits
    like any other. Strictly stronger - the old assertion was still
    describing a working v1 rule we had disabled.
    """
    out, failed = migrate_v1(
        {
            "rules": [V1_NO_DEVICES_ON],
            "defaults": {
                "devices": ["climate.salon", "switch.boiler"],
                "settings": {"temperature": 24},
            },
        }
    )
    assert failed == []
    by_id = {rule["id"]: rule for rule in out["rules"]}
    assert set(by_id) == {"n1-climate", "n1-switch"}
    assert by_id["n1-climate"]["action"] == "climate.set_temperature"
    assert by_id["n1-climate"]["data"] == {"temperature": 24}
    assert by_id["n1-switch"]["action"] == "switch.turn_on"
    assert by_id["n1-switch"]["data"] == {}, "v1 ignored settings for switch"
    assert all(rule["enabled"] is True for rule in out["rules"])
    # And both parts stash what the user actually wrote.
    assert by_id["n1-climate"]["migration_source"] == V1_NO_DEVICES_ON
    assert by_id["n1-switch"]["migration_source"] == V1_NO_DEVICES_ON


def test_a_malformed_shared_devices_list_does_not_disable_a_rule_that_has_its_own():
    """A corrupt `defaults.devices` is dropped with a warning (I1); a rule
    carrying its own devices must not care."""
    out, failed = migrate_v1(
        {"rules": [V1_SIMPLE_ON, V1_NO_DEVICES_ON], "defaults": {"devices": 5}}
    )
    assert failed == ["n1"]  # only the one that needed the fallback
    survivor = next(rule for rule in out["rules"] if rule["id"] == "b")
    assert survivor["enabled"] is True
    assert survivor["action"] == "switch.turn_on"


# --- I6: what a VALID, WORKING v1 store did ------------------------------
#     Every case below is cited to v1's own source at 5192d4c. Five rounds
#     of fixes asked "what nonsense can a v1 store contain?"; none asked
#     "what did a working v1 store DO?" - and that is where the two worst
#     defects were. The full enumeration is the table in the report.


V1_MIXED = {
    "id": "e", "profile": 1, "day": "1", "time": "12:00:00", "action": "on",
    "devices": ["climate.salon", "switch.boiler", "climate.bedroom"],
    "settings": {"temperature": 26},
}


def test_a_mixed_domain_rule_worked_in_v1_so_it_becomes_one_rule_per_domain():
    """5192d4c:engine.py:104 looped `for entity_id in rule.devices` and
    5192d4c:device_ops.py:71 re-derived the domain per entity, so this rule
    drove BOTH appliances correctly. Disabling it threw away a working piece
    of someone's schedule."""
    out, failed = migrate_v1({"rules": [V1_MIXED], "defaults": {}})

    assert failed == []
    by_id = {rule["id"]: rule for rule in out["rules"]}
    assert set(by_id) == {"e-climate", "e-switch"}
    # Both entities of the same domain stay on one rule, in v1's order.
    assert by_id["e-climate"]["target"] == {
        "entity_id": ["climate.salon", "climate.bedroom"]
    }
    assert by_id["e-climate"]["action"] == "climate.set_temperature"
    assert by_id["e-climate"]["data"] == {"temperature": 26}
    # ...and the switch part gets the action v1 gave it, with no settings.
    assert by_id["e-switch"]["target"] == {"entity_id": ["switch.boiler"]}
    assert by_id["e-switch"]["action"] == "switch.turn_on"
    assert by_id["e-switch"]["data"] == {}
    # Present AND WORKING, which is stronger than the promise.
    assert all(rule["enabled"] is True for rule in out["rules"])
    # The rule count changed under the user, so both parts say where they
    # came from - the whole original rule, not this part's slice of it.
    assert all(rule["migration_source"] == V1_MIXED for rule in out["rules"])


def test_a_split_rules_ids_are_derived_and_stable_not_random():
    """A re-migration - restoring a .storage backup - must produce the same
    ids, or the rules come back as strangers with new entities."""
    first, _ = migrate_v1({"rules": [V1_MIXED], "defaults": {}})
    second, _ = migrate_v1({"rules": [V1_MIXED], "defaults": {}})
    assert [r["id"] for r in first["rules"]] == ["e-climate", "e-switch"]
    assert [r["id"] for r in first["rules"]] == [r["id"] for r in second["rules"]]


def test_a_split_id_never_lands_on_an_id_the_store_already_uses():
    """A hand-edited store can contain `e-climate` right next to `e`, and
    two rules with the same id break every update and delete by id."""
    squatter = {
        "id": "e-climate", "profile": 1, "day": "1", "time": "09:00:00",
        "action": "on", "devices": ["switch.other"],
    }
    out, failed = migrate_v1({"rules": [V1_MIXED, squatter], "defaults": {}})
    ids = [rule["id"] for rule in out["rules"]]
    assert len(ids) == len(set(ids)), ids
    assert "e-climate-2" in ids
    assert failed == []


def test_the_split_copies_every_rule_level_field_to_both_parts():
    raw = {
        **V1_MIXED, "name": "Evening", "icon": "mdi:x", "color": "red",
        "enabled": True, "replay_on_restart": True,
    }
    out, _ = migrate_v1({"rules": [raw], "defaults": {}})
    for rule in out["rules"]:
        assert rule["name"] == "Evening"
        assert rule["icon"] == "mdi:x"
        assert rule["color"] == "red"
        assert rule["profile"] == 1 and rule["day"] == "1"
        assert rule["time"] == "12:00:00"
        assert rule["replay"] == {"enabled": True}


def test_a_split_rule_produces_calls_home_assistant_accepts():
    import voluptuous as vol
    from homeassistant.components.climate import SET_TEMPERATURE_SCHEMA
    from homeassistant.helpers import config_validation as cv

    from custom_components.shabbat_scheduler.block import merge_defaults
    from custom_components.shabbat_scheduler.device_ops import expand_action

    schemas = {
        "switch.turn_on": cv.make_entity_service_schema(None),
        "climate.set_temperature": SET_TEMPERATURE_SCHEMA,
        "climate.set_hvac_mode": cv.make_entity_service_schema(
            {vol.Required("hvac_mode"): cv.string}
        ),
    }
    out, failed = migrate_v1({"rules": [V1_MIXED], "defaults": {}})
    assert failed == []
    for stored in out["rules"]:
        rule = merge_defaults(out["defaults"], rule_from_dict(stored))
        for action, data in expand_action(rule.action, dict(rule.data)):
            schemas[action]({**data, **rule.target})


def test_a_split_rules_two_parts_are_not_reported_as_a_conflict():
    """Same profile, day and time by construction - but disjoint targets,
    so `find_conflicts` must not warn about a rule conflicting with itself."""
    from custom_components.shabbat_scheduler.block import conflict_warnings

    out, _ = migrate_v1({"rules": [V1_MIXED], "defaults": {}})
    rules = [rule_from_dict(item) for item in out["rules"]]
    warnings = conflict_warnings(
        out["defaults"], rules, lambda target: frozenset(target.get("entity_id", ()))
    )
    assert warnings == []


def test_a_domain_v1_could_not_drive_is_kept_disabled_not_invented():
    """5192d4c:device_ops.py:95-101 returned Skip("unsupported domain") for
    anything outside climate + _SIMPLE_DOMAINS, so v1 made NO call. Inventing
    `lock.turn_on` (which does not exist) or `scene.turn_on` (which does, and
    would start doing something new) are both worse than saying so."""
    for entity_id in ("lock.front", "cover.blinds", "scene.evening", "media_player.tv"):
        raw = {
            "id": "u", "profile": 1, "day": "1", "time": "12:00:00",
            "action": "on", "devices": [entity_id],
        }
        out, failed = migrate_v1({"rules": [raw], "defaults": {}})
        assert failed == ["u"], entity_id
        kept = out["rules"][0]
        assert kept["enabled"] is False
        assert kept["action"] == "shabbat_scheduler.unmigrated"
        reason = kept["migration_error"]
        assert entity_id.split(".")[0] in reason, reason
        assert kept["migration_source"] == raw


def test_every_domain_v1_could_drive_still_migrates():
    """The allow-list must not be so tight it rejects what v1 supported.
    5192d4c:device_ops.py:14 plus the climate branch."""
    for domain in ("switch", "light", "input_boolean", "fan"):
        for action, service in (("on", "turn_on"), ("off", "turn_off")):
            raw = {
                "id": "s", "profile": 1, "day": "1", "time": "12:00:00",
                "action": action, "devices": [f"{domain}.thing"],
            }
            out, failed = migrate_v1({"rules": [raw], "defaults": {}})
            assert failed == [], (domain, action)
            assert out["rules"][0]["action"] == f"{domain}.{service}"


def test_a_split_part_on_a_domain_v1_could_not_drive_fails_alone():
    """Exactly what v1 did: drove the climate entity, skipped the lock. The
    working half must not be lost with the half that never worked."""
    raw = {
        "id": "m", "profile": 1, "day": "1", "time": "12:00:00", "action": "on",
        "devices": ["climate.salon", "lock.front"],
        "settings": {"temperature": 26},
    }
    out, failed = migrate_v1({"rules": [raw], "defaults": {}})

    assert failed == ["m-lock"]
    by_id = {rule["id"]: rule for rule in out["rules"]}
    assert by_id["m-climate"]["enabled"] is True
    assert by_id["m-climate"]["action"] == "climate.set_temperature"
    assert by_id["m-lock"]["enabled"] is False
    assert by_id["m-lock"]["migration_source"] == raw


def test_settings_keys_v1_never_read_are_not_carried_into_the_call():
    """5192d4c:device_ops.py:_plan_climate read hvac_mode, temperature and
    fan_mode. Anything else it IGNORED, and the rule worked. Carrying it
    breaks the rule outright: set_temperature is PREVENT_EXTRA, so the whole
    call - temperature included - is refused at fire time."""
    raw = {
        "id": "k", "profile": 1, "day": "1", "time": "12:00:00", "action": "on",
        "devices": ["climate.salon"],
        "settings": {
            "temperature": 26, "hvac_mode": "cool", "fan_mode": "quiet",
            "swing_mode": "both", "humidity": 40, "target_temp_high": 28,
        },
    }
    out, failed = migrate_v1({"rules": [raw], "defaults": {}})
    assert failed == []
    assert out["rules"][0]["data"] == {
        "temperature": 26, "hvac_mode": "cool", "fan_mode": "quiet",
    }


def test_a_v1_rule_whose_settings_v1_never_read_at_all_still_fires_as_v1_did():
    """Only unrecognised keys: v1 made NO call for this rule, so v2 must not
    invent one - least of all a `climate.set_temperature` HA refuses."""
    raw = {
        "id": "k", "profile": 1, "day": "1", "time": "12:00:00", "action": "on",
        "devices": ["climate.salon"], "settings": {"swing_mode": "both"},
    }
    out, failed = migrate_v1({"rules": [raw], "defaults": {}})
    assert failed == ["k"]
    assert out["rules"][0]["enabled"] is False
    assert out["rules"][0]["migration_source"] == raw


def test_the_surviving_settings_still_produce_calls_home_assistant_accepts():
    import voluptuous as vol
    from homeassistant.components.climate import SET_TEMPERATURE_SCHEMA
    from homeassistant.helpers import config_validation as cv

    from custom_components.shabbat_scheduler.device_ops import expand_action

    schemas = {
        "climate.set_temperature": SET_TEMPERATURE_SCHEMA,
        "climate.set_hvac_mode": cv.make_entity_service_schema(
            {vol.Required("hvac_mode"): cv.string}
        ),
        "climate.set_fan_mode": cv.make_entity_service_schema(
            {vol.Required("fan_mode"): cv.string}
        ),
    }
    raw = {
        "id": "k", "profile": 1, "day": "1", "time": "12:00:00", "action": "on",
        "devices": ["climate.salon"],
        "settings": {"temperature": 26, "swing_mode": "both"},
    }
    out, _ = migrate_v1({"rules": [raw], "defaults": {}})
    rule = rule_from_dict(out["rules"][0])
    for action, data in expand_action(rule.action, dict(rule.data)):
        schemas[action]({**data, **rule.target})


def test_a_climate_on_rule_with_no_settings_anywhere_is_not_invented_into_turn_on():
    """5192d4c:device_ops.py:124-183 - _plan_climate with no hvac_mode,
    temperature or fan_mode appended NO calls, and 5192d4c:engine.py:493-500
    reported `ok` with the state unchanged. So this rule did nothing in v1.
    `climate.turn_on` would start an air conditioner, unattended, on a
    Shabbat, at whatever temperature it was last left at."""
    raw = {
        "id": "z", "profile": 1, "day": "1", "time": "12:00:00", "action": "on",
        "devices": ["climate.salon"],
    }
    out, failed = migrate_v1({"rules": [raw], "defaults": {}})

    assert failed == ["z"]
    kept = out["rules"][0]
    assert kept["enabled"] is False
    assert kept["action"] == "shabbat_scheduler.unmigrated"
    assert "no service call" in kept["migration_error"]
    assert kept["migration_source"] == raw
    # A climate OFF rule with no settings is unaffected: v1 DID call
    # climate.turn_off for it (5192d4c:device_ops.py:111-122).
    out, failed = migrate_v1(
        {"rules": [{**raw, "action": "off"}], "defaults": {}}
    )
    assert failed == []
    assert out["rules"][0]["action"] == "climate.turn_off"


def test_a_custom_rule_ignores_devices_exactly_as_v1_did():
    """5192d4c:engine.py:451-470 - _apply_custom used `rule.script` and
    `rule.variables` and never looked at `devices`. So a custom rule with
    devices must not split, inherit, or grow a target from them."""
    raw = {**V1_CUSTOM, "devices": ["climate.salon", "switch.boiler"]}
    out, failed = migrate_v1(
        {"rules": [raw], "defaults": {"devices": ["light.hall"]}}
    )
    assert failed == []
    assert len(out["rules"]) == 1, "a custom rule must never be split"
    assert out["rules"][0]["action"] == "script.turn_on"
    assert out["rules"][0]["target"] == {"entity_id": ["script.boiler"]}


async def test_both_halves_of_a_split_rule_get_their_own_switch_entity(
    hass, hass_storage, jerusalem, rule_switch_entity_id
):
    """The split changes the rule COUNT, so it changes the entity count. A
    rule switch's unique_id is derived from `rule.id` and its entity_id from
    the rule's NAME - and both parts share the name. "No rule switch had
    been created at all" was a real production bug in this project, so the
    end of the pipeline gets checked rather than assumed.
    """
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.shabbat_scheduler.const import DOMAIN

    hass_storage["shabbat_scheduler.rules"] = {
        "version": 1, "minor_version": 1, "key": "shabbat_scheduler.rules",
        "data": {"rules": [{**V1_MIXED, "name": "Evening"}], "defaults": {}},
    }
    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    store = hass.data[DOMAIN][entry.entry_id]["store"]
    assert {rule.id for rule in store.rules} == {"e-climate", "e-switch"}

    climate_switch = rule_switch_entity_id(entry, "e-climate")
    switch_switch = rule_switch_entity_id(entry, "e-switch")
    assert climate_switch, "the climate half has no switch entity"
    assert switch_switch, "the switch half has no switch entity"
    assert climate_switch != switch_switch, "one entity for two rules"
    # Both enabled, so both are schedulable - the point of splitting.
    assert hass.states.get(climate_switch).state == "on"
    assert hass.states.get(switch_switch).state == "on"


# --- Row 40: v1 gated its three settings keys on the VALUE, not the key ---
#     `hvac_mode = settings.get("hvac_mode")` then `if hvac_mode is not None`
#     (5192d4c:device_ops.py:126, :140, :153 - one per key). Filtering on key
#     membership instead carries a null through into a call HA refuses. And
#     it is reachable from a VALID v1 config: v1 applied no per-key
#     validation to `settings`, so its own rule_from_api and import_yaml
#     both accepted a null.


def _climate_rule(settings):
    return {
        "id": "r", "profile": 1, "day": "1", "time": "12:00:00", "action": "on",
        "devices": ["climate.salon"], "settings": settings,
    }


def test_a_null_settings_value_is_dropped_the_way_v1_dropped_it():
    """v1 made the temperature call and no hvac call at all. v2 emitted
    `climate.set_hvac_mode {hvac_mode: None}`, which HA refuses."""
    for key in ("hvac_mode", "fan_mode"):
        raw = _climate_rule({key: None, "temperature": 24})
        out, failed = migrate_v1({"rules": [raw], "defaults": {}})

        assert failed == [], key
        assert out["rules"][0]["data"] == {"temperature": 24}, key
        assert out["rules"][0]["enabled"] is True


def test_all_null_settings_route_exactly_where_row_16_decided():
    """`{temperature: None}` made NO call in v1, so it is the row-16 case:
    kept, disabled, reported - not a single permanently-failing call. The
    `if not recognised` guard missed it because the dict is not empty."""
    for settings in (
        {"temperature": None},
        {"hvac_mode": None},
        {"fan_mode": None},
        {"hvac_mode": None, "temperature": None, "fan_mode": None},
    ):
        out, failed = migrate_v1({"rules": [_climate_rule(settings)], "defaults": {}})

        assert failed == ["r"], settings
        kept = out["rules"][0]
        assert kept["enabled"] is False
        assert kept["action"] == "shabbat_scheduler.unmigrated"
        assert "no service call" in kept["migration_error"], settings
        assert kept["migration_source"] == _climate_rule(settings)


def test_a_null_reaches_every_inheriting_rule_through_the_shared_settings():
    """The same shape, one level up: a null in `defaults.settings` hits every
    rule that inherits it, so it must be dropped there too."""
    out, failed = migrate_v1(
        {
            "rules": [_climate_rule({"temperature": 24})],
            "defaults": {"settings": {"hvac_mode": None, "fan_mode": "quiet"}},
        }
    )
    assert failed == []
    assert out["rules"][0]["data"] == {"temperature": 24, "fan_mode": "quiet"}


def test_a_rules_explicit_null_still_suppresses_an_inherited_value():
    """v1 merged `{**defaults.settings, **rule.settings}` and THEN checked
    for None, so a rule writing `hvac_mode: null` genuinely turned the
    global one off for itself. The suppression half was already right; what
    was wrong is that the null itself was then carried into the call."""
    out, failed = migrate_v1(
        {
            "rules": [_climate_rule({"hvac_mode": None, "temperature": 26})],
            "defaults": {"settings": {"hvac_mode": "cool", "temperature": 24}},
        }
    )
    assert failed == []
    assert out["rules"][0]["data"] == {"temperature": 26}


def test_a_null_never_reaches_a_call_home_assistant_would_refuse():
    from homeassistant.components.climate import SET_TEMPERATURE_SCHEMA

    from custom_components.shabbat_scheduler.device_ops import expand_action

    raw = _climate_rule({"hvac_mode": None, "temperature": 24})
    out, _ = migrate_v1({"rules": [raw], "defaults": {}})
    rule = rule_from_dict(out["rules"][0])
    calls = expand_action(rule.action, dict(rule.data))
    # One call, not two: there is no mode to set.
    assert [action for action, _ in calls] == ["climate.set_temperature"]
    for _action, data in calls:
        SET_TEMPERATURE_SCHEMA({**data, **rule.target})


# --- Profile bound constant guard -------------------------------------------


def test_the_profile_bound_is_read_from_the_shared_constant():
    """Not a behaviour test - a guard against the bound drifting back
    into six independent literals. If MAX_PROFILE ever changes, this
    module must move with it without being separately edited."""
    from custom_components.shabbat_scheduler.const import MAX_PROFILE, MIN_PROFILE
    from custom_components.shabbat_scheduler.migration import _parses_as_profile

    assert _parses_as_profile(MAX_PROFILE) is True
    assert _parses_as_profile(MAX_PROFILE + 1) is False
    assert _parses_as_profile(MIN_PROFILE) is True
    assert _parses_as_profile(MIN_PROFILE - 1) is False
