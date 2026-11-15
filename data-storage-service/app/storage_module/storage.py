import json

# import os
# from dotenv import load_dotenv
from typing import Protocol

from app.schemas import (
    GroupOut,
    MilestoneScheduleOut,
    RefreshResponse,
    TopicOut,
    TopicRequest,
)
from app.storage_module.loader import ILoader, JsonLoader

# from app.storage_module.parser import GoogleSheetsParser
from app.storage_module.saver import ISaver, JsonSaver


class StorageInterface(Protocol):
    def list_topics(
        self, params: TopicRequest, limit: int, offset: int
    ) -> tuple[int, list[TopicOut]]: ...
    def get_topic(self, topic_id: str) -> TopicOut | None: ...
    def get_milestones(
        self, year: int, examiner: str | None
    ) -> MilestoneScheduleOut: ...
    def list_groups(self) -> list[GroupOut]: ...
    def get_group(self, group_id: str) -> GroupOut | None: ...

    def try_start_refresh(self) -> None: ...  # бросает RefreshInProgressError
    def run_refresh(self) -> None: ...
    def refresh_status(self) -> RefreshResponse: ...


import threading
from datetime import date, datetime, timezone

from app.core.exceptions import RefreshInProgressError
from app.schemas import (
    GroupOut,
    MilestoneOut,
    MilestoneScheduleOut,
    RefreshResponse,
    StudentOut,
    TopicOut,
    TopicRequest,
)

# LOG_FILE = "table_api/logs/storage.log"
# load_dotenv()
# CREDENTIALS_FILE = os.getenv("CREDENTIALS_FILE")
# FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
# GROUP_DATA_FILE = os.getenv("GROUP_DATA_FILE")
# TOPIC_DATA_FILE = os.getenv("TOPIC_DATA_FILE")
# SCHEDULE_DATA_FILE = os.getenv("SCHEDULE_DATA_FILE")
# if not CREDENTIALS_FILE:
#     raise ValueError("ОШИБКА: Не найден CREDENTIALS_FILE в .env!")
# if not FOLDER_ID:
#     raise ValueError("ОШИБКА: Не найден GOOGLE_DRIVE_FOLDER_ID в .env!")

TOPICS = [
    TopicOut(
        id="1",
        year=2026,
        topic="База знаний диалоговой системы NIKA",
        description="Разработка онтологии",
        is_used=True,
        curator="Иванов И.И.",
        examiner="Петров П.П.",
        rounded_final_grade=9,
        technologies="Python, OSTIS"
    ),
    TopicOut(
        id="2",
        year=2026,
        topic="Интеллектуальный ассистент по источнику данных на основании RAG",
        description="Разработка интеллектуальной системы, использующей подход Retrieval-Augmented Generation (RAG) для извлечения, анализа и генерации ответов на основе данных из указанного источника. В режиме диалога на естественном языке пользователь задаёт вопросы об учебном материале и организации учебного процесса, а система формирует ответы на основе проверенной и согласованной информации из базы знаний, что повышает достоверность и единообразие предоставляемых сведений. В качестве подхода RAG могут применяться графы знаний, векторный поиск, поиск по ключевым словам и другие методы.",
        is_used=True,
        curator="Сотрудник А.",
        examiner="Сотрудник Б.",
        rounded_final_grade=None,
        technologies="RAG,Графы знаний,Векторный поиск,Поиск по ключевым словам"
    ),
    TopicOut(
        id="3",
        year=2026,
        topic="Персональный ассистент по обучению",
        description=None,
        is_used=True,
        curator="Сотрудник В.",
        examiner="Сотрудник Г.",
        rounded_final_grade=None,
        technologies=None
    ),
    TopicOut(
        id="4",
        year=2026,
        topic="База знаний ассистента по оформлению научных работ и автоматической проверке уникальности текста",
        description="База знаний ассистента по оформлению научных работ и автоматической проверке уникальности текста — включает ГОСТы, правила цитирования, шаблоны оформления и методы обнаружения заимствований для автоматической проверки студенческих статей и курсовых.",
        is_used=True,
        curator="Сотрудник Д.",
        examiner="Сотрудник Е.",
        rounded_final_grade=None,
        technologies="Логический язык программирования, LLM"
    ),
    TopicOut(
        id="5",
        year=2026,
        topic="База знаний интеллектуальной обучающей системы по дисциплине «Алгоритмы и структуры данных»",
        description="База знаний интеллектуальной обучающей системы по дисциплине «Алгоритмы и структуры данных» — структурирует определения алгоритмов, примеры кода, типовые задачи, сложности операций и типичные ошибки для адаптивного обучения студентов.",
        is_used=True,
        curator="Сотрудник Ж.",
        examiner="Сотрудник Ж.",
        rounded_final_grade=None,
        technologies="Логический язык программирования, LLM",
    ),
    TopicOut(
        id="6",
        year=2026,
        topic="База знаний планировщика питания и совместимости продуктов для студенческой столовой",
        description=None,
        is_used=True,
        curator="Сотрудник И.",
        examiner="Сотрудник К.",
        rounded_final_grade=None,
        technologies=None,
    ),
    TopicOut(
        id="7",
        year=2026,
        topic="База знаний RAG-системы автоматического выявления фактологических противоречий в неструктурированных данных",
        description=None,
        is_used=True,
        curator="Сотрудник Л.",
        examiner="Сотрудник М.",
        rounded_final_grade=None,
        technologies="RAG"
    ),
    TopicOut(
        id="8",
        year=2026,
        topic="scp-интерпретатор",
        description="Создание средств для разработки программ на Языке SCP.",
        is_used=True,
        curator="Сотрудник Н.",
        examiner="Сотрудник О.",
        rounded_final_grade=None,
        technologies="SCP"
    ),
    TopicOut(
        id="9",
        year=2026,
        topic="sc-машина",
        description="Разработка sc-machine - той части платформы OSTIS, которая отвечает за эмуляцию семантической памяти и API доступа к ней.",
        is_used=True,
        curator="Сотрудник П.",
        examiner="Сотрудник Р.",
        rounded_final_grade=None,
        technologies="OSTIS, sc-machine"
    ),
    TopicOut(
        id="10",
        year=2026,
        topic="ИСС по музыке",
        description="Описание будет добавлено позже",
        is_used=True,
        curator="Сотрудник С.",
        examiner="Сотрудник Т.",
        rounded_final_grade=None,
        technologies=None
    ),
    TopicOut(
        id="11",
        year=2026,
        topic="ИСС по искусству",
        description="Описание будет добавлено позже",
        is_used=True,
        curator="Сотрудник У.",
        examiner="Сотрудник Ф.",
        rounded_final_grade=None,
        technologies=None
    ),
]

