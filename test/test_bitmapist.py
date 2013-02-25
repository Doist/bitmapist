# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import unittest

from bitmapist import Bitmapist
import redis

client = redis.Redis('localhost', 6380)
bm = Bitmapist(client)


def test_mark_with_diff_days():
    bm.delete_all_events()

    bm.mark_event('active', 123)

    now = datetime.utcnow()

    # Month
    month_ago = now - timedelta(days=30)

    assert 123 in bm.get_month_event('active', now)
    assert 124 not in bm.get_month_event('active', now)
    assert 123 not in bm.get_week_event('active', month_ago)

    # Week
    week_ago = now - timedelta(days=7)
    assert 123 in bm.get_week_event('active', now)
    assert 124 not in bm.get_week_event('active', now)
    assert 123 not in bm.get_week_event('active', week_ago)

    # Day
    day_ago = now - timedelta(days=1)

    assert 123 in bm.get_day_event('active', now)
    assert 124 not in bm.get_day_event('active', now)
    assert 123 not in bm.get_day_event('active', day_ago)

    # Hour
    hour_ago = now - timedelta(hours=1)
    assert 123 in bm.get_hour_event('active', now)
    assert 124 not in bm.get_hour_event('active', now)
    assert 123 not in bm.get_hour_event('active', hour_ago)
    assert 124 not in bm.get_hour_event('active', hour_ago)


def test_mark_counts():
    bm.delete_all_events()

    now = datetime.utcnow()

    assert bm.get_month_event('active', now).get_count() == 0

    bm.mark_event('active', 123)
    bm.mark_event('active', 23232)

    assert len(bm.get_month_event('active', now)) == 2


def test_mark_attribute_multi_with_invalid_mark_as():
    bm.delete_all_events()
    assert bm.get_attribute('active').get_count() == 0
    try:
        bm.mark_attribute('active', 123, 4)
    except ValueError:
        pass
    else:
        raise Exception('No error thrown when expected')


def test_mark_attribute_multi_with_mark_as_works():
    bm.delete_all_events()
    assert bm.get_attribute('active').get_count() == 0
    bm.mark_attribute('active', 123)
    assert bm.get_attribute('active').get_count() == 1
    bm.mark_attribute('active', 123, 0)
    assert bm.get_attribute('active').get_count() == 0


def test_mark_attribute_counts_multi():
    bm.delete_all_events()

    assert bm.get_attribute('active').get_count() == 0

    bm.mark_attribute_multi('active', [123, 23232])

    assert len(bm.get_attribute('active')) == 2
    assert 123 in bm.get_attribute('active')
    assert 23232 in bm.get_attribute('active')


def test_mark_attribute_counts():
    bm.delete_all_events()

    assert bm.get_attribute('active').get_count() == 0

    bm.mark_attribute('active', 123)
    bm.mark_attribute('active', 23232)

    assert len(bm.get_attribute('active')) == 2


def test_different_dates():
    bm.delete_all_events()

    now = datetime.utcnow()
    yesterday = now - timedelta(days=1)

    bm.mark_event('active', 123, now=now)
    bm.mark_event('active', 23232, now=yesterday)

    assert bm.get_day_event('active', now).get_count() == 1

    assert bm.get_day_event('active', yesterday).get_count() == 1


def test_different_buckets():
    bm.delete_all_events()

    now = datetime.utcnow()

    bm.mark_event('active', 123)
    bm.mark_event('tasks_completed', 23232)

    assert bm.get_month_event('active', now).get_count() == 1
    assert bm.get_month_event('tasks_completed', now).get_count() == 1


def test_bit_operations():
    bm.delete_all_events()

    now = datetime.utcnow()
    last_month = datetime.utcnow() - timedelta(days=30)

    # 123 has been active for two months
    bm.mark_event('active', 123, now=now)
    bm.mark_event('active', 123, now=last_month)

    # 224 has only been active last_month
    bm.mark_event('active', 224, now=last_month)

    # Assert basic premises
    assert bm.get_month_event('active', last_month).get_count() == 2
    assert bm.get_month_event('active', now).get_count() == 1

    # Try out with bit AND operation
    active_2_months = bm.bit_op_and(
        bm.get_month_event('active', last_month),
        bm.get_month_event('active', now)
    )
    assert active_2_months.get_count() == 1
    assert 123 in active_2_months
    assert 224 not in active_2_months

    # Try out with bit OR operation
    assert bm.bit_op_or(
        bm.get_month_event('active', last_month),
        bm.get_month_event('active', now)
    ).get_count() == 2

    # Try nested operations
    active_2_months = bm.bit_op_and(
        bm.bit_op_and(
            bm.get_month_event('active', last_month),
            bm.get_month_event('active', now)
        ),
        bm.get_month_event('active', now)
    )

    assert 123 in active_2_months
    assert 224 not in active_2_months


