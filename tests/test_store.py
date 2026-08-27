from datetime import UTC, datetime, time, timedelta, timezone

from custom_components.shabbat_scheduler.const import STORAGE_KEY, STORAGE_VERSION
from custom_components.shabbat_scheduler.models import EREV, Replay, Rule
from custom_components.shabbat_scheduler.store import (
    RuleStore,
    rule_from_dict,
    rule_to_dict,
)


def test_rule_dict_round_trip():
    rule = Rule(
        id="r1", profile=2, day=EREV, time=time(22, 30),
        action="climate.set_temperature",
        target={"entity_id": ["climate.a"]},
        data={"temperature": 26},
        condition=({"condition": "state", "entity_id": "binary_sensor.gate",
                    "state": "on"},),
        replay=Replay(enabled=True, within=timedelta(hours=2)),
        name="test",
    )
    restored = rule_from_dict(rule_to_dict(rule))
    # Whole-dataclass equality, not a field spot-check: every v2 field is
    # populated above precisely so a serialiser that drops one is caught.
    assert restored == rule
    assert isinstance(restored.action, str)
    assert isinstance(restored.target, dict)
    assert isinstance(restored.condition, tuple)
    assert isinstance(restored.time, time)


async def test_store_starts_empty_and_disabled(hass):
    store = RuleStore(hass)
    await store.async_load()
    assert store.rules == []
    assert store.enabled is False  # master switch defaults OFF


async def test_add_and_persist(hass):
    store = RuleStore(hass)
    await store.async_load()
    rule = Rule(id="r1", profile=1, day="1", time=time(11, 0), action="input_boolean.turn_on")
    await store.async_add(rule)

    reloaded = RuleStore(hass)
    await reloaded.async_load()
    assert [r.id for r in reloaded.rules] == ["r1"]


async def test_update_changes_only_named_fields(hass):
    store = RuleStore(hass)
    await store.async_load()
    await store.async_add(
        Rule(id="r1", profile=1, day="1", time=time(11, 0), action="input_boolean.turn_on")
    )
    await store.async_update("r1", enabled=False)
    assert store.rules[0].enabled is False
    assert store.rules[0].time == time(11, 0)


async def test_delete(hass):
    store = RuleStore(hass)
    await store.async_load()
    await store.async_add(
        Rule(id="r1", profile=1, day="1", time=time(11, 0), action="input_boolean.turn_on")
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
        Rule(id="r1", profile=1, day="1", time=time(11, 0), action="input_boolean.turn_on")
    )
    assert set(_stored(hass_storage)) == {"rules", "defaults", "enabled"}


async def test_a_pre_upgrade_dry_run_key_is_ignored_not_migrated(hass, hass_storage):
    """The key carried no information worth preserving - it is simply
    absent from a freshly-loaded store, never read back out."""
    hass_storage[STORAGE_KEY] = {
        "version": STORAGE_VERSION,
        "key": STORAGE_KEY,
        "data": {
            "rules": [], "defaults": {}, "enabled": True, "dry_run": True,
        },
    }
    store = RuleStore(hass)
    await store.async_load()

    assert store.enabled is True
    assert not hasattr(store, "dry_run") or "dry_run" not in vars(store)


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
                         action="input_boolean.turn_on")
                )
            ],
            "defaults": {"temperature": 26},
            "enabled": True,
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
            "active_block": {"candle_lighting": "not-a-datetime"},
        },
    }
    store = RuleStore(hass)
    await store.async_load()
    assert store.active_block is None
    assert store.enabled is True


# ---- the per-rule outcome map (Task 11) ----
#
# `engine.last_run` is ONE transient value for the whole integration,
# overwritten by the next rule to act, so it can never answer "why did
# *this* rule not fire?" - which is half of the standing constraint (the
# logbook half already holds). These pin the durable, per-rule half.


def _stored_rule(rule_id: str = "r1") -> Rule:
    """A rule whose only interesting property is its id.

    Every outcome test needs the rule to EXIST, because `async_save`
    prunes outcomes whose rule is gone - see
    `test_an_outcome_is_dropped_when_its_rule_is_deleted`.
    """
    return Rule(
        id=rule_id, profile=1, day="1", time=time(11, 0),
        action="input_boolean.turn_on",
    )


_BLOCKED = {
    "outcome": "blocked",
    "at": "2026-08-25T18:00:00+00:00",
    "detail": "condition 1 of 1 (state on input_boolean.kids) not met",
}


