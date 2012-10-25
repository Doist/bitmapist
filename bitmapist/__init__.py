# -*- coding: utf-8 -*-
"""
bitmapist
~~~~~~~~~
Implements a powerful analytics library on top of Redis's support for bitmaps and bitmap operations.

This library makes it possible to implement real-time, highly scalable analytics that can answer following questions:

* Has user 123 been online today? This week? This month?
* Has user 123 performed action "X"?
* How many users have been active have this month? This hour?
* How many unique users have performed action "X" this week?
* How many % of users that were active last week are still active?
* How many % of users that were active last month are still active this month?

This library is very easy to use and enables you to create your own reports easily.

Using Redis bitmaps you can store events for millions of users in a very little amount of memory (megabytes).
You should be careful about using huge ids (e.g. 2^32 or bigger) as this could require larger amounts of memory.

If you want to read more about bitmaps please read following:
* http://blog.getspool.com/2011/11/29/fast-easy-realtime-metrics-using-redis-bitmaps/
* http://redis.io/commands/setbit
* http://en.wikipedia.org/wiki/Bit_array
* http://www.slideshare.net/crashlytics/crashlytics-on-redis-analytics

Requires Redis 2.6+ and newest version of redis-py.

Examples
========

Setting things up::

    from datetime import datetime, timedelta
    from bitmapist import mark_event, MonthEvents

    now = datetime.utcnow()
    last_month = datetime.utcnow() - timedelta(days=30)

Mark user 123 as active::

    mark_event('active', 123)

Answer if user 123 has been active this month::

    assert 123 in MonthEvents('active', now.year, now.month)

How many users have been active this week?::

    print len(WeekEvents('active', now.year, now.isocalendar()[1]))

Perform bit operations. Which users that have been active last month are still active this month?::

    active_2_months = BitOpAnd(
        MonthEvents('active', last_month.year, last_month.month),
        MonthEvents('active', now.year, now.month)
    )

Nest bit operations!::

    active_2_months = BitOpAnd(
        BitOpAnd(
            MonthEvents('active', last_month.year, last_month.month),
            MonthEvents('active', now.year, now.month)
        ),
        MonthEvents('active', now.year, now.month)
    )

:copyright: 2012 by Doist Ltd.
:developer: Amir Salihefendic ( http://amix.dk )
:license: BSD
"""
import types
import redis

from datetime import datetime


#--- Systems related ----------------------------------------------
SYSTEMS = {
    'default': redis.Redis(host='localhost', port=6379)
}

def setup_redis(name, host, port, **kw):
    """
    Setup a redis system.

    :param :name The name of the system
    :param :host The host of the redis installation
    :param :port The port of the redis installation
    :param :**kw Any additional keyword arguments will be passed to `redis.Redis`.

    Example::

        setup_redis('stats_redis', 'localhost', 6380)

        mark_event('active', 1, system='stats_redis')
    """
    SYSTEMS[name] = redis.Redis(host=host, port=port, **kw)

def get_redis(system='default'):
    """
    Get a redis-py client instance with entry `system`.

    :param :system The name of the system, extra systems can be setup via `setup_redis`
    """
    return SYSTEMS[system]


#--- Events marking and deleting ----------------------------------------------
def mark_event(event_name, uuid, system='default', now=None):
    """
    Marks an event for hours, days, weeks and months.

    :param :event_name The name of the event, could be "active" or "new_signups"
    :param :uuid An unique id, typically user id. The id should not be huge, read Redis documentation why (bitmaps)
    :param :system The Redis system to use
    :param :now Which date should be used as a reference point, default is `datetime.utcnow`

    Examples::

        # Mark id 1 as active
        mark_event('active', 1)

        # Mark task completed for id 252
        mark_event('tasks:completed', 252)
    """
    if not now:
        now = datetime.utcnow()

    stat_objs = (
        MonthEvents(event_name, now.year, now.month),
        WeekEvents(event_name, now.year, now.isocalendar()[1]),
        DayEvents(event_name, now.year, now.month, now.day),
        HourEvents(event_name, now.year, now.month, now.day, now.hour)
    )

    with get_redis(system).pipeline() as p:
        p.multi()
        for obj in stat_objs:
            p.setbit(obj.redis_key, uuid, 1)
        p.execute()


def delete_all_events(system='default'):
    """
    Delete all events from the database.
    """
    cli = get_redis(system)
    keys = cli.keys('trackist_*')
    if len(keys) > 0:
        cli.delete(*keys)


