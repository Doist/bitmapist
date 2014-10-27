import bitmapist


def test_equality():
    ev1 = bitmapist.YearEvents('foo', 2014)
    ev2 = bitmapist.YearEvents('foo', 2014)
    ev3 = bitmapist.YearEvents('foo', 2015)
    assert ev1 == ev2
    assert ev1 != ev3
