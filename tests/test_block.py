import json
from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

import pytest

from custom_components.shabbat_scheduler.block import (
    block_payload,
    compute_block,
    has_profile,
    merge_defaults,
    resolve_rules,
)
from custom_components.shabbat_scheduler.models import EREV, Rule

TZ = ZoneInfo("Asia/Jerusalem")


def test_regular_shabbat_is_one_day():
    # Real values observed on the live instance.
    block = compute_block(
        datetime(2026, 8, 14, 18, 44, tzinfo=TZ),
        datetime(2026, 8, 15, 20, 1, tzinfo=TZ),
    )
    assert block.length == 1
    assert block.erev_date == date(2026, 8, 14)
    assert block.day_dates == (date(2026, 8, 15),)


def test_chag_adjacent_to_shabbat_is_two_days():
    block = compute_block(
        datetime(2026, 10, 1, 18, 0, tzinfo=TZ),
        datetime(2026, 10, 3, 19, 30, tzinfo=TZ),
    )
    assert block.length == 2
    assert block.erev_date == date(2026, 10, 1)
    assert block.day_dates == (date(2026, 10, 2), date(2026, 10, 3))


def test_three_day_block():
    block = compute_block(
        datetime(2026, 9, 30, 18, 0, tzinfo=TZ),
        datetime(2026, 10, 3, 19, 30, tzinfo=TZ),
    )
    assert block.length == 3
    assert block.day_dates == (
        date(2026, 10, 1),
        date(2026, 10, 2),
        date(2026, 10, 3),
    )


def test_havdalah_before_candle_lighting_is_rejected():
    with pytest.raises(ValueError):
        compute_block(
            datetime(2026, 8, 15, 20, 1, tzinfo=TZ),
            datetime(2026, 8, 14, 18, 44, tzinfo=TZ),
        )


def test_same_day_havdalah_is_rejected():
    # A zero-length block is meaningless and would produce no full days.
    with pytest.raises(ValueError):
        compute_block(
            datetime(2026, 8, 14, 18, 44, tzinfo=TZ),
            datetime(2026, 8, 14, 23, 0, tzinfo=TZ),
        )


def _block_1day():
    return compute_block(
        datetime(2026, 8, 14, 18, 44, tzinfo=TZ),
        datetime(2026, 8, 15, 20, 1, tzinfo=TZ),
    )


def test_merge_defaults_fills_unset_keys_only():
    defaults = {
        "target": {"entity_id": ["climate.a"]},
        "data": {"temperature": 26, "fan_mode": "quiet"},
    }
    rule = Rule(
        id="r1",
        profile=1,
        day="1",
        time=time(11, 0),
        action="on",
        data={"temperature": 24},
    )
    merged = merge_defaults(defaults, rule)
    assert merged.target == {"entity_id": ["climate.a"]}
    assert merged.data == {"temperature": 24, "fan_mode": "quiet"}
    # The original must not be mutated.
    assert rule.data == {"temperature": 24}


def test_merge_defaults_keeps_explicit_target():
    defaults = {"target": {"entity_id": ["climate.a"]}}
    rule = Rule(
        id="r1",
        profile=1,
        day="1",
        time=time(11, 0),
        action="on",
        target={"entity_id": ["climate.b"]},
    )
    assert merge_defaults(defaults, rule).target == {"entity_id": ["climate.b"]}


def test_resolve_binds_erev_and_days_to_dates():
    rules = [
        Rule(id="a", profile=1, day="1", time=time(11, 0), action="on"),
        Rule(id="b", profile=1, day=EREV, time=time(23, 0), action="off"),
    ]
    resolved = resolve_rules(rules, _block_1day(), TZ)
    assert [r.rule.id for r in resolved] == ["b", "a"]  # sorted by datetime
    assert resolved[0].when == datetime(2026, 8, 14, 23, 0, tzinfo=TZ)
    assert resolved[1].when == datetime(2026, 8, 15, 11, 0, tzinfo=TZ)


