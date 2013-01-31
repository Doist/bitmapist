# -*- coding: utf-8 -*-
"""
bitmapist.cohort
~~~~~~~~~~~~~~~~
Implements cohort analytics on top of the data stored in bitmapist.

This library makes it possible to implement real-time, highly scalable analytics that can answer following questions:

* Generate a cohort table over real-time data stored in bitmapist
* How many % of users that were active last [days, weeks, months] are still active?
* How many % of users that performed action X also performed action Y (and this over time)

A screenshot of the library in action:
https://d2dq6e731uoz0t.cloudfront.net/d5b299fafecc15eb3ea9f7f12f70a061/as/cohort.png

If you want to read more about cohort please read following:
* http://en.wikipedia.org/wiki/Cohort_(statistics)
* https://mixpanel.com/docs/learn-the-features/retention-overview [ I was inspired by this, but didn't want to pay the steep price ]


Examples
========

Mark user 123 as active and mark some other events::

    from bitmapist import mark_event

    mark_event('active', 123)
    mark_event('song:add', 123)
    mark_event('song:play', 123)

Generate the form that makes it easy to query the bitmapist database::

    html_form = bitmapist_cohort.render_html_form(
        action_url='/_Cohort',
        selections1=[ ('Are Active', 'active'), ],
        selections2=[ ('Played song', 'song:play'), ],
        time_group='days',
        select1='active',
        select2='song:play'
    )

    # action_url is the action URL of the <form> element
    # selections1, selections2 specifies the events that the user can select in the form
    # time_group can be `days`, `weeks` or `months`
    # select1, select2 specifies the current selected events in the <form>

Get the data and render it via HTML::

    dates_data = bitmapist_cohort.get_dates_data(select1='active',
                                                 select2='song:play',
                                                 time_group='days',
                                                 system='default')

    html_data = bitmapist_cohort.render_html_data(dates_data,
                                                  time_group='days')

    # All the arguments should come from the FORM element (html_form)
    # but to make things more clear I have filled them in directly

:copyright: 2012 by Doist Ltd.
:developer: Amir Salihefendic ( http://amix.dk )
:license: BSD
"""
from os import path

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from mako.lookup import TemplateLookup

from bitmapist import WeekEvents, DayEvents, MonthEvents, BitOpAnd


#--- HTML rendering ----------------------------------------------
def render_html_form(action_url, selections1, selections2,
                     time_group='days', select1=None, select2=None):
    """
    Render a HTML form that can be used to query the data in bitmapist.

    :param :action_url The action URL of the <form> element. The form will always to a GET request.
    :param :selections1 A list of selections that the user can filter by, example `[ ('Are Active', 'active'), ]`
    :param :selections2 A list of selections that the user can filter by, example `[ ('Played song', 'song:play'), ]`
    :param :time_group What data should be clustred by, can be `days`, `weeks` or `months`
    :param :select1 What is the current selected filter (first)
    :param :select2 What is the current selected filter (second)
    """
    return get_lookup().get_template('form_data.mako').render(
            selections1=selections1,
            selections2=selections2,
            time_group=time_group,
            select1=select1,
            select2=select2,
            action_url=action_url
    )


def render_html_data(dates_data,
                     as_precent=True, time_group='days'):
    """
    Render's data as HTML, inside a TABLE element.

    :param :dates_data The data that's returned by `get_dates_data`
    :param :as_precent Should the data be shown as percents or as counts. Defaults to `True`
    :param :time_group What is the data grouped by? Can be `days`, `weeks` or `months`
    """
    return get_lookup().get_template('table_data.mako').render(
        dates_data=dates_data,
        as_precent=as_precent,
        time_group=time_group
    )


#--- Data rendering ----------------------------------------------
def get_dates_data(select1, select2,
                   time_group='days', system='default',
                   as_precent=True):
    """
    Fetch the data from bitmapist.

    :param :select1 First filter (could be `active`)
    :param :select2 Second filter (could be `song:played`)
    :param :time_group What is the data grouped by? Can be `days`, `weeks` or `months`
    :param :system What bitmapist should be used?
    :param :as_precent If `True` then percents as calculated and shown. Defaults to `True`
    :return A list of day data, formated like `[[datetime, count], ...]`
    """
    # Days
    if time_group == 'days':
        fn_get_events = _day_events_fn

        date_range = 25
        now = datetime.utcnow() - timedelta(days=24)
        timedelta_inc = lambda d: timedelta(days=d)
    # Weeks
    elif time_group == 'weeks':
        fn_get_events = _weeks_events_fn

        date_range = 12
        now = datetime.utcnow() - relativedelta(weeks=11)
        timedelta_inc = lambda w: relativedelta(weeks=w)
    # Months
    elif time_group == 'months':
        fn_get_events = _month_events_fn

        date_range = 6
        now = datetime.utcnow() - relativedelta(months=5)
        now -= timedelta(days=now.day-1)
        timedelta_inc = lambda m: relativedelta(months=m)

    dates = []

    for i in range(0, date_range):
        result = [now]

        # Total count
        day_events = fn_get_events(select1, now, system)

        total_day_count = len(day_events)
        result.append(total_day_count)

        # Daily count
        for d_delta in range(0, 13):
            if total_day_count == 0:
                result.append( '' )
                continue

            delta_now = now + timedelta_inc(d_delta)

            delta_events = fn_get_events(select2, delta_now, system)

            if not delta_events.has_events_marked():
                result.append('')
                continue

            day_set_op = BitOpAnd(system, day_events, delta_events)

            delta_count = len(day_set_op)
            if delta_count == 0:
                result.append(float(0.0))
            else:
                if as_precent:
                    result.append( (float(delta_count) / float(total_day_count)) * 100 )
                else:
                    result.append( delta_count )

        dates.append( result )

        now = now + timedelta_inc(1)

    return dates


#--- Private ----------------------------------------------
def _day_events_fn(key, date, system):
    return DayEvents(key, date.year, date.month, date.day, system=system)

def _month_events_fn(key, date, system):
    return MonthEvents(key, date.year, date.month, system=system)

def _weeks_events_fn(key, date, system):
    return WeekEvents(key, date.year, date.isocalendar()[1], system=system)


_LOOKUP = None
def get_lookup():
    global _LOOKUP

    if not _LOOKUP:
        file_path = path.dirname(path.abspath(__file__))
        _LOOKUP = TemplateLookup(directories=[path.join(file_path, 'tmpl')],
                                 encoding_errors='replace')

    return _LOOKUP

__all__ = ['render_html_form',
           'render_html_data',
           'get_dates_data']
