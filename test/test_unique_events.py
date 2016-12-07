import bitmapist


def test_mark():
    ev = bitmapist.UniqueEvents('foo')
    ev.mark(1)
    assert 1 in ev
    assert 2 not in ev


def test_unmark():
    ev = bitmapist.UniqueEvents('foo')
    ev.mark(1)
    ev.unmark(1)
    assert 1 not in ev


def test_ops():
    foo = bitmapist.UniqueEvents('foo')
    foo.mark(1)
    foo.mark(2)
    bar = bitmapist.UniqueEvents('bar')
    bar.mark(2)
    bar.mark(3)

    assert list(foo & bar) == [2]
    assert list(foo | bar) == [1, 2, 3]


def test_ops_with_dates():
    bitmapist.mark_event('active', 1)
    bitmapist.mark_event('active', 2)
    foo = bitmapist.UniqueEvents('foo')
    foo.mark(2)
    foo.mark(3)
    active = bitmapist.DayEvents('active')

    assert list(foo & active) == [2]
    assert list(foo | active) == [1, 2, 3]

    assert list(foo & active.prev()) == []
    assert list(foo | active.prev()) == [2, 3]


def test_track_unique():
    bitmapist.mark_event('foo', 1, track_unique=True)
    bitmapist.mark_event('foo', 2, track_unique=False)
    assert list(bitmapist.DayEvents('foo')) == [1, 2]
    assert list(bitmapist.UniqueEvents('foo')) == [1]
