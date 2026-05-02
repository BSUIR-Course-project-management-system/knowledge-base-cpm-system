import holidays
from datetime import datetime


class DateChecker:
    def __init__(self) -> None:
        self.calendar = holidays.country_holidays("BY")

    def is_work_day(self, date: datetime) -> bool:
        is_holiday = date in self.calendar
        is_weekend = date.weekday() >= 5

        return not (is_holiday or is_weekend)
