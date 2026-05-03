import logging
import sys
import json
import os
from dotenv import load_dotenv

from parser import GoogleSheetsParser
from loader import ILoader, JsonLoader
from saver import ISaver, JsonSaver

LOG_FILE = "table_api/logs/google_sheets_api.log"

load_dotenv()

CREDENTIALS_FILE = os.getenv("CREDENTIALS_FILE")
FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
GROUP_DATA_FILE = os.getenv("GROUP_DATA_FILE")

if not CREDENTIALS_FILE:
    raise ValueError("ОШИБКА: Не найден CREDENTIALS_FILE в .env!")

if not FOLDER_ID:
    raise ValueError("ОШИБКА: Не найден GOOGLE_DRIVE_FOLDER_ID в .env!")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)


class Storage:
    """
    Класс хранилища данных.
    Представляет собой сущность для выдачи и манипуляций данными другим модулям.
    Включает в себя парсер Google Таблиц для удаленного хранения большинства данных.
    .. seealso::
        :class:`GoogleSheetsParser`
    """

    def __init__(self):
        self._parser = GoogleSheetsParser(CREDENTIALS_FILE)
        self._loader = JsonLoader()
        self._saver = JsonSaver()
        self._load_all_group_data()

    def _load_all_group_data(self) -> None:
        logging.info("Storage запрашивает данные у парсера...")
        try:
            data = self._parser.fetch_all_groups(
                self._parser.get_all_sheets_in_folder(FOLDER_ID)
            )
            self._saver.save(data=data, file_path=GROUP_DATA_FILE)
        except Exception as e:
            logging.error(f"Ошибка при загрузке данных: {e}")
            return

    def _find_first(self, data, target_key, default=None):
        """
        Рекурсивно ищет target_key в словарях и списках.
        Возвращает первое найденное значение или default.
        """
        if isinstance(data, dict):
            if target_key in data:
                return data[target_key]
            for value in data.values():
                result = self.find_first(value, target_key, default)
                if result is not default:
                    return result
        elif isinstance(data, list):
            for item in data:
                result = self.find_first(item, target_key, default)
                if result is not default:
                    return result
        return default

    def get_unique_topics(self):
        unique_topics = {}

        data = self._loader.load(GROUP_DATA_FILE)
        # new_data = self._loader.load("topic_data.json")

        for sheet_name, records in data.items():
            for row in records:
                topic = row.get("topic", "").strip()
                curator = row.get("curator", "").strip()
                examiner = row.get("examiner", "").strip()
                date_defence: str = self._find_first(row, "date_defence")
                rounded_final_grade = self._find_first(row, "rounded_final_grade")
                if topic:
                    unique_topics[topic] = {
                        "curator": curator,
                        "examiner": examiner,
                        "is_used": True,
                        "date_defence": date_defence,
                        "rounded_final_grade": rounded_final_grade,
                    }

        formatted_topics = []

        for idx, (topic, info) in enumerate(unique_topics.items(), start=1):
            formatted_topics.append(
                {
                    "id": str(idx),
                    "topic": topic,
                    "description:": info.get("description", "").strip(),
                    "is_used": info["is_used"],
                    "curator": info["curator"],
                    "examiner": info["examiner"],
                    "date_defence": info["date_defence"],
                    "rounded_final_grade": info["rounded_final_grade"],
                }
            )

        return json.dumps(formatted_topics, ensure_ascii=False, indent=2)

    def get_examiner_schedule(self, examiner):
        """Заглушка"""
        logging.info("Использование данных заглушки для графика")
        mock_data = {
            "Milestone_1": [],
            "Milestone_2": [],
            "Milestone_3": [],
        }
        json_result = json.dumps(mock_data, ensure_ascii=False, indent=2)

        return json_result


if __name__ == "__main__":
    storage = Storage()
    print(storage.get_unique_topics())
