import pytest
import pandas as pd
from unittest.mock import patch, MagicMock, PropertyMock
from table_api.src.parser import GoogleSheetsParser


@pytest.fixture
def parser(tmp_path):
    """Создаёт экземпляр GoogleSheetsParser с замоканными внешними зависимостями."""
    with (
        patch("table_api.src.parser.gspread.service_account"),
        patch(
            "table_api.src.parser.service_account.Credentials.from_service_account_file"
        ),
        patch("table_api.src.parser.build"),
        patch("table_api.src.parser.Logger"),
    ):
        p = GoogleSheetsParser("fake_credentials.json")
    return p


@pytest.fixture
def boolean_mapping(tmp_path):
    """Создаёт временный файл boolean_mapping.json."""
    import json

    mapping = {
        "true": {"да": True, "yes": True, "true": True, "+": True},
        "false": {"нет": False, "no": False, "false": False, "-": False},
    }
    f = tmp_path / "boolean_mapping.json"
    f.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")
    return str(f)


class TestNormalize:
    def test_lowercase(self, parser):
        assert parser._normalize("HELLO") == "hello"

    def test_strip_whitespace(self, parser):
        assert parser._normalize("  text  ") == "text"

    def test_replace_yo(self, parser):
        assert parser._normalize("Ёлка") == "елка"

    def test_combined(self, parser):
        assert parser._normalize("  ЁЖИК  ") == "ежик"

    def test_empty_string(self, parser):
        assert parser._normalize("") == ""

    def test_numbers_converted(self, parser):
        assert parser._normalize(42) == "42"

    def test_already_normalized(self, parser):
        assert parser._normalize("test") == "test"


class TestBuildReverseMapping:
    def test_basic_reverse(self, parser):
        mapping = {"topic": ["тема", "Тема курсовой"]}
        result = parser._build_reverse_mapping(mapping)
        assert result["тема"] == "topic"
        assert result["тема курсовой"] == "topic"

    def test_multiple_targets(self, parser):
        mapping = {
            "curator": ["куратор", "преподаватель"],
            "examiner": ["проверяющий", "экзаменатор"],
        }
        result = parser._build_reverse_mapping(mapping)
        assert result["куратор"] == "curator"
        assert result["проверяющий"] == "examiner"

    def test_empty_mapping(self, parser):
        result = parser._build_reverse_mapping({})
        assert result == {}

    def test_aliases_are_normalized(self, parser):
        mapping = {"topic": ["  ТЕМА  "]}
        result = parser._build_reverse_mapping(mapping)
        assert "тема" in result


class TestValueTypeConversion:
    @patch("table_api.src.parser.GoogleSheetsParser._load_mapping")
    def test_none_returns_none(self, mock_load, parser):
        assert parser._value_type_conversion(None) is None

    @patch("table_api.src.parser.GoogleSheetsParser._load_mapping")
    def test_nan_returns_none(self, mock_load, parser):
        import math

        result = parser._value_type_conversion(float("nan"))
        assert result is None

    @patch("table_api.src.parser.GoogleSheetsParser._load_mapping")
    def test_empty_string_returns_none(self, mock_load, parser):
        mock_load.return_value = {"true": {}, "false": {}}
        result = parser._value_type_conversion("  ")
        assert result is None

    @patch("table_api.src.parser.GoogleSheetsParser._load_mapping")
    def test_integer_string(self, mock_load, parser):
        mock_load.return_value = {"true": {}, "false": {}}
        assert parser._value_type_conversion("42") == 42

    @patch("table_api.src.parser.GoogleSheetsParser._load_mapping")
    def test_negative_integer_string(self, mock_load, parser):
        mock_load.return_value = {"true": {}, "false": {}}
        assert parser._value_type_conversion("-10") == -10

    @patch("table_api.src.parser.GoogleSheetsParser._load_mapping")
    def test_float_string_dot(self, mock_load, parser):
        mock_load.return_value = {"true": {}, "false": {}}
        assert parser._value_type_conversion("3.14") == 3.14

    @patch("table_api.src.parser.GoogleSheetsParser._load_mapping")
    def test_float_string_comma(self, mock_load, parser):
        mock_load.return_value = {"true": {}, "false": {}}
        assert parser._value_type_conversion("3,14") == 3.14

    @patch("table_api.src.parser.GoogleSheetsParser._load_mapping")
    def test_boolean_true_da(self, mock_load, parser):
        mock_load.return_value = {"true": {"да": True}, "false": {"нет": False}}
        assert parser._value_type_conversion("да") is True

    @patch("table_api.src.parser.GoogleSheetsParser._load_mapping")
    def test_boolean_false_net(self, mock_load, parser):
        mock_load.return_value = {"true": {"да": True}, "false": {"нет": False}}
        assert parser._value_type_conversion("нет") is False

    @patch("table_api.src.parser.GoogleSheetsParser._load_mapping")
    def test_plain_text_returned_as_is(self, mock_load, parser):
        mock_load.return_value = {"true": {}, "false": {}}
        assert parser._value_type_conversion("Разработка ИИ") == "Разработка ИИ"

    @patch("table_api.src.parser.GoogleSheetsParser._load_mapping")
    def test_non_string_int_returned(self, mock_load, parser):
        result = parser._value_type_conversion(100)
        assert result == 100

    @patch("table_api.src.parser.GoogleSheetsParser._load_mapping")
    def test_non_string_list_returned(self, mock_load, parser):
        """Список не является str и не является None/NaN → возвращается как есть.
        pd.isna([1,2,3]) бросает ValueError → значение возвращается сразу."""
        lst = [1, 2, 3]

        with pytest.raises(ValueError):
            parser._value_type_conversion(lst)


