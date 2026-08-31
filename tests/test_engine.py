import asyncio
import dataclasses
import logging
from datetime import time
from unittest.mock import patch

import pytest
from homeassistant.const import EVENT_CALL_SERVICE
from homeassistant.core import Context, callback
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.shabbat_scheduler.const import (
    EVENT_RULE_APPLIED,
    EVENT_RULE_COMPLETED,
    UNKNOWN_ENTITY_PREFIX,
)
from custom_components.shabbat_scheduler.engine import ShabbatEngine
from custom_components.shabbat_scheduler.models import Replay, Rule
from custom_components.shabbat_scheduler.store import RuleStore

# The v2 idiom, used throughout this file: a rule is an `action`
# ("domain.service") plus a `target` selector, not a v1 `Action` enum plus a
# `devices` tuple plus a climate-shaped `settings` dict. Outcomes changed
# with it - `_call` reports "called" / "failed" / "would_call", never v1's
# "changed" / "ok" / "skipped", because v2 hands the call to
# `async_call_from_config` instead of comparing the entity's current state
# against a desired one it understands.
_ON = "input_boolean.turn_on"
_OFF = "input_boolean.turn_off"


# `engine` and `_rule` are both `tests/conftest.py` fixtures now (moved
# there in Task 10 so `tests/test_execution_domains.py` could use them too,
# without copying either) - see that module for why they are fixtures and
# not importable functions.


async def test_apply_calls_the_rules_action(hass, engine, _rule):
    hass.states.async_set("input_boolean.t", "off")
    results = await engine.async_apply_rule(_rule())
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.t").state == "on"
    assert results[0]["outcome"] == "called"


async def test_a_target_entity_that_does_not_exist_is_reported_as_failed(
    hass, engine, _rule
):
    """Was the CHARACTERISATION TEST for Plan-2 Gap B. Now the fix.

    It used to assert outcome "called", pinning the wrong behaviour on
    purpose so that whoever closed the gap would be told by this test
    failing rather than by nothing at all. That happened in Task 9; this
    is the corrected assertion, kept under the same identity so the
    history of the gap stays attached to the test that pinned it.

    The gap: v1 read each device's state itself, so a typo'd entity id
    came back `failed`. v2 hands the whole target to
    `async_call_from_config`, and Home Assistant's own service layer
    accepts a target naming an entity that does not exist without
    raising - so the engine had nothing to report but success, and a
    misspelt entity id looked exactly like a rule that fired. The engine
    now checks the explicitly named ids first.
    """
    results = await engine.async_apply_rule(_rule(entities=("input_boolean.nope",)))

    assert results[0]["outcome"] == "failed"
    assert results[0]["unknown_targets"] == ["input_boolean.nope"]


async def test_a_target_naming_only_unknown_entities_is_reported_as_failed(
    hass, engine, _rule
):
    """A typo must not look like a rule that fired.

    Home Assistant's service layer accepts a target naming an entity that
    does not exist without raising, so the engine has nothing to report
    but success unless it looks first.
    """
    rule = _rule(
        action=_ON,
        entities=("input_boolean.doe_not_exist",),
    )
    [result] = await engine.async_apply_rule(rule)

    assert result["outcome"] == "failed"
    assert result["unknown_targets"] == ["input_boolean.doe_not_exist"]
    # The last_run sensor and the logbook both read `error`; "failed" with
    # nothing to read is a rule that does not say why it did not fire.
    assert "input_boolean.doe_not_exist" in result["error"]


async def test_a_partly_wrong_target_still_calls_and_still_reports_the_typo(
    hass, engine, _rule
):
    """One typo among three must not suppress the other two."""
    hass.states.async_set("input_boolean.t", "off")
    hass.states.async_set("input_boolean.salon", "off")
    rule = _rule(
        action=_ON,
        entities=(
            "input_boolean.t",
            "input_boolean.nope",
            "input_boolean.salon",
        ),
    )
    [result] = await engine.async_apply_rule(rule)
    await hass.async_block_till_done()

    assert result["outcome"] == "called"
    assert result["unknown_targets"] == ["input_boolean.nope"]
    # The two real entities were genuinely acted on - reporting the typo
    # must not have cost the rest of the target its call.
    assert hass.states.get("input_boolean.t").state == "on"
    assert hass.states.get("input_boolean.salon").state == "on"


async def test_an_area_target_is_not_checked_entity_by_entity(
    hass, engine, area_registry, entity_registry, _rule
):
    """Only ids the USER typed are checked.

    The area here holds a registry entity with NO state - an unloaded or
    unavailable entity, which is an ordinary condition, not a typo. It
    comes out of the registry, so it exists by construction.

    This is the test that fails if the check ever widens from
    `selected.referenced` to `referenced | indirectly_referenced`: the
    wider set contains this stateless entity and would report it as a
    misspelling that the user never made.
    """
    async_mock_service(hass, "input_boolean", "turn_on")
    area = area_registry.async_create("Salon")
    entry = entity_registry.async_get_or_create(
        "input_boolean", "demo", "no-state-yet",
        suggested_object_id="registered_but_stateless",
    )
    entity_registry.async_update_entity(entry.entity_id, area_id=area.id)
    # The premise of the test: indirectly referenced, and stateless.
    assert hass.states.get(entry.entity_id) is None

    rule = dataclasses.replace(
        _rule(action=_ON, entities=()), target={"area_id": [area.id]}
    )
    [result] = await engine.async_apply_rule(rule)

    assert "unknown_targets" not in result
    assert result["outcome"] == "called"


async def test_a_rule_with_no_target_is_unaffected(hass, engine, _rule ):
    """notify.* and friends carry no entity at all."""
    calls = async_mock_service(hass, "notify", "persistent_notification")
    rule = _rule(action="notify.persistent_notification", entities=())
    [result] = await engine.async_apply_rule(rule)

    assert "unknown_targets" not in result
    assert result["outcome"] == "called"
    assert len(calls) == 1


async def test_a_group_member_without_a_state_is_not_a_misspelling(hass, engine, _rule
):
    """A group the USER typed expands to members the user did not type.

    `async_extract_referenced_entity_ids` runs with `expand_group` on, so
    `selected.referenced` is the POST-EXPANSION set: the group's members
    are in it, and the group id the user actually typed is not. Drawing
    the unknown set from there reported a merely-unavailable member as a
    misspelling and downgraded the whole rule to "failed" - even though
    the live member fired. Round-1 review finding.

    This is the same false-positive class the `indirectly_referenced`
    exclusion prevents, arriving through a path that exclusion misses.
    """
    await async_setup_component(
        hass,
        "group",
        {
            "group": {
                "g": {
                    "entities": [
                        "input_boolean.member_a",
                        "input_boolean.member_b",
                    ]
                }
            }
        },
    )
    # One live member, one that exists to the group but has no state -
    # unloaded or unavailable, an entirely ordinary condition.
    hass.states.async_set("input_boolean.member_a", "off")
    await hass.async_block_till_done()
    assert hass.states.get("input_boolean.member_b") is None

    calls = async_mock_service(hass, "input_boolean", "turn_on")
    rule = dataclasses.replace(
        _rule(action=_ON, entities=()), target={"entity_id": ["group.g"]}
    )
    [result] = await engine.async_apply_rule(rule)
    await hass.async_block_till_done()

    assert result["outcome"] == "called"
    assert "unknown_targets" not in result
    assert len(calls) == 1


async def test_a_typo_beside_a_working_area_still_reports_called(
    hass, engine, area_registry, entity_registry, _rule
):
    """Every TYPED id is unknown, yet the rule did something.

    A mixed target's real work can come entirely from a selector that
    names no entity id. Counting only typed ids made this a total miss
    and reported "failed" while the area's entity fired. Round-1 review
    finding.
    """
    area = area_registry.async_create("Salon")
    entry = entity_registry.async_get_or_create(
        "input_boolean", "demo", "lives-in-the-area",
        suggested_object_id="in_the_area",
    )
    entity_registry.async_update_entity(entry.entity_id, area_id=area.id)
    hass.states.async_set(entry.entity_id, "off")

    calls = async_mock_service(hass, "input_boolean", "turn_on")
    rule = dataclasses.replace(
        _rule(action=_ON, entities=()),
        target={"entity_id": ["input_boolean.nope"], "area_id": [area.id]},
    )
    [result] = await engine.async_apply_rule(rule)
    await hass.async_block_till_done()

    # The typo is still reported - it just is not fatal.
    assert result["outcome"] == "called"
    assert result["unknown_targets"] == ["input_boolean.nope"]
    assert len(calls) == 1


async def test_an_existing_group_with_no_live_member_is_not_called_a_typo(
    hass, engine, _rule
):
    """Nothing resolved, but nothing was MISSPELT either.

    The downgrade needs a typo as well as an empty resolution. Without
    that, this rule would report "failed" with an empty list of ids to
    blame - "no such entity: " - which says nothing at all.

    It does not get away with bare success either: it reached nothing, so
    it carries the third diagnostic instead.
    """
    await async_setup_component(
        hass,
        "group",
        {"group": {"g": {"entities": ["input_boolean.gone"]}}},
    )
    await hass.async_block_till_done()
    async_mock_service(hass, "input_boolean", "turn_on")

    rule = dataclasses.replace(
        _rule(action=_ON, entities=()), target={"entity_id": ["group.g"]}
    )
    [result] = await engine.async_apply_rule(rule)

    assert result["outcome"] == "called"
    assert "unknown_targets" not in result
    assert "error" not in result
    assert result["no_live_targets"] is True


async def test_a_call_that_reached_nothing_says_so_rather_than_nothing(
    hass, engine, caplog, _rule
):
    """THE THIRD DIAGNOSTIC. Round-2 review finding.

    A rule that affected nothing must not report success in silence -
    that is the exact shape this integration exists to prevent - but
    `failed` would be wrong too, because nothing is misspelt and the call
    genuinely was made. So there is a third thing to say.

    A leftover `group.x` STATE with no group behind it: it has a state, so
    it is not a typo, and `expand_entity_ids` resolves it to nothing.
    """
    hass.states.async_set("group.leftover", "on")
    calls = async_mock_service(hass, "input_boolean", "turn_on")

    rule = dataclasses.replace(
        _rule(action=_ON, entities=()), target={"entity_id": ["group.leftover"]}
    )
    [result] = await engine.async_apply_rule(rule)

    assert result["outcome"] == "called"
    assert result["no_live_targets"] is True
    assert "unknown_targets" not in result
    assert "error" not in result
    assert len(calls) == 1
    # Reads as "reached nothing", never as a failure: a false failure
    # notification on Shabbat could push someone into intervening by hand.
    assert "nothing can have changed" in caplog.text
    assert "failed" not in caplog.text.lower()


