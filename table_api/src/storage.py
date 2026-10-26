import json
import os
from dotenv import load_dotenv

from table_api.src.parser import GoogleSheetsParser
from table_api.src.loader import ILoader, JsonLoader
from table_api.src.saver import ISaver, JsonSaver
from logger.logger import Logger

LOG_FILE = "table_api/logs/storage.log"

load_dotenv()

CREDENTIALS_FILE = os.getenv("CREDENTIALS_FILE")
FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
GROUP_DATA_FILE = os.getenv("GROUP_DATA_FILE")
TOPIC_DATA_FILE = os.getenv("TOPIC_DATA_FILE")
SCHEDULE_DATA_FILE = os.getenv("SCHEDULE_DATA_FILE")

if not CREDENTIALS_FILE:
    raise ValueError("ОШИБКА: Не найден CREDENTIALS_FILE в .env!")

if not FOLDER_ID:
    raise ValueError("ОШИБКА: Не найден GOOGLE_DRIVE_FOLDER_ID в .env!")


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
        self._logger = Logger(LOG_FILE, level="INFO")
        self._loader: ILoader = JsonLoader()
        self._saver: ISaver = JsonSaver()
        # self._topic_matcher: TopicMatcher = TopicMatcher(
        #     "search_module/models/all-MiniLM-L6-v2"
        # )

    def update_data_from_cloud(self):
        """
        Обновление данных из облака в json файлы.

        """
        self._logger.info("Storage запрашивает все данные у парсера...")
        try:
            data = self._parser.get_all_data_from_cloud(
                self._parser.get_all_sheets_in_folder(FOLDER_ID)
            )
            self._saver.save(TOPIC_DATA_FILE, data["topic_data"])
            self._saver.save(GROUP_DATA_FILE, data["group_data"])
            self._saver.save(SCHEDULE_DATA_FILE, data["schedule_data"])
        except Exception as e:
            raise RuntimeError(f"Непредвиденная ошибка: {e}")
        self._logger.info("Все данные успешно обновлены!")

    def _load_all_group_data(self) -> None:

        self._logger.info("Storage запрашивает данные о группе у парсера...")
        try:
            data = self._parser.fetch_all_groups(
                self._parser.get_all_sheets_in_folder(FOLDER_ID)
            )
            self._saver.save(data=data, file_path=GROUP_DATA_FILE)
            self._logger.info("Storage загрузил данные о группе в файл")
        except Exception as e:
            self._logger.error(f"Ошибка при загрузке данных: {e}")
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
                result = self._find_first(value, target_key, default)
                if result is not default:
                    return result
        elif isinstance(data, list):
            for item in data:
                result = self._find_first(item, target_key, default)
                if result is not default:
                    return result
        return default

    def get_unique_topics(self):
        """Получение списка уникальных тем."""
        unique_topics = {}

        data = self._loader.load(GROUP_DATA_FILE)
        if data:
            for _, records in data.items():
                for row in records:
                    topic = (row.get("topic", "") or "").strip()
                    curator = (row.get("curator", "") or "").strip()
                    examiner = (row.get("examiner", "") or "").strip()
                    description = (
                        row.get("description", "Описание будет добавлено позже")
                        or "Описание будет добавлено позже"
                    ).strip()
                    date_defence: str = self._find_first(row, "date_defence")
                    rounded_final_grade = self._find_first(row, "rounded_final_grade")
                    if topic:
                        unique_topics[topic] = {
                            "curator": curator,
                            "examiner": examiner,
                            "description": description,
                            "is_used": True,
                            "date_defence": date_defence,
                            "rounded_final_grade": rounded_final_grade,
                        }
        data = self._loader.load(TOPIC_DATA_FILE)
        if data:
            for _, records in data.items():
                for row in records:
                    topic = (row.get("topic", "") or "").strip()
                    curator = (row.get("curator", "") or "").strip()
                    examiner = (row.get("examiner", "") or "").strip()
                    description = (
                        row.get("description", "Описание будет добавлено позже")
                        or "Описание будет добавлено позже"
                    ).strip()
                    date_defence: str = self._find_first(row, "date_defence")
                    rounded_final_grade = self._find_first(row, "rounded_final_grade")
                    if topic not in unique_topics.keys():
                        # if not self._topic_matcher.is_topic_in_list(
                        #     topic, list(unique_topics.keys())
                        # ):
                        unique_topics[topic] = {
                            "curator": curator,
                            "examiner": examiner,
                            "description": description,
                            "is_used": False,
                            "date_defence": date_defence,
                            "rounded_final_grade": rounded_final_grade,
                        }

        formatted_topics = []
        if not unique_topics:
            return json.dumps(formatted_topics, ensure_ascii=False, indent=2)
        for idx, (topic, info) in enumerate(unique_topics.items(), start=1):
            formatted_topics.append(
                {
                    "id": str(idx),
                    "topic": topic,
                    "description": info.get("description", "").strip(),
                    "is_used": info.get("is_used", False),
                    "curator": info.get("curator", ""),
                    "examiner": info.get("examiner", ""),
                    "date_defence": info.get("date_defence", ""),
                    "rounded_final_grade": info.get("rounded_final_grade"),
                }
            )

        return json.dumps(formatted_topics, indent=2, ensure_ascii=False)

    def get_examiner_schedule(self, examiner: str, year: int = 2026):
        """Получение расписания опроцентовок конкретного проверяющего"""
        self._logger.info("Загрузка данных из файла для графика")
        data = self._loader.load(SCHEDULE_DATA_FILE)
        if not data:
            data = self._parser.fetch_examiner_schedule(
                self._parser.get_all_sheets_in_folder(FOLDER_ID)
            )
        data: dict = data.get(str(year), {})
        examiner_data: dict[list] = {
            "milestone_1": [],
            "milestone_2": [],
            "milestone_3": [],
        }
        for milestone, topics in data.items():
            for topic in topics:
                if (
                    examiner.lower().strip()
                    in topic.get("examiner", "").lower().strip()
                ):
                    examiner_data[milestone].append(topic)

        return json.dumps(examiner_data, ensure_ascii=False, indent=2)

    def add_topic(
        self,
        *,
        key_title: str = "ТЕСТ 2026",
        topic: str,
        description: str = "Описание будет добавлено позже",
        curator: str = "",
        examiner: str = "",
    ):
        try:
            self._parser.append_row_with_format(
                spreadsheets_ids=self._parser.get_all_sheets_in_folder(FOLDER_ID),
                key_title=key_title,
                worksheet_title="Темы",
                row_data=[topic, description, curator, examiner],
            )
        except Exception:
            raise Exception("Ошибка добавления в таблицу")

    def remove_topic(
        self,
        *,
        key_title: str = "ТЕСТ 2026",
        topic: str,
    ):
        try:
            self._parser.delete_row_by_topic(
                spreadsheets_ids=self._parser.get_all_sheets_in_folder(FOLDER_ID),
                key_title=key_title,
                worksheet_title="Темы",
                theme_title=topic,
            )
        except Exception:
            raise Exception("Ошибка добавления в таблицу")


if __name__ == "__main__":
    storage = Storage()
    storage.update_data_from_cloud()
    print(storage.get_unique_topics())
    # print(storage.get_examiner_schedule("грак"))