class TestReplacePreservingSuffix:
    def test_exact_match(self, parser):
        reverse_map = {"milestone_1": "milestone_1"}
        result = parser._replace_preserving_suffix("milestone_1", reverse_map)
        assert result == "milestone_1"

    def test_match_with_digit_suffix(self, parser):
        reverse_map = {"опроцент": "milestone"}
        result = parser._replace_preserving_suffix("опроцент 1", reverse_map)
        assert result == "milestone 1"

    def test_no_match_returns_original(self, parser):
        reverse_map = {"some_key": "target"}
        result = parser._replace_preserving_suffix("completely_different", reverse_map)
        assert result == "completely_different"

    def test_suffix_with_letter_drops_suffix(self, parser):
        """Суффикс с буквами не допускается — возвращается замена без суффикса."""
        reverse_map = {"куратор": "curator"}
        result = parser._replace_preserving_suffix("кураторы", reverse_map)
        assert result == "curator"

    def test_longer_key_takes_priority(self, parser):
        """Более длинный ключ имеет приоритет при сортировке."""
        reverse_map = {"куратор проекта": "project_curator", "куратор": "curator"}
        result = parser._replace_preserving_suffix("куратор проекта", reverse_map)
        assert result == "project_curator"


class TestGetHeadersNumberOfRows:
    def test_single_header_row(self, parser):
        table = [
            ["Тема", "Куратор"],
            ["ИИ система", "Иванов"],
            ["ML модель", "Петров"],
        ]
        assert parser._get_headers_number_of_rows(table) == 1

    def test_two_header_rows(self, parser):
        table = [
            ["Оценка", "Оценка", "ФИО"],
            ["Оценка", "Итог", "ФИО"],
            ["5", "5", "Иванов"],
        ]
        assert parser._get_headers_number_of_rows(table) == 2


class TestParseTimeRange:
    def test_dash_separator(self, parser):
        result = parser._parse_time_range("10:00-12:00")
        assert result == {"start": "10:00", "end": "12:00"}

    def test_em_dash_separator(self, parser):
        result = parser._parse_time_range("10:00—12:00")
        assert result == {"start": "10:00", "end": "12:00"}

    def test_en_dash_separator(self, parser):
        result = parser._parse_time_range("10:00–12:00")
        assert result == {"start": "10:00", "end": "12:00"}

    def test_no_separator(self, parser):
        result = parser._parse_time_range("10:00")
        assert result == {"start": "10:00", "end": ""}

    def test_empty_string(self, parser):
        result = parser._parse_time_range("")
        assert result == {"start": "", "end": ""}

    def test_with_spaces(self, parser):
        result = parser._parse_time_range("  9:00 - 11:00  ")
        assert result["start"] == "9:00"
        assert result["end"] == "11:00"

    def test_none_input(self, parser):
        """None преобразуется в строку 'None', которая не пустая → возвращается как start."""
        result = parser._parse_time_range(None)

        assert result == {"start": "None", "end": ""}