def delete_temporary_bitop_keys(system='default'):
    """
    Delete all temporary keys that are used when using bit operations.
    """
    cli = get_redis(system)
    keys = cli.keys('trackist_bitop_*')
    if len(keys) > 0:
        cli.delete(*keys)


#--- Events ----------------------------------------------
class MixinCounts:
    """
    Extends with an obj.get_count() that uses BITCOUNT to
    count all the events. Supports also __len__
    """
    def get_count(self):
        cli = get_redis(self.system)
        count = cli.bitcount(self.redis_key)
        return count

    def __len__(self):
        return self.get_count()


class MixinContains:
    """
    Makes it possible to see if an uuid has been marked.

    Example::

       user_active_today = 123 in DayEvents('active', 2012, 10, 23)
    """
    def __contains__(self, uuid):
        cli = get_redis(self.system)
        if cli.getbit(self.redis_key, uuid):
            return True
        else:
            return False


class MonthEvents(MixinCounts, MixinContains):
    """
    Events for a month.

    Example::

        MonthEvents('active', 2012, 10)
    """
    def __init__(self, event_name, year, month, system='default'):
        self.system = system
        self.redis_key = _prefix_key(event_name,
                                     '%s-%s' % (year, month))


class WeekEvents(MixinCounts, MixinContains):
    """
    Events for a week.

    Example::

        WeekEvents('active', 2012, 48)
    """
    def __init__(self, event_name, year, week, system='default'):
        self.system = system
        self.redis_key = _prefix_key(event_name, 'W%s-%s' % (year, week))


class DayEvents(MixinCounts, MixinContains):
    """
    Events for a day.

    Example::

        DayEvents('active', 2012, 10, 23)
    """
    def __init__(self, event_name, year, month, day, system='default'):
        self.system = system
        self.redis_key = _prefix_key(event_name,
                                     '%s-%s-%s' % (year, month, day))


class HourEvents(MixinCounts, MixinContains):
    """
    Events for a hour.

    Example::

        HourEvents('active', 2012, 10, 23, 13)
    """
    def __init__(self, event_name, year, month, day, hour, system='default'):
        self.system = system
        self.redis_key = _prefix_key(event_name,
                                     '%s-%s-%s-%s' %\
                                         (year, month, day, hour))


#--- Bit operations ----------------------------------------------
class BitOperation:

    """
    Base class for bit operations (AND, OR, XOR).

    Please note that each bit operation creates a new key prefixed with `trackist_bitop_`.
    These temporary keys can be deleted with `delete_temporary_bitop_keys`.

    You can even nest bit operations.

    Example::

        active_2_months = BitOpAnd(
            MonthEvents('active', last_month.year, last_month.month),
            MonthEvents('active', now.year, now.month)
        )

        active_2_months = BitOpAnd(
            BitOpAnd(
                MonthEvents('active', last_month.year, last_month.month),
                MonthEvents('active', now.year, now.month)
            ),
            MonthEvents('active', now.year, now.month)
        )

    """

    def __init__(self, op_name, system_or_event, *events):
        # Smartly resolve system_or_event, makes it possible to build a cleaner API
        if hasattr(system_or_event, 'redis_key'):
            events = list(events)
            events.insert(0, system_or_event)
            system = self.system = 'default'
        else:
            system = self.system = system_or_event

        event_redis_keys = [ev.redis_key for ev in events]

        self.redis_key = 'trackist_bitop_%s_%s' % (op_name,
                                                   '-'.join(event_redis_keys))

        cli = get_redis(system)
        cli.bitop(op_name, self.redis_key, *event_redis_keys)


class BitOpAnd(BitOperation, MixinContains, MixinCounts):

    def __init__(self, system_or_event, *events):
        BitOperation.__init__(self, 'AND', system_or_event, *events)

class BitOpOr(BitOperation, MixinContains, MixinCounts):

    def __init__(self, system_or_event, *events):
        BitOperation.__init__(self, 'OR', system_or_event, *events)

class BitOpXor(BitOperation, MixinContains, MixinCounts):

    def __init__(self, system_or_event, *events):
        BitOperation.__init__(self, 'XOR', system_or_event, *events)


#--- Private ----------------------------------------------
def _prefix_key(event_name, date):
    return 'trackist_%s_%s' % (event_name, date)
