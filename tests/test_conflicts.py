"""Conflicts on overlapping resolved targets (Task 9).

`find_conflicts` is pure - it takes a resolver callable rather than
importing anything from Home Assistant - so most of this file exercises
it with a stub registry. The one HA-aware test at the bottom exists
because a resolver is easy to get subtly wrong in a way that reports NO
conflicts on a genuinely conflicting schedule: see
`test_the_real_resolver_expands_a_registered_area_to_its_entities`.
"""

from datetime import datetime, time
from zoneinfo import ZoneInfo

from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import entity_registry as er

from custom_components.shabbat_scheduler.block import (
    compute_block,
    conflict_warnings,
    find_conflicts,
    preview_payload,
)
from custom_components.shabbat_scheduler.models import Rule
from custom_components.shabbat_scheduler.websocket_api import _resolver

T = time(18, 0)
T2 = time(19, 0)


def rule(**over):
    base = dict(
        id="r", profile=1, day="1", time=T,
        action="climate.set_temperature",
        target={}, data={},
    )
    base.update(over)
    return Rule(**base)


def _as_list(value):
    """Match `homeassistant.helpers.config_validation.ensure_list` closely
    enough for a stub: a bare id or a list of ids, never neither."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _resolve(target):
    """A stand-in registry: areas expand to their entities."""
    AREAS = {"salon": {"climate.salon", "light.salon"}}
    out = set(target.get("entity_id", []))
    for area in _as_list(target.get("area_id")):
        out |= AREAS.get(area, set())
    return frozenset(out)


def test_two_rules_on_the_same_entity_at_the_same_time_conflict():
    rules = [rule(id="a", time=T, target={"entity_id": ["climate.salon"]}),
             rule(id="b", time=T, target={"entity_id": ["climate.salon"]})]
    assert find_conflicts(rules, _resolve)


def test_an_area_overlapping_an_entity_conflicts():
    """The reason a resolver is needed at all."""
    rules = [rule(id="a", time=T, target={"area_id": "salon"}),
             rule(id="b", time=T, target={"entity_id": ["climate.salon"]})]
    conflicts = find_conflicts(rules, _resolve)
    assert conflicts and "climate.salon" in conflicts[0].targets


def test_different_times_do_not_conflict():
    assert find_conflicts([rule(id="a", time=T), rule(id="b", time=T2)], _resolve) == []


def test_different_profiles_do_not_conflict():
    assert find_conflicts(
        [rule(id="a", profile=1), rule(id="b", profile=3)], _resolve
    ) == []


def test_a_disabled_rule_never_conflicts():
    assert find_conflicts(
        [rule(id="a"), rule(id="b", enabled=False)], _resolve
    ) == []


def test_non_overlapping_targets_do_not_conflict():
    assert find_conflicts(
        [rule(id="a", target={"entity_id": ["climate.salon"]}),
         rule(id="b", target={"entity_id": ["climate.kids"]})],
        _resolve,
    ) == []


def test_identical_rules_now_conflict_which_v1_would_not_have_flagged():
    """Accepted weakening: without understanding the payload, "same" and
    "opposite" are indistinguishable."""
    same = {"entity_id": ["climate.salon"]}
    assert find_conflicts(
        [rule(id="a", target=same, data={"temperature": 26}),
         rule(id="b", target=same, data={"temperature": 26})],
        _resolve,
    )


def test_three_overlapping_rules_yield_one_conflict_per_pair():
    """Pairwise is deliberate (see the comment in find_conflicts): a merged
    group of 3+ would have to summarise non-uniform overlaps across rules,
    reintroducing the ambiguity the resolver exists to remove."""
    same = {"entity_id": ["climate.salon"]}
    rules = [rule(id="a", target=same), rule(id="b", target=same), rule(id="c", target=same)]
    conflicts = find_conflicts(rules, _resolve)
    assert {frozenset(c.rule_ids) for c in conflicts} == {
        frozenset(("a", "b")), frozenset(("a", "c")), frozenset(("b", "c")),
    }


# --- conflict_warnings and preview_payload thread the resolver through ---
#
# These existed before Task 9 with a v1-shaped `find_conflicts`; kept here,
# updated to the resolver-taking signature, so the wiring from
# `preview_payload` down to `find_conflicts` stays covered rather than
# only the pure grouping logic above.

TZ = ZoneInfo("Asia/Jerusalem")
BLOCK = compute_block(
    datetime(2026, 8, 14, 18, 44, tzinfo=TZ),
    datetime(2026, 8, 15, 20, 1, tzinfo=TZ),
)


def test_conflict_warnings_merges_the_defaults_before_resolving():
    """Devices from `defaults` are merged in before conflicts are looked for."""
    warnings = conflict_warnings(
        {"target": {"entity_id": ["climate.salon"]}},
        [rule(id="a", target={}), rule(id="b", target={})],
        _resolve,
    )
    assert warnings and warnings[0]["kind"] == "conflict"
    assert "climate.salon" in warnings[0]["targets"]


def test_preview_payload_resolves_the_block_and_finds_no_conflict():
    payload = preview_payload({}, [rule(id="a", time=T)], BLOCK, TZ, _resolve)
    assert payload["profile"] == 1
    assert [item["rule_id"] for item in payload["rules"]] == ["a"]
    assert payload["conflicts"] == []
    assert payload["warnings"] == []


def test_preview_payload_reports_no_block():
    payload = preview_payload({}, [rule(id="a")], None, TZ, _resolve)
    assert payload["profile"] is None
    assert [w["kind"] for w in payload["warnings"]] == ["no_block"]


def test_preview_payload_warns_when_no_profile_matches():
    payload = preview_payload({}, [rule(id="a", profile=3)], BLOCK, TZ, _resolve)
    assert [w["kind"] for w in payload["warnings"]] == ["no_profile"]


def test_preview_payload_finds_conflicts_through_the_defaults():
    payload = preview_payload(
        {"target": {"entity_id": ["climate.salon"]}},
        [rule(id="a", time=T, target={}), rule(id="b", time=T, target={})],
        BLOCK,
        TZ,
        _resolve,
    )
    assert payload["conflicts"] and payload["conflicts"][0]["kind"] == "conflict"
    assert payload["conflicts"][0]["profile"] == 1


def test_preview_payload_honours_a_hypothetical_block_length():
    """What a user actually opens preview to ask: "what would a 3-day chag
    do?" - anchored on the real candle lighting, not the real block length."""
    payload = preview_payload(
        {},
        [rule(id="a", profile=1), rule(id="c", profile=3)],
        BLOCK,
        TZ,
        _resolve,
        block_length=3,
    )
    assert payload["profile"] == 3
    assert [item["rule_id"] for item in payload["rules"]] == ["c"]


# --- The real, HA-backed resolver, not just the stub ----------------------


async def test_the_real_resolver_expands_a_registered_area_to_its_entities(hass):
    """Wiring, not just logic.

    A resolver built on the wrong `helpers.target` names still runs and
    still returns a (silently empty) frozenset, so nothing here would fail
    loudly without an actual area, with an actual entity in it, proving
    the entity comes back out.
    """
    area = ar.async_get(hass).async_get_or_create("salon")
    entry = er.async_get(hass).async_get_or_create(
        "climate", "test", "salon_unique", suggested_object_id="salon"
    )
    er.async_get(hass).async_update_entity(entry.entity_id, area_id=area.id)

    resolve = _resolver(hass)
    assert resolve({"area_id": "salon"}) == {entry.entity_id}

    # And the same wiring is what a conflict is built on.
    conflicts = find_conflicts(
        [
            rule(id="a", time=T, target={"area_id": "salon"}),
            rule(id="b", time=T, target={"entity_id": [entry.entity_id]}),
        ],
        resolve,
    )
    assert conflicts and entry.entity_id in conflicts[0].targets