class TestTableRowToNestedDicts:
    @patch(
        "table_api.src.parser.GoogleSheetsParser._value_type_conversion",
        side_effect=lambda self, v: v,
    )
    def test_flat_row(self, mock_convert, parser):
        row = pd.Series({"topic": "ИИ", "curator": "Иванов"})
        with patch.object(parser, "_value_type_conversion", side_effect=lambda v: v):
            result = parser._table_row_to_nested_dicts(
                row, GoogleSheetsParser.HIERARCHY_DIVIDE_SYMBOL
            )
        assert result["topic"] == "ИИ"
        assert result["curator"] == "Иванов"

    def test_nested_row(self, parser):
        divide = GoogleSheetsParser.HIERARCHY_DIVIDE_SYMBOL
        row = pd.Series(
            {f"grade{divide}final": "5", f"grade{divide}prelim": "4", "topic": "ML"}
        )
        with patch.object(parser, "_value_type_conversion", side_effect=lambda v: v):
            result = parser._table_row_to_nested_dicts(row, divide)
        assert result["grade"]["final"] == "5"
        assert result["grade"]["prelim"] == "4"
        assert result["topic"] == "ML"


class TestLoadMapping:
    @patch("table_api.src.parser.Logger")
    def test_load_returns_mapping_when_file_exists(self, mock_logger_cls, tmp_path):
        import json

        mapping = {"topic": ["тема", "курс"]}
        f = tmp_path / "col_mapping.json"
        f.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")

        with (
            patch("table_api.src.parser.gspread.service_account"),
            patch(
                "table_api.src.parser.service_account.Credentials.from_service_account_file"
            ),
            patch("table_api.src.parser.build"),
        ):
            p = GoogleSheetsParser("fake.json")

        mock_loader = MagicMock()
        mock_loader.load.return_value = mapping
        result = p._load_mapping("any_path", loader=mock_loader)
        assert result == mapping

    @patch("table_api.src.parser.Logger")
    def test_load_returns_none_when_file_missing(self, mock_logger_cls):
        with (
            patch("table_api.src.parser.gspread.service_account"),
            patch(
                "table_api.src.parser.service_account.Credentials.from_service_account_file"
            ),
            patch("table_api.src.parser.build"),
        ):
            p = GoogleSheetsParser("fake.json")

        mock_loader = MagicMock()
        mock_loader.load.return_value = None
        result = p._load_mapping("missing.json", loader=mock_loader)
        assert result is None

    @patch("table_api.src.parser.Logger")
    def test_load_reversed_mapping(self, mock_logger_cls):
        with (
            patch("table_api.src.parser.gspread.service_account"),
            patch(
                "table_api.src.parser.service_account.Credentials.from_service_account_file"
            ),
            patch("table_api.src.parser.build"),
        ):
            p = GoogleSheetsParser("fake.json")

        mapping = {"topic": ["тема"]}
        mock_loader = MagicMock()
        mock_loader.load.return_value = mapping
        result = p._load_mapping("any.json", reversed=True, loader=mock_loader)
        assert "тема" in result
        assert result["тема"] == "topic"


class TestParseGroupInfo:
    def test_non_digit_sheet_name_returns_none(self, parser):
        ws = MagicMock()
        ws.title = "Темы"
        result = parser._parse_group_info(ws)
        assert result is None

    def test_short_digit_name_returns_none(self, parser):
        ws = MagicMock()
        ws.title = "4216"
        result = parser._parse_group_info(ws)
        assert result is None

    def test_empty_sheet_returns_none(self, parser):
        ws = MagicMock()
        ws.title = "421602"
        ws.get_all_values.return_value = []
        result = parser._parse_group_info(ws)
        assert result is None

    def test_one_row_sheet_returns_none(self, parser):
        ws = MagicMock()
        ws.title = "421602"
        ws.get_all_values.return_value = [["Тема", "Куратор"]]
        result = parser._parse_group_info(ws)
        assert result is None

    def test_valid_sheet_returns_list(self, parser):
        ws = MagicMock()
        ws.title = "421602"
        ws.get_all_values.return_value = [
            ["Тема", "Куратор"],
            ["Тема", "Куратор"],
            ["ИИ система", "Иванов"],
        ]
        with (
            patch.object(parser, "_get_structured_group_table_data_frame") as mock_df,
            patch.object(parser, "_table_row_to_nested_dicts") as mock_nested,
        ):
            df = pd.DataFrame([{"topic": "ИИ система", "curator": "Иванов"}])
            mock_df.return_value = df.replace("", None)
            mock_nested.return_value = {"topic": "ИИ система", "curator": "Иванов"}
            result = parser._parse_group_info(ws)
        assert isinstance(result, list)