async def test_a_rules_last_outcome_survives_a_reload(hass):
    """Transient state cannot answer "why did this not fire?" tomorrow."""
    store = RuleStore(hass)
    await store.async_load()
    await store.async_add(_stored_rule())
    await store.async_record_outcome("r1", _BLOCKED)

    reloaded = RuleStore(hass)
    await reloaded.async_load()
    assert reloaded.last_outcome("r1")["outcome"] == "blocked"
    assert "input_boolean.kids" in reloaded.last_outcome("r1")["detail"]
    assert reloaded.last_outcome("r1")["at"] == "2026-08-25T18:00:00+00:00"


async def test_a_rule_that_never_ran_has_no_outcome(hass):
    """None, not an empty dict: the card renders nothing at all for it."""
    store = RuleStore(hass)
    await store.async_load()
    await store.async_add(_stored_rule())
    assert store.last_outcome("r1") is None
    assert store.last_outcome("never-existed") is None


async def test_a_store_written_before_last_outcome_existed_still_loads(
    hass, hass_storage
):
    """An alpha user's rules survive upgrades.

    A version-2 store with no `last_outcome`/`last_outcomes` key at all -
    the shape every existing install has on disk right now. The rules must
    come back, with no outcome, rather than the load failing. This is why
    STORAGE_VERSION does not move: the key is absent-tolerant, and this is
    the proof rather than the claim.
    """
    hass_storage[STORAGE_KEY] = {
        "version": STORAGE_VERSION,
        "key": STORAGE_KEY,
        "data": {
            "rules": [rule_to_dict(_stored_rule())],
            # Non-default on purpose: a fixture equal to the loader's own
            # defaults would pass against a loader that read nothing.
            "defaults": {"temperature": 26},
            "enabled": True,
        },
    }
    store = RuleStore(hass)
    await store.async_load()

    assert [r.id for r in store.rules] == ["r1"]
    assert store.defaults == {"temperature": 26}
    assert store.enabled is True
    assert store.last_outcome("r1") is None


async def test_a_malformed_outcome_map_is_ignored_not_fatal(hass, hass_storage):
    """A hand-edited .storage must degrade, never stop the integration."""
    hass_storage[STORAGE_KEY] = {
        "version": STORAGE_VERSION,
        "key": STORAGE_KEY,
        "data": {
            "rules": [rule_to_dict(_stored_rule())],
            "defaults": {},
            "enabled": True,
            "last_outcomes": ["not", "a", "map"],
        },
    }
    store = RuleStore(hass)
    await store.async_load()
    assert store.last_outcome("r1") is None
    assert store.enabled is True


async def test_one_rules_outcome_does_not_overwrite_another(hass):
    """The bug this replaces: last_run held ONE result for the whole
    integration, so the next rule to fire erased the previous rule's."""
    store = RuleStore(hass)
    await store.async_load()
    await store.async_replace_all({}, [_stored_rule("r1"), _stored_rule("r2")])
    await store.async_record_outcome("r1", {"outcome": "failed", "at": "x",
                                            "detail": "boom"})
    await store.async_record_outcome("r2", {"outcome": "called", "at": "y",
                                            "detail": None})
    assert store.last_outcome("r1")["outcome"] == "failed"
    assert store.last_outcome("r1")["detail"] == "boom"
    assert store.last_outcome("r2")["outcome"] == "called"


async def test_an_outcome_is_replaced_not_merged(hass):
    """The next verdict for a rule REPLACES the last one.

    Driven where merge and replace differ: the first outcome carries both
    diagnostics, the second carries neither. A merging implementation
    would keep reporting a typo the rule no longer has - i.e. the card
    would go on blaming a misspelling the user already fixed.
    """
    store = RuleStore(hass)
    await store.async_load()
    await store.async_add(_stored_rule())
    await store.async_record_outcome("r1", {
        "outcome": "failed", "at": "x", "detail": "no such entity: light.typo",
        "unknown_targets": ["light.typo"], "no_live_targets": True,
    })
    await store.async_record_outcome(
        "r1", {"outcome": "called", "at": "y", "detail": None}
    )

    outcome = store.last_outcome("r1")
    assert outcome["outcome"] == "called"
    assert outcome["detail"] is None
    assert "unknown_targets" not in outcome
    assert "no_live_targets" not in outcome