async def test_a_dead_device_id_target_also_says_it_reached_nothing(hass, engine, _rule
):
    """The same silence, arriving through `device_id` instead.

    A device-only target names no entity id, so the unknown-entity check
    has nothing to look at and has always been silent here. The third
    diagnostic covers it for free, without needing to know about devices
    at all, because it asks about the RESOLVED set rather than the typed
    one.
    """
    async_mock_service(hass, "input_boolean", "turn_on")
    rule = dataclasses.replace(
        _rule(action=_ON, entities=()), target={"device_id": ["deadbeef"]}
    )
    [result] = await engine.async_apply_rule(rule)

    assert result["outcome"] == "called"
    assert result["no_live_targets"] is True
    assert "unknown_targets" not in result


async def test_a_misspelt_group_id_is_reported_as_a_typo(hass, engine, _rule ):
    """Where "typed but absent from `referenced`" meets "has no state".

    This is the one input that separates the engine's implementation from
    the `referenced & typed` shape suggested in review, which otherwise
    survives the whole suite. `group.expand_entity_ids` resolves a
    `group.`-prefixed id by reading its STATE; a misspelt one has none, so
    it resolves to nothing and never appears in `selected.referenced`.
    Intersecting with `referenced` therefore finds nothing to report and
    calls this rule a success. Drawing from the typed ids names the typo.
    """
    async_mock_service(hass, "input_boolean", "turn_on")
    rule = dataclasses.replace(
        _rule(action=_ON, entities=()), target={"entity_id": ["group.typo"]}
    )
    [result] = await engine.async_apply_rule(rule)

    assert result["outcome"] == "failed"
    assert result["unknown_targets"] == ["group.typo"]
    assert "group.typo" in result["error"]
    # A misspelling is the more actionable diagnosis, so it is the one
    # reported; the two do not stack on one call.
    assert "no_live_targets" not in result


async def test_a_healthy_call_says_nothing_about_live_targets(hass, engine, _rule ):
    """The diagnostic must be silent when there is nothing to say."""
    hass.states.async_set("input_boolean.t", "off")
    [result] = await engine.async_apply_rule(_rule())
    await hass.async_block_till_done()

    assert result["outcome"] == "called"
    assert "no_live_targets" not in result


async def test_the_all_wildcard_does_not_claim_to_have_reached_nothing(
    hass, engine, _rule
):
    """`entity_id: all` resolves to an EMPTY set and acts on everything.

    HA strips the wildcard before resolving, so the naive reading of the
    resolved set is "reached nothing" while the service layer goes on to
    act on every entity in the domain - the exact inverse of the truth,
    and the fastest way to train the user to ignore these warnings.
    """
    async_mock_service(hass, "input_boolean", "turn_on")
    rule = dataclasses.replace(
        _rule(action=_ON, entities=()), target={"entity_id": "all"}
    )
    [result] = await engine.async_apply_rule(rule)

    assert result["outcome"] == "called"
    assert "no_live_targets" not in result
    assert "unknown_targets" not in result


async def test_a_target_home_assistant_cannot_even_parse_does_not_raise(
    hass, engine, caplog, _rule
):
    """The `except` in `_inspect_target` is reachable, and this reaches it.

    `TargetSelection` puts each selector's values in a `set`, so an
    unhashable one - a dict where a list belongs, which a hand-edited
    YAML import can produce - raises TypeError before any resolution
    happens. That must not pre-empt the call: HA's own validator gives a
    far better diagnosis of this rule a few lines later than anything the
    unknown-target check could add.
    """
    rule = dataclasses.replace(
        _rule(action=_ON, entities=()), target={"entity_id": {"nope": 1}}
    )
    with caplog.at_level(logging.DEBUG, logger="custom_components.shabbat_scheduler.engine"):
        with patch("custom_components.shabbat_scheduler.engine.asyncio.sleep"):
            [result] = await engine.async_apply_rule(rule)

    # Swallowed, logged, and left to Home Assistant to complain about.
    assert "could not resolve target" in caplog.text
    assert "unknown_targets" not in result
    # It still reached the service layer, and failed there on HA's terms.
    assert result["outcome"] == "failed"
    assert UNKNOWN_ENTITY_PREFIX not in result["error"]


async def test_a_bare_string_entity_id_is_one_id_not_eighteen_characters(
    hass, engine, _rule
):
    """Home Assistant accepts `entity_id` as a string or a list.

    An authored rule or an imported YAML rule can carry either, and the
    named-id count is what decides "was EVERY named entity unknown?". A
    bare string iterated without normalising yields its characters, so the
    count would be 18, never 1, and this total miss would report "called".
    """
    rule = dataclasses.replace(
        _rule(action=_ON, entities=()),
        target={"entity_id": "input_boolean.nope"},
    )
    [result] = await engine.async_apply_rule(rule)

    assert result["outcome"] == "failed"
    assert result["unknown_targets"] == ["input_boolean.nope"]


async def test_the_all_wildcard_is_not_reported_as_a_misspelt_entity(hass, engine, _rule
):
    """`entity_id: all` is a wildcard, not an entity id.

    `states.get("all")` is None, so a naive check warns that the rule
    names a nonexistent entity called "all" - a loud complaint about a
    rule that is perfectly fine, and the fastest way to teach the user to
    ignore these warnings.
    """
    async_mock_service(hass, "input_boolean", "turn_on")
    rule = dataclasses.replace(
        _rule(action=_ON, entities=()), target={"entity_id": "all"}
    )
    [result] = await engine.async_apply_rule(rule)

    assert "unknown_targets" not in result
    assert result["outcome"] == "called"


async def test_a_simulated_run_still_reports_an_unknown_target(
    hass, jerusalem, test_booleans, _rule
):
    """A simulated run is where you WANT to find the typo."""
    engine = ShabbatEngine(hass, RuleStore(hass))
    await engine.store.async_load()

    rule = _rule(action=_ON, entities=("input_boolean.nope",))
    [result] = await engine.async_apply_rule(rule, simulate=True)

    assert result["outcome"] == "would_call"
    assert result["unknown_targets"] == ["input_boolean.nope"]


async def test_simulate_makes_no_service_calls(hass, jerusalem, test_booleans, _rule):
    engine = ShabbatEngine(hass, RuleStore(hass))
    await engine.store.async_load()

    hass.states.async_set("input_boolean.t", "off")
    results = await engine.async_apply_rule(_rule(), simulate=True)
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.t").state == "off"
    assert results[0]["outcome"] == "would_call"


async def test_a_simulated_run_still_reports_reaching_nothing_live(hass, engine, _rule):
    """The sibling of test_a_simulated_run_still_reports_an_unknown_target.

    A target that resolves to nothing live (every member of an existing
    group unavailable, say) must still carry the diagnostic under a
    simulated run, exactly as an unknown target already does - a
    simulated run is where you WANT to find out a rule would not have
    done anything real.
    """
    await hass.async_block_till_done()
    hass.states.async_set("group.g", "unknown", {"entity_id": ["input_boolean.member"]})
    rule = _rule(action="input_boolean.turn_on", entities=("group.g",))

    [result] = await engine.async_apply_rule(rule, simulate=True)

    assert result["outcome"] == "would_call"
    assert result["no_live_targets"] is True
    assert "unknown_targets" not in result


async def test_a_rule_can_still_call_a_script(hass, engine, _rule ):
    """v1's `Action.CUSTOM` + `script` field is now just an ordinary action."""
    calls = []

    async def record(call):
        calls.append(call)

    hass.services.async_register("script", "turn_on", record)
    await engine.async_apply_rule(
        _rule(action="script.turn_on", entities=("script.demo",))
    )
    await hass.async_block_till_done()

    assert calls[0].data["entity_id"] == ["script.demo"]


async def test_last_run_is_recorded(hass, engine, _rule ):
    hass.states.async_set("input_boolean.t", "off")
    await engine.async_apply_rule(_rule())
    assert engine.last_run
    # Keyed on the call, not on an entity: one v2 result covers the whole
    # target, which may be an area or a label with no single entity in it.
    assert engine.last_run[0]["action"] == _ON
    assert engine.last_run[0]["target"] == {"entity_id": ["input_boolean.t"]}


async def test_engine_recognises_its_own_context(hass, engine, _rule ):
    """A context the engine issued for a call must later be recognised as ours.

    This is what a future enforcement feature needs to tell "we changed this"
    apart from "a human changed this" - the entire reason for recording
    contexts at all.
    """
    captured = []

    async def record(call):
        captured.append(call)

    hass.services.async_register("input_boolean", "turn_on", record)
    hass.states.async_set("input_boolean.t", "off")

    await engine.async_apply_rule(_rule())
    await hass.async_block_till_done()

    assert captured, "expected the engine to have called input_boolean.turn_on"
    issued_context = captured[0].context

    # No longer keyed per entity - see ShabbatEngine.is_our_context.
    assert engine.is_our_context(issued_context)
    assert not engine.is_our_context(Context())


# --- One expanded call failing must not abort the rest of the rule ---------


async def test_a_later_expanded_call_still_runs_after_an_earlier_one_fails(
    hass, engine
):
    """v1 made one call per device and proved a sibling device survived a
    failure. v2 makes ONE call for the whole target, so the surviving form
    of that property is the climate shim, which is the only thing that
    still turns one authored action into several calls: if
    `climate.set_hvac_mode` fails, `climate.set_temperature` must still be
    attempted rather than the rule aborting half-applied.
    """
    hvac_attempts = []

    async def always_fail(call):
        hvac_attempts.append(call)
        raise RuntimeError("unit did not answer")

    hass.services.async_register("climate", "set_hvac_mode", always_fail)
    temperature = async_mock_service(hass, "climate", "set_temperature")
    # A real target entity, so this test stays about the shim's ordering
    # and not about the unknown-target check (Plan-2 Gap B), which would
    # otherwise report every call here as failed for the wrong reason.
    hass.states.async_set("climate.ac", "off")

    rule = Rule(
        id="r", profile=1, day="1", time=time(11, 0),
        action="climate.set_temperature",
        target={"entity_id": ["climate.ac"]},
        data={"hvac_mode": "cool", "temperature": 22},
    )
    with patch("custom_components.shabbat_scheduler.engine.asyncio.sleep"):
        results = await engine.async_apply_rule(rule)
    await hass.async_block_till_done()

    assert len(hvac_attempts) == 3          # retried, then given up on
    assert len(temperature) == 1            # ...and the next call still ran
    by_action = {r["action"]: r["outcome"] for r in results}
    assert by_action["climate.set_hvac_mode"] == "failed"
    assert by_action["climate.set_temperature"] == "called"


# --- A PROPERTY v2 GAVE UP, recorded rather than left to be discovered -----


