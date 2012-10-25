#!/usr/bin/env python
# Copyright (c) 2007 Qtrac Ltd. All rights reserved.
# This module is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

import os

from setuptools import setup

setup(name='bitmapist',
      version = '1.4',
      author="amix",
      author_email="amix@amix.dk",
      url="http://www.amix.dk/",
      install_requires = ['redis>=2.7.1'],
      classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
      ],
      packages=['bitmapist', 'test'],
      platforms=["Any"],
      license="BSD",
      keywords='redis bitmap analytics bitmaps realtime',
      description="Implements a powerful analytics library using Redis bitmaps.",
      long_description="""\
bitmapist
---------------
Implements a powerful analytics library using Redis bitmaps.

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
* http://amix.dk/blog/post/19714 [my blog post]

Requires Redis 2.6+ and newest version of redis-py.

Examples
---------------

Setting things up::

    from datetime import datetime, timedelta
    from bitmapist import setup_redis, delete_all_events, mark_event,\
                          MonthEvents, WeekEvents, DayEvents, HourEvents,\
                          BitOpAnd, BitOpOr

    now = datetime.utcnow()
    last_month = datetime.utcnow() - timedelta(days=30)

Mark user 123 as active and has played a song::

    mark_event('active', 123)
    mark_event('song:played', 123)

Answer if user 123 has been active this month::

    assert 123 in MonthEvents('active', now.year, now.month)
    assert 123 in MonthEvents('song:played', now.year, now.month)

How many users have been active this week?::

    print len(WeekEvents('active', now.year, now.isocalendar()[1]))

Perform bit operations. How many users that have been active last month are still active this month?::

    active_2_months = BitOpAnd(
        MonthEvents('active', last_month.year, last_month.month),
        MonthEvents('active', now.year, now.month)
    )
    print len(active_2_months)

    # Is 123 active for 2 months?
    assert 123 in active_2_months

Work with nested bit operations (imagine what you can do with this ;-))::

    active_2_months = BitOpAnd(
        BitOpAnd(
            MonthEvents('active', last_month.year, last_month.month),
            MonthEvents('active', now.year, now.month)
        ),
        MonthEvents('active', now.year, now.month)
    )
    print len(active_2_months)
    assert 123 in active_2_months

Copyright: 2012 by Doist Ltd.

Developer: Amir Salihefendic ( http://amix.dk )

License: BSD""")
