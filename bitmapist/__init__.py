# -*- coding: utf-8 -*-
"""
bitmapist
~~~~~~~~~
Implements a powerful analytics library on top of Redis's support for bitmaps and bitmap operations.

This library makes it possible to implement real-time, highly scalable analytics that can answer following questions:

* Has user 123 been online today? This week? This month? This year?
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

As something new tracking hourly is disabled (to save memory!) To enable it as default do::

    import bitmapist
    bitmapist.TRACK_HOURLY = True

Additionally you can supply an extra argument to mark_event to bypass the default value::

    mark_event('active', 123, track_hourly=False)

:copyright: 2012 by Doist Ltd.
:developer: Amir Salihefendic ( http://amix.dk )
:license: BSD
"""
from builtins import range, bytes

import threading
import redis
import calendar
from collections import defaultdict
from datetime import datetime, date, timedelta

local_thread = threading.local()

# --- Systems related

SYSTEMS = {
    'default': redis.StrictRedis(host='localhost', port=6379)
}

# Should hourly be tracked as default?
# Note that this can have huge implications in amounts
# of memory that Redis uses (especially with huge integers)
TRACK_HOURLY = False

# Should unique events be tracked as default?
TRACK_UNIQUE = False


def setup_redis(name, host, port, **kw):
    """
    Setup a redis system.

    :param :name The name of the system
    :param :host The host of the redis installation
    :param :port The port of the redis installation
    :param :**kw Any additional keyword arguments will be passed to `redis.StrictRedis`.

    Example::

        setup_redis('stats_redis', 'localhost', 6380)

        mark_event('active', 1, system='stats_redis')
    """
    redis_client = kw.pop('redis_client', redis.StrictRedis)
    SYSTEMS[name] = redis_client(host=host, port=port, **kw)


def get_redis(system='default'):
    """
    Get a redis-py client instance with entry `system`.

    :param :system The name of the system, redis.StrictRedis or redis.Pipeline
        instance, extra systems can be setup via `setup_redis`
    """
    if isinstance(system, redis.StrictRedis):
        return system
    else:
        return SYSTEMS[system]


# --- Events marking and deleting

def mark_event(event_name, uuid, system='default', now=None, track_hourly=None,
               track_unique=None, use_pipeline=True):
    """
    Marks an event for hours, days, weeks and months.

    :param :event_name The name of the event, could be "active" or "new_signups"
    :param :uuid An unique id, typically user id. The id should not be huge,
        read Redis documentation why (bitmaps)
    :param :system The Redis system to use (string, Redis instance, or Pipeline
        instance).
    :param :now Which date should be used as a reference point, default is
        `datetime.utcnow()`
    :param :track_hourly Should hourly stats be tracked, defaults to
        bitmapist.TRACK_HOURLY
    :param :track_unique Should unique stats be tracked, defaults to
        bitmapist.TRACK_UNIQUE
    :param :use_pipeline Boolean flag indicating if the command should use
        pipelines or not. You may want to avoid using pipeline within the
        command if you provide the pipeline object in `system` argument and
        want to manage the pipe execution yourself.

    Examples::

        # Mark id 1 as active
        mark_event('active', 1)

        # Mark task completed for id 252
        mark_event('tasks:completed', 252)
    """
    _mark(event_name, uuid, system, now, track_hourly, track_unique, use_pipeline, value=1)


def unmark_event(event_name, uuid, system='default', now=None, track_hourly=None,
                 track_unique=None, use_pipeline=True):
    _mark(event_name, uuid, system, now, track_hourly, track_unique, use_pipeline, value=0)


def _mark(event_name, uuid, system='default', now=None,
          track_hourly=None, track_unique=None, use_pipeline=True, value=1):
    if track_hourly is None:
        track_hourly = TRACK_HOURLY
    if track_unique is None:
        track_unique = TRACK_UNIQUE

    if not now:
        now = datetime.utcnow()

    obj_classes = [MonthEvents, WeekEvents, DayEvents]
    if track_hourly:
        obj_classes.append(HourEvents)
    if track_unique:
        obj_classes.append(UniqueEvents)

    client = get_redis(system)
    if use_pipeline:
        client = client.pipeline()

    for obj_class in obj_classes:
        client.setbit(obj_class.from_date(event_name, now).redis_key, uuid, value)

    if use_pipeline:
        client.execute()


