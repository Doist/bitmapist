import bitmapist


def test_delta_hour():
    ev = bitmapist.HourEvents('foo', 2014, 1, 1, 0)
    n = ev.next()
    assert (n.year, n.month, n.day, n.hour) == (2014, 1, 1, 1)
    p = ev.prev()
    assert (p.year, p.month, p.day, p.hour) == (2013, 12, 31, 23)


def test_delta_day():
    ev = bitmapist.DayEvents('foo', 2014, 1, 1)
    n = ev.next()
    assert (n.year, n.month, n.day) == (2014, 1, 2)
    p = ev.prev()
    assert (p.year, p.month, p.day) == (2013, 12, 31)


def test_delta_week():
    ev = bitmapist.WeekEvents('foo', 2014, 1)
    n = ev.next()
    assert (n.year, n.week) == (2014, 2)
    p = ev.prev()
    assert (p.year, p.week) == (2013, 52)


def test_delta_month():
    ev = bitmapist.MonthEvents('foo', 2014, 1)
    n = ev.next()
    assert (n.year, n.month) == (2014, 2)
    p = ev.prev()
    assert (p.year, p.month) == (2013, 12)


def test_delta_year():
    ev = bitmapist.YearEvents('foo', 2014)
    n = ev.next()
    assert n.year == 2015
    p = ev.prev()
    assert p.year == 2013