async def test_two_rules_on_one_device_at_one_instant_can_interleave(hass, engine):
    """CHARACTERISATION TEST. This records a GUARANTEE v2 NO LONGER MAKES.

    The spec named this exact failure: "the unit left off with a target
    temperature applied - a state matching neither rule." v1 prevented it
    with a lock keyed on `entity_id`, so two rules touching one air
    conditioner at the same minute could not have their calls interleave.
    v1's `test_concurrent_rules_on_same_device_do_not_interleave` proved
    it, and this test stands in that one's place.

    Task 6 re-keyed the lock to `rule.id`, of necessity: a v2 target may
    be an area, a floor or a label, so there is no single entity to key a
    lock on, and a call may carry no entity at all (`notify.*`). The lock
    still stops ONE rule interleaving with a re-entrant application of
    ITSELF. It no longer stops two DIFFERENT rules interleaving with each
    other. See the comment on `ShabbatEngine._locks`.

    What still protects the household is DETECTION, not prevention:
    `block.find_conflicts` reports any two enabled rules at the same
    profile/day/time whose resolved targets overlap, and the card shows
    that as a conflict. The user is told; the engine no longer refuses on
    their behalf. That is the whole of the trade.

    The interleave below is forced deterministically rather than raced
    for: rule A is held inside its first service call while rule B runs
    to completion. Under v1's per-entity lock, B could not have started.
    """
    calls: list[tuple[str, object]] = []
    rule_a_is_inside = asyncio.Event()
    release_rule_a = asyncio.Event()

    async def set_hvac_mode(call):
        mode = call.data.get("hvac_mode")
        calls.append(("hvac_mode", mode))
        if mode == "cool":              # rule A: hold it mid-rule
            rule_a_is_inside.set()
            await release_rule_a.wait()

    async def set_temperature(call):
        calls.append(("temperature", call.data.get("temperature")))

    hass.services.async_register("climate", "set_hvac_mode", set_hvac_mode)
    hass.services.async_register("climate", "set_temperature", set_temperature)

    def _climate_rule(rule_id, hvac_mode, temperature):
        # Each expands, via the climate shim, into set_hvac_mode then
        # set_temperature - the only path in v2 that still turns one
        # authored action into several calls, and so the only place two
        # rules CAN interleave.
        return Rule(
            id=rule_id, profile=1, day="1", time=time(11, 0),
            action="climate.set_temperature",
            target={"entity_id": ["climate.ac"]},
            data={"hvac_mode": hvac_mode, "temperature": temperature},
        )

    task_a = asyncio.create_task(
        engine.async_apply_rule(_climate_rule("a", "cool", 22))
    )
    await rule_a_is_inside.wait()

    # Rule A is suspended inside its FIRST call, holding only its own
    # lock. Rule B runs the whole way through, on the same entity.
    await engine.async_apply_rule(_climate_rule("b", "heat", 24))

    assert calls == [("hvac_mode", "cool"), ("hvac_mode", "heat"),
                     ("temperature", 24)], calls

    release_rule_a.set()
    await task_a
    await hass.async_block_till_done()

    # The damage, spelled out: rule A's temperature lands LAST, after rule
    # B's mode and B's temperature. The unit is left on rule B's hvac_mode
    # carrying rule A's temperature - a state matching NEITHER rule, which
    # is the spec's own words for the outcome v1 existed to prevent.
    assert calls == [("hvac_mode", "cool"), ("hvac_mode", "heat"),
                     ("temperature", 24), ("temperature", 22)], calls


async def test_one_rule_still_cannot_interleave_with_itself(hass, engine):
    """The half of v1's guarantee that DID survive the re-keying.

    `_locks` is keyed on `rule.id`, so a rule applied twice concurrently -
    a timer and a catch-up racing, a manual re-trigger - still runs its
    expanded calls as two complete, uninterrupted sequences. Without this
    the test above would read as "locking was simply removed".
    """
    calls: list[tuple[str, object]] = []
    first_is_inside = asyncio.Event()
    release_first = asyncio.Event()

    async def set_hvac_mode(call):
        calls.append(("hvac_mode", call.data.get("hvac_mode")))
        if not first_is_inside.is_set():
            first_is_inside.set()
            await release_first.wait()

    async def set_temperature(call):
        calls.append(("temperature", call.data.get("temperature")))

    hass.services.async_register("climate", "set_hvac_mode", set_hvac_mode)
    hass.services.async_register("climate", "set_temperature", set_temperature)

    rule = Rule(
        id="same-rule", profile=1, day="1", time=time(11, 0),
        action="climate.set_temperature",
        target={"entity_id": ["climate.ac"]},
        data={"hvac_mode": "cool", "temperature": 22},
    )

    first = asyncio.create_task(engine.async_apply_rule(rule))
    await first_is_inside.wait()
    second = asyncio.create_task(engine.async_apply_rule(rule))

    # The second application is blocked on the SAME lock, so it cannot
    # have reached any service call while the first is still inside one.
    await asyncio.sleep(0)
    assert calls == [("hvac_mode", "cool")], calls

    release_first.set()
    await asyncio.gather(first, second)
    await hass.async_block_till_done()

    # Two whole sequences, never interleaved.
    assert calls == [
        ("hvac_mode", "cool"), ("temperature", 22),
        ("hvac_mode", "cool"), ("temperature", 22),
    ], calls


# --- Task 10: retry on failure ----------------------------------------------


async def test_failed_call_is_retried_then_notified(hass, engine, _rule ):
    # A bare `switch` entity: the switch component is not loaded, so the stub
    # service below is the only handler and can be made to fail on demand.
    hass.states.async_set("switch.t", "off")
    attempts = []

    async def always_fail(call):
        attempts.append(call)
        raise RuntimeError("boom")

    hass.services.async_register("switch", "turn_on", always_fail)

    rule = _rule(action="switch.turn_on", entities=("switch.t",))
    # Patch sleep so the test does not actually wait 60 seconds. It is not
    # merely slow if left alone: any test that also freezes time freezes
    # `time.monotonic()`, which IS the event loop's clock, so this sleep
    # would never return at all. See the `timeout` setting in pyproject.toml.
    with patch("custom_components.shabbat_scheduler.engine.asyncio.sleep"):
        results = await engine.async_apply_rule(rule)

    assert len(attempts) == 3
    assert results[0]["outcome"] == "failed"
    # This HA version's persistent_notification no longer creates entity
    # states (see homeassistant/components/persistent_notification) - it
    # keeps notifications in hass.data instead, so that's what we check.
    assert hass.data.get("persistent_notification")


async def test_retry_succeeds_on_second_attempt(hass, engine, _rule ):
    hass.states.async_set("switch.t", "off")
    attempts = []

    async def fail_once(call):
        attempts.append(call)
        if len(attempts) == 1:
            raise RuntimeError("transient")

    hass.services.async_register("switch", "turn_on", fail_once)

    with patch("custom_components.shabbat_scheduler.engine.asyncio.sleep"):
        results = await engine.async_apply_rule(
            _rule(action="switch.turn_on", entities=("switch.t",))
        )

    assert len(attempts) == 2
    assert results[0]["outcome"] == "called"


from datetime import timedelta

from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.shabbat_scheduler.const import (
    CANDLE_SENSOR,
    EVENT_RULE_APPLIED,
    HAVDALAH_SENSOR,
)


def _set_zmanim(hass, candle: str, havdalah: str):
    hass.states.async_set(CANDLE_SENSOR, candle)
    hass.states.async_set(HAVDALAH_SENSOR, havdalah)


async def test_refresh_computes_the_block(hass, engine):
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.async_refresh()
    assert engine.current_block.length == 1


async def test_missing_sensor_keeps_the_cached_block(hass, engine):
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.async_refresh()

    hass.states.async_remove(CANDLE_SENSOR)
    await engine.async_refresh()
    assert engine.current_block is not None  # cached, not wiped


async def test_no_matching_profile_notifies(hass, engine):
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    # The master must be on, otherwise refresh returns before the check.
    await engine.store.async_set_enabled(True)
    await engine.store.async_add(
        Rule(id="r", profile=3, day="1", time=time(11, 0), action=_ON)
    )
    await engine.async_refresh()

    assert engine.upcoming() == []
    # DEVIATION from the brief (flagged, not silently fixed): this HA
    # version's persistent_notification no longer creates
    # `persistent_notification.*` entity states (see the sibling test
    # `test_failed_call_is_retried_then_notified` above, which already
    # documents this and checks hass.data instead). The brief's literal
    # assertion on hass.states.async_all() would always be empty here, so
    # the notification would never be verified as having fired. Using the
    # same hass.data check already established in this file.
    assert hass.data.get("persistent_notification")


async def test_disabled_master_schedules_nothing(hass, engine):
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_add(
        Rule(id="r", profile=1, day="1", time=time(11, 0),
             action=_ON, target={"entity_id": ["input_boolean.t"]})
    )
    await engine.async_refresh()  # master defaults OFF
    assert engine.upcoming() == []


@pytest.mark.parametrize("expected_lingering_timers", [True])
# DEVIATION from the brief (flagged, not silently fixed): once time is
# frozen (see below) `async_refresh` schedules a genuine
# `async_track_point_in_time` callback ~23h out for the rule's `when`. That
# handle is still pending at test teardown, which
# pytest-homeassistant-custom-component's `verify_cleanup` fixture treats as
# a hard failure ("Lingering timer") outside tests/components/*. This is a
# real, scheduling-only test - nothing in it fires or cancels the timer - so
# the framework's own documented escape hatch applies (see
# `expected_lingering_timers` in pytest_homeassistant_custom_component's
# plugins.py).
async def test_enabled_master_lists_upcoming_rules(hass, engine, freezer):
    # DEVIATION from the brief (flagged, not silently fixed): async_refresh
    # filters to `item.when > now` using the real wall clock, and the
    # brief's fixed zmanim literals place day 1 at 2026-08-15T11:00
    # Asia/Jerusalem. That instant is now in the past relative to the
    # machine's real clock, so without freezing time this test would fail
    # for a reason unrelated to the code under test - it is time-bombed as
    # written. Freezing to a moment before the block keeps the brief's exact
    # zmanim literals unchanged while restoring the comparison it depends on.
    freezer.move_to("2026-08-14T12:00:00+03:00")
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    await engine.store.async_add(
        Rule(id="r", profile=1, day="1", time=time(11, 0),
             action=_ON, target={"entity_id": ["input_boolean.t"]})
    )
    await engine.async_refresh()
    assert [item.rule.id for item in engine.upcoming()] == ["r"]


# --- Fix round 1: implausible zmanim must notify, not fail silently -------


async def test_implausible_zmanim_notifies_and_schedules_nothing(hass, engine):
    """havdalah at/before candle lighting must surface a notification.

    The no-matching-profile silent-failure path already raises a
    persistent_notification; this path (compute_block's ValueError) must
    be equally loud, not just logged.
    """
    # havdalah BEFORE candle lighting - implausible per compute_block.
    _set_zmanim(hass, "2026-08-15T17:01:00+00:00", "2026-08-14T15:44:00+00:00")
    await engine.store.async_set_enabled(True)
    await engine.store.async_add(
        Rule(id="r", profile=1, day="1", time=time(11, 0),
             action=_ON, target={"entity_id": ["input_boolean.t"]})
    )
    await engine.async_refresh()

    assert engine.upcoming() == []
    assert hass.data.get("persistent_notification")


