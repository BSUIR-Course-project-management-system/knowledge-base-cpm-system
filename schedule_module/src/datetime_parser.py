from datetime import datetime
from .logger import logger


class DatetimeParser:
    """
    Класс для парсинга дат из строк
    """

    @staticmethod
    def parse_iso(dt_str: str) -> datetime:
        """Метод получения из строки формата YYYY-MM-DD объект datetime

        Args:
            dt_str (str): Строка в формате YYYY-MM-DD

        Returns:
            datetime: Объект класса datetime
        """
        logger.info(f"Парсинг даты из строки {dt_str}")
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
