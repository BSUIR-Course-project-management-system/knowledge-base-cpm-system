from schedule_module.src.datetime_parser import DatetimeParser
from datetime import datetime


class TestDatetimeParser:
    def test_parse_iso(self):
        result1 = DatetimeParser.parse_iso("2024-05-02")
        result2 = DatetimeParser.parse_iso("2024-02-29")
        result3 = DatetimeParser.parse_iso("2023-12-31")

        assert result1 == datetime(2024, 5, 2, 0, 0)
        assert result2 == datetime(2024, 2, 29, 0, 0)
        assert result3 == datetime(2023, 12, 31, 0, 0)