# --- Task 12: restart catch-up ---------------------------------------------

from freezegun import freeze_time


# DEVIATION from the brief (flagged, not silently fixed): the brief's three
# catch-up tests never call `engine.async_refresh()`, but `async_catch_up`
# reads `self._block`, which starts as None and is only ever populated by
# `async_refresh()` (see its assignment from `compute_block(*zmanim)`). As
# written, every one of the brief's tests would exercise nothing but the
# `self._block is None` early-return - test 1 would then fail outright
# (asserting "on" while the device never gets touched) and tests 2-3 would
# pass, but only vacuously, for the wrong reason. In real use,
# `async_setup_entry` calls `async_refresh()` before `async_catch_up()` so
# `_block` is already populated by the time catch-up runs; these tests add
# that same call to match. `async_refresh()` is called outside `freeze_time`
# since block computation only reads the zmanim sensors, never the clock.
#
# v2 NOTE for this whole section: catch-up is now OPT-IN per rule
# (`replay.enabled`) rather than a desired-state comparison the engine
# derives for itself, so every rule below that is expected to replay says
# so. "custom rule" in the names below means what v1 called
# `Action.CUSTOM` + a `script` field, which in v2 is just an ordinary
# `script.turn_on` action - the property each test pins is unchanged.
async def test_catch_up_applies_the_last_passed_rule(hass, engine):
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    hass.states.async_set("input_boolean.t", "off")
    await engine.store.async_replace_all({}, [
        Rule(id="on", profile=1, day="1", time=time(11, 0),
             action=_ON, target={"entity_id": ["input_boolean.t"]},
             replay=Replay(enabled=True)),
        Rule(id="off", profile=1, day="1", time=time(18, 0),
             action=_OFF, target={"entity_id": ["input_boolean.t"]},
             replay=Replay(enabled=True)),
    ])
    await engine.async_refresh()

    # 11:30 local - the 11:00 ON has passed, 18:00 OFF has not.
    with freeze_time("2026-08-15T08:30:00+00:00"):
        results = await engine.async_catch_up()
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.t").state == "on"
    assert [r["outcome"] for r in results] == ["called"]


async def test_catch_up_before_any_rule_does_nothing(hass, engine):
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    hass.states.async_set("input_boolean.t", "off")
    await engine.store.async_replace_all({}, [
        Rule(id="on", profile=1, day="1", time=time(11, 0),
             action=_ON, target={"entity_id": ["input_boolean.t"]}),
    ])
    await engine.async_refresh()

    with freeze_time("2026-08-15T06:00:00+00:00"):  # 09:00 local
        assert await engine.async_catch_up() == []


async def test_catch_up_skips_custom_rules_by_default(hass, engine):
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    calls = []

    async def record(call):
        calls.append(call)

    hass.services.async_register("script", "turn_on", record)
    await engine.store.async_replace_all({}, [
        Rule(id="c", profile=1, day="1", time=time(11, 0),
             action="script.turn_on",
             target={"entity_id": ["script.demo"]}),
    ])
    await engine.async_refresh()

    with freeze_time("2026-08-15T08:30:00+00:00"):
        await engine.async_catch_up()
    await hass.async_block_till_done()
    assert calls == []


# --- Fix round 1: custom replay must be gated by resolve_rules, not free --


async def test_catch_up_replays_a_passed_replay_on_restart_custom_rule(hass, engine):
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    calls = []

    async def record(call):
        calls.append(call)

    hass.services.async_register("script", "turn_on", record)
    await engine.store.async_replace_all({}, [
        Rule(id="c", profile=1, day="1", time=time(11, 0),
             action="script.turn_on",
             target={"entity_id": ["script.demo"]},
             replay=Replay(enabled=True)),
    ])
    await engine.async_refresh()

    # 11:30 local - the 11:00 custom rule has passed.
    with freeze_time("2026-08-15T08:30:00+00:00"):
        await engine.async_catch_up()
    await hass.async_block_till_done()
    assert len(calls) == 1


async def test_catch_up_does_not_replay_a_custom_rule_that_has_not_passed(hass, engine):
    # Regression test for the bug the coordinator's round-1 review caught:
    # the original implementation looped over the unfiltered rule list and
    # replayed every opted-in rule unconditionally,
    # firing scripts scheduled for later the same day immediately on
    # restart. Confirmed to fail against the pre-fix code (calls == 1).
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    calls = []

    async def record(call):
        calls.append(call)

    hass.services.async_register("script", "turn_on", record)
    await engine.store.async_replace_all({}, [
        Rule(id="c", profile=1, day="1", time=time(18, 0),
             action="script.turn_on",
             target={"entity_id": ["script.demo"]},
             replay=Replay(enabled=True)),
    ])
    await engine.async_refresh()

    # 11:30 local - the 18:00 custom rule has NOT passed yet.
    with freeze_time("2026-08-15T08:30:00+00:00"):
        await engine.async_catch_up()
    await hass.async_block_till_done()
    assert calls == []


async def test_catch_up_does_not_replay_a_disabled_custom_rule(hass, engine):
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    calls = []

    async def record(call):
        calls.append(call)

    hass.services.async_register("script", "turn_on", record)
    await engine.store.async_replace_all({}, [
        Rule(id="c", profile=1, day="1", time=time(11, 0),
             action="script.turn_on",
             target={"entity_id": ["script.demo"]},
             replay=Replay(enabled=True), enabled=False),
    ])
    await engine.async_refresh()

    with freeze_time("2026-08-15T08:30:00+00:00"):
        await engine.async_catch_up()
    await hass.async_block_till_done()
    assert calls == []


async def test_catch_up_on_a_conflicting_pair_applies_both_in_order(hass, engine):
    """DELIBERATE v2 CHANGE, pinned here rather than left to be discovered.

    v1's catch-up asked `block.desired_state_at` what state each device
    should be in, and when two rules at the same moment gave contradictory
    answers it DECLINED to act - `results == []`, the device untouched.
    `desired_state_at` is gone (Task 8; test_replay.py asserts its
    absence), because an opaque service call has no queryable desired
    state to compare. So catch-up no longer arbitrates: it replays every
    opted-in passed rule in time order, and for a same-moment pair the
    LAST one applied wins.

    That is not a silent loss - `find_conflicts` still reports this pair
    as a conflict over the websocket, which is where the user is told.
    But the engine no longer refuses on their behalf, and this test says
    so out loud so nobody reads v1's docstring and believes otherwise.
    """
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    hass.states.async_set("input_boolean.t", "off")
    await engine.store.async_replace_all({}, [
        Rule(id="on", profile=1, day="1", time=time(11, 0),
             action=_ON, target={"entity_id": ["input_boolean.t"]},
             replay=Replay(enabled=True)),
        Rule(id="off-same-time", profile=1, day="1", time=time(11, 0),
             action=_OFF, target={"entity_id": ["input_boolean.t"]},
             replay=Replay(enabled=True)),
    ])
    await engine.async_refresh()

    with freeze_time("2026-08-15T08:30:00+00:00"):
        results = await engine.async_catch_up()
    await hass.async_block_till_done()

    assert [r["outcome"] for r in results] == ["called", "called"]
    # Both ran; the schedule's own order decided the outcome, not the engine.
    assert hass.states.get("input_boolean.t").state == "off"


# --- Final review C1: a rolled-forward zmanim pair must not cancel the -----
# --- remaining rules of the block that is still in force -------------------

from datetime import date


# The hold now arms a release timer (NEW-1) for `tail + 1s`; this test stops
# at the tail itself, so that timer is legitimately still pending at teardown.
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_rolled_forward_zmanim_keep_the_current_blocks_tail(
    hass, engine, freezer
):
    """At havdalah jewish_calendar advances to NEXT week - mid-block.

    Both zmanim sensors jump to the following occurrence the moment
    `now >= havdalah`, which fires the state listener and refreshes. If the
    engine adopted that candidate block it would cancel every still-pending
    timer of the block actually in force, so a deliberately post-havdalah
    rule ("23:00 turn everything off on the last day") would never fire and
    the AC would run all night with nothing in the log.
    """
    freezer.move_to("2026-08-15T05:00:00+00:00")
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    hass.states.async_set("input_boolean.t", "on")
    await engine.store.async_replace_all({}, [
        Rule(id="late-off", profile=1, day="1", time=time(23, 0),
             action=_OFF, target={"entity_id": ["input_boolean.t"]}),
    ])
    await engine.async_refresh()
    assert [item.rule.id for item in engine.upcoming()] == ["late-off"]

    # Havdalah passes (20:01 local); the sensors roll forward to next week.
    freezer.move_to("2026-08-15T17:01:30+00:00")
    _set_zmanim(hass, "2026-08-21T15:36:00+00:00", "2026-08-22T16:53:00+00:00")
    await engine.async_refresh()

    assert engine.current_block.erev_date == date(2026, 8, 14)
    assert [item.rule.id for item in engine.upcoming()] == ["late-off"]

    # 23:00 Asia/Jerusalem == 20:00 UTC.
    async_fire_time_changed(
        hass, dt_util.parse_datetime("2026-08-15T20:00:00+00:00")
    )
    await hass.async_block_till_done()
    assert hass.states.get("input_boolean.t").state == "off"


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_next_block_is_adopted_once_the_tail_has_passed(hass, engine, freezer ):
    """The hold is only until the current block's last rule is spent."""
    freezer.move_to("2026-08-15T05:00:00+00:00")
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    await engine.store.async_replace_all({}, [
        Rule(id="late-off", profile=1, day="1", time=time(23, 0),
             action=_OFF, target={"entity_id": ["input_boolean.t"]}),
    ])
    await engine.async_refresh()
    assert engine.current_block.erev_date == date(2026, 8, 14)

    # Sunday morning: the 23:00 tail is long gone.
    freezer.move_to("2026-08-16T05:00:00+00:00")
    _set_zmanim(hass, "2026-08-21T15:36:00+00:00", "2026-08-22T16:53:00+00:00")
    await engine.async_refresh()

    assert engine.current_block.erev_date == date(2026, 8, 21)
    assert [item.rule.id for item in engine.upcoming()] == ["late-off"]


