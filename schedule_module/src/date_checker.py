import holidays
from datetime import datetime


class DateChecker:
    def __init__(self) -> None:
        """
        Конструктор класса
        """
        self.calendar = holidays.country_holidays("BY")

    def is_work_day(self, date: datetime) -> bool:
        """Метод проверки является ли дата рабочим днем

        Args:
            date (datetime):Дата, которую нужно проверить

        Returns:
            bool: true, если дата является рабочим днем, иначе false
        """
        is_holiday = date in self.calendar
        is_weekend = date.weekday() >= 5

        return not (is_holiday or is_weekend)
