from datetime import datetime
from .logger import logger


class DatetimeParser:
    @staticmethod
    def parse_iso(dt_str: str) -> datetime:
        logger.info(f"Парсинг даты из строки {dt_str}")
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
