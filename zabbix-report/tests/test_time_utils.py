import os
import sys
import time
import unittest
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from time_utils import (  # noqa: E402
    DISPLAY_TIMEZONE,
    UTC,
    datetime_to_unix,
    format_report_timestamp,
    parse_report_timestamp,
    unix_to_datetime,
)


@contextmanager
def system_timezone(value):
    previous = os.environ.get("TZ")
    os.environ["TZ"] = value
    if hasattr(time, "tzset"):
        time.tzset()
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = previous
        if hasattr(time, "tzset"):
            time.tzset()


class TimeUtilsTests(unittest.TestCase):
    def test_epoch_before_at_and_after_1970_are_portable(self):
        self.assertEqual(datetime_to_unix(datetime(1969, 12, 31, 23, 59, 59, tzinfo=UTC)), -1)
        self.assertEqual(datetime_to_unix(datetime(1970, 1, 1, tzinfo=UTC)), 0)
        self.assertEqual(datetime_to_unix(datetime(1970, 1, 1, 0, 0, 1, tzinfo=UTC)), 1)
        self.assertEqual(unix_to_datetime(-1), datetime(1969, 12, 31, 23, 59, 59, tzinfo=UTC))

    def test_naive_datetime_is_explicitly_operational_time(self):
        naive = datetime(2026, 7, 27, 9, 0)
        aware = naive.replace(tzinfo=DISPLAY_TIMEZONE)
        self.assertEqual(datetime_to_unix(naive), datetime_to_unix(aware))

    def test_aware_datetime_offsets_represent_the_same_instant(self):
        utc_value = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        other_zone = utc_value.astimezone(timezone(timedelta(hours=9)))
        self.assertEqual(datetime_to_unix(utc_value), datetime_to_unix(other_zone))

    def test_calendar_boundaries_and_leap_day_round_trip(self):
        values = [
            datetime(2024, 2, 29, 23, 59, 59, tzinfo=UTC),
            datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC),
            datetime(2026, 1, 31, 23, 59, 59, tzinfo=UTC),
        ]
        for value in values:
            with self.subTest(value=value):
                self.assertEqual(unix_to_datetime(datetime_to_unix(value)), value)

    def test_report_parsing_and_formatting_ignore_system_timezone(self):
        expected = datetime_to_unix(datetime(2026, 7, 27, 9, 30))
        results = []
        for timezone_name in ("UTC0", "GMT+9", "GMT-3"):
            with system_timezone(timezone_name):
                results.append(
                    (
                        parse_report_timestamp("27/07/2026 09:30"),
                        format_report_timestamp(expected),
                    )
                )
        self.assertEqual(results, [(expected, "27/07/2026 09:30")] * 3)

    def test_zero_is_absence_but_negative_timestamp_is_valid(self):
        self.assertIsNone(parse_report_timestamp(0))
        self.assertIsNone(parse_report_timestamp("0"))
        self.assertEqual(parse_report_timestamp(-1), -1)
        self.assertEqual(format_report_timestamp(-1), "31/12/1969 20:59")


if __name__ == "__main__":
    unittest.main()
