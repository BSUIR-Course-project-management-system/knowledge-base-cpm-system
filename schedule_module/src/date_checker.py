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
    
    @staticmethod
    def is_correct_format(date: str) -> bool:
        """Проверяет корректный ли формат у даты (YYYY-MM-DD)

        Args:
            datetime (str): Строка, которую надо проверить

        Returns:
            bool: true, если строка формата YYYY-MM-DD, иначе false
        """
        try:
            datetime.strptime(date, "%Y-%m-%d")
            return True
        except ValueError:
            return False