def test_bit_operation_not():
    bm.delete_all_events()
    bm.mark_attribute('paid_user', 4)
    bm.mark_attribute('paid_user', 7)
    assert len(bm.bit_op_not(bm.get_attribute('paid_user'))) == 6

    bm.mark_attribute('paid_user', 9)
    assert len(bm.bit_op_not(bm.get_attribute('paid_user'))) == 13


def test_events_marked():
    bm.delete_all_events()

    now = datetime.utcnow()

    assert bm.get_month_event('active', now).get_count() == 0
    assert bm.get_month_event('active', now).has_events_marked() == False

    bm.mark_event('active', 123, now=now)

    assert bm.get_month_event('active', now).get_count() == 1
    assert bm.get_month_event('active', now).has_events_marked() == True


def test_attributes_marked():
    bm.delete_all_events()

    assert bm.get_attribute('paid_user').get_count() == 0

    bm.mark_attribute('paid_user', 123)

    assert bm.get_attribute('paid_user').get_count() == 1
    assert 123 in bm.get_attribute('paid_user')


def test_attribute_get_count():
    bm.delete_all_events()

    assert bm.get_attribute('paid_user').get_count() == 0

    bm.mark_attribute_multi('paid_user', range(123, 144))
    assert bm.get_attribute('paid_user').get_count() == 21
    assert bm.get_attribute('paid_user').get_count(120, 128) == 5
    assert bm.get_attribute('paid_user').get_count(128, 136) == 8
    assert bm.get_attribute('paid_user').get_count(128, 144) == 16
    assert bm.get_attribute('paid_user').get_count(128, 146) == 16
    assert bm.get_attribute('paid_user').get_count(120, 136) == 13
    assert bm.get_attribute('paid_user').get_count(132, 140) == 8
    assert bm.get_attribute('paid_user').get_count(136, 139) == 3


def test_event_get_count():
    bm.delete_all_events()
    now = datetime.utcnow()

    assert bm.get_month_event('active', now).get_count() == 0

    for uid in xrange(123, 144):
        bm.mark_event('active', uid, now)
    assert bm.get_month_event('active', now).get_count() == 21
    assert bm.get_month_event('active', now).get_count(120, 128) == 5
    assert bm.get_month_event('active', now).get_count(128, 136) == 8
    assert bm.get_month_event('active', now).get_count(128, 144) == 16
    assert bm.get_month_event('active', now).get_count(128, 146) == 16
    assert bm.get_month_event('active', now).get_count(120, 136) == 13
    assert bm.get_month_event('active', now).get_count(132, 140) == 8
    assert bm.get_month_event('active', now).get_count(136, 139) == 3


def test_set_divider():
    bm2 = Bitmapist(client, divider='_')
    bm2.delete_all_events()
    bm2.mark_attribute('paiduser', 123)
    assert 'trackist_at_paiduser' in \
        client.keys()


def test_set_key_prefix():
    bm2 = Bitmapist(client, prefix='HELLO')
    bm2.delete_all_events()
    bm2.mark_attribute('paid_user', 123)
    assert 'HELLO:at:paid_user' in \
        client.keys()


def test_get_all_event_names():
    bm.delete_all_events()

    bm.mark_event('signed-up', 123)
    bm.mark_event('logged-on', 123)

    event_names = bm.get_all_event_names()
    assert set(['signed-up', 'logged-on']) == set(event_names)


def test_get_all_attribute_names():
    bm.delete_all_events()

    bm.mark_attribute('sad', 123)
    bm.mark_attribute('happy', 123)

    att_names = bm.get_all_attribute_names()
    assert set(['happy', 'sad']) == set(att_names)
