from datetime import datetime, time
from zoneinfo import ZoneInfo

from custom_components.shabbat_scheduler.block import (
    compute_block,
    conflict_warnings,
    find_conflicts,
    preview_payload,
)
from custom_components.shabbat_scheduler.models import Rule


def _rule(rule_id, action, devices=("climate.a",), day="1", at=time(18, 0), profile=1):
    return Rule(
        id=rule_id, profile=profile, day=day, time=at,
        action=action, devices=devices,
    )


def test_opposing_actions_on_one_device_conflict():
    conflicts = find_conflicts([_rule("a", "on"), _rule("b", "off")])
    assert len(conflicts) == 1
    assert conflicts[0].device == "climate.a"
    assert set(conflicts[0].rule_ids) == {"a", "b"}


def test_identical_actions_are_not_conflicts():
    assert find_conflicts([_rule("a", "off"), _rule("b", "off")]) == []


def test_different_times_are_not_conflicts():
    assert find_conflicts(
        [_rule("a", "on"), _rule("b", "off", at=time(19, 0))]
    ) == []


def test_different_devices_are_not_conflicts():
    assert find_conflicts(
        [_rule("a", "on"), _rule("b", "off", devices=("climate.b",))]
    ) == []


def test_different_profiles_are_not_conflicts():
    assert find_conflicts(
        [_rule("a", "on"), _rule("b", "off", profile=2)]
    ) == []


def test_disabled_rules_do_not_conflict():
    enabled = _rule("a", "on")
    disabled = Rule(
        id="b", profile=1, day="1", time=time(18, 0),
        action="off", devices=("climate.a",), enabled=False,
    )
    assert find_conflicts([enabled, disabled]) == []


def test_custom_rules_are_excluded():
    custom = Rule(
        id="b", profile=1, day="1", time=time(18, 0),
        action="custom", devices=("climate.a",), script="script.x",
    )
    assert find_conflicts([_rule("a", "on"), custom]) == []


def test_conflict_detected_per_shared_device():
    conflicts = find_conflicts([
        _rule("a", "on", devices=("climate.a", "climate.b")),
        _rule("b", "off", devices=("climate.b",)),
    ])
    assert len(conflicts) == 1
    assert conflicts[0].device == "climate.b"


# --- The one preview resolution, shared by `preview` and `simulate` ------

TZ = ZoneInfo("Asia/Jerusalem")
BLOCK = compute_block(
    datetime(2026, 8, 14, 18, 44, tzinfo=TZ),
    datetime(2026, 8, 15, 20, 1, tzinfo=TZ),
)


def test_preview_payload_resolves_the_block():
    payload = preview_payload({}, [_rule("a", "on")], BLOCK, TZ)
    assert payload["profile"] == 1
    assert [item["rule_id"] for item in payload["rules"]] == ["a"]
    assert payload["conflicts"] == []
    assert payload["warnings"] == []


def test_preview_payload_reports_no_block():
    payload = preview_payload({}, [_rule("a", "on")], None, TZ)
    assert payload["profile"] is None
    assert [w["kind"] for w in payload["warnings"]] == ["no_block"]


def test_preview_payload_warns_when_no_profile_matches():
    payload = preview_payload({}, [_rule("a", "on", profile=3)], BLOCK, TZ)
    assert [w["kind"] for w in payload["warnings"]] == ["no_profile"]


def test_preview_payload_finds_conflicts_through_the_defaults():
    """Devices from `defaults` are merged in before conflicts are looked for."""
    payload = preview_payload(
        {"devices": ["climate.a"]},
        [_rule("a", "on", devices=()), _rule("b", "off", devices=())],
        BLOCK,
        TZ,
    )
    assert [c["device"] for c in payload["conflicts"]] == ["climate.a"]
    assert payload["conflicts"][0]["kind"] == "conflict"
    assert payload["conflicts"][0]["profile"] == 1


def test_preview_payload_honours_a_hypothetical_block_length():
    payload = preview_payload(
        {},
        [_rule("a", "on"), _rule("c", "on", profile=3)],
        BLOCK,
        TZ,
        block_length=3,
    )
    assert payload["profile"] == 3
    assert [item["rule_id"] for item in payload["rules"]] == ["c"]


def test_conflict_warnings_merges_the_defaults():
    warnings = conflict_warnings(
        {"devices": ["climate.a"]},
        [_rule("a", "on", devices=()), _rule("b", "off", devices=())],
    )
    assert [w["device"] for w in warnings] == ["climate.a"]
