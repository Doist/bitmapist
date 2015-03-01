[![Build Status](https://travis-ci.org/Doist/bitmapist.svg?branch=master)](https://travis-ci.org/Doist/bitmapist)

bitmapist: a powerful analytics library for Redis
=================================================================

This Python library makes it possible to implement real-time, highly scalable analytics that can answer following questions:

* Has user 123 been online today? This week? This month?
* Has user 123 performed action "X"?
* How many users have been active have this month? This hour?
* How many unique users have performed action "X" this week?
* How many % of users that were active last week are still active?
* How many % of users that were active last month are still active this month?
* What users performed action "X"?

This library is very easy to use and enables you to create your own reports easily.

Using Redis bitmaps you can store events for millions of users in a very little amount of memory (megabytes).
You should be careful about using huge ids (e.g. 2^32 or bigger) as this could require larger amounts of memory.

Now with Cohort charts! Read more here:

* [Releasing bitmapist.cohort - or how we saved over $2000/month!](http://amix.dk/blog/post/19718)

If you want to read more about bitmaps please read following:

* http://blog.getspool.com/2011/11/29/fast-easy-realtime-metrics-using-redis-bitmaps/
* http://redis.io/commands/setbit
* http://en.wikipedia.org/wiki/Bit_array
* http://www.slideshare.net/crashlytics/crashlytics-on-redis-analytics
* http://amix.dk/blog/post/19714 [my blog post]

Requires Redis 2.6+ and newest version of redis-py.


Installation
============

Can be installed very easily via:

    $ sudo pip install bitmapist


Ports
=====

* PHP port: https://github.com/jeremyFreeAgent/Bitter


Examples
========

Setting things up:

```python
from datetime import datetime, timedelta
from bitmapist import setup_redis, delete_all_events, mark_event,\
                      MonthEvents, WeekEvents, DayEvents, HourEvents,\
                      BitOpAnd, BitOpOr

now = datetime.utcnow()
last_month = datetime.utcnow() - timedelta(days=30)
```

Mark user 123 as active and has played a song:

```python
mark_event('active', 123)
mark_event('song:played', 123)
```

Answer if user 123 has been active this month:

```python
assert 123 in MonthEvents('active', now.year, now.month)
assert 123 in MonthEvents('song:played', now.year, now.month)
assert MonthEvents('active', now.year, now.month).has_events_marked() == True
```


How many users have been active this week?:

```python
print len(WeekEvents('active', now.year, now.isocalendar()[1]))
```

If you're interested in "current events", you can omit extra `now.whatever`
arguments. Events will be populated with current time automatically.

For example, these two calls are equivalent:

```python

MonthEvents('active') == MonthEvents('active', now.year, now.month)

```

Additionally, for the sake of uniformity, you can create an event from
any datetime object with a `from_date` static method.

```python

MonthEvents('active').from_date(now) == MonthEvents('active', now.year, now.month)

```

Get the list of these users (user ids):

```python
print list(WeekEvents('active', now.year, now.isocalendar()[1]))
```

Perform bit operations. How many users that have been active last month are still active this month?

```python
active_2_months = BitOpAnd(
    MonthEvents('active', last_month.year, last_month.month),
    MonthEvents('active', now.year, now.month)
)
print len(active_2_months)

# Is 123 active for 2 months?
assert 123 in active_2_months
```

Alternatively, you can use standard Python syntax for bitwise operations.


```python
last_month_event = MonthEvents('active', last_month.year, last_month.month)
this_month_event = MonthEvents('active', now.year, now.month)
active_two_months = last_month_event & this_month_event
```
Operators `&`, `|`, `^` and `~` supported.

Work with nested bit operations (imagine what you can do with this ;-))!

```python
active_2_months = BitOpAnd(
    BitOpAnd(
        MonthEvents('active', last_month.year, last_month.month),
        MonthEvents('active', now.year, now.month)
    ),
    MonthEvents('active', now.year, now.month)
)
print len(active_2_months)
assert 123 in active_2_months

# Delete the temporary AND operation
active_2_months.delete()
```

There are special methods `prev` and `next` returning "sibling" events and
allowing you to walk through events in time without any sophisticated
iterators. A `delta` method allows you to "jump" forward or backward for
more than one step. Uniform API allows you to use all types of base events
(from hour to year) with the same code.

```python

current_month = MonthEvents()
prev_month = current_month.prev()
next_month = current_month.next()
year_ago = current_month.delta(-12)

```

Every event object has `period_start` and `period_end` methods to find a
time span of the event. This can be useful for caching values when the caching
of "events in future" is not desirable:

```python

ev = MonthEvent('active', dt)
if ev.period_end() < now:
    cache.set('active_users_<...>', len(ev))

```


As something new tracking hourly is disabled (to save memory!) To enable it as default do::

```python
import bitmapist
bitmapist.TRACK_HOURLY = True
```

Additionally you can supply an extra argument to `mark_event` to bypass the default value::

```python
mark_event('active', 123, track_hourly=False)
```

Copyright: 2012 by Doist Ltd.

License: BSD