MILESTONES = [
    MilestoneOut(
        id="1",
        examiner="Иванова Н. В.",
        topic_title="База знаний интеллектуального помощника для студентов высшего учебного заведения (Leonard) - 1",
        start=datetime(2026, 4, 9, 15, 0),
        end=datetime(2026, 4, 9, 15, 30),
        hold_format="очно, 610-5",
        note="На опроцентовку заходим по проектам",
    ),
    MilestoneOut(
        id="2",
        examiner="Иванова Н. В.",
        topic_title="База знаний интеллектуальной системы по ЖКХ",
        start=datetime(2026, 4, 7, 15, 0),
        end=datetime(2026, 4, 7, 15, 30),
        hold_format="очно, 610-5",
        note="На опроцентовку заходим по проектам",
    ),
    MilestoneOut(
        id="3",
        examiner="Иванова Н. В.",
        topic_title="База знаний цифрового двойника предприятия (Савушкин продукт)",
        start=datetime(2026, 4, 7, 15, 0),
        end=datetime(2026, 4, 7, 15, 30),
        hold_format="очно, 610-5",
        note="На опроцентовку заходим по проектам",
    ),
]


GROUPS = [
    GroupOut(
        group_id="111102",
        students=[
            StudentOut(
                number=1,
                name="Студент Тестовый",
                topic_title="База знаний диалоговой системы NIKA",
                is_topic_accepted=True,
                curator="Иванов И.И.",
                examiner="Иванов И.И.",
            ),
        ],
    ),
    GroupOut(
        group_id="111103",
        students=[
            StudentOut(
                number=1,
                name="Студент Тестовый",
                topic_title="База знаний интеллектуальной обучающей системы по дисциплине «Алгоритмы и структуры данных»",
                is_topic_accepted=True,
                curator="Сотрудник Ж.",
                examiner="Сотрудник Ж.",
            ),
        ],
    ),
    GroupOut(
        group_id="111104",
        students=[
            StudentOut(
                number=1,
                name="Студент Тестовый",
                topic_title="База знаний планировщика питания и совместимости продуктов для студенческой столовой",
                is_topic_accepted=True,
                curator="Сотрудник И.",
                examiner="Сотрудник К.",
            ),
        ],
    ),
    GroupOut(
        group_id="111105",
        students=[
            StudentOut(
                number=1,
                name="Студент Тестовый",
                topic_title="Цифровой двойник предприятия (Савушкин продукт)",
                is_topic_accepted=True,
                curator="Сотрудник Л.",
                examiner="Сотрудник М.",
            ),
        ],
    ),
    GroupOut(
        group_id="111106",
        students=[
            StudentOut(
                number=1,
                name="Студент Тестовый",
                topic_title="Интеллектуальная система по ЖКХ",
                is_topic_accepted=True,
                curator="Сотрудник Н.",
                examiner="Сотрудник О.",
            ),
        ],
    ),
    GroupOut(
        group_id="111107",
        students=[
            StudentOut(
                number=1,
                name="Студент Тестовый",
                topic_title="Цифровой двойник предприятия",
                is_topic_accepted=True,
                curator="Сотрудник П.",
                examiner="Сотрудник Р.",
            ),
        ],
    ),
    GroupOut(
        group_id="111108",
        students=[
            StudentOut(
                number=1,
                name="Студент Тестовый",
                topic_title="Интеллектуальный ассистент по университету",
                is_topic_accepted=True,
                curator="Сотрудник С.",
                examiner="Сотрудник Т.",
            ),
        ],
    ),
]