# --- Re-review NEW-1: the hold must RELEASE ITSELF once the tail is spent --


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_the_hold_releases_itself_and_arms_the_next_block(hass, engine, freezer ):
    """Holding the block is only half the fix; letting go is the other half.

    Nothing else can release it. After havdalah the jewish_calendar sensors
    hold NEXT week's values and do not change again until the next havdalah,
    and HA fires EVENT_STATE_REPORTED (not state_changed) when a state is
    re-published identically - so the zmanim listener never runs. The tail
    rule fires on its own timer and async_apply_rule does not refresh. If
    the hold does not expire by itself, `_block` stays a week old with no
    timers for the block that is actually coming, and the WHOLE of the next
    Shabbat is silently skipped.
    """
    freezer.move_to("2026-08-15T05:00:00+00:00")
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    hass.states.async_set("input_boolean.t", "on")
    await engine.store.async_replace_all({}, [
        Rule(id="morning-on", profile=1, day="1", time=time(9, 0),
             action=_ON, target={"entity_id": ["input_boolean.t"]}),
        Rule(id="late-off", profile=1, day="1", time=time(23, 0),
             action=_OFF, target={"entity_id": ["input_boolean.t"]}),
    ])
    await engine.async_refresh()
    assert engine.current_block.erev_date == date(2026, 8, 14)

    # 20:01:30 local - havdalah has just passed and the sensors rolled
    # forward, so the listener refreshes and the hold must engage.
    freezer.move_to("2026-08-15T17:01:30+00:00")
    _set_zmanim(hass, "2026-08-21T15:36:00+00:00", "2026-08-22T16:53:00+00:00")
    await engine.async_refresh()
    assert engine.current_block.erev_date == date(2026, 8, 14)
    assert [item.rule.id for item in engine.upcoming()] == ["late-off"]

    # 23:00 local - the tail fires on its own timer, nothing else happens.
    freezer.move_to("2026-08-15T20:00:00+00:00")
    async_fire_time_changed(
        hass, dt_util.parse_datetime("2026-08-15T20:00:00+00:00")
    )
    await hass.async_block_till_done()
    assert hass.states.get("input_boolean.t").state == "off"

    # Moments later the hold is protecting nothing and must let go on its
    # own - no restart, no switch toggle, no YAML import, no state change.
    freezer.move_to("2026-08-15T20:00:05+00:00")
    async_fire_time_changed(
        hass, dt_util.parse_datetime("2026-08-15T20:00:01+00:00")
    )
    await hass.async_block_till_done()

    assert engine.current_block.erev_date == date(2026, 8, 21)
    assert [item.rule.id for item in engine.upcoming()] == [
        "morning-on", "late-off"
    ]

    # ...and the next Shabbat genuinely happens: 09:00 local on 22 Aug.
    async_fire_time_changed(
        hass, dt_util.parse_datetime("2026-08-22T06:00:00+00:00")
    )
    await hass.async_block_till_done()
    assert hass.states.get("input_boolean.t").state == "on"


# --- Re-review: the hold must survive a restart inside its own window -----


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_a_restart_inside_the_hold_still_fires_the_pending_tail(
    hass, jerusalem, test_booleans, freezer
):
    """A restart between havdalah and the tail used to lose the tail rule.

    The hold lives only in memory. Restart HA at 21:00 with a 23:00 rule
    still pending and `_block` starts as None, so setup reads the
    already-rolled-forward sensors, adopts NEXT week's block, and catch-up
    against a wholly-future block does nothing. The 23:00 OFF never fires
    and the air conditioner runs the night, silently. The block in force
    therefore has to outlive the process.
    """
    freezer.move_to("2026-08-15T05:00:00+00:00")
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")

    store = RuleStore(hass)
    await store.async_load()
    await store.async_set_enabled(True)
    await store.async_replace_all({}, [
        Rule(id="late-off", profile=1, day="1", time=time(23, 0),
             action=_OFF, target={"entity_id": ["input_boolean.t"]}),
    ])
    engine = ShabbatEngine(hass, store)
    hass.states.async_set("input_boolean.t", "on")
    await engine.async_refresh()
    assert engine.current_block.erev_date == date(2026, 8, 14)

    # 20:01:30 local - havdalah passes, the sensors roll forward, the hold
    # engages on the 14 Aug block.
    freezer.move_to("2026-08-15T17:01:30+00:00")
    _set_zmanim(hass, "2026-08-21T15:36:00+00:00", "2026-08-22T16:53:00+00:00")
    await engine.async_refresh()
    assert engine.current_block.erev_date == date(2026, 8, 14)

    # 21:00 local - Home Assistant restarts. Every timer and all in-memory
    # state is gone; only .storage survives, and the sensors read next week.
    freezer.move_to("2026-08-15T18:00:00+00:00")
    await engine.async_shutdown()

    restarted_store = RuleStore(hass)
    await restarted_store.async_load()
    restarted = ShabbatEngine(hass, restarted_store)
    await restarted.async_refresh()

    assert restarted.current_block.erev_date == date(2026, 8, 14)
    assert [item.rule.id for item in restarted.upcoming()] == ["late-off"]

    # 23:00 local - the rule the restart nearly ate.
    freezer.move_to("2026-08-15T20:00:00+00:00")
    async_fire_time_changed(
        hass, dt_util.parse_datetime("2026-08-15T20:00:00+00:00")
    )
    await hass.async_block_till_done()
    assert hass.states.get("input_boolean.t").state == "off"


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_a_restart_after_the_tail_adopts_the_next_block(
    hass, jerusalem, test_booleans, freezer
):
    """The persisted block must not pin the engine to a spent block."""
    freezer.move_to("2026-08-15T05:00:00+00:00")
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")

    store = RuleStore(hass)
    await store.async_load()
    await store.async_set_enabled(True)
    await store.async_replace_all({}, [
        Rule(id="late-off", profile=1, day="1", time=time(23, 0),
             action=_OFF, target={"entity_id": ["input_boolean.t"]}),
    ])
    engine = ShabbatEngine(hass, store)
    await engine.async_refresh()
    assert store.active_block is not None
    await engine.async_shutdown()

    # Tuesday: the 14 Aug block's tail is days gone.
    freezer.move_to("2026-08-18T05:00:00+00:00")
    _set_zmanim(hass, "2026-08-21T15:36:00+00:00", "2026-08-22T16:53:00+00:00")
    restarted_store = RuleStore(hass)
    await restarted_store.async_load()
    restarted = ShabbatEngine(hass, restarted_store)
    await restarted.async_refresh()

    assert restarted.current_block.erev_date == date(2026, 8, 21)
    # ...and the spent block is not left lying in .storage forever.
    assert restarted_store.active_block == (
        restarted.current_block.candle_lighting,
        restarted.current_block.havdalah,
    )


async def test_concurrent_refreshes_do_not_double_up_timers(hass, engine, freezer ):
    """Persisting the block introduces an await mid-refresh.

    Both zmanim sensors change at the same instant, so two `_zmanim_changed`
    tasks - two `async_refresh` calls - can genuinely overlap. If the second
    starts while the first is inside that await, it cancels nothing (the
    first already cancelled every timer) and both then append their own set,
    so every rule of the block fires twice.
    """
    freezer.move_to("2026-08-15T05:00:00+00:00")
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    hass.states.async_set("input_boolean.t", "on")
    await engine.store.async_replace_all({}, [
        Rule(id="off", profile=1, day="1", time=time(11, 0),
             action=_OFF, target={"entity_id": ["input_boolean.t"]}),
    ])

    fired = []
    hass.bus.async_listen(EVENT_RULE_APPLIED, lambda event: fired.append(event))

    real_save = RuleStore.async_save

    async def yielding_save(self):
        # The mocked .storage in this test harness writes to a dict without
        # ever yielding to the loop, so the overlap this test is about
        # cannot occur unless the executor hop a real Store.async_save
        # performs is put back.
        await asyncio.sleep(0)
        await real_save(self)

    with patch.object(RuleStore, "async_save", yielding_save):
        await asyncio.gather(engine.async_refresh(), engine.async_refresh())

    freezer.move_to("2026-08-15T08:00:00+00:00")
    async_fire_time_changed(
        hass, dt_util.parse_datetime("2026-08-15T08:00:00+00:00")
    )
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.t").state == "off"
    assert len(fired) == 1


# --- Final review I1: block dates must be derived in the LOCAL timezone ----


async def test_block_dates_follow_the_local_timezone_not_utc(hass, test_booleans):
    """HA serialises timestamp sensors as UTC; the dates must still be local.

    Israel hides this bug (evening local == same UTC date), so the test uses
    a timezone west of UTC where the two genuinely differ.
    """
    await hass.config.async_set_time_zone("America/New_York")
    store = RuleStore(hass)
    await store.async_load()
    engine = ShabbatEngine(hass, store)

    # 20:44 local on Friday 14 Aug is 00:44 UTC on Saturday 15 Aug.
    _set_zmanim(hass, "2026-08-15T00:44:00+00:00", "2026-08-16T00:53:00+00:00")
    await engine.async_refresh()

    assert engine.current_block.erev_date == date(2026, 8, 14)
    assert engine.current_block.day_dates == (date(2026, 8, 15),)
    assert engine.current_block.length == 1


# --- Final review I5: unreadable zmanim sensors must not fail silently -----


async def test_unreadable_zmanim_with_no_cached_block_notifies(hass, engine):
    """A renamed/missing jewish_calendar entity used to be wholly silent."""
    await engine.store.async_set_enabled(True)
    await engine.async_refresh()

    assert engine.current_block is None
    assert "shabbat_scheduler_zmanim" in hass.data["persistent_notification"]
    message = hass.data["persistent_notification"]["shabbat_scheduler_zmanim"][
        "message"
    ]
    assert CANDLE_SENSOR in message
    assert HAVDALAH_SENSOR in message


async def test_unreadable_zmanim_is_quiet_when_a_block_is_cached(hass, engine):
    """The cached-block path is correctly quiet - it must stay that way."""
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.async_refresh()
    hass.states.async_remove(CANDLE_SENSOR)
    await engine.async_refresh()

    assert engine.current_block is not None
    assert "shabbat_scheduler_zmanim" not in hass.data.get(
        "persistent_notification", {}
    )


async def test_zmanim_notification_is_dismissed_once_readable(hass, engine):
    await engine.async_refresh()
    assert "shabbat_scheduler_zmanim" in hass.data["persistent_notification"]

    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.async_refresh()
    assert "shabbat_scheduler_zmanim" not in hass.data["persistent_notification"]


# --- Final review I2/I3: nothing may be dropped in silence ----------------


async def test_an_unsupported_domain_is_no_longer_a_thing(hass, engine, _rule ):
    """v1's `cover.` test, inverted: the limitation it guarded is GONE.

    v1 could only drive four domains and reported `skipped` for anything
    else; the risk was that it reported OK instead. v2 hands every action
    to `async_call_from_config`, so a cover rule is an ordinary rule and
    must actually make the call - there is no allow-list left to fall off.
    """
    calls = async_mock_service(hass, "cover", "close_cover")
    # A real target entity: this test is about the allow-list being gone,
    # not about the unknown-target check (Plan-2 Gap B).
    hass.states.async_set("cover.a", "open")
    results = await engine.async_apply_rule(
        _rule(action="cover.close_cover", entities=("cover.a",))
    )
    await hass.async_block_till_done()

    assert [item["outcome"] for item in results] == ["called"]
    assert len(calls) == 1


