from datetime import datetime, timezone

import pytest

import bitmapist


@pytest.mark.parametrize(
    "cls",
    [
        bitmapist.HourEvents,
        bitmapist.DayEvents,
        bitmapist.WeekEvents,
        bitmapist.MonthEvents,
        bitmapist.YearEvents,
    ],
)
def test_period_start_end(cls):
    dt = datetime(2014, 1, 1, 8, 30, tzinfo=timezone.utc)
    ev = cls.from_date("foo", dt)
    assert ev.period_start() <= dt <= ev.period_end()