def test_resolve_selects_only_the_matching_profile():
    rules = [
        Rule(id="a", profile=1, day="1", time=time(11, 0), action="on"),
        Rule(id="b", profile=3, day="1", time=time(11, 0), action="on"),
    ]
    resolved = resolve_rules(rules, _block_1day(), TZ)
    assert [r.rule.id for r in resolved] == ["a"]


def test_resolve_drops_disabled_rules():
    rules = [
        Rule(
            id="a", profile=1, day="1", time=time(11, 0),
            action="on", enabled=False,
        )
    ]
    assert resolve_rules(rules, _block_1day(), TZ) == []


def test_resolve_keeps_post_havdalah_times():
    # 23:00 on the last day is after havdalah (20:01) and must still resolve.
    rules = [Rule(id="a", profile=1, day="1", time=time(23, 0), action="off")]
    resolved = resolve_rules(rules, _block_1day(), TZ)
    assert resolved[0].when == datetime(2026, 8, 15, 23, 0, tzinfo=TZ)


def test_resolve_skips_an_unparsable_day_without_aborting_the_others():
    """Task 5 round 4's hardening, exercised at the branch that matters.

    `resolve_rules` filters disabled rules out first, so a bad `day` only
    ever reaches `int(rule.day)` on a rule that made it past that filter -
    an ENABLED rule with an unparsable `day`, reachable via a hand-edited
    `.storage` file or a YAML import. Before the `try/except ValueError:
    continue` guard, this raised inside the loop and aborted resolving
    every OTHER rule too, not just this one.
    """
    rules = [
        Rule(id="a", profile=1, day="1", time=time(11, 0), action="on"),
        Rule(id="bad", profile=1, day="tuesday", time=time(12, 0), action="on"),
    ]
    resolved = resolve_rules(rules, _block_1day(), TZ)
    assert [r.rule.id for r in resolved] == ["a"]


def test_has_profile():
    rules = [Rule(id="a", profile=2, day="1", time=time(11, 0), action="on")]
    assert has_profile(rules, 2) is True
    assert has_profile(rules, 1) is False


def test_has_profile_ignores_disabled_rules():
    """All-disabled is the same as absent, as far as "will anything run?" goes.

    Otherwise the profile check passes, nothing is scheduled, and the
    missing-profile notification never fires.
    """
    rules = [
        Rule(id="a", profile=2, day="1", time=time(11, 0),
             action="on", enabled=False),
    ]
    assert has_profile(rules, 2) is False

    rules.append(
        Rule(id="b", profile=2, day="1", time=time(12, 0), action="on")
    )
    assert has_profile(rules, 2) is True


def test_block_payload_describes_the_block_for_the_card():
    block = compute_block(
        datetime(2026, 8, 14, 18, 44, tzinfo=UTC),
        datetime(2026, 8, 15, 20, 1, tzinfo=UTC),
    )
    payload = block_payload(block)

    assert payload["length"] == 1
    assert payload["candle_lighting"] == "2026-08-14T18:44:00+00:00"
    assert payload["havdalah"] == "2026-08-15T20:01:00+00:00"
    assert payload["dates"] == {"erev": "2026-08-14", "1": "2026-08-15"}


def test_block_payload_keys_days_the_same_way_rules_do():
    """day_dates[0] is day_1, and rules spell their day '1', not '0'.

    An off-by-one here would silently file every rule under the wrong
    date - the card would render a correct-looking timeline on the wrong
    days, which is worse than rendering nothing.
    """
    block = compute_block(
        datetime(2026, 10, 2, 18, 0, tzinfo=UTC),
        datetime(2026, 10, 4, 19, 0, tzinfo=UTC),
    )
    payload = block_payload(block)

    assert payload["length"] == 2
    assert payload["dates"] == {
        "erev": "2026-10-02",
        "1": "2026-10-03",
        "2": "2026-10-04",
    }


def test_block_payload_is_none_when_there_is_no_block():
    assert block_payload(None) is None


def test_block_payload_is_json_able():
    """It crosses a websocket; a date or datetime object would not survive."""
    block = compute_block(
        datetime(2026, 8, 14, 18, 44, tzinfo=UTC),
        datetime(2026, 8, 15, 20, 1, tzinfo=UTC),
    )
    json.dumps(block_payload(block))