async def test_a_value_home_assistant_rejects_is_reported_failed_not_called(
    hass, engine, caplog, _rule
):
    """The successor to v1's unsupported-fan-mode test.

    v1 knew climate's `fan_modes` attribute itself and reported `skipped`
    for a mode the unit did not have. v2 knows nothing about climate, so
    the guarantee has to come from Home Assistant's own service
    validation - and the thing that must not happen is unchanged: a value
    the unit cannot accept must never come back as if the rule fired.
    """
    hass.states.async_set(
        "climate.ac", "cool",
        {"fan_modes": ["auto", "high"], "fan_mode": "auto",
         "supported_features": 8},
    )

    async def reject(_call):
        raise ValueError("Fan mode quiet is not valid")

    hass.services.async_register("climate", "set_fan_mode", reject)

    with patch("custom_components.shabbat_scheduler.engine.asyncio.sleep"):
        results = await engine.async_apply_rule(
            _rule(action="climate.set_fan_mode", entities=("climate.ac",),
                  data={"fan_mode": "quiet"})
        )

    assert [item["outcome"] for item in results] == ["failed"]
    assert "quiet" in results[0]["error"]
    assert "quiet" in caplog.text


# --- Final review I4: a failure must record WHY --------------------------


async def test_failure_records_the_exception_and_a_reason(hass, engine, caplog, _rule ):
    """The log line and the notification are the only forensic surface.

    On a Shabbat night nobody can investigate live; "failed after 3 attempts"
    cannot distinguish a missing service from a timeout from a cloud auth
    error.
    """
    hass.states.async_set("switch.t", "off")

    async def always_fail(_call):
        raise RuntimeError("cloud auth expired")

    hass.services.async_register("switch", "turn_on", always_fail)

    with patch("custom_components.shabbat_scheduler.engine.asyncio.sleep"):
        results = await engine.async_apply_rule(
            _rule(action="switch.turn_on", entities=("switch.t",))
        )

    assert results[0]["outcome"] == "failed"
    # v1 called this key `reason`; v2's `_call` calls it `error`. It still
    # carries the TYPE as well as the message - an HA exception that
    # stringifies to "" would otherwise leave a `failed` result saying
    # nothing at all about why.
    assert "cloud auth expired" in results[0]["error"]
    assert "RuntimeError" in results[0]["error"]

    message = next(iter(hass.data["persistent_notification"].values()))["message"]
    assert "cloud auth expired" in message
    assert "RuntimeError" in message

    assert "cloud auth expired" in caplog.text
    assert "Traceback" in caplog.text  # exc_info on the final failure


# --- Final review minor: an all-disabled profile must notify --------------


async def test_all_disabled_rules_notify_like_a_missing_profile(hass, engine):
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    await engine.store.async_replace_all({}, [
        Rule(id="r", profile=1, day="1", time=time(11, 0), action=_ON,
             target={"entity_id": ["input_boolean.t"]}, enabled=False),
    ])
    await engine.async_refresh()

    assert engine.upcoming() == []
    assert "shabbat_scheduler_no_profile" in hass.data["persistent_notification"]


# --- Task 8: self-describing event, fired before the calls, shared context -


async def test_event_is_self_describing_and_fires_before_the_calls(hass, engine, _rule
):
    """The logbook renders historical events, so the payload must stand alone."""
    hass.states.async_set("input_boolean.t", "off")
    order: list[str] = []
    events: list = []

    @callback
    def _event(event):
        events.append(event)
        order.append("event")

    hass.bus.async_listen(EVENT_RULE_APPLIED, _event)

    @callback
    def _call(event):
        order.append("call")

    hass.bus.async_listen(EVENT_CALL_SERVICE, _call)

    rule = _rule()
    rule = dataclasses.replace(rule, name="בוקר שבת")
    await engine.async_apply_rule(rule)
    await hass.async_block_till_done()

    assert events[0].data["rule_id"] == rule.id
    assert events[0].data["name"] == "בוקר שבת"
    # v2 payload: the action and its target, not v1's enum + `devices`.
    assert events[0].data["action"] == _ON
    assert events[0].data["target"] == {"entity_id": ["input_boolean.t"]}
    assert order[0] == "event"  # must precede the calls, or attribution breaks


async def test_all_calls_of_one_rule_share_the_events_context(hass, engine):
    """A rule that expands to SEVERAL calls must stamp them all identically.

    v1 got several calls by having several `devices`; v2 makes one call per
    target, so the surviving multi-call path is the climate shim, which
    turns one authored `climate.set_temperature` into set_hvac_mode +
    set_temperature. Both must carry the event's context or Home
    Assistant attributes half the rule's changes to nothing.
    """
    hvac = async_mock_service(hass, "climate", "set_hvac_mode")
    temperature = async_mock_service(hass, "climate", "set_temperature")
    contexts: list[str] = []
    event_context: list[str] = []

    @callback
    def _event(event):
        event_context.append(event.context.id)

    hass.bus.async_listen(EVENT_RULE_APPLIED, _event)

    @callback
    def _call(event):
        contexts.append(event.context.id)

    hass.bus.async_listen(EVENT_CALL_SERVICE, _call)

    await engine.async_apply_rule(
        Rule(
            id="r", profile=1, day="1", time=time(11, 0),
            action="climate.set_temperature",
            target={"entity_id": ["climate.ac"]},
            data={"hvac_mode": "cool", "temperature": 22},
        )
    )
    await hass.async_block_till_done()

    assert len(hvac) == 1 and len(temperature) == 1  # genuinely two calls
    assert len(contexts) == 2
    assert len(set(contexts)) == 1
    assert contexts[0] == event_context[0]


async def test_concurrent_rules_get_distinct_contexts(hass, engine, _rule ):
    """Two rules applied at once must not share or overwrite each other's."""
    hass.states.async_set("input_boolean.t", "off")
    hass.states.async_set("input_boolean.salon", "off")
    seen: list[str] = []

    @callback
    def _event(event):
        seen.append(event.context.id)

    hass.bus.async_listen(EVENT_RULE_APPLIED, _event)

    await asyncio.gather(
        engine.async_apply_rule(
            dataclasses.replace(
                _rule(entities=("input_boolean.t",)), id="one"
            )
        ),
        engine.async_apply_rule(
            dataclasses.replace(
                _rule(action=_OFF, entities=("input_boolean.salon",)), id="two"
            )
        ),
    )
    await hass.async_block_till_done()

    assert len(seen) == 2
    assert len(set(seen)) == 2


from homeassistant.helpers.dispatcher import async_dispatcher_connect

from custom_components.shabbat_scheduler.const import SIGNAL_RULES_CHANGED

# --- Task 11: the durable, PER-RULE outcome ------------------------------
#
# `engine.last_run` is a single transient value for the whole integration,
# overwritten by the next rule to act, so it can never answer "why did
# *this* rule not fire?" tomorrow. The logbook half of the constraint held;
# these pin the half the card reads.


async def _seeded(engine, rule):
    """The rule as the engine really sees it: present in the store.

    `RuleStore.async_save` prunes outcomes for rules that no longer exist,
    so an outcome recorded for a rule that was never in the store is
    correctly dropped again. In production `async_apply_rule` is only ever
    reached for a rule the store holds - a timer built from it, or a
    catch-up pass over it - so seeding is what makes these tests match
    reality rather than a shortcut around it.
    """
    await engine.store.async_replace_all({}, [rule])
    return rule


async def test_a_rule_that_ran_records_that_it_ran(hass, engine, _rule):
    hass.states.async_set("input_boolean.t", "off")
    rule = await _seeded(engine, _rule())

    await engine.async_apply_rule(rule)
    await hass.async_block_till_done()

    outcome = engine.store.last_outcome(rule.id)
    assert outcome["outcome"] == "called"
    assert outcome["detail"] is None
    # The two target diagnostics are ADDITIVE keys, absent on a healthy
    # call. Asserted by absence, not by comparing the whole dict: an
    # explicit `"no_live_targets": False` would render a warning on the
    # card for a rule that worked perfectly.
    assert "unknown_targets" not in outcome
    assert "no_live_targets" not in outcome
    # A verdict with no timestamp cannot be told apart from last week's.
    assert dt_util.parse_datetime(outcome["at"]) is not None


async def test_simulate_never_records_a_durable_outcome(hass, engine, _rule):
    """`would_call` is not `called`, and it must never overwrite a real
    verdict, because the run it describes did not really happen."""
    hass.states.async_set("input_boolean.t", "off")
    rule = await _seeded(engine, _rule())

    await engine.async_apply_rule(rule, simulate=True)

    assert engine.store.last_outcome(rule.id) is None


async def test_simulate_does_not_record_even_when_the_rule_is_blocked(hass, engine, _rule):
    """Ablate this and a simulated but blocked rule leaves a real verdict
    behind - the exact thing 'never persisted' forbids."""
    hass.states.async_set("input_boolean.kids", "off")
    rule = await _seeded(engine, _rule(condition=(
        {"condition": "state", "entity_id": "input_boolean.kids", "state": "on"},
    )))
    calls = []
    async_dispatcher_connect(hass, SIGNAL_RULES_CHANGED, lambda: calls.append(1))

    results = await engine.async_apply_rule(rule, simulate=True)
    await hass.async_block_till_done()

    assert results[0]["outcome"] == "blocked"
    assert engine.store.last_outcome(rule.id) is None
    # Same guarantee as the non-blocked path
    # (test_simulate_does_not_signal_rules_changed), proven independently
    # here rather than left to follow from code-reading: SIGNAL_RULES_CHANGED
    # only ever fires from inside _async_record_outcome, and the blocked
    # branch guards that call with the identical `if not simulate:` the
    # non-blocked branch uses - but that identity is exactly the kind of
    # thing a future edit could accidentally break on one branch and not
    # the other.
    assert calls == []


async def test_simulate_does_not_signal_rules_changed(hass, engine, _rule):
    hass.states.async_set("input_boolean.t", "off")
    rule = await _seeded(engine, _rule())
    calls = []
    async_dispatcher_connect(hass, SIGNAL_RULES_CHANGED, lambda: calls.append(1))

    await engine.async_apply_rule(rule, simulate=True)
    await hass.async_block_till_done()

    assert calls == []


async def test_simulate_does_not_change_last_run(hass, engine, _rule):
    """`last_run`/`last_run_at` back `sensor.shabbat_scheduler_last_run`, a
    REAL entity - a simulated run moving it would be the exact lie "it did
    not really happen" forbids, reached through the sensor instead of the
    per-rule outcome the tests above already pin."""
    hass.states.async_set("input_boolean.t", "off")
    rule = await _seeded(engine, _rule())
    before, before_at = engine.last_run, engine.last_run_at

    results = await engine.async_apply_rule(rule, simulate=True)

    assert results[0]["outcome"] == "would_call"  # the call did happen, simulated
    assert engine.last_run is before
    assert engine.last_run_at is before_at


