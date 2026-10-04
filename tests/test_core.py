import unittest
from datetime import datetime

from exif_time_parser import parse_exif_datetime, normalize_exif_datetime


class ParseTests(unittest.TestCase):
    def test_bare_canonical_form(self):
        dt = parse_exif_datetime("2023:04:01 12:30:45")
        self.assertEqual(dt, datetime(2023, 4, 1, 12, 30, 45))

    def test_empty_string_returns_none(self):
        self.assertIsNone(parse_exif_datetime(""))

    def test_whitespace_only_returns_none(self):
        self.assertIsNone(parse_exif_datetime("   "))

    def test_none_returns_none(self):
        # EXIF libraries frequently hand us None for missing tags.
        self.assertIsNone(parse_exif_datetime(None))

    def test_dot_subsecond(self):
        dt = parse_exif_datetime("2023:04:01 12:30:45.500")
        self.assertEqual(dt, datetime(2023, 4, 1, 12, 30, 45, 500000))

    def test_single_digit_subsecond_means_tenths(self):
        # ``.5`` is 500000us, not 5us. Left-pad, don't right-pad.
        dt = parse_exif_datetime("2023:04:01 12:30:45.5")
        self.assertEqual(dt, datetime(2023, 4, 1, 12, 30, 45, 500000))

    def test_space_subsecond_apple_style(self):
        dt = parse_exif_datetime("2023:04:01 12:30:45 500")
        self.assertEqual(dt, datetime(2023, 4, 1, 12, 30, 45, 500000))

    def test_trailing_digit_subsecond(self):
        dt = parse_exif_datetime("2023:04:01 12:30:45500")
        self.assertEqual(dt, datetime(2023, 4, 1, 12, 30, 45, 500000))

    def test_six_digit_subsecond(self):
        dt = parse_exif_datetime("2023:04:01 12:30:45.123456")
        self.assertEqual(dt, datetime(2023, 4, 1, 12, 30, 45, 123456))

    def test_overlong_subsec_truncates_to_microseconds(self):
        dt = parse_exif_datetime("2023:04:01 12:30:45.1234567")
        self.assertEqual(dt, datetime(2023, 4, 1, 12, 30, 45, 123456))

    def test_z_timezone_is_dropped(self):
        dt = parse_exif_datetime("2023:04:01 12:30:45Z")
        self.assertEqual(dt, datetime(2023, 4, 1, 12, 30, 45))
        self.assertIsNone(dt.tzinfo)

    def test_numeric_offset_is_dropped(self):
        dt = parse_exif_datetime("2023:04:01 12:30:45+05:30")
        self.assertEqual(dt, datetime(2023, 4, 1, 12, 30, 45))
        self.assertIsNone(dt.tzinfo)

    def test_negative_offset_is_dropped(self):
        dt = parse_exif_datetime("2023:04:01 12:30:45-08:00")
        self.assertEqual(dt, datetime(2023, 4, 1, 12, 30, 45))

    def test_dash_separator_is_rejected(self):
        # EXIF uses colons. A dash-separated value is a different
        # metadata dialect and we refuse it on purpose.
        self.assertIsNone(parse_exif_datetime("2023-04-01 12:30:45"))

    def test_invalid_date_returns_none(self):
        self.assertIsNone(parse_exif_datetime("2023:02:30 12:30:45"))

    def test_truncated_value_returns_none(self):
        self.assertIsNone(parse_exif_datetime("2023:04:01 12:30"))

    def test_garbage_returns_none(self):
        self.assertIsNone(parse_exif_datetime("not a date"))

    def test_offset_without_minutes_rejected(self):
        self.assertIsNone(parse_exif_datetime("2023:04:01 12:30:45+05"))


class NormalizeTests(unittest.TestCase):
    def test_canonical_round_trips(self):
        self.assertEqual(normalize_exif_datetime("2023:04:01 12:30:45"),
                         "2023:04:01 12:30:45")

    def test_dot_subsec_normalised_to_six_digits(self):
        self.assertEqual(normalize_exif_datetime("2023:04:01 12:30:45.5"),
                         "2023:04:01 12:30:45.500000")

    def test_z_stripped(self):
        self.assertEqual(normalize_exif_datetime("2023:04:01 12:30:45Z"),
                         "2023:04:01 12:30:45")

    def test_offset_stripped(self):
        self.assertEqual(normalize_exif_datetime("2023:04:01 12:30:45+05:30"),
                         "2023:04:01 12:30:45")

    def test_unparseable_yields_empty(self):
        self.assertEqual(normalize_exif_datetime("garbage"), "")

    def test_round_trip_through_parse(self):
        normalised = normalize_exif_datetime("2023:04:01 12:30:45.5")
        dt = parse_exif_datetime(normalised)
        self.assertEqual(dt, datetime(2023, 4, 1, 12, 30, 45, 500000))


if __name__ == "__main__":
    unittest.main()
