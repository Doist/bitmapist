bitmapist: a powerful analytics library for Redis
=================================================================

This Python library makes it possible to implement real-time, highly scalable analytics that can answer following questions:

* Has user 123 been online today? This week? This month?
* Has user 123 performed action "X"?
* How many users have been active have this month? This hour?
* How many unique users have performed action "X" this week?
* How many % of users that were active last week are still active?
* How many % of users that were active last month are still active this month?

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
import redis
from datetime import datetime, timedelta
from bitmapist import Bitmapist

bm = Bitmapist(redis_client=redis.Redis('localhost', 6379))

now = datetime.utcnow()
last_month = datetime.utcnow() - timedelta(days=30)
```

Mark user 123 as active and has played a song:

```python
bm.mark_event('active', 123)
bm.mark_event('song:played', 123)
```

Mark user 123 as a paid user:

```python
bm.mark_attribute('paid_user', 123)
```

Answer if user 123 has been active this month:

```python
assert 123 in bm.get_month_event('active', now)
assert bm.get_month_event('active', now).has_events_marked() == True
```

How many users have been active this week?:

```python
print len(bm.get_week_event('active', now))
```

Perform bit operations. How many users that have been active last month are still active this month?

```python
active_2_months = bm.bit_op_and(
    bm.get_month_event('active', last_month),
    bm.get_month_event('active', now),
)
print len(active_2_months)

# Is 123 active for 2 months?
assert 123 in active_2_months
```

Work with nested bit operations (imagine what you can do with this ;-))!

```python
active_2_months = bm.bit_op_and(
    bm.bit_op_and(
        bm.get_month_event('active', last_month),
        bm.get_month_event('active', now),
    ),
    bm.get_attribute('paid_user')
)
print len(active_2_months)
assert 123 in active_2_months
```

Copyright: 2012 by Doist Ltd.

Developer: Amir Salihefendic ( http://amix.dk )

License: BSD