async def test_simulate_does_not_change_last_run_even_when_blocked(hass, engine, _rule):
    """Ablate the guard on the blocked branch specifically and a simulated
    but blocked rule still moves `last_run` - the same shape
    `test_simulate_does_not_record_even_when_the_rule_is_blocked` pins for
    the per-rule outcome, proven independently for the blocked path since
    the guard had to be applied there separately."""
    hass.states.async_set("input_boolean.kids", "off")
    rule = await _seeded(engine, _rule(condition=(
        {"condition": "state", "entity_id": "input_boolean.kids", "state": "on"},
    )))
    before, before_at = engine.last_run, engine.last_run_at

    results = await engine.async_apply_rule(rule, simulate=True)

    assert results[0]["outcome"] == "blocked"
    assert engine.last_run is before
    assert engine.last_run_at is before_at


async def test_a_real_run_still_records_and_signals(hass, engine, _rule):
    """The two tests above ablated: a REAL run (simulate defaults False)
    must still record and signal, or the guard above proves nothing."""
    hass.states.async_set("input_boolean.t", "off")
    rule = await _seeded(engine, _rule())
    calls = []
    async_dispatcher_connect(hass, SIGNAL_RULES_CHANGED, lambda: calls.append(1))

    await engine.async_apply_rule(rule)
    await hass.async_block_till_done()

    assert engine.store.last_outcome(rule.id) is not None
    assert calls == [1]


# --- Follow-up to b1b6095: neither event fires at all under simulate ------
#
# b1b6095 tried to keep a simulated run out of the logbook by having
# logbook.py's describer return `{}` for a `dry_run: True` event. That does
# not work: HA's `async_describe_events` extension point has no way to
# suppress a row entirely - `logbook/processor.py`'s `yield data` is
# unconditional, so a `{}` result still produced a BLANK row (domain +
# timestamp only), confirmed against the real dev container's recorder (see
# this fix round's report). The tests below prove the actual mechanism
# instead: the event itself is never fired at all, which is both necessary
# and sufficient for "the logbook must not say it happened" - a describer
# that never runs cannot render anything, blank or otherwise. This is fully
# verifiable at the Python level without touching the recorder, unlike the
# describer-in-isolation tests these replace, which is exactly the kind of
# insufficient evidence this fix round exists to correct.


async def test_simulate_fires_neither_event(hass, engine, _rule):
    """The positive-path guarantee: a simulated, unblocked run must not put
    EVENT_RULE_APPLIED or EVENT_RULE_COMPLETED on the bus at all."""
    hass.states.async_set("input_boolean.t", "off")
    rule = await _seeded(engine, _rule())
    applied = []
    completed = []
    hass.bus.async_listen(EVENT_RULE_APPLIED, lambda event: applied.append(event))
    hass.bus.async_listen(EVENT_RULE_COMPLETED, lambda event: completed.append(event))

    results = await engine.async_apply_rule(rule, simulate=True)
    await hass.async_block_till_done()

    assert results[0]["outcome"] == "would_call"  # the call did happen, simulated
    assert applied == []
    assert completed == []


async def test_simulate_fires_neither_event_even_when_blocked(hass, engine, _rule):
    """Ablate the guard on the blocked branch specifically and a simulated
    but blocked rule still fires both events - the same shape the
    `last_run`/durable-outcome guards above are pinned for independently on
    this path, since the guard had to be applied there separately too."""
    hass.states.async_set("input_boolean.kids", "off")
    rule = await _seeded(engine, _rule(condition=(
        {"condition": "state", "entity_id": "input_boolean.kids", "state": "on"},
    )))
    applied = []
    completed = []
    hass.bus.async_listen(EVENT_RULE_APPLIED, lambda event: applied.append(event))
    hass.bus.async_listen(EVENT_RULE_COMPLETED, lambda event: completed.append(event))

    results = await engine.async_apply_rule(rule, simulate=True)
    await hass.async_block_till_done()

    assert results[0]["outcome"] == "blocked"
    assert applied == []
    assert completed == []


async def test_a_real_run_still_fires_both_events(hass, engine, _rule):
    """The negative-path ablation: a REAL run (simulate defaults False) must
    still fire both events, or the two guards above prove nothing - this is
    also the pre-existing behaviour
    `test_event_is_self_describing_and_fires_before_the_calls` already pins
    for EVENT_RULE_APPLIED alone; this adds EVENT_RULE_COMPLETED and a
    direct real-vs-simulated contrast in one place."""
    hass.states.async_set("input_boolean.t", "off")
    rule = await _seeded(engine, _rule())
    applied = []
    completed = []
    hass.bus.async_listen(EVENT_RULE_APPLIED, lambda event: applied.append(event))
    hass.bus.async_listen(EVENT_RULE_COMPLETED, lambda event: completed.append(event))

    await engine.async_apply_rule(rule)
    await hass.async_block_till_done()

    assert len(applied) == 1
    assert len(completed) == 1
    assert applied[0].data["dry_run"] is False
    assert completed[0].data["dry_run"] is False


async def test_force_conditions_skips_evaluation_entirely(hass, engine, _rule):
    hass.states.async_set("input_boolean.kids", "off")  # would normally block
    hass.states.async_set("input_boolean.t", "off")
    rule = await _seeded(engine, _rule(condition=(
        {"condition": "state", "entity_id": "input_boolean.kids", "state": "on"},
    )))

    results = await engine.async_apply_rule(rule, simulate=True, force_conditions=True)

    assert results[0]["outcome"] == "would_call"  # not "blocked"


async def test_at_evaluates_a_time_condition_against_a_hypothetical_moment(
    hass, jerusalem, engine, _rule
):
    from datetime import datetime

    hass.states.async_set("input_boolean.t", "off")
    # after 20:00 local - false right now (test runs at an arbitrary real
    # time), true at the `at` below.
    rule = await _seeded(engine, _rule(condition=(
        {"condition": "time", "after": "20:00:00"},
    )))

    at = datetime(2026, 8, 15, 21, 0, tzinfo=dt_util.get_time_zone(jerusalem.config.time_zone))
    results = await engine.async_apply_rule(rule, simulate=True, at=at)

    assert results[0]["outcome"] == "would_call"


async def test_at_does_not_affect_a_state_condition(hass, jerusalem, engine, _rule):
    """`at` is scoped to `sun`/`time` only - a `state` condition still
    reads the real state, not something keyed off `at`."""
    from datetime import datetime

    hass.states.async_set("input_boolean.kids", "off")
    hass.states.async_set("input_boolean.t", "off")
    rule = await _seeded(engine, _rule(condition=(
        {"condition": "state", "entity_id": "input_boolean.kids", "state": "on"},
    )))

    at = datetime(2026, 8, 15, 21, 0, tzinfo=dt_util.get_time_zone(jerusalem.config.time_zone))
    results = await engine.async_apply_rule(rule, simulate=True, at=at)

    assert results[0]["outcome"] == "blocked"


async def test_check_at_scoped_restores_dt_util_even_if_the_checker_raises(
    jerusalem, engine
):
    """The monkeypatch on dt_util.now/utcnow MUST be restored even when the
    wrapped checker call raises. A leaked patch here would corrupt every
    other timing decision in the whole integration - this is the single
    most dangerous class of bug this feature could introduce.
    """
    from datetime import datetime

    original_now = dt_util.now
    original_utcnow = dt_util.utcnow

    def _boom(hass_arg, variables):
        raise RuntimeError("boom")

    at = datetime(2026, 8, 15, 21, 0, tzinfo=dt_util.get_time_zone(jerusalem.config.time_zone))

    with pytest.raises(RuntimeError, match="boom"):
        engine._check_at_scoped(_boom, at)

    # Identity, not just "returns a plausible time": a replacement lambda
    # that happens to compute the real time would still pass a looser
    # check while leaving the patch in place.
    assert dt_util.now is original_now
    assert dt_util.utcnow is original_utcnow


async def test_a_blocked_rule_records_which_condition_held_it_back(
    hass, engine, _rule
):
    """The card says the same words the logbook says.

    `_condition_block_reason` already produces this wording for the
    logbook row; reusing it verbatim is the point, not duplication - the
    person reading the card and the person reading the logbook must not be
    told two different things about the same rule.
    """
    hass.states.async_set("input_boolean.kids", "off")
    rule = await _seeded(engine, _rule(condition=(
        {"condition": "state", "entity_id": "input_boolean.kids", "state": "on"},
    )))

    await engine.async_apply_rule(rule)

    outcome = engine.store.last_outcome(rule.id)
    assert outcome["outcome"] == "blocked"
    assert outcome["detail"] == (
        "condition 1 of 1 (state on input_boolean.kids) not met"
    )


async def test_a_failed_rule_records_why_it_failed(hass, engine, _rule):
    """"failed" with nothing to read is a rule that does not say why."""
    hass.states.async_set("switch.t", "off")

    async def always_fail(_call):
        raise RuntimeError("cloud auth expired")

    hass.services.async_register("switch", "turn_on", always_fail)
    rule = await _seeded(
        engine, _rule(action="switch.turn_on", entities=("switch.t",))
    )

    with patch("custom_components.shabbat_scheduler.engine.asyncio.sleep"):
        await engine.async_apply_rule(rule)

    outcome = engine.store.last_outcome(rule.id)
    assert outcome["outcome"] == "failed"
    assert "cloud auth expired" in outcome["detail"]
    assert "RuntimeError" in outcome["detail"]


async def test_a_stale_replay_skip_records_how_late_it_was(hass, engine):
    """The skip never reaches `async_apply_rule` at all.

    `async_catch_up` appends its result and `continue`s, so the recording
    has to happen on that path too - otherwise the one outcome the user
    most needs to see the morning after a restart is the one the card
    cannot show.
    """
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    hass.states.async_set("input_boolean.t", "off")
    await engine.store.async_replace_all({}, [
        Rule(id="on11", profile=1, day="1", time=time(11, 0), action=_ON,
             target={"entity_id": ["input_boolean.t"]},
             replay=Replay(enabled=True, within=timedelta(hours=1))),
    ])
    await engine.async_refresh()

    with freeze_time("2026-08-15T14:00:00+00:00"):   # 17:00 local, 6h late
        await engine.async_catch_up()
    await hass.async_block_till_done()

    outcome = engine.store.last_outcome("on11")
    assert outcome["outcome"] == "skipped_stale"
    # The same string the logbook row carries: how late, and the window it
    # blew. "too old" without either number is not actionable.
    assert "late" in outcome["detail"]
    assert "1:00:00" in outcome["detail"]
    assert outcome["at"] == "2026-08-15T14:00:00+00:00"
    # The rule really was not replayed - the outcome is not decoration.
    assert hass.states.get("input_boolean.t").state == "off"


