import unittest
from datetime import datetime, timedelta, timezone

from autobuka import ServerClock, class_start, parse_hhmm


class TestParse(unittest.TestCase):
    def test_parse_hhmm_range(self):
        self.assertEqual(parse_hhmm("10:00 - 12:50"), (10, 0))

    def test_parse_hhmm_seconds(self):
        self.assertEqual(parse_hhmm("08:25:00.0000000"), (8, 25))

    def test_class_start_full(self):
        dt = class_start("2026-07-04", "10:00:00.0000000")
        self.assertEqual((dt.year, dt.month, dt.day, dt.hour, dt.minute), (2026, 7, 4, 10, 0))
        self.assertEqual(dt.utcoffset(), timedelta(hours=7))

    def test_class_start_hhmm_only(self):
        dt = class_start("2026-07-04", "13:55")
        self.assertEqual((dt.hour, dt.minute), (13, 55))


class TestServerClock(unittest.TestCase):
    def test_offset_from_header(self):
        header = "Fri, 03 Jul 2026 17:44:20 GMT"
        local = datetime(2026, 7, 3, 17, 44, 10, tzinfo=timezone.utc)  # lokal 10s tertinggal
        clock = ServerClock.from_header_date(header, local_utc=local)
        self.assertEqual(clock.offset, timedelta(seconds=10))

    def test_zero_offset(self):
        header = "Fri, 03 Jul 2026 17:44:20 GMT"
        local = datetime(2026, 7, 3, 17, 44, 20, tzinfo=timezone.utc)
        self.assertEqual(ServerClock.from_header_date(header, local_utc=local).offset, timedelta(0))


if __name__ == "__main__":
    unittest.main()
