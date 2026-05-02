from datetime import datetime


class DatetimeParser:
    @staticmethod
    def parse_iso(dt_str: str) -> datetime:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
