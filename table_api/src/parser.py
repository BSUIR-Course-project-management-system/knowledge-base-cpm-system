import gspread
import pandas as pd
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build
from typing import Any
from table_api.src.loader import ILoader, JsonLoader
from logger.logger import Logger

GROUP_TABLE_COLUMN_MAPPING = "table_api/config/column_mapping.json"
BOOLEAN_MAPPING = "table_api/config/boolean_mapping.json"
LOG_FILE = "table_api/logs/parser.log"


class GoogleSheetsParser:
    """
    Класс парсера Google Sheets для извлечения информации из Google Drive с Google Sheets.

    Использует сервисный аккаунт Google Cloud, библиотеку ``gspread`` для простого синтаксиса извлечения данных из таблиц и официальную библиотеку ``google-api-client`` для извлечения всех таблиц в папке.
    """

    HIERARCHY_DIVIDE_SYMBOL = "␟"

    def __init__(self, credentials_path: str):
        self._logger = Logger(LOG_FILE, level="INFO")
        try:
            self._logger.info("Попытка авторизации в Google Cloud")
            self._gserv_acc = gspread.service_account(filename=credentials_path)
            self._logger.info("Успешная авторизация в Google Cloud!")

            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                # !: Если необходимо добавить функционал записи убрать в конце .readonly, но лучше делать отдельный класс под запись
                scopes=["https://www.googleapis.com/auth/drive.readonly"],
            )
            self._drive_service = build("drive", "v3", credentials=credentials)

        except Exception as e:
            self._logger.error(f"Непредвиденная ошибка при работе с API: {e}")

    def get_all_sheets_in_folder(self, folder_id: str) -> list:
        """
        Ищет все файлы типа Google Sheets внутри указанной папки.

        :param folder_id: ID папки в которой ищем
        :type folder_id: str
        :return: Список ID найденных Google Sheets
        :rtype: list
        """
        self._logger.info(f"Начинаем поиск Google Таблиц в папке с ID: {folder_id}")
        sheet_ids = []
        page_token = None
        query = f"mimeType='application/vnd.google-apps.spreadsheet' and '{folder_id}' in parents and trashed = false"
        try:
            while True:
                self._logger.debug(
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
                    self._logger.debug(
                        "На данной странице (итерации) таблиц не найдено."
                    )

                for file in files:
                    self._logger.info(
                        f"Найдена таблица: '{file.get('name')}' (ID: {file.get('id')})"
                    )
                    sheet_ids.append(file.get("id"))

                page_token = response.get("nextPageToken")
                if not page_token:
                    self._logger.info(
                        "Поиск таблиц в папке успешно завершен. Больше страниц нет."
                    )
                    break

        except Exception as e:
            self._logger.error(
                f"Критическая ошибка при поиске файлов на Google Диске: {e}"
            )

        self._logger.info(
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

    def _load_mapping(
        self, file_path: str, reversed: bool = False, loader: ILoader = JsonLoader()
    ):
        """
        Функция загрузки маппинга из файла `json`.

        :param file_path: Путь к файлу `json`
        :type file_path: str
        :param reversed: Флаг необходима ли нормализация маппинга(разворот)
        :type reversed: bool
        :return: Маппинг, `None` в случае отсутствия файла.
        :rtype: dict | None
        """
        mapping = loader.load(file_path)
        if not mapping:
            mapping = None
            self._logger.warning("Файл маппинга не найден")
        if reversed and mapping:
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

        if mapping:
            new_cols = []
            for column in df.columns:
                norm = self._normalize(column)
                target = mapping.get(norm)
                if divide_symbol in column:
                    target_parts = norm.split(divide_symbol)
                    normalized_parts = []
                    for part in target_parts:
                        normalized_part = self._normalize(part)
                        if mapping.get(normalized_part) is not None:
                            normalized_part = mapping.get(normalized_part)
                        else:
                            normalized_part = self._replace_preserving_suffix(
                                normalized_part, mapping
                            )

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
            self._logger.info(f"Передан не тот лист: {sheet_name}")
            return None

        self._logger.info(f"Начало парсинга листа {sheet_name}")

        divide_symbol = GoogleSheetsParser.HIERARCHY_DIVIDE_SYMBOL

        raw = worksheet.get_all_values(combine_merged_cells=True)

        if not raw or len(raw) < 2:
            self._logger.warning(f"Лист {sheet_name} пуст или содержит меньше 2 строк")
            return None

        df = self._get_structured_group_table_data_frame(raw, divide_symbol)
        df = df.replace("", None)
        # Сворачиваем в список вложенных словарей
        records = [
            self._table_row_to_nested_dicts(row, divide_symbol)
            for _, row in df.iterrows()
        ]
        self._logger.info(
            f"Успешный парсинг листа {sheet_name}, записей: {len(records)}"
        )
        return records

    def _parse_topics_info(self, worksheet: gspread.Worksheet):
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
            self._logger.info(
                f"Передан не тот лист : {sheet_name}(нужен {expected_sheet_name})"
            )
            return None

        self._logger.info(f"Начало парсинга листа {sheet_name}")
        divide_symbol = GoogleSheetsParser.HIERARCHY_DIVIDE_SYMBOL
        raw = worksheet.get_all_values(combine_merged_cells=True)
        if not raw or len(raw) < 2:
            self._logger.warning(f"Лист {sheet_name} пуст или содержит меньше 2 строк")
            return None

        df = self._get_structured_group_table_data_frame(raw, divide_symbol)
        df = df.replace("", None)

        # Сворачиваем в список вложенных словарей
        records = [
            self._table_row_to_nested_dicts(row, divide_symbol)
            for _, row in df.iterrows()
        ]
        self._logger.info(
            f"Успешный парсинг листа {sheet_name}, записей: {len(records)}"
        )
        return records

    def _parse_time_range(self, raw_time_str):
        """
        Разбивает строку времени по тире и возвращает словарь.
        """
        raw_time_str = str(raw_time_str).strip()
        if not raw_time_str:
            return {"start": "", "end": ""}

        normalized_str = raw_time_str.replace("—", "-").replace("–", "-")

        if "-" in normalized_str:
            parts = normalized_str.split("-", 1)
            return {"start": parts[0].strip(), "end": parts[1].strip()}
        else:
            return {"start": raw_time_str, "end": ""}

    def _parse_sub_tables(
        self, raw_table: list, separator_text: str, separator_key: str
    ):
        """
        Универсальная логика для листов, содержащих несколько подтаблиц.
        """
        sub_tables = {}

        header_row_idx = -1
        col_indices = []
        table_names = []

        for r_idx, row in enumerate(raw_table):
            prev_cell = ""
            for c_idx, cell in enumerate(row):
                cell_str = self._normalize(str(cell))

                if separator_text in cell_str and prev_cell != cell_str:
                    header_row_idx = r_idx
                    match = re.search(r"\d+", cell_str)
                    col_indices.append(c_idx)
                    table_names.append(f"{separator_key}{match.group()}")
                prev_cell = cell_str
            if col_indices:
                break

        if not col_indices:
            return {}

        for i in range(len(col_indices)):
            start_col = col_indices[i]
            end_col = (
                col_indices[i + 1]
                if i + 1 < len(col_indices)
                else len(raw_table[header_row_idx])
            )
            table_name = table_names[i]

            sub_raw_table = []

            for row in raw_table[header_row_idx + 1 :]:
                padded_row = (
                    row + [""] * (end_col - len(row)) if len(row) < end_col else row
                )

                sub_row = padded_row[start_col:end_col]

                if any(str(c).strip() for c in sub_row):
                    sub_raw_table.append(sub_row)

            if not sub_raw_table or len(sub_raw_table) < 2:
                continue

            last_valid_col = -1
            num_cols = len(sub_raw_table[0])

            for col_idx in range(num_cols):
                if any(
                    str(row[col_idx]).strip() != ""
                    for row in sub_raw_table
                    if col_idx < len(row)
                ):
                    last_valid_col = col_idx

            if last_valid_col != -1:
                sub_raw_table = [row[: last_valid_col + 1] for row in sub_raw_table]

            df = self._get_structured_group_table_data_frame(
                sub_raw_table, GoogleSheetsParser.HIERARCHY_DIVIDE_SYMBOL
            )

            # Удаляем дублирующиеся столбцы (чтобы df["topic"] не ломался)
            df = df.loc[:, ~df.columns.duplicated()].copy()

            if "examiner" in df.columns:
                df["examiner"] = df["examiner"].replace("", pd.NA).ffill()
                df["numb"] = df["numb"].replace("", pd.NA).ffill()

            if "topic" in df.columns:
                df = df.dropna(subset=["topic"])
                df = df[df["topic"].astype(str).str.strip() != ""]

            if "time" in df.columns:
                df["time"] = df["time"].apply(self._parse_time_range)

            df = df.fillna("")

            sub_tables[table_name] = df.to_dict(orient="records")

        return sub_tables

    def _parse_milestone_schedule_info(self, worksheet: gspread.Worksheet):
        sheet_name = self._normalize(worksheet.title)
        self._logger.info(f"Начало парсинга листа {sheet_name}")
        if "график опроцентов" not in sheet_name:
            self._logger.info(f"Передан не тот лист: {sheet_name}")
            return None
        # divide_symbol = GoogleSheetsParser.HIERARCHY_DIVIDE_SYMBOL

        raw = worksheet.get_all_values(combine_merged_cells=True)

        if not raw or len(raw) < 2:
            self._logger.warning(f"Лист {sheet_name} пуст или содержит меньше 2 строк")
            return None

        return self._parse_sub_tables(
            raw, separator_text="опроцентов", separator_key="milestone_"
        )

    # TODO: написать универсальный роутер по типам листов

    def get_all_data_from_cloud(self, spreadsheets: list[str]) -> dict:
        """
        Функция загрузки всех данных из облака в словарь проиндексированный по типу данных в нем

        :param spreadsheets: Список ID таблиц
        :type spreadsheets: list[str]
        :return: Все данные из облака(данные групп, данные тем, расписание опроцентовок) проиндексированные по типу ``data["name_data"]``
        :rtype: dict
        """
        all_data = {}
        group_data = {}
        topic_data = {}
        schedule_data = {}
        for spreadsheet_id in spreadsheets:
            self._logger.info(f"Попытка открытия таблицы с ID: {spreadsheet_id}")
            sheet = self._gserv_acc.open_by_key(spreadsheet_id)
            self._logger.info(f"Таблица с '{sheet.title}' успешно найдена и открыта")

            self._logger.info(f"Начало парсинга документа {sheet.title}")
            for worksheet in sheet.worksheets():
                sheet_name = worksheet.title
                self._logger.info(f"Парсинг листа: {sheet_name}")
                if sheet_name.isdigit() and len(sheet_name) == 6:
                    group_worksheet = self._parse_group_info(worksheet=worksheet)

                    if not group_worksheet:
                        self._logger.warning(f"Лист {sheet_name} пуст")
                        continue
                    self._logger.warning(f"Лист {sheet.title} пуст")

                    group_data[sheet_name] = group_worksheet

                elif self._normalize("Темы") in self._normalize(sheet_name):
                    topic_worksheet = self._parse_topics_info(worksheet=worksheet)
                    if not topic_worksheet:
                        self._logger.warning(f"Лист {sheet_name} пуст")
                        continue
                    year_of_topics = re.search(r"\d{4}", sheet.title)
                    key = year_of_topics.group() if year_of_topics else "default"
                    if key not in topic_data:
                        topic_data[key] = topic_worksheet
                    else:
                        topic_data[key].extend(topic_worksheet)

                elif self._normalize("график опроцентов") in self._normalize(
                    sheet_name
                ):
                    schedule_worksheet = self._parse_milestone_schedule_info(
                        worksheet=worksheet
                    )
                    year_of_topics = re.search(r"\d{4}", sheet.title)
                    key = year_of_topics.group() if year_of_topics else "default"
                    schedule_data[key] = schedule_worksheet
                else:
                    self._logger.info(f"Необработанный тип листа: {sheet_name}")

                self._logger.info(f"Успешный парсинг листа {sheet_name}")

            self._logger.info(f"Успешный парсинг документа {sheet.title}")
        all_data["group_data"] = group_data
        all_data["topic_data"] = topic_data
        all_data["schedule_data"] = schedule_data
        return all_data

    def fetch_all_groups(self, spreadsheets: list[str]):
        all_data = {}
        for spreadsheet_id in spreadsheets:
            self._logger.info(f"Попытка открытия таблицы с ID: {spreadsheet_id}")
            sheet = self._gserv_acc.open_by_key(spreadsheet_id)
            self._logger.info(f"Таблица с '{sheet.title}' успешно найдена и открыта")

            self._logger.info(f"Начало парсинга документа {sheet.title}")
            for worksheet in sheet.worksheets():
                sheet_name = worksheet.title
                parsed_worksheet = self._parse_group_info(worksheet=worksheet)
                if not parsed_worksheet:
                    continue

                all_data[sheet_name] = parsed_worksheet
                self._logger.info(f"Успешный парсинг листа {sheet_name}")

            self._logger.info(f"Успешный парсинг документа {sheet.title}")

        return all_data

    def fetch_examiner_schedule(self, spreadsheets: list[str]):
        all_data = {}
        for spreadsheet_id in spreadsheets:
            self._logger.info(f"Попытка открытия таблицы с ID: {spreadsheet_id}")
            sheet = self._gserv_acc.open_by_key(spreadsheet_id)
            self._logger.info(f"Таблица с '{sheet.title}' успешно найдена и открыта")

            self._logger.info(f"Начало парсинга документа {sheet.title}")
            for worksheet in sheet.worksheets():
                sheet_name = worksheet.title
                parsed_worksheet = self._parse_milestone_schedule_info(
                    worksheet=worksheet
                )
                if not parsed_worksheet:
                    continue

                year_of_topics = re.search(r"\d{4}", sheet.title)
                key = year_of_topics.group() if year_of_topics else "default"
                all_data[key] = parsed_worksheet
                self._logger.info(f"Успешный парсинг листа {sheet_name}")

            self._logger.info(f"Успешный парсинг документа {sheet.title}")
        return all_data