def mark_unique(event_name, uuid, system='default'):
    """
    Mark unique event

    Unique event (aka "user flag") is an event which doesn't depend on date.
    Can be used for storing user properties, A/B testing, extra filtering, etc.

    :param :event_name The name of the event, could be "active" or "new_signups"
    :param :uuid An unique id, typically user id. The id should not be huge,
        read Redis documentation why (bitmaps)
    :param :system The Redis system to use (string, Redis instance, or Pipeline

    Examples::

        # Mark id 42 as premium
        mark_unique('premium', 42)
    """
    _mark_unique(event_name, uuid, system, value=1)


def unmark_unique(event_name, uuid, system='default'):
    """
    Unmark unique event

    Unique event (aka "user flag") is an event which doesn't depend on date.
    Can be used for storing user properties, A/B testing, extra filtering, etc.

    :param :event_name The name of the event, could be "active" or "new_signups"
    :param :uuid An unique id, typically user id. The id should not be huge,
        read Redis documentation why (bitmaps)
    :param :system The Redis system to use (string, Redis instance, or Pipeline

    Examples::

        # Mark id 42 as not premium anymore
        unmark_unique('premium', 42)
    """
    _mark_unique(event_name, uuid, system, value=0)


def _mark_unique(event_name, uuid, system='default', value=1):
    get_redis(system).setbit(UniqueEvents(event_name).redis_key, uuid, value)


def get_event_names(system='default', prefix='', batch=10000):
    """
    Return the list of all event names, with no particular order. Optional
    `prefix` value is used to filter only subset of keys
    """
    cli = get_redis(system)
    expr = 'trackist_%s*' % prefix
    ret = set()
    for result in cli.scan_iter(match=expr, count=batch):
        result = result.decode()
        chunks = result.split('_')
        event_name = '_'.join(chunks[1:-1])
        if not event_name.startswith('bitop_'):
            ret.add(event_name)
    return list(ret)


def delete_all_events(system='default'):
    """
    Delete all events from the database.
    """
    cli = get_redis(system)
    keys = cli.keys('trackist_*')
    if keys:
        cli.delete(*keys)


def delete_temporary_bitop_keys(system='default'):
    """
    Delete all temporary keys that are used when using bit operations.
    """
    cli = get_redis(system)
    keys = cli.keys('trackist_bitop_*')
    if keys:
        cli.delete(*keys)


def delete_runtime_bitop_keys():
    """
    Delete all BitOp keys that were created.
    """
    bitop_keys = _bitop_keys()
    for system in bitop_keys:
        if len(bitop_keys[system]) > 0:
            cli = get_redis(system)
            cli.delete(*bitop_keys[system])
    bitop_keys.clear()


# --- Events

class MixinIter:
    """
    Extends with an obj.get_uuids() returning the iterator of uuids in a key
    (unpacks the key)
    """
    def get_uuids(self):
        cli = get_redis(self.system)
        val = cli.get(self.redis_key)
        if val is None:
            return

        val = bytes(val)

        for char_num, char in enumerate(val):
            # shortcut
            if char == 0:
                continue
            # find set bits, generate smth like [1, 0, ...]
            bits = [(char >> i) & 1 for i in range(7, -1, -1)]
            # list of positions with ones
            set_bits = list(pos for pos, val in enumerate(bits) if val)
            # yield everything we need
            for bit in set_bits:
                yield char_num * 8 + bit

    def __iter__(self):
        for item in self.get_uuids():
            yield item


class MixinBitOperations:

    def __invert__(self):
        return BitOpNot(self)

    def __or__(self, other):
        return BitOpOr(self, other)

    def __and__(self, other):
        return BitOpAnd(self, other)

    def __xor__(self, other):
        return BitOpXor(self, other)


class MixinEventsMisc:
    """
    Extends with an obj.has_events_marked()
    that returns `True` if there are any events marked,
    otherwise `False` is returned.

    Extens also with a obj.delete()
    (useful for deleting temporary calculations).
    """
    def has_events_marked(self):
        cli = get_redis(self.system)
        return cli.exists(self.redis_key)

    def delete(self):
        cli = get_redis(self.system)
        cli.delete(self.redis_key)

    def __eq__(self, other):
        other_key = getattr(other, 'redis_key', None)
        if other_key is None:
            return NotImplemented
        return self.redis_key == other_key


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


