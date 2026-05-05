from datetime import datetime
from typing import Dict, Any, List, Tuple
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
    
    @staticmethod
    def parse_from_json(data: Dict[str, Any]) -> List[Tuple[datetime, datetime]]:
        """Метод для преобразования json данных от API в datetime объекты

        Args:
            data (Dict[str, Any]): Данные из Google таблиц по проверяющему

        Returns:
            List[Tuple[datetime, datetime]]: Временные рамки занятых дней под опроцентовки
        """
        occupied_data_list = []
        for key, value in data.items():
            if key.startswith("milestone_"):
                occupied_data_list.extend(value)

        date_format = "%d.%m.%Y %H:%M"
        result = []

        for day in occupied_data_list:
            date = day["day"]
            start_time = day["time"].get("start")
            end_time = day["time"].get("end")

            if not start_time or not end_time:
                continue

            start_datetime = datetime.strptime(f"{date} {start_time}", date_format)
            end_datetime = datetime.strptime(f"{date} {end_time}", date_format)
            result.append((start_datetime, end_datetime))

        return result
