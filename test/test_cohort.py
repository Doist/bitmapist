from datetime import date, datetime, timedelta, timezone

import pytest

from bitmapist import mark_event
from bitmapist.cohort import _weeks_events_fn, get_dates_data


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


def test_weeks_events_fn_iso_year_boundary():
    """Test that _weeks_events_fn uses ISO year, not calendar year.

    At year boundaries, a date's calendar year can differ from its ISO year.
    For example, Dec 30, 2024 is in ISO week 1 of 2025.
    """
    # Dec 30, 2024 is a Monday in ISO week 1 of 2025
    dec_30_2024 = date(2024, 12, 30)
    iso_year, iso_week, _ = dec_30_2024.isocalendar()
    assert iso_year == 2025  # Verify our test date assumption
    assert iso_week == 1

    event = _weeks_events_fn("test_event", dec_30_2024, "default")
    # Should use ISO year (2025), not calendar year (2024)
    assert event.year == 2025
    assert event.week == 1

    # Jan 1, 2025 is also in ISO week 1 of 2025
    jan_1_2025 = date(2025, 1, 1)
    event2 = _weeks_events_fn("test_event", jan_1_2025, "default")
    assert event2.year == 2025
    assert event2.week == 1

    # Both dates should produce the same week event
    assert event.redis_key == event2.redis_key
