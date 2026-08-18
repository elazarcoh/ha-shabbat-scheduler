from datetime import datetime, time
from zoneinfo import ZoneInfo

from custom_components.shabbat_scheduler.block import (
    compute_block,
    conflict_warnings,
    desired_state_at,
    find_conflicts,
    preview_payload,
)
from custom_components.shabbat_scheduler.models import Action, Conflict, Rule


def _rule(rule_id, action, devices=("climate.a",), day="1", at=time(18, 0), profile=1):
    return Rule(
        id=rule_id, profile=profile, day=day, time=at,
        action=action, devices=devices,
    )


def test_opposing_actions_on_one_device_conflict():
    conflicts = find_conflicts([_rule("a", Action.ON), _rule("b", Action.OFF)])
    assert len(conflicts) == 1
    assert conflicts[0].device == "climate.a"
    assert set(conflicts[0].rule_ids) == {"a", "b"}


def test_identical_actions_are_not_conflicts():
    assert find_conflicts([_rule("a", Action.OFF), _rule("b", Action.OFF)]) == []


def test_different_times_are_not_conflicts():
    assert find_conflicts(
        [_rule("a", Action.ON), _rule("b", Action.OFF, at=time(19, 0))]
    ) == []


def test_different_devices_are_not_conflicts():
    assert find_conflicts(
        [_rule("a", Action.ON), _rule("b", Action.OFF, devices=("climate.b",))]
    ) == []


def test_different_profiles_are_not_conflicts():
    assert find_conflicts(
        [_rule("a", Action.ON), _rule("b", Action.OFF, profile=2)]
    ) == []


def test_disabled_rules_do_not_conflict():
    enabled = _rule("a", Action.ON)
    disabled = Rule(
        id="b", profile=1, day="1", time=time(18, 0),
        action=Action.OFF, devices=("climate.a",), enabled=False,
    )
    assert find_conflicts([enabled, disabled]) == []


def test_custom_rules_are_excluded():
    custom = Rule(
        id="b", profile=1, day="1", time=time(18, 0),
        action=Action.CUSTOM, devices=("climate.a",), script="script.x",
    )
    assert find_conflicts([_rule("a", Action.ON), custom]) == []


def test_conflict_detected_per_shared_device():
    conflicts = find_conflicts([
        _rule("a", Action.ON, devices=("climate.a", "climate.b")),
        _rule("b", Action.OFF, devices=("climate.b",)),
    ])
    assert len(conflicts) == 1
    assert conflicts[0].device == "climate.b"


TZ = ZoneInfo("Asia/Jerusalem")


def _block():
    return compute_block(
        datetime(2026, 8, 14, 18, 44, tzinfo=TZ),
        datetime(2026, 8, 15, 20, 1, tzinfo=TZ),
    )


def _rules():
    return [
        Rule(id="on", profile=1, day="1", time=time(11, 0),
             action=Action.ON, devices=("climate.a",)),
        Rule(id="off", profile=1, day="1", time=time(18, 0),
             action=Action.OFF, devices=("climate.a",)),
    ]


def test_returns_none_before_the_first_rule():
    when = datetime(2026, 8, 15, 9, 0, tzinfo=TZ)
    assert desired_state_at(_rules(), _block(), when, "climate.a", TZ) is None


def test_returns_the_most_recent_passed_rule():
    when = datetime(2026, 8, 15, 12, 0, tzinfo=TZ)
    result = desired_state_at(_rules(), _block(), when, "climate.a", TZ)
    assert result.id == "on"


def test_returns_the_latest_when_several_have_passed():
    when = datetime(2026, 8, 15, 19, 0, tzinfo=TZ)
    result = desired_state_at(_rules(), _block(), when, "climate.a", TZ)
    assert result.id == "off"


def test_exact_boundary_counts_as_passed():
    when = datetime(2026, 8, 15, 11, 0, tzinfo=TZ)
    result = desired_state_at(_rules(), _block(), when, "climate.a", TZ)
    assert result.id == "on"


def test_unknown_device_is_undefined():
    when = datetime(2026, 8, 15, 19, 0, tzinfo=TZ)
    assert desired_state_at(_rules(), _block(), when, "climate.zzz", TZ) is None


def test_ambiguous_latest_moment_returns_a_conflict():
    rules = [
        Rule(id="a", profile=1, day="1", time=time(18, 0),
             action=Action.ON, devices=("climate.a",)),
        Rule(id="b", profile=1, day="1", time=time(18, 0),
             action=Action.OFF, devices=("climate.a",)),
    ]
    when = datetime(2026, 8, 15, 19, 0, tzinfo=TZ)
    result = desired_state_at(rules, _block(), when, "climate.a", TZ)
    assert isinstance(result, Conflict)
    assert set(result.rule_ids) == {"a", "b"}


def test_custom_rules_never_define_desired_state():
    rules = [
        Rule(id="c", profile=1, day="1", time=time(11, 0), action=Action.CUSTOM,
             devices=("climate.a",), script="script.x"),
    ]
    when = datetime(2026, 8, 15, 12, 0, tzinfo=TZ)
    assert desired_state_at(rules, _block(), when, "climate.a", TZ) is None


# --- The one preview resolution, shared by `preview` and `simulate` ------

TZ = ZoneInfo("Asia/Jerusalem")
BLOCK = compute_block(
    datetime(2026, 8, 14, 18, 44, tzinfo=TZ),
    datetime(2026, 8, 15, 20, 1, tzinfo=TZ),
)


def test_preview_payload_resolves_the_block():
    payload = preview_payload({}, [_rule("a", Action.ON)], BLOCK, TZ)
    assert payload["profile"] == 1
    assert [item["rule_id"] for item in payload["rules"]] == ["a"]
    assert payload["conflicts"] == []
    assert payload["warnings"] == []


def test_preview_payload_reports_no_block():
    payload = preview_payload({}, [_rule("a", Action.ON)], None, TZ)
    assert payload["profile"] is None
    assert [w["kind"] for w in payload["warnings"]] == ["no_block"]


def test_preview_payload_warns_when_no_profile_matches():
    payload = preview_payload({}, [_rule("a", Action.ON, profile=3)], BLOCK, TZ)
    assert [w["kind"] for w in payload["warnings"]] == ["no_profile"]


def test_preview_payload_finds_conflicts_through_the_defaults():
    """Devices from `defaults` are merged in before conflicts are looked for."""
    payload = preview_payload(
        {"devices": ["climate.a"]},
        [_rule("a", Action.ON, devices=()), _rule("b", Action.OFF, devices=())],
        BLOCK,
        TZ,
    )
    assert [c["device"] for c in payload["conflicts"]] == ["climate.a"]
    assert payload["conflicts"][0]["kind"] == "conflict"
    assert payload["conflicts"][0]["profile"] == 1


def test_preview_payload_honours_a_hypothetical_block_length():
    payload = preview_payload(
        {},
        [_rule("a", Action.ON), _rule("c", Action.ON, profile=3)],
        BLOCK,
        TZ,
        block_length=3,
    )
    assert payload["profile"] == 3
    assert [item["rule_id"] for item in payload["rules"]] == ["c"]


def test_conflict_warnings_merges_the_defaults():
    warnings = conflict_warnings(
        {"devices": ["climate.a"]},
        [_rule("a", Action.ON, devices=()), _rule("b", Action.OFF, devices=())],
    )
    assert [w["device"] for w in warnings] == ["climate.a"]