async def test_a_typo_beside_a_working_entity_records_called_AND_the_typo(
    hass, engine, _rule
):
    """`called` and a diagnostic, at once.

    A partial typo still fires the rest of the target, so the outcome is
    genuinely `called` - and a row saying only "fired" while one named
    entity silently did nothing is the quiet failure this integration
    exists to prevent. The two are orthogonal, so they compose rather than
    displacing one another.
    """
    hass.states.async_set("input_boolean.t", "off")
    rule = await _seeded(engine, _rule(
        entities=("input_boolean.t", "input_boolean.nope"),
    ))

    await engine.async_apply_rule(rule)
    await hass.async_block_till_done()

    outcome = engine.store.last_outcome(rule.id)
    assert outcome["outcome"] == "called"
    assert outcome["unknown_targets"] == ["input_boolean.nope"]
    assert "no_live_targets" not in outcome


async def test_a_call_that_reached_nothing_records_that_too(hass, engine, _rule):
    """The third diagnostic, and it is NOT `failed`.

    The call genuinely happened and nothing is misspelt, so downgrading
    the outcome would be a lie in the opposite direction. It rides
    alongside `called` instead.
    """
    hass.states.async_set("group.leftover", "on")
    async_mock_service(hass, "input_boolean", "turn_on")
    rule = await _seeded(engine, dataclasses.replace(
        _rule(action=_ON, entities=()), target={"entity_id": ["group.leftover"]},
    ))

    await engine.async_apply_rule(rule)
    await hass.async_block_till_done()

    outcome = engine.store.last_outcome(rule.id)
    assert outcome["outcome"] == "called"
    assert outcome["no_live_targets"] is True
    assert "unknown_targets" not in outcome


async def test_a_multi_call_rule_records_the_worst_of_its_calls(hass, engine):
    """The climate shim turns one authored action into up to three calls.

    If any of them fails, "it ran" is not what the family needs to know.
    Same precedence the logbook row uses, from the same constant in
    `const.py`, so the row and the logbook line cannot drift into
    disagreeing about the same rule.

    DRIVEN WHERE "FIRST" AND "WORST" DIFFER, which is the whole point.
    `expand_action` emits `set_hvac_mode` BEFORE `set_temperature`, so
    failing the hvac call would put the failure in `results[0]` and an
    implementation that simply reported the first result would pass while
    proving nothing. The FIRST call here succeeds and the SECOND fails, so
    only a real worst-of fold gets this right. Confirmed by reverting the
    fold to `results[0]["outcome"]`: without this direction the suite
    stayed green.
    """
    async def always_fail(_call):
        raise RuntimeError("unit did not answer")

    async_mock_service(hass, "climate", "set_hvac_mode")
    hass.services.async_register("climate", "set_temperature", always_fail)
    hass.states.async_set("climate.ac", "off")

    rule = await _seeded(engine, Rule(
        id="r", profile=1, day="1", time=time(11, 0),
        action="climate.set_temperature",
        target={"entity_id": ["climate.ac"]},
        data={"hvac_mode": "cool", "temperature": 22},
    ))
    with patch("custom_components.shabbat_scheduler.engine.asyncio.sleep"):
        await engine.async_apply_rule(rule)
    await hass.async_block_till_done()

    outcome = engine.store.last_outcome("r")
    assert outcome["outcome"] == "failed"
    assert "unit did not answer" in outcome["detail"]


async def test_one_rules_outcome_does_not_erase_anothers(hass, engine):
    """The whole point. `last_run` held ONE result for the integration."""
    hass.states.async_set("input_boolean.t", "off")
    hass.states.async_set("input_boolean.kids", "off")
    blocked = Rule(
        id="blocked", profile=1, day="1", time=time(11, 0), action=_ON,
        target={"entity_id": ["input_boolean.t"]},
        condition=({"condition": "state", "entity_id": "input_boolean.kids",
                    "state": "on"},),
    )
    ran = Rule(
        id="ran", profile=1, day="1", time=time(12, 0), action=_ON,
        target={"entity_id": ["input_boolean.t"]},
    )
    await engine.store.async_replace_all({}, [blocked, ran])

    await engine.async_apply_rule(blocked)
    await engine.async_apply_rule(ran)
    await hass.async_block_till_done()

    assert engine.store.last_outcome("blocked")["outcome"] == "blocked"
    assert engine.store.last_outcome("ran")["outcome"] == "called"


async def test_an_outcome_reaches_an_open_card(hass, engine, _rule):
    """Durable is not enough: the constraint says "and on the card".

    A wall tablet left open through Shabbat renders only what was pushed
    to it, and nothing else pushes between rules - the zmanim sensors do
    not change again until havdalah. Without this the outcome appears
    only after the next unrelated edit, i.e. not during the block anyone
    would want to read it in.
    """
    hass.states.async_set("input_boolean.t", "off")
    rule = await _seeded(engine, _rule())
    pushes = []
    async_dispatcher_connect(
        hass, SIGNAL_RULES_CHANGED, lambda: pushes.append(1)
    )

    await engine.async_apply_rule(rule)
    await hass.async_block_till_done()

    assert pushes, "the outcome was recorded where no open card can see it"


async def test_recording_an_outcome_re_evaluates_nothing(hass, engine, _rule):
    """Fire once, never re-assert.

    The STORE's change listener is `_rules_changed` (__init__.py), which
    reschedules the engine. If recording went through it, every rule that
    fired would trigger a refresh from inside its own application, on the
    one day nobody can intervene. The card is pushed over the dispatcher
    instead, which has no path back into the store.
    """
    hass.states.async_set("input_boolean.t", "off")
    rule = await _seeded(engine, _rule())
    notified = []
    engine.store.async_set_change_listener(lambda: notified.append(1))

    await engine.async_apply_rule(rule)
    await hass.async_block_till_done()

    assert notified == []


# --- auto-disarm: an opt-in reset of the master switch ---------------------
#
# Off by default (const.py's DEFAULT_AUTO_DISARM) - these tests build their
# own engine with it on, rather than using the shared `engine` fixture,
# which stays at the constructor default so every other test in this file
# is unaffected.


async def test_auto_disarm_off_by_default_never_disarms(hass, engine, freezer):
    """The shared `engine` fixture never asked for this - the master switch

    must stay exactly as set, well past havdalah and past every rule's own
    time, matching every install's behaviour before this feature existed.
    """
    freezer.move_to("2026-08-14T12:00:00+00:00")
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await engine.store.async_set_enabled(True)
    await engine.store.async_add(
        Rule(id="r", profile=1, day="1", time=time(11, 0),
             action=_ON, target={"entity_id": ["input_boolean.t"]})
    )
    await engine.async_refresh()

    # Well past havdalah (20:01 local) and the rule (11:00 local).
    async_fire_time_changed(
        hass, dt_util.parse_datetime("2026-08-15T19:00:00+00:00")
    )
    await hass.async_block_till_done()

    assert engine.store.enabled is True


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_auto_disarm_fires_at_havdalah_when_no_rule_follows_it(
    hass, jerusalem, freezer
):
    """The simple case: nothing scheduled after havdalah, so havdalah

    itself is the correct moment.
    """
    store = RuleStore(hass)
    await store.async_load()
    engine = ShabbatEngine(hass, store, auto_disarm=True)

    freezer.move_to("2026-08-14T12:00:00+00:00")
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await store.async_set_enabled(True)
    await store.async_add(
        Rule(id="morning-on", profile=1, day="1", time=time(11, 0),
             action=_ON, target={"entity_id": ["input_boolean.t"]})
    )
    await engine.async_refresh()
    assert store.enabled is True

    # Refreshed one minute before havdalah, not exactly at it: `now` has to
    # stay strictly before the disarm target for `_async_refresh` to
    # schedule it at all (`item.when > now`) - refreshing AT the target
    # would filter it straight back out. A timer registered hours earlier
    # against the frozen clock does not reliably fire on a later, distant
    # `freezer.move_to` alone either, the same pairing this file's other
    # tail-firing tests use throughout - so this re-registers it just
    # ahead of time, then the actual havdalah moment fires it.
    freezer.move_to("2026-08-15T17:00:00+00:00")
    await engine.async_refresh()

    # 20:01 local - havdalah itself. Nothing else is scheduled after it.
    async_fire_time_changed(
        hass, dt_util.parse_datetime("2026-08-15T17:01:00+00:00")
    )
    await hass.async_block_till_done()

    assert store.enabled is False


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_auto_disarm_waits_for_a_rule_scheduled_after_havdalah(
    hass, jerusalem, test_booleans, freezer
):
    """The exact concern this feature was asked to handle: a rule due

    AFTER havdalah must get to fire before the switch turns itself off -
    disarming at bare havdalah would cut it off first.
    """
    store = RuleStore(hass)
    await store.async_load()
    engine = ShabbatEngine(hass, store, auto_disarm=True)

    freezer.move_to("2026-08-14T12:00:00+00:00")
    _set_zmanim(hass, "2026-08-14T15:44:00+00:00", "2026-08-15T17:01:00+00:00")
    await store.async_set_enabled(True)
    hass.states.async_set("input_boolean.t", "on")
    # 23:00 local == 20:00 UTC - two hours after the 20:01 local havdalah.
    await store.async_add(
        Rule(id="late-off", profile=1, day="1", time=time(23, 0),
             action=_OFF, target={"entity_id": ["input_boolean.t"]})
    )
    await engine.async_refresh()

    # Havdalah passes - the switch must still be armed, or the late rule
    # (which the hold logic elsewhere in this file already protects) would
    # be pointless to protect: it would fire into a disarmed engine anyway.
    # Refreshed right before each fire, the same pairing this file's other
    # tail-firing tests use throughout - see the simpler havdalah-only test
    # above for why a distant `freezer.move_to` alone is not enough.
    freezer.move_to("2026-08-15T17:01:30+00:00")
    await engine.async_refresh()
    async_fire_time_changed(
        hass, dt_util.parse_datetime("2026-08-15T17:01:30+00:00")
    )
    await hass.async_block_till_done()
    assert store.enabled is True, "disarmed at havdalah, before the late rule could fire"

    # One minute ahead of the late rule, same reasoning as the havdalah-only
    # test above: `now` must stay strictly before it for the refresh to
    # schedule it at all.
    freezer.move_to("2026-08-15T19:59:00+00:00")
    await engine.async_refresh()
    assert store.enabled is True

    # 23:00 local - the late rule fires, and disarm is scheduled for this
    # exact moment too (the later of havdalah/tail).
    async_fire_time_changed(
        hass, dt_util.parse_datetime("2026-08-15T20:00:00+00:00")
    )
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.t").state == "off", "the late rule itself did not fire"
    assert store.enabled is False


async def test_auto_disarm_does_not_write_when_already_off(hass, freezer):
    """The guard in engine.py's `_auto_disarm`: no spurious save/notify

    for a household that already turned it off by hand before havdalah.
    """
    store = RuleStore(hass)
    await store.async_load()
    engine = ShabbatEngine(hass, store, auto_disarm=True)

    with patch.object(
        store, "async_set_enabled", wraps=store.async_set_enabled
    ) as spy:
        await engine._auto_disarm(dt_util.utcnow())
        spy.assert_not_called()
