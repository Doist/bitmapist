#!/usr/bin/env python
# Copyright (c) 2007 Qtrac Ltd. All rights reserved.
# This module is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

import os

from setuptools import setup

setup(name='bitmapist',
      version='2.6.3',
      author="amix",
      author_email="amix@amix.dk",
      url="http://www.amix.dk/",
      install_requires=['redis>=2.7.2.1', 'mako', 'python-dateutil>=2.1'],
      dependency_links=['https://github.com/yayalice/redis-py/tarball/master#egg=redis-2.7.2.1'],
      classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
      ],
      packages=['bitmapist', 'bitmapist.cohort'],
      include_package_data=True,
      zip_safe=False,
      platforms=["Any"],
      license="BSD",
      keywords='redis bitmap analytics bitmaps realtime cohort',
      description="Implements a powerful analytics library using Redis bitmaps.",
      long_description="""\
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
    from bitmapist import Bitmapist

    bm = Bitmapist(redis_client=redis.Redis('localhost', 6379))

    now = datetime.utcnow()
    last_month = datetime.utcnow() - timedelta(days=30)

Mark user 123 as active::

    bm.mark_event('active', 123)

Mark user 123 as a paid_user:

    bm.mark_attribute('paid_user', 123)

Answer if user 123 has been active this month::

    assert 123 in bm.get_month_event('active', now)

How many users have been active this week?::

    print len(bm.get_week_event('active', now))

Perform bit operations. Which users that have been active last month are still active this month?::

    active_2_months = bm.bit_op_and(
        bm.get_month_event('active', last_month),
        bm.get_month_event('active', now),
    )

Nest bit operations!::

    active_2_months = bm.bit_op_and(
        bm.bit_op_and(
            bm.get_month_event('active', last_month),
            bm.get_month_event('active', now),
        ),
        bm.get_attribute('paid_user')
    )

:copyright: 2012 by Doist Ltd.
:developer: Amir Salihefendic ( http://amix.dk )
:license: BSD""")
