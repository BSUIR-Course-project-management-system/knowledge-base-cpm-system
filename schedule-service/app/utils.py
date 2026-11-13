from datetime import datetime
from typing import Dict, Any, List, Tuple
import holidays


def is_work_day(date: datetime) -> bool:
    """Метод проверки является ли дата рабочим днем

    Args:
        date (datetime):Дата, которую нужно проверить

    Returns:
        bool: true, если дата является рабочим днем, иначе false
    """
    calendar = holidays.country_holidays("BY")

    is_holiday = date in calendar
    is_weekend = date.weekday() >= 5

    return not (is_holiday or is_weekend)


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
