import pytest
from datetime import datetime
from schedule_module.src.date_checker import DateChecker


class TestDateChecker:
    @pytest.fixture
    def checker(self):
        checker = DateChecker()
        return checker

    def test_is_work_day(self, checker):
        date_work = datetime(2024, 5, 2)
        date_weekend = datetime(2024, 5, 4)
        date_holiday = datetime(2024, 1, 1)

        assert checker.is_work_day(date_work)
        assert not checker.is_work_day(date_weekend)
        assert not checker.is_work_day(date_holiday)

    def test_is_correct_format(self, checker):
        result1 = checker.is_correct_format("2024-02-29")
        result2 = checker.is_correct_format("2024-13-01")
        result3 = checker.is_correct_format("2024/02/29")

        assert result1
        assert not result2
        assert not result3
