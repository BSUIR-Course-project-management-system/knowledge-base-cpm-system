import gspread
import logging
import sys
import pandas as pd
import json
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
from dotenv import load_dotenv
from typing import Any
from abc import ABC, abstractmethod


GROUP_TABLE_COLUMN_MAPPING = "table_api/config/column_mapping.json"
BOOLEAN_MAPPING = "table_api/config/boolean_mapping.json"
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


class ILoader(ABC):
    @abstractmethod
    def load(self, file_path: str) -> dict:
        pass


class JsonLoader(ILoader):
    def load(self, file_path: str) -> dict:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                result = json.load(f)
                return result
        except FileNotFoundError:
            logging.error("Файл для загрузки не найден")
            return None


class ISaver(ABC):
    @abstractmethod
    def save(self, file_path: str) -> dict:
        pass


class JsonSaver(ISaver):
    def save(self, file_path: str, data: dict) -> None:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except FileNotFoundError:
            logging.error("Файл для загрузки не найден")
            return


class GoogleSheetsParser:
    """
    Класс парсера Google Sheets для извлечения информации из Google Drive с Google Sheets.

    Использует сервисный аккаунт Google Cloud, библиотеку ``gspread`` для простого синтаксиса извлечения данных из таблиц и официальную библиотеку ``google-api-client`` для извлечения всех таблиц в папке.
    """

    HIERARCHY_DIVIDE_SYMBOL = "␟"

    def __init__(self, credentials_path: str):
        try:
            logging.info("Попытка авторизации в Google Cloud")
            self._gserv_acc = gspread.service_account(filename=credentials_path)
            logging.info("Успешная авторизация в Google Cloud!")

            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                # !: Если необходимо добавить функционал записи убрать в конце .readonly, но лучше делать отдельный класс под запись
                scopes=["https://www.googleapis.com/auth/drive.readonly"],
            )
            self._drive_service = build("drive", "v3", credentials=credentials)

        except Exception as e:
            logging.error(f"Непредвиденная ошибка при работе с API: {e}", exc_info=True)

    def get_all_sheets_in_folder(self, folder_id: str) -> list:
        """
        Ищет все файлы типа Google Sheets внутри указанной папки.

        :param folder_id: ID папки в которой ищем
        :type folder_id: str
        :return: Список ID найденных Google Sheets
        :rtype: list
        """
        logging.info(f"Начинаем поиск Google Таблиц в папке с ID: {folder_id}")
        sheet_ids = []
        page_token = None
        query = f"mimeType='application/vnd.google-apps.spreadsheet' and '{folder_id}' in parents and trashed = false"
        try:
            while True:
                logging.debug(
                    "Отправка запроса к Google Drive API для получения списка файлов..."
                )
                response = (
                    self._drive_service.files()
                    .list(
                        q=query,
                        spaces="drive",
                        fields="nextPageToken, files(id, name)",
                        pageToken=page_token,
                    )
                    .execute()
                )

                files = response.get("files", [])
                if not files:
                    logging.debug("На данной странице (итерации) таблиц не найдено.")

                for file in files:
                    logging.info(
                        f"Найдена таблица: '{file.get('name')}' (ID: {file.get('id')})"
                    )
                    sheet_ids.append(file.get("id"))

                page_token = response.get("nextPageToken")
                if not page_token:
                    logging.info(
                        "Поиск таблиц в папке успешно завершен. Больше страниц нет."
                    )
                    break

        except Exception as e:
            logging.error(
                f"Критическая ошибка при поиске файлов на Google Диске: {e}",
                exc_info=True,
            )

        logging.info(
            f"Итог: найдено {len(sheet_ids)} таблиц(ы) для последующего парсинга."
        )
        return sheet_ids

    @staticmethod
    def _normalize(text: str) -> str:
        """
        Безопасная нормализация для сравнения заголовков. Преобразует строку в нижний регистр без пробелов слева и справа и заменяет `'ё'` на `'е'`

        :param text: Текст для нормализации
        :type text
        :return: Нормализованная строка
        :rtype: str
        """
        return str(text).strip().lower().replace("ё", "е")

    def _build_reverse_mapping(self, mapping: dict[str, list[str]]) -> dict[str, str]:
        """
        Преобразует ``{"target": ["alias1", "alias2"]}`` в ``{"alias1_norm": "target", ...}``.
        Что удобно для дальнейшей обработки.
        Используется для таких словарей с маппингом значение: ``список_ключей[ключи...]``

        :param mapping: Словарь с прямым маппингом
        :type mapping: dict[str, list[str]]
        :return: Словарь с нормалищованным маппингом
        :rtype: dict[str, str]
        """
        reverse = {}
        for target, aliases in mapping.items():
            for alias in aliases:
                reverse[self._normalize(alias)] = target
        return reverse

    def _load_mapping(self, file_path: str, reversed: bool = False):
        """
        Функция загрузки маппинга из файла `json`.

        :param file_path: Путь к файлу `json`
        :type file_path: str
        :param reversed: Флаг необходима ли нормализация маппинга(разворот)
        :type reversed: bool
        :return: Маппинг, `None` в случае отсутствия файла.
        :rtype: dict | None
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                mapping = json.load(f)
        except FileNotFoundError:
            mapping = None
            logging.warning("Файл маппинга не найден")
        if reversed:
            return self._build_reverse_mapping(mapping)
        return mapping

    def _value_type_conversion(self, value: Any) -> Any:
        """
        Функция для преобразования значения(обычно строки из ячейки таблицы) для сериализации в `json`

        :param value: Значение для преобразования
        :type value: Any
        :return: Нормализованное значение
        :rtype: Any
        """
        if value is None or pd.isna(value):
            return None
        if isinstance(value, str):
            value = value.strip()
            if value == "":
                return None
            mapping = self._load_mapping(file_path=BOOLEAN_MAPPING)
            trues = tuple(mapping["true"].keys())
            falses = tuple(mapping["false"].keys())
            if value.lower() in trues:
                return True
            if value.lower() in falses:
                return False
            if re.fullmatch(r"[-+]?\d+", value):
                return int(value)
            normalized = value.replace(",", ".")
            if re.fullmatch(r"[-+]?\d*\.?\d+", normalized):
                return float(normalized)
            return value
        return value

    def _replace_preserving_suffix(self, text: str, reverse_map: dict) -> str:
        """
        Функция для корректных преобразований с маппингом.
        Если текст начинается с ключа маппинга, то проверяет есть ли суффикс (цифры, знаки препинания).
        Добавляет в качестве суффикса только цифры, знаки препинания, пробелы, НО не буквы
        Если нет суффикса, то возвращает подходящий ключ.
        Если ни один ключ маппинга не подошел - возвращает исходный текст.

        :param text: Текст для преобразования в ключ маппинга
        :type text: str
        :param reverse_map: Маппинг ! обязательно обратный (для объяснения смотри :meth:`_build_reverse_mapping`)
        :type reverse_map: dict
        :return: Итоговое значение текста
        :rtype: str

        .. seealso::
            :meth:`_build_reverse_mapping`
        """
        for key in sorted(reverse_map.keys(), key=len, reverse=True):
            norm_key = self._normalize(key)
            if text.startswith(norm_key):
                suffix = text[len(norm_key) :]
                # Разрешаем в суффиксе только цифры, пробелы, знаки препинания, НО не буквы
                if not suffix or re.fullmatch(r"[\d\s\W]*", suffix):
                    return reverse_map[norm_key] + suffix
                else:
                    return reverse_map[norm_key]
        # Если ни один ключ не подошёл – возвращаем исходный текст
        return text

    def _get_headers_number_of_rows(
        self, table: list[list[Any]], start_row_index: int = 0, start_col_index: int = 0
    ) -> int:
        """
        Получает высоту заголовков таблицы.
        Как работает: берет стартовые индексы и отсчитывает от них повторяющиеся значения стартового заголовка,
        как только значение заголовка меняется счет заканчивается.

        :param table: Таблица для которой посчитать
        :type table: list[list[Any]]
        :param start_row_index: Начальный индекс строки (`default = 0`)
        :type start_row_index: int
        :param start_col_index: Начальный индекс столбца (`default = 0`)
        :type start_col_index: int
        :return: Количество строк занимаемых заголовками
        :rtype: int
        """
        first_header = table[start_row_index][start_col_index]
        row = 1
        while self._normalize(first_header) == self._normalize(
            table[row][start_col_index]
        ):
            row += 1
        return row

    def _get_structured_group_table_data_frame(
        self,
        raw_table: list,
        divide_symbol: str,
    ) -> pd.DataFrame:
        """
        Создание структурированной таблицы данных группы с корректной обработкой вложенности заголовков.

        :param raw_table: Сырая таблица !!! обязательно с дополненными объединенными ячейками (пример смотреть :meth:`_parse_group_info`)
        :type raw_table: list
        :param divide_symbol: Символ для разделения иерархических заголовков
        :type divide_symbol: str
        :return: Структурированная полноценная DataFrame таблица
        :rtype: pd.DataFrame
        """
        max_cols = max(len(row) for row in raw_table)

        padded = [row + [""] * (max_cols - len(row)) for row in raw_table]

        header_rows = self._get_headers_number_of_rows(raw_table)

        headers = [row[:] for row in padded[:header_rows]]

        col_keys = []
        for col in range(max_cols):
            parts = []
            for row in range(header_rows):
                val = headers[row][col].strip()
                if val and (not parts or parts[-1] != val):
                    parts.append(val)
            col_keys.append(divide_symbol.join(parts) if parts else f"col_{col}")

        df = pd.DataFrame(padded[header_rows:], columns=col_keys)

        mapping = self._load_mapping(GROUP_TABLE_COLUMN_MAPPING, reversed=True)
        # print(df.columns)

        if mapping:
            new_cols = []
            for column in df.columns:
                norm = self._normalize(column)
                # print(f"norm {norm}")
                target = mapping.get(norm)
                if divide_symbol in column:
                    target_parts = norm.split(divide_symbol)
                    # print(f"target_parts {target_parts}")
                    normalized_parts = []
                    for part in target_parts:
                        normalized_part = self._normalize(part)
                        if mapping.get(normalized_part) is not None:
                            normalized_part = mapping.get(normalized_part)
                        else:
                            normalized_part = self._replace_preserving_suffix(
                                normalized_part, mapping
                            )
                            # print(f"re:{norm}")

                        normalized_parts.append(normalized_part)

                    target = GoogleSheetsParser.HIERARCHY_DIVIDE_SYMBOL.join(
                        normalized_parts
                    )

                new_cols.append(target if target else f"extra{divide_symbol}{column}")
            df.columns = new_cols
        else:
            df.columns = [f"extra{divide_symbol}{column}" for column in df.columns]
        return df

    def _table_row_to_nested_dicts(self, row, divide_symbol: str) -> dict:
        """
        Функция преобразования строки таблицы в словарь вложенных словарей(иерархическая структура).
        Используется для преобразования в `json`. (обычно с `pd.DataFrame`)
        Пример использования: :meth:`_parse_group_info`->:meth:`upload_all_data_to_json`

        :param row: Строка таблицы для преобразования
        :param divide_symbol: Символ разделения иерархической структуры
        :type divide_symbol: str
        :return: Словарь с иерархической структурой и данными строки таблицы
        :rtype: dict
        """
        nested = {}
        for key, value in row.items():
            value = self._value_type_conversion(value)
            parts = key.split(divide_symbol)
            d = nested
            for p in parts[:-1]:
                d = d.setdefault(p, {})
            d[parts[-1]] = value
        return nested

    def _parse_group_info(self, worksheet: gspread.Worksheet) -> list[dict]:
        """
        Функция парсинга листа с данными группы.

        :param worksheet: Лист группы в Google Sheet таблице
        :type worksheet: gspread.Worksheet
        :return: Данные группы представленные в виде списка вложенных словарей(иерархия)
        :rtype: list[dict]
        """
        sheet_name = worksheet.title
        if not (sheet_name.isdigit() and len(sheet_name) == 6):
            logging.info(f"Передан не тот лист: {sheet_name}")
            return None

        logging.info(f"Начало парсинга листа {sheet_name}")

        divide_symbol = GoogleSheetsParser.HIERARCHY_DIVIDE_SYMBOL

        raw = worksheet.get_all_values(combine_merged_cells=True)

        if not raw or len(raw) < 2:
            logging.warning(f"Лист {sheet_name} пуст или содержит меньше 2 строк")
            return None

        df = self._get_structured_group_table_data_frame(raw, divide_symbol)
        df = df.replace("", None)

        # Сворачиваем в список вложенных словарей
        records = [
            self._table_row_to_nested_dicts(row, divide_symbol)
            for _, row in df.iterrows()
        ]
        logging.info(f"Успешный парсинг листа {sheet_name}, записей: {len(records)}")
        return records

    def _parse_milestone_info(self, worksheet: gspread.Worksheet):
        pass

    def _parse_themes_info(self, worksheet: gspread.Worksheet):
        """
        Функция парсинга листа с данными о темах.

        :param worksheet: Лист тем в Google Sheet таблице
        :type worksheet: gspread.Worksheet
        :return: Данные тем представленные в виде списка словарей
        :rtype: list[dict]
        """
        sheet_name = worksheet.title
        expected_sheet_name = "Темы"
        if self._normalize(expected_sheet_name) not in self._normalize(sheet_name):
            logging.info(f"Передан не тот лист (нужен Темы): {sheet_name}")
            return None

        logging.info(f"Начало парсинга листа {sheet_name}")
        divide_symbol = GoogleSheetsParser.HIERARCHY_DIVIDE_SYMBOL
        raw = worksheet.get_all_values(combine_merged_cells=True)
        if not raw or len(raw) < 2:
            logging.warning(f"Лист {sheet_name} пуст или содержит меньше 2 строк")
            return None

        df = self._get_structured_group_table_data_frame(raw, divide_symbol)
        df = df.replace("", None)

        # Сворачиваем в список вложенных словарей
        records = [
            self._table_row_to_nested_dicts(row, divide_symbol)
            for _, row in df.iterrows()
        ]
        logging.info(f"Успешный парсинг листа {sheet_name}, записей: {len(records)}")
        print(records)
        return records

    def upload_all_data_to_json(self, spreadsheets: list[str]):
        """
        Функция загрузки всех данных из таблиц в `json` файлы.

        :param spreadsheets: Список ID таблиц
        :type spreadsheets: list[str]
        """
        group_data = {}
        for spreadsheet_id in spreadsheets:
            logging.info(f"Попытка открытия таблицы с ID: {spreadsheet_id}")
            sheet = self._gserv_acc.open_by_key(spreadsheet_id)
            logging.info(f"Таблица с '{sheet.title}' успешно найдена и открыта")

            logging.info(f"Начало парсинга документа {sheet.title}")
            for worksheet in sheet.worksheets():
                sheet_name = worksheet.title
                if sheet_name.isdigit() and len(sheet_name) == 6:
                    logging.info(f"Парсинг листа группы: {sheet_name}")
                    parsed_worksheet = self._parse_group_info(worksheet=worksheet)

                    if not parsed_worksheet:
                        logging.warning(f"Лист {sheet_name} пуст")
                        continue
                    logging.warning(f"Лист {sheet.title} пуст")
                    print(
                        json.dumps(
                            self._parse_themes_info(worksheet=worksheet),
                            ensure_ascii=False,
                            indent=2,
                        )
                    )

                group_data[sheet_name] = parsed_worksheet

                logging.info(f"Успешный парсинг листа {sheet_name}")

            logging.info(f"Успешный парсинг документа {sheet.title}")
        pass

    def fetch_all_groups(self, spreadsheets: list[str]):
        all_data = {}
        for spreadsheet_id in spreadsheets:
            logging.info(f"Попытка открытия таблицы с ID: {spreadsheet_id}")
            sheet = self._gserv_acc.open_by_key(spreadsheet_id)
            logging.info(f"Таблица с '{sheet.title}' успешно найдена и открыта")

            logging.info(f"Начало парсинга документа {sheet.title}")
            for worksheet in sheet.worksheets():
                sheet_name = worksheet.title

                parsed_worksheet = self._parse_group_info(worksheet=worksheet)

                if not parsed_worksheet:
                    continue

                all_data[sheet_name] = parsed_worksheet
                logging.info(f"Успешный парсинг листа {sheet_name}")

            logging.info(f"Успешный парсинг документа {sheet.title}")

        return all_data

    def fetch_examiner_schedule(self, spreadsheets: list[str]):
        for spreadsheet_id in spreadsheets:
            logging.info(f"Попытка открытия таблицы с ID: {spreadsheet_id}")
            sheet = self._gserv_acc.open_by_key(spreadsheet_id)
            logging.info(f"Таблица с '{sheet.title}' успешно найдена и открыта")

            logging.info(f"Начало парсинга документа {sheet.title}")
            logging.error(f"Ошибка парсинга(не реализовано) {sheet.title}")


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

    def find_first(self, data, target_key, default=None):
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
                date_defence: str = self.find_first(row, "date_defence")
                rounded_final_grade = self.find_first(row, "rounded_final_grade")
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
