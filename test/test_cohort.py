import pytest
from datetime import datetime, timedelta

from bitmapist import mark_event
from bitmapist.cohort import get_dates_data


@pytest.fixture
def events():
    today = datetime.utcnow()
    tomorrow = today + timedelta(days=1)

    mark_event('signup', 111, now=today)
    mark_event('active', 111, now=today)
    mark_event('active', 111, now=tomorrow)

    mark_event('signup', 222, now=today)
    mark_event('active', 222, now=today)

    mark_event('task1', 111, now=today)
    mark_event('task1', 111, now=tomorrow)
    mark_event('task2', 111, now=today)
    mark_event('task2', 111, now=tomorrow)
    mark_event('task1', 222, now=today)
    mark_event('task1', 222, now=tomorrow)
    mark_event('task2', 222, now=today)
    mark_event('task2', 222, now=tomorrow)


@pytest.mark.parametrize("select1,select1b,select2,select2b, expected", [
    ('active', None, 'active', None, [2, 100, 50]),
    ('active', None, 'unknown', None, [2, '', '']),
    ('unknown', None, 'active', None, [0, '', '']),
    ('signup', 'active', 'active', None, [2, 100, 50]),
    ('signup', 'active', 'active', 'signup', [2, 100, 0]),
    ('task1', 'task2', 'task2', 'task1', [2, 100, 100]),
    ('task1', 'task2', 'task1', 'task2', [2, 100, 100]),
])
def test_cohort(select1, select1b, select2, select2b, expected, events):
    r = get_dates_data(select1=select1, select1b=select1b,
                       select2=select2, select2b=select2b,
                       time_group='days', as_precent=1,
                       num_results=1, num_of_rows=1)
    assert r[0][1:] == expected