async def test_an_outcome_is_dropped_when_its_rule_is_deleted(hass):
    """The map cannot grow without bound on a long-running instance."""
    store = RuleStore(hass)
    await store.async_load()
    await store.async_replace_all({}, [_stored_rule("r1"), _stored_rule("r2")])
    await store.async_record_outcome("r1", _BLOCKED)
    await store.async_record_outcome("r2", _BLOCKED)

    await store.async_delete("r1")

    assert store.last_outcome("r1") is None
    assert store.last_outcome("r2") is not None


async def test_pruning_reaches_the_file_not_just_memory(hass, hass_storage):
    store = RuleStore(hass)
    await store.async_load()
    await store.async_replace_all({}, [_stored_rule("r1"), _stored_rule("r2")])
    await store.async_record_outcome("r1", _BLOCKED)
    await store.async_record_outcome("r2", _BLOCKED)
    assert set(_stored(hass_storage)["last_outcomes"]) == {"r1", "r2"}

    await store.async_replace_all({}, [_stored_rule("r2")])
    assert set(_stored(hass_storage)["last_outcomes"]) == {"r2"}


async def test_a_store_with_no_outcomes_keeps_its_old_shape(hass, hass_storage):
    """Additive: the key appears only once there is something to write.

    Not cosmetic. `test_a_store_without_an_active_block_keeps_its_old_shape`
    pins the same property for `active_block`, for the same reason - a
    store that gains a key on every save is a store whose on-disk shape
    nobody can reason about across versions.
    """
    store = RuleStore(hass)
    await store.async_load()
    await store.async_add(_stored_rule())
    assert "last_outcomes" not in _stored(hass_storage)

    await store.async_record_outcome("r1", _BLOCKED)
    assert "last_outcomes" in _stored(hass_storage)


async def test_recording_an_outcome_does_not_notify_anything(hass):
    """Fire once, never re-assert.

    The store's change listener is `_rules_changed` (__init__.py), which
    RESCHEDULES the engine. Notifying from here would mean every rule that
    fires triggers a refresh from inside its own application - a
    re-evaluation, on the one day nobody can intervene. The card is pushed
    by the engine instead, which cannot re-enter the store.
    """
    store = RuleStore(hass)
    await store.async_load()
    await store.async_add(_stored_rule())
    calls = []
    store.async_set_change_listener(lambda: calls.append(1))

    await store.async_record_outcome("r1", _BLOCKED)
    assert calls == []


async def test_replace_all_swaps_defaults_and_rules(hass):
    store = RuleStore(hass)
    await store.async_load()
    await store.async_replace_all(
        {"temperature": 26},
        [Rule(id="x", profile=3, day="2", time=time(9, 0), action="input_boolean.turn_off")],
    )
    assert store.defaults == {"temperature": 26}
    assert [r.id for r in store.rules] == ["x"]


import pytest


async def test_change_listener_fires_on_add_update_delete(hass):
    store = RuleStore(hass)
    await store.async_load()
    calls = []
    store.async_set_change_listener(lambda: calls.append(1))

    rule = Rule(id="r1", profile=1, day="1", time=time(11, 0), action="input_boolean.turn_on")
    await store.async_add(rule)
    await store.async_update("r1", enabled=False)
    await store.async_delete("r1")
    await store.async_replace_all({}, [rule])

    assert len(calls) == 4


async def test_change_listener_fires_for_enabled(hass):
    """The card renders it, so it must push."""
    store = RuleStore(hass)
    await store.async_load()
    calls = []
    store.async_set_change_listener(lambda: calls.append(1))

    await store.async_set_enabled(True)
    assert len(calls) == 1


async def test_change_listener_does_not_fire_for_active_block(hass):
    """The block in force is engine bookkeeping, not user-visible state."""
    store = RuleStore(hass)
    await store.async_load()
    calls = []
    store.async_set_change_listener(lambda: calls.append(1))

    await store.async_set_active_block(
        datetime(2026, 8, 14, 18, 44, tzinfo=UTC),
        datetime(2026, 8, 15, 20, 1, tzinfo=UTC),
    )
    assert calls == []

    # Clearing must be just as silent. The change listener now reschedules
    # the engine, and clearing runs at the END of a block - so a notify
    # here would fire a refresh from inside a refresh, during Shabbat.
    await store.async_clear_active_block()
    assert calls == []


async def test_update_of_unknown_rule_raises(hass):
    store = RuleStore(hass)
    await store.async_load()
    with pytest.raises(KeyError):
        await store.async_update("nope", enabled=False)
