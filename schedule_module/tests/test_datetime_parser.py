from typing import Any, Dict
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
        
    def test_parse_from_json(self):
        data: Dict[str, Any] = {
            "milestone_1": [
                {
                    "day": "13.03.2026",
                    "time": {"start": "", "end": ""},
                },
                {
                    "day": "09.04.2026",
                    "time": {"start": "15:00", "end": "15:30"},
                },
                {
                    "day": "07.04.2026",
                    "time": {"start": "15:00", "end": "15:30"},
                }
            ],
            "milestone_2": [
                {
                    "day": "07.04.2026",
                    "time": {"start": "15:30", "end": "16:00"},
                },
                {
                    "day": "07.04.2026",
                    "time": {"start": "16:00", "end": "16:30"},
                },
                {
                    "day": "09.04.2026",
                    "time": {"start": "15:30", "end": "16:00"},
                },
                {
                    "day": "13.03.2026",
                    "time": {"start": "", "end": ""},
                }
            ],
            "milestone_3": [],
        }

        expected = [
            (datetime(2026, 4, 9, 15, 0), datetime(2026, 4, 9, 15, 30)),
            (datetime(2026, 4, 7, 15, 0), datetime(2026, 4, 7, 15, 30)),
            (datetime(2026, 4, 7, 15, 30), datetime(2026, 4, 7, 16, 0)),
            (datetime(2026, 4, 7, 16, 0), datetime(2026, 4, 7, 16, 30)),
            (datetime(2026, 4, 9, 15, 30), datetime(2026, 4, 9, 16, 0))
        ]

        result = DatetimeParser.parse_from_json(data)

        assert len(result) == len(expected)
        assert set(result) == set(expected)

        for start, end in result:
            assert start.date() != datetime(2026, 3, 13).date()