class UniqueEvents(MixinIter, MixinCounts, MixinContains,
                   MixinEventsMisc, MixinBitOperations):

    @classmethod
    def from_date(cls, event_name, dt=None, system='default'):
        return cls(event_name, system=system)

    def __init__(self, event_name, system='default'):
        self.event_name = event_name
        self.system = system
        self.redis_key = _prefix_key(event_name, 'u')

    def next(self):
        return self

    def prev(self):
        return self


class GenericPeriodEvents(MixinIter, MixinCounts, MixinContains,
                          MixinEventsMisc, MixinBitOperations):

    def next(self):
        """ next object in a datetime line """
        return self.delta(value=1)

    def prev(self):
        """ prev object in a datetime line """
        return self.delta(value=-1)


class YearEvents(GenericPeriodEvents):
    """
    Events for a year.

    Example::

        YearEvents('active', 2012)
    """
    @classmethod
    def from_date(cls, event_name, dt=None, system='default'):
        dt = dt or datetime.utcnow()
        return cls(event_name, dt.year, system=system)

    def __init__(self, event_name, year=None, system='default'):
        now = datetime.utcnow()
        self.event_name = event_name
        self.year = not_none(year, now.year)
        self.system = system

        months = []
        for m in range(1, 13):
            months.append(MonthEvents(event_name, self.year, m, system))
        or_op = BitOpOr(system, *months)
        self.redis_key = or_op.redis_key

    def delta(self, value):
        return self.__class__(self.event_name, self.year + value, self.system)

    def period_start(self):
        return datetime(self.year, 1, 1)

    def period_end(self):
        return datetime(self.year, 12, 31, 23, 59, 59, 999999)


class MonthEvents(GenericPeriodEvents):
    """
    Events for a month.

    Example::

        MonthEvents('active', 2012, 10)
    """
    @classmethod
    def from_date(cls, event_name, dt=None, system='default'):
        dt = dt or datetime.utcnow()
        return cls(event_name, dt.year, dt.month, system=system)

    def __init__(self, event_name, year=None, month=None, system='default'):
        now = datetime.utcnow()
        self.event_name = event_name
        self.year = not_none(year, now.year)
        self.month = not_none(month, now.month)
        self.system = system
        self.redis_key = _prefix_key(event_name,
                                     '%s-%s' % (self.year, self.month))

    def delta(self, value):
        year, month = add_month(self.year, self.month, value)
        return self.__class__(self.event_name, year, month, self.system)

    def period_start(self):
        return datetime(self.year, self.month, 1)

    def period_end(self):
        _, day = calendar.monthrange(self.year, self.month)
        return datetime(self.year, self.month, day, 23, 59, 59, 999999)


class WeekEvents(GenericPeriodEvents):
    """
    Events for a week.

    Example::

        WeekEvents('active', 2012, 48)
    """
    @classmethod
    def from_date(cls, event_name, dt=None, system='default'):
        dt = dt or datetime.utcnow()
        dt_year, dt_week, _ = dt.isocalendar()
        return cls(event_name, dt_year, dt_week, system=system)

    def __init__(self, event_name, year=None, week=None, system='default'):
        now = datetime.utcnow()
        now_year, now_week, _ = now.isocalendar()
        self.event_name = event_name
        self.year = not_none(year, now_year)
        self.week = not_none(week, now_week)
        self.system = system
        self.redis_key = _prefix_key(event_name, 'W%s-%s' % (self.year, self.week))

    def delta(self, value):
        dt = iso_to_gregorian(self.year, self.week + value, 1)
        year, week, _ = dt.isocalendar()
        return self.__class__(self.event_name, year, week, self.system)

    def period_start(self):
        s = iso_to_gregorian(self.year, self.week, 1)  # mon
        return datetime(s.year, s.month, s.day)

    def period_end(self):
        e = iso_to_gregorian(self.year, self.week, 7)  # mon
        return datetime(e.year, e.month, e.day, 23, 59, 59, 999999)