class StubStorage:
    """
    Интерфейс хранилища данных.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._running = False
        self._updated: datetime | None = None

    def list_topics(self, params: TopicRequest, limit, offset):
        items = [
            t
            for t in TOPICS
            if (params.year is None or t.year == params.year)
            and (params.is_used is None or t.is_used == params.is_used)
            and (params.curator is None or t.curator == params.curator)
            and (params.examiner is None or t.examiner == params.examiner)
        ]
        return len(items), items[offset : offset + limit]

    def get_milestones(self, year, examiner):
        items = [
            m
            for m in MILESTONES
            if m.start.year == year and (examiner is None or m.examiner == examiner)
        ]
        return MilestoneScheduleOut(year=year, milestones=items)

    def list_groups(self):
        return GROUPS

    def get_group(self, group_id):
        return next((g for g in GROUPS if g.group_id == group_id), None)

    def try_start_refresh(self):
        with self._lock:
            if self._running:
                raise RefreshInProgressError
            self._running = True

    def run_refresh(self):
        self._updated = datetime.now(timezone.utc)
        with self._lock:
            self._running = False

    def refresh_status(self):
        status = "running" if self._running else ("ok" if self._updated else "started")
        return RefreshResponse(
            status=status, record_count=len(TOPICS), updated_at=self._updated
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
        ...
        # self._parser = GoogleSheetsParser(CREDENTIALS_FILE)
        # self._logger = Logger(LOG_FILE, level="INFO")
        # self._loader: ILoader = JsonLoader()
        # self._saver: ISaver = JsonSaver()

    def synchronize(self):
        """
        Обновление данных из облака в json файлы.

        """
        ...
        # self._logger.info("Storage запрашивает все данные у парсера...")
        # try:
        #     data = self._parser.get_all_data_from_cloud(
        #         self._parser.get_all_sheets_in_folder(FOLDER_ID)
        #     )
        #     self._saver.save(TOPIC_DATA_FILE, data["topic_data"])
        #     self._saver.save(GROUP_DATA_FILE, data["group_data"])
        #     self._saver.save(SCHEDULE_DATA_FILE, data["schedule_data"])
        # except Exception as e:
        #     raise RuntimeError(f"Непредвиденная ошибка: {e}")
        # self._logger.info("Все данные успешно обновлены!")

    def _load_all_group_data(self) -> None:
        ...
        # self._logger.info("Storage запрашивает данные о группе у парсера...")
        # try:
        #     data = self._parser.fetch_all_groups(
        #         self._parser.get_all_sheets_in_folder(FOLDER_ID)
        #     )
        #     self._saver.save(data=data, file_path=GROUP_DATA_FILE)
        #     self._logger.info("Storage загрузил данные о группе в файл")
        # except Exception as e:
        #     self._logger.error(f"Ошибка при загрузке данных: {e}")
        #     return

    def _find_first(self, data, target_key, default=None):
        """
        Рекурсивно ищет target_key в словарях и списках.
        Возвращает первое найденное значение или default.
        """
        ...
        # if isinstance(data, dict):
        #     if target_key in data:
        #         return data[target_key]
        #     for value in data.values():
        #         result = self._find_first(value, target_key, default)
        #         if result is not default:
        #             return result
        # elif isinstance(data, list):
        #     for item in data:
        #         result = self._find_first(item, target_key, default)
        #         if result is not default:
        #             return result
        # return default

    def topics(self):
        """Получение списка уникальных тем."""
        ...
        # unique_topics = {}
        # # TODO : переделать под новую логику лоадера
        # data = self._loader.load(GROUP_DATA_FILE)
        # if data:
        #     for _, records in data.items():
        #         for row in records:
        #             topic = (row.get("topic", "") or "").strip()
        #             curator = (row.get("curator", "") or "").strip()
        #             examiner = (row.get("examiner", "") or "").strip()
        #             description = (
        #                 row.get("description", "Описание будет добавлено позже")
        #                 or "Описание будет добавлено позже"
        #             ).strip()
        #             date_defence: str = self._find_first(row, "date_defence")
        #             rounded_final_grade = self._find_first(row, "rounded_final_grade")
        #             if topic:
        #                 unique_topics[topic] = {
        #                     "curator": curator,
        #                     "examiner": examiner,
        #                     "description": description,
        #                     "is_used": True,
        #                     "date_defence": date_defence,
        #                     "rounded_final_grade": rounded_final_grade,
        #                 }
        # # TODO : переделать под новую логику лоадера
        # data = self._loader.load(TOPIC_DATA_FILE)
        # if data:
        #     for _, records in data.items():
        #         for row in records:
        #             topic = (row.get("topic", "") or "").strip()
        #             curator = (row.get("curator", "") or "").strip()
        #             examiner = (row.get("examiner", "") or "").strip()
        #             description = (
        #                 row.get("description", "Описание будет добавлено позже")
        #                 or "Описание будет добавлено позже"
        #             ).strip()
        #             date_defence: str = self._find_first(row, "date_defence")
        #             rounded_final_grade = self._find_first(row, "rounded_final_grade")
        #             if topic not in unique_topics.keys():
        #                 # if not self._topic_matcher.is_topic_in_list(
        #                 #     topic, list(unique_topics.keys())
        #                 # ):
        #                 unique_topics[topic] = {
        #                     "curator": curator,
        #                     "examiner": examiner,
        #                     "description": description,
        #                     "is_used": False,
        #                     "date_defence": date_defence,
        #                     "rounded_final_grade": rounded_final_grade,
        #                 }

        # formatted_topics = []
        # if not unique_topics:
        #     return json.dumps(formatted_topics, ensure_ascii=False, indent=2)
        # for idx, (topic, info) in enumerate(unique_topics.items(), start=1):
        #     formatted_topics.append(
        #         {
        #             "id": str(idx),
        #             "topic": topic,
        #             "description": info.get("description", "").strip(),
        #             "is_used": info.get("is_used", False),
        #             "curator": info.get("curator", ""),
        #             "examiner": info.get("examiner", ""),
        #             "date_defence": info.get("date_defence", ""),
        #             "rounded_final_grade": info.get("rounded_final_grade"),
        #         }
        #     )

        # return json.dumps(formatted_topics, indent=2, ensure_ascii=False)

    def examiner_schedule(self, examiner: str, year: int = 2026):
        """Получение расписания опроцентовок конкретного проверяющего"""
        ...
        # self._logger.info("Загрузка данных из файла для графика")
        # # TODO : переделать под новую логику лоадера
        # data = self._loader.load(SCHEDULE_DATA_FILE)
        # if not data:
        #     data = self._parser.fetch_examiner_schedule(
        #         self._parser.get_all_sheets_in_folder(FOLDER_ID)
        #     )
        # data: dict = data.get(str(year), {})
        # examiner_data: dict[list] = {
        #     "milestone_1": [],
        #     "milestone_2": [],
        #     "milestone_3": [],
        # }
        # for milestone, topics in data.items():
        #     for topic in topics:
        #         if (
        #             examiner.lower().strip()
        #             in topic.get("examiner", "").lower().strip()
        #         ):
        #             examiner_data[milestone].append(topic)

        # return json.dumps(examiner_data, ensure_ascii=False, indent=2)

    def add_topic(
        self,
        *,
        key_topic: str = "ТЕСТ 2026",
        topic: str,
        description: str = "Описание будет добавлено позже",
        curator: str = "",
        examiner: str = "",
    ): ...

    #     try:
    #         self._parser.append_row_with_format(
    #             spreadsheets_ids=self._parser.get_all_sheets_in_folder(FOLDER_ID),
    #             key_topic=key_topic,
    #             worksheet_topic="Темы",
    #             row_data=[topic, description, curator, examiner],
    #         )
    #     except Exception:
    #         raise Exception("Ошибка добавления в таблицу")

    # def remove_topic(
    #     self,
    #     *,
    #     key_topic: str = "ТЕСТ 2026",
    #     topic: str,
    # ):
    #     try:
    #         self._parser.delete_row_by_topic(
    #             spreadsheets_ids=self._parser.get_all_sheets_in_folder(FOLDER_ID),
    #             key_topic=key_topic,
    #             worksheet_topic="Темы",
    #             theme_topic=topic,
    #         )
    #     except Exception:
    #         raise Exception("Ошибка добавления в таблицу")


# if __name__ == "__main__":
#     storage = Storage()
#     storage.update_data_from_cloud()
#     print(storage.get_unique_topics())
