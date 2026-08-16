from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pytest

from custom_components.shabbat_scheduler.block import (
    compute_block,
    has_profile,
    merge_defaults,
    resolve_rules,
)
from custom_components.shabbat_scheduler.models import Action, EREV, Rule

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
        "devices": ["climate.a"],
        "settings": {"temperature": 26, "fan_mode": "quiet"},
    }
    rule = Rule(
        id="r1",
        profile=1,
        day="1",
        time=time(11, 0),
        action=Action.ON,
        settings={"temperature": 24},
    )
    merged = merge_defaults(defaults, rule)
    assert merged.devices == ("climate.a",)
    assert merged.settings == {"temperature": 24, "fan_mode": "quiet"}
    # The original must not be mutated.
    assert rule.settings == {"temperature": 24}


def test_merge_defaults_keeps_explicit_devices():
    defaults = {"devices": ["climate.a"]}
    rule = Rule(
        id="r1",
        profile=1,
        day="1",
        time=time(11, 0),
        action=Action.ON,
        devices=("climate.b",),
    )
    assert merge_defaults(defaults, rule).devices == ("climate.b",)


def test_resolve_binds_erev_and_days_to_dates():
    rules = [
        Rule(id="a", profile=1, day="1", time=time(11, 0), action=Action.ON),
        Rule(id="b", profile=1, day=EREV, time=time(23, 0), action=Action.OFF),
    ]
    resolved = resolve_rules(rules, _block_1day(), TZ)
    assert [r.rule.id for r in resolved] == ["b", "a"]  # sorted by datetime
    assert resolved[0].when == datetime(2026, 8, 14, 23, 0, tzinfo=TZ)
    assert resolved[1].when == datetime(2026, 8, 15, 11, 0, tzinfo=TZ)


def test_resolve_selects_only_the_matching_profile():
    rules = [
        Rule(id="a", profile=1, day="1", time=time(11, 0), action=Action.ON),
        Rule(id="b", profile=3, day="1", time=time(11, 0), action=Action.ON),
    ]
    resolved = resolve_rules(rules, _block_1day(), TZ)
    assert [r.rule.id for r in resolved] == ["a"]


def test_resolve_drops_disabled_rules():
    rules = [
        Rule(
            id="a", profile=1, day="1", time=time(11, 0),
            action=Action.ON, enabled=False,
        )
    ]
    assert resolve_rules(rules, _block_1day(), TZ) == []


def test_resolve_keeps_post_havdalah_times():
    # 23:00 on the last day is after havdalah (20:01) and must still resolve.
    rules = [Rule(id="a", profile=1, day="1", time=time(23, 0), action=Action.OFF)]
    resolved = resolve_rules(rules, _block_1day(), TZ)
    assert resolved[0].when == datetime(2026, 8, 15, 23, 0, tzinfo=TZ)


def test_has_profile():
    rules = [Rule(id="a", profile=2, day="1", time=time(11, 0), action=Action.ON)]
    assert has_profile(rules, 2) is True
    assert has_profile(rules, 1) is False