class DayEvents(GenericPeriodEvents):
    """
    Events for a day.

    Example::

        DayEvents('active', 2012, 10, 23)
    """
    @classmethod
    def from_date(cls, event_name, dt=None, system='default'):
        dt = dt or datetime.utcnow()
        return cls(event_name, dt.year, dt.month, dt.day, system=system)

    def __init__(self, event_name, year=None, month=None, day=None, system='default'):
        now = datetime.utcnow()
        self.event_name = event_name
        self.year = not_none(year, now.year)
        self.month = not_none(month, now.month)
        self.day = not_none(day, now.day)
        self.system = system
        self.redis_key = _prefix_key(event_name,
                                     '%s-%s-%s' % (self.year, self.month, self.day))

    def delta(self, value):
        dt = date(self.year, self.month, self.day) + timedelta(days=value)
        return self.__class__(self.event_name, dt.year, dt.month, dt.day, self.system)

    def period_start(self):
        return datetime(self.year, self.month, self.day)

    def period_end(self):
        return datetime(self.year, self.month, self.day, 23, 59, 59, 999999)


class HourEvents(GenericPeriodEvents):
    """
    Events for a hour.

    Example::

        HourEvents('active', 2012, 10, 23, 13)
    """
    @classmethod
    def from_date(cls, event_name, dt=None, system='default'):
        dt = dt or datetime.utcnow()
        return cls(event_name, dt.year, dt.month, dt.day, dt.hour, system=system)

    def __init__(self, event_name, year=None, month=None, day=None, hour=None, system='default'):
        now = datetime.utcnow()
        self.event_name = event_name
        self.year = not_none(year, now.year)
        self.month = not_none(month, now.month)
        self.day = not_none(day, now.day)
        self.hour = not_none(hour, now.hour)
        self.system = system
        self.redis_key = _prefix_key(event_name,
                                     '%s-%s-%s-%s' %
                                     (self.year, self.month, self.day, self.hour))

    def delta(self, value):
        dt = datetime(self.year, self.month, self.day, self.hour) + timedelta(hours=value)
        return self.__class__(self.event_name, dt.year, dt.month, dt.day, dt.hour, self.system)

    def period_start(self):
        return datetime(self.year, self.month, self.day, self.hour)

    def period_end(self):
        return datetime(self.year, self.month, self.day, self.hour, 59, 59, 999999)


# --- Bit operations


class BitOperation(MixinIter, MixinContains, MixinCounts, MixinEventsMisc,
                   MixinBitOperations):

    """
    Base class for bit operations (AND, OR, XOR).

    Please note that each bit operation creates a new key prefixed with `trackist_bitop_`.
    These temporary keys can be deleted with `delete_temporary_bitop_keys` or
    `delete_runtime_bitop_keys`.

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
        _bitop_keys()[system].add(self.redis_key)

        cli = get_redis(system)
        cli.bitop(op_name, self.redis_key, *event_redis_keys)


class BitOpAnd(BitOperation):

    def __init__(self, system_or_event, *events):
        BitOperation.__init__(self, 'AND', system_or_event, *events)


class BitOpOr(BitOperation):

    def __init__(self, system_or_event, *events):
        BitOperation.__init__(self, 'OR', system_or_event, *events)


class BitOpXor(BitOperation):

    def __init__(self, system_or_event, *events):
        BitOperation.__init__(self, 'XOR', system_or_event, *events)


class BitOpNot(BitOperation):

    def __init__(self, system_or_event, *events):
        BitOperation.__init__(self, 'NOT', system_or_event, *events)


# --- Private

def _prefix_key(event_name, date):
    return 'trackist_%s_%s' % (event_name, date)


# --- Helper functions

def add_month(year, month, delta):
    """
    Helper function which adds `delta` months to current `(year, month)` tuple
    and returns a new valid tuple `(year, month)`
    """
    year, month = divmod(year * 12 + month + delta, 12)
    if month == 0:
        month = 12
        year = year - 1
    return year, month


def not_none(*keys):
    """
    Helper function returning first value which is not None
    """
    for key in keys:
        if key is not None:
            return key


def iso_year_start(iso_year):
    "The gregorian calendar date of the first day of the given ISO year"
    fourth_jan = date(iso_year, 1, 4)
    delta = timedelta(fourth_jan.isoweekday()-1)
    return fourth_jan - delta


def iso_to_gregorian(iso_year, iso_week, iso_day):
    "Gregorian calendar date for the given ISO year, week and day"
    year_start = iso_year_start(iso_year)
    return year_start + timedelta(days=iso_day-1, weeks=iso_week-1)


def _bitop_keys():
    """Hold created BitOp keys (per thread)"""
    v = getattr(local_thread, 'bitop_keys', None)
    if v is None:
        v = defaultdict(set)
        setattr(local_thread, 'bitop_keys', v)
    return v
