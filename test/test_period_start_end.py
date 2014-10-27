# -*- coding: utf-8 -*-
import pytest
import datetime
import bitmapist


@pytest.mark.parametrize('cls', [bitmapist.HourEvents, bitmapist.DayEvents,
                                 bitmapist.WeekEvents, bitmapist.MonthEvents,
                                 bitmapist.YearEvents])
def test_period_start_end(cls):
    dt = datetime.datetime(2014, 1, 1, 8, 30)
    ev = cls.from_date('foo', dt)
    assert ev.period_start() <= dt <= ev.period_end()
