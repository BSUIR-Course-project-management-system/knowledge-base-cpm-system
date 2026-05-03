import gspread
# import logging
import sys
import os
import pandas as pd
import numpy as np
import json
from dotenv import load_dotenv

LOG_FILE = "table_api/logs/google_sheets_api.log"
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s | %(levelname)-8s | %(message)s",
#     handlers=[
#         logging.FileHandler(LOG_FILE, encoding="utf-8"),
#         logging.StreamHandler(sys.stdout),
#     ],
# )
load_dotenv()
CREDENTIALS_FILE = os.getenv("CREDENTIALS_FILE")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

if not SPREADSHEET_ID:
    raise ValueError("ОШИБКА: Не найден ID в .env!")

COLUMNS_FOR_GROUP_FETCHING = [
    "ФИО",
    "Тема курсового проекта",
    "Куратор курсового проекта",
    "Проверяющий по курсовому проекту",
]


class GoogleSheetsParser:
    def __init__(self, credentials_path: str, spreadsheets_ids: list[str]):
        try:
            # logging.info("Попытка авторизации в Google Cloud")
            self._gserv_acc = gspread.service_account(filename=credentials_path)
            # logging.info("Успешная авторизация в Google Cloud!")
            self._spreadsheets = spreadsheets_ids
        except Exception as e:
            # logging.error(f"Непредвиденная ошибка при работе с API: {e}", exc_info=True)
            pass

    def get_raw_data(self):
        pass

    def fetch_all_groups(self):
        all_data = {}
        for spreadsheet_id in self._spreadsheets:
            # logging.info(f"Попытка открытия таблицы с ID: {spreadsheet_id}")
            sheet = self._gserv_acc.open_by_key(spreadsheet_id)
            # logging.info(f"Таблица с '{sheet.title}' успешно найдена и открыта")

            # logging.info(f"Начало парсинга документа {sheet.title}")
            for worksheet in sheet.worksheets():
                sheet_name = worksheet.title
                if not (sheet_name.isdigit() and len(sheet_name) == 6):
                    # logging.info(
                    #     f"Пропускаем лист с ненужной информацией: {sheet_name}"
                    # )
                    continue
                # logging.info(f"Начало парсинга листа {sheet_name}")
                raw_data = worksheet.get_all_values()
                if not raw_data or len(raw_data) < 4:
                    continue
                headers = raw_data[0]

                df = pd.DataFrame(raw_data[1:], columns=headers)
                columns_to_keep = [
                    col for col in COLUMNS_FOR_GROUP_FETCHING if col in df.columns
                ]
                df = df[columns_to_keep]

                if "" in df.columns:
                    df = df.drop(columns=[""])

                if "ФИО" in df.columns:
                    df = df.dropna(subset=["ФИО"])
                    df = df[df["ФИО"].str.strip() != ""]

                all_data[sheet_name] = df.to_dict(orient="records")
            #     logging.info(f"Успешный парсинг листа {sheet_name}")
            # logging.info(f"Успешный парсинг документа {sheet.title}")
        return all_data

    def fetch_examiner_schedule(self):
        pass


class Storage:
    def __init__(self):
        self._parser = GoogleSheetsParser(
            CREDENTIALS_FILE,
            [
                SPREADSHEET_ID,
            ],
        )

    def _load_all_group_data(self) -> dict:
        # logging.info("Storage запрашивает данные у парсера...")
        try:
            return self._parser.fetch_all_groups()
        except Exception as e:
            # logging.error(f"Ошибка при получении данных: {e}")
            return {}

    def get_unique_topics(self):
        unique_topics = {}
        data = self._load_all_group_data()
        for sheet_name, records in data.items():
            for row in records:
                topic = row.get("Тема курсового проекта", "").strip()
                curator = row.get("Куратор курсового проекта", "").strip()
                examiner = row.get("Проверяющий по курсовому проекту", "").strip()
                if topic:
                    unique_topics[topic] = {
                        "curator": curator,
                        "examiner": examiner,
                        "is_used": True,
                    }

        formatted_topics = []

        for idx, (topic_text, info) in enumerate(unique_topics.items(), start=1):
            formatted_topics.append(
                {
                    "id": str(idx),
                    "text": topic_text,
                    "is_used": info["is_used"],
                    "curator": info["curator"],
                    "examiner": info["examiner"],
                }
            )

        return json.dumps(formatted_topics, ensure_ascii=False, indent=2)

    def get_examiner_schedule(self, examiner):
        """Заглушка"""
        # logging.info("Использование данных заглушки для графика")
        mock_data = {
            "Milestone_1": [],
            "Milestone_2": [
                {
                    "project": "База знаний интеллектуального помощника (Leonard)",
                    "day": "ЧТ",
                    "start_time": "15:00",
                    "end_time": "15:30",
                    "format": "очно, 610-5",
                },
                {
                    "project": "База знаний интеллектуальной системы по ЖКХ",
                    "day": "ВТ",
                    "start_time": "15:00",
                    "end_time": "15:30",
                    "format": "очно, 610-5",
                },
                {
                    "project": "База знаний цифрового двойника предприятия (Савушкин продукт)",
                    "day": "ВТ",
                    "start_time": "15:30",
                    "end_time": "16:00",
                    "format": "очно, 610-5",
                },
                {
                    "project": "База знаний интеллектуальной справочной системы по специальности «Искусственный интеллект»",
                    "day": "ВТ",
                    "start_time": "16:00",
                    "end_time": "16:30",
                    "format": "очно, 610-5",
                },
                {
                    "project": "База знаний интеллектуальной системы управления курсовыми и дипломными проектами кафедры",
                    "day": "ЧТ",
                    "start_time": "15:30",
                    "end_time": "16:00",
                    "format": "очно, 610-5",
                },
                {
                    "project": "База знаний RAG-системы автоматического выявления фактологических противоречий в неструктурированных данных",
                    "day": "ЧТ",
                    "start_time": "16:30",
                    "end_time": "17:00",
                    "format": "очно, 610-5",
                },
                {
                    "project": "База знаний интеллектуальной системы парковки",
                    "day": "ВТ",
                    "start_time": "16:30",
                    "end_time": "17:00",
                    "format": "очно, 610-5",
                },
                {
                    "project": "База знаний интеллектуальной диалоговой системы NIKA",
                    "day": "ЧТ",
                    "start_time": "17:00",
                    "end_time": "17:30",
                    "format": "очно, 610-5",
                },
            ],
            "Milestone_3": [],
        }
        json_result = json.dumps(mock_data, ensure_ascii=False, indent=2)

        return json_result


if __name__ == "__main__":
    storage = Storage()

    topics_json = storage.get_unique_topics()
    print(topics_json)
    print(storage.get_examiner_schedule("Гракова"))
