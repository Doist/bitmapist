# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from bitmapist import setup_redis, delete_all_events, mark_event,\
                      MonthEvents, WeekEvents, DayEvents, HourEvents,\
                      BitOpAnd, BitOpOr


def setup_module():
    setup_redis('default', 'localhost', 6380)
    setup_redis('default_copy', 'localhost', 6380)


def test_mark_with_diff_days():
    delete_all_events()

    mark_event('active', 123)

    now = datetime.utcnow()

    # Month
    assert 123 in MonthEvents('active', now.year, now.month)
    assert 124 not in MonthEvents('active', now.year, now.month)

    # Week
    assert 123 in WeekEvents('active', now.year, now.isocalendar()[1])
    assert 124 not in WeekEvents('active', now.year, now.isocalendar()[1])

    # Day
    assert 123 in DayEvents('active', now.year, now.month, now.day)
    assert 124 not in DayEvents('active', now.year, now.month, now.day)

    # Hour
    assert 123 in HourEvents('active', now.year, now.month, now.day, now.hour)
    assert 124 not in HourEvents('active', now.year, now.month, now.day, now.hour)
    assert 124 not in HourEvents('active', now.year, now.month, now.day, now.hour-1)


def test_mark_counts():
    delete_all_events()

    now = datetime.utcnow()

    assert MonthEvents('active', now.year, now.month).get_count() == 0

    mark_event('active', 123)
    mark_event('active', 23232)

    assert len(MonthEvents('active', now.year, now.month)) == 2


def test_different_dates():
    delete_all_events()

    now = datetime.utcnow()
    yesterday = now - timedelta(days=1)

    mark_event('active', 123, now=now)
    mark_event('active', 23232, now=yesterday)

    assert DayEvents('active',
                   now.year,
                   now.month,
                   now.day).get_count() == 1

    assert DayEvents('active',
                   yesterday.year,
                   yesterday.month,
                   yesterday.day).get_count() == 1


def test_different_buckets():
    delete_all_events()

    now = datetime.utcnow()

    mark_event('active', 123)
    mark_event('tasks:completed', 23232)

    assert MonthEvents('active', now.year, now.month).get_count() == 1
    assert MonthEvents('tasks:completed', now.year, now.month).get_count() == 1


def test_bit_operations():
    delete_all_events()

    now = datetime.utcnow()
    last_month = datetime.utcnow() - timedelta(days=30)

    # 123 has been active for two months
    mark_event('active', 123, now=now)
    mark_event('active', 123, now=last_month)

    # 224 has only been active last_month
    mark_event('active', 224, now=last_month)

    # Assert basic premises
    assert MonthEvents('active', last_month.year, last_month.month).get_count() == 2
    assert MonthEvents('active', now.year, now.month).get_count() == 1

    # Try out with bit AND operation
    active_2_months = BitOpAnd(
        MonthEvents('active', last_month.year, last_month.month),
        MonthEvents('active', now.year, now.month)
    )
    assert active_2_months.get_count() == 1
    assert 123 in active_2_months
    assert 224 not in active_2_months

    # Try out with bit OR operation
    assert BitOpOr(
        MonthEvents('active', last_month.year, last_month.month),
        MonthEvents('active', now.year, now.month)
    ).get_count() == 2

    # Try out with a different system
    active_2_months = BitOpAnd(
        'default_copy',
        MonthEvents('active', last_month.year, last_month.month),
        MonthEvents('active', now.year, now.month),
    )
    assert active_2_months.get_count() == 1
    assert active_2_months.system == 'default_copy'

    # Try nested operations
    active_2_months = BitOpAnd(
        BitOpAnd(
            MonthEvents('active', last_month.year, last_month.month),
            MonthEvents('active', now.year, now.month)
        ),
        MonthEvents('active', now.year, now.month)
    )

    assert 123 in active_2_months
    assert 224 not in active_2_months
