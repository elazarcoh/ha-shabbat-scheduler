from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from custom_components.shabbat_scheduler.block import compute_block

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