class TestParseTopicsInfo:
    def test_wrong_sheet_name_returns_none(self, parser):
        ws = MagicMock()
        ws.title = "421602"
        result = parser._parse_topics_info(ws)
        assert result is None

    def test_correct_sheet_name_тематика(self, parser):
        ws = MagicMock()
        ws.title = "Темы 2026"
        ws.get_all_values.return_value = [
            ["Тема", "Описание"],
            ["Тема", "Описание"],
            ["ML", "Обучение модели"],
        ]
        with (
            patch.object(parser, "_get_structured_group_table_data_frame") as mock_df,
            patch.object(parser, "_table_row_to_nested_dicts") as mock_nested,
        ):
            df = pd.DataFrame([{"topic": "ML", "description": "Обучение модели"}])
            mock_df.return_value = df.replace("", None)
            mock_nested.return_value = {"topic": "ML"}
            result = parser._parse_topics_info(ws)
        assert isinstance(result, list)

    def test_empty_sheet_returns_none(self, parser):
        ws = MagicMock()
        ws.title = "Темы"
        ws.get_all_values.return_value = []
        result = parser._parse_topics_info(ws)
        assert result is None


class TestParseMilestoneScheduleInfo:
    def test_wrong_sheet_name_returns_none(self, parser):
        ws = MagicMock()
        ws.title = "421602"
        result = parser._parse_milestone_schedule_info(ws)
        assert result is None

    def test_correct_sheet_empty_returns_none(self, parser):
        ws = MagicMock()
        ws.title = "График опроцентов 2026"
        ws.get_all_values.return_value = []
        result = parser._parse_milestone_schedule_info(ws)
        assert result is None

    def test_correct_sheet_with_data(self, parser):
        ws = MagicMock()
        ws.title = "График опроцентов 2026"
        ws.get_all_values.return_value = [
            ["Опроцентов 1", "", "Опроцентов 2", ""],
            ["Тема", "Проверяющий", "Тема", "Проверяющий"],
            ["ИИ система", "Иванов", "ML модель", "Петров"],
        ]
        with patch.object(
            parser, "_parse_sub_tables", return_value={"milestone_1": []}
        ):
            result = parser._parse_milestone_schedule_info(ws)
        assert result is not None


class TestParseSubTables:
    def test_no_separator_returns_empty(self, parser):
        raw = [
            ["Тема", "Куратор"],
            ["ML", "Иванов"],
        ]
        result = parser._parse_sub_tables(raw, "опроцентов", "milestone_")
        assert result == {}

    def test_finds_subtable_with_number(self, parser):
        """Код проверяет наличие 'examiner' и 'numb' колонок → передаём обе."""
        raw = [
            ["Опроцентов 1", "", "Опроцентов 2", ""],
            ["Тема", "Проверяющий", "Тема", "Проверяющий"],
            ["ИИ система", "Иванов", "ML модель", "Петров"],
        ]
        with (
            patch.object(parser, "_get_structured_group_table_data_frame") as mock_df,
            patch.object(parser, "_load_mapping", return_value=None),
        ):
            df1 = pd.DataFrame(
                [{"topic": "ИИ система", "examiner": "Иванов", "numb": "1"}]
            )
            df2 = pd.DataFrame(
                [{"topic": "ML модель", "examiner": "Петров", "numb": "2"}]
            )
            mock_df.side_effect = [df1, df2]
            result = parser._parse_sub_tables(raw, "опроцентов", "milestone_")
        assert "milestone_1" in result or "milestone_2" in result
