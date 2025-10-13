from datetime import datetime, timedelta, timezone

import pytest

from bitmapist import mark_event
from bitmapist.cohort import get_dates_data


@pytest.fixture
def events():
    today = datetime.now(tz=timezone.utc)
    tomorrow = today + timedelta(days=1)

    mark_event("signup", 111, now=today)
    mark_event("active", 111, now=today)
    mark_event("active", 111, now=tomorrow)

    mark_event("signup", 222, now=today)
    mark_event("active", 222, now=today)

    mark_event("task1", 111, now=today)
    mark_event("task1", 111, now=tomorrow)
    mark_event("task2", 111, now=today)
    mark_event("task2", 111, now=tomorrow)
    mark_event("task1", 222, now=today)
    mark_event("task1", 222, now=tomorrow)
    mark_event("task2", 222, now=today)
    mark_event("task2", 222, now=tomorrow)


@pytest.mark.parametrize(
    ("select1", "select1b", "select2", "select2b", "expected"),
    [
        # Basic tests without select1b/select2b
        ("active", None, "active", None, [2, 100, 50]),
        ("active", None, "unknown", None, [2, "", ""]),
        ("unknown", None, "active", None, [0, "", ""]),

        # Tests with select1b (AND conditions for select1)
        ("signup", "active", "active", None, [2, 100, 50]),

        # Tests with both select1b and select2b
        ("task1", "task2", "task2", "task1", [2, 100, 100]),

        # When select1 has no events but select1b has events, result should be 0
        ("unknown", "active", "active", None, [0, "", ""]),

        # When select1 has events but select2 AND select2b results in 0
        ("active", None, "unknown", "active", [2, "", ""]),

        # When select1 has events but select1b has no events (no overlap)
        ("active", "unknown", "active", None, [0, "", ""]),

        # When select2 has events but select2b has no events (no overlap)
        ("active", None, "active", "unknown", [2, "", ""]),
    ],
)
def test_cohort(select1, select1b, select2, select2b, expected, events):
    r = get_dates_data(
        select1=select1,
        select1b=select1b,
        select2=select2,
        select2b=select2b,
        time_group="days",
        as_percent=1,
        num_results=1,
        num_of_rows=1,
    )
    assert r[0][1:] == expected
