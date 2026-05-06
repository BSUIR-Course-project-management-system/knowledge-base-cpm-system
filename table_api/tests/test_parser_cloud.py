import re
import pytest
from unittest.mock import patch, MagicMock, call
# Все Google API полностью замоканы.


@pytest.fixture
def parser():
    with (
        patch("table_api.src.parser.gspread.service_account"),
        patch(
            "table_api.src.parser.service_account.Credentials.from_service_account_file"
        ),
        patch("table_api.src.parser.build"),
        patch("table_api.src.parser.Logger"),
    ):
        from table_api.src.parser import GoogleSheetsParser

        p = GoogleSheetsParser("fake_credentials.json")
    return p


def _make_worksheet(title: str):
    ws = MagicMock()
    ws.title = title
    return ws


def _make_spreadsheet(title: str, worksheets):
    sheet = MagicMock()
    sheet.title = title
    sheet.worksheets.return_value = worksheets
    return sheet


class TestGetAllSheetsInFolder:
    def test_returns_empty_list_on_no_files(self, parser):
        parser._drive_service = MagicMock()
        response = {"files": [], "nextPageToken": None}
        parser._drive_service.files.return_value.list.return_value.execute.return_value = response
        result = parser.get_all_sheets_in_folder("fake_folder")
        assert result == []

    def test_returns_ids_of_found_files(self, parser):
        parser._drive_service = MagicMock()
        response_page1 = {
            "files": [
                {"id": "id_1", "name": "Sheet1"},
                {"id": "id_2", "name": "Sheet2"},
            ],
            "nextPageToken": None,
        }
        parser._drive_service.files.return_value.list.return_value.execute.return_value = response_page1
        result = parser.get_all_sheets_in_folder("fake_folder")
        assert "id_1" in result
        assert "id_2" in result
        assert len(result) == 2

    def test_handles_pagination(self, parser):
        parser._drive_service = MagicMock()
        response_page1 = {
            "files": [{"id": "id_1", "name": "Sheet1"}],
            "nextPageToken": "token_abc",
        }
        response_page2 = {
            "files": [{"id": "id_2", "name": "Sheet2"}],
            "nextPageToken": None,
        }
        parser._drive_service.files.return_value.list.return_value.execute.side_effect = [
            response_page1,
            response_page2,
        ]
        result = parser.get_all_sheets_in_folder("fake_folder")
        assert len(result) == 2

    def test_handles_api_exception(self, parser):
        parser._drive_service = MagicMock()
        parser._drive_service.files.return_value.list.return_value.execute.side_effect = Exception(
            "API error"
        )
        # Не должен упасть — ошибка перехватывается внутри
        result = parser.get_all_sheets_in_folder("fake_folder")
        assert result == []


class TestGetAllDataFromCloud:
    def test_returns_dict_with_three_keys(self, parser):
        parser._gserv_acc = MagicMock()
        parser._gserv_acc.open_by_key.return_value = _make_spreadsheet("ТЕСТ 2026", [])
        result = parser.get_all_data_from_cloud([])
        assert "group_data" in result
        assert "topic_data" in result
        assert "schedule_data" in result

    def test_group_worksheet_6_digit_parsed(self, parser):
        parser._gserv_acc = MagicMock()
        ws_group = _make_worksheet("421602")
        ws_group.get_all_values.return_value = []
        sheet = _make_spreadsheet("ТЕСТ 2026", [ws_group])
        parser._gserv_acc.open_by_key.return_value = sheet

        with patch.object(
            parser, "_parse_group_info", return_value=[{"topic": "ИИ"}]
        ) as mock_parse:
            result = parser.get_all_data_from_cloud(["fake_id"])

        mock_parse.assert_called_once_with(worksheet=ws_group)
        assert "421602" in result["group_data"]

    def test_topics_worksheet_parsed(self, parser):
        parser._gserv_acc = MagicMock()
        ws_topics = _make_worksheet("Темы")
        sheet = _make_spreadsheet("ТЕСТ 2026", [ws_topics])
        parser._gserv_acc.open_by_key.return_value = sheet

        with patch.object(parser, "_parse_topics_info", return_value=[{"topic": "ML"}]):
            result = parser.get_all_data_from_cloud(["fake_id"])

        assert "2026" in result["topic_data"]

    def test_schedule_worksheet_parsed(self, parser):
        parser._gserv_acc = MagicMock()
        ws_sched = _make_worksheet("График опроцентов 2026")
        sheet = _make_spreadsheet("ТЕСТ 2026", [ws_sched])
        parser._gserv_acc.open_by_key.return_value = sheet

        with patch.object(
            parser, "_parse_milestone_schedule_info", return_value={"milestone_1": []}
        ):
            result = parser.get_all_data_from_cloud(["fake_id"])

        assert "2026" in result["schedule_data"]

    def test_unknown_worksheet_ignored(self, parser):
        parser._gserv_acc = MagicMock()
        ws_unknown = _make_worksheet("Неизвестный лист")
        sheet = _make_spreadsheet("ТЕСТ 2026", [ws_unknown])
        parser._gserv_acc.open_by_key.return_value = sheet

        result = parser.get_all_data_from_cloud(["fake_id"])
        assert result["group_data"] == {}

    def test_topic_data_extends_existing_key(self, parser):
        """Если ключ уже есть в topic_data, новые записи добавляются через extend."""
        parser._gserv_acc = MagicMock()
        ws1 = _make_worksheet("Темы")
        ws2 = _make_worksheet("Темы 2026")
        sheet = _make_spreadsheet("ТЕСТ 2026", [ws1, ws2])
        parser._gserv_acc.open_by_key.return_value = sheet

        with patch.object(
            parser,
            "_parse_topics_info",
            side_effect=[
                [{"topic": "Тема 1"}],
                [{"topic": "Тема 2"}],
            ],
        ):
            result = parser.get_all_data_from_cloud(["fake_id"])

        assert len(result["topic_data"]["2026"]) == 2

    def test_empty_group_worksheet_skipped(self, parser):
        parser._gserv_acc = MagicMock()
        ws_group = _make_worksheet("421602")
        sheet = _make_spreadsheet("ТЕСТ 2026", [ws_group])
        parser._gserv_acc.open_by_key.return_value = sheet

        with patch.object(parser, "_parse_group_info", return_value=None):
            result = parser.get_all_data_from_cloud(["fake_id"])

        assert "421602" not in result["group_data"]

    def test_title_without_year_uses_default_key(self, parser):
        parser._gserv_acc = MagicMock()
        ws_topics = _make_worksheet("Темы")
        sheet = _make_spreadsheet("Без года", [ws_topics])
        parser._gserv_acc.open_by_key.return_value = sheet

        with patch.object(parser, "_parse_topics_info", return_value=[{"topic": "X"}]):
            result = parser.get_all_data_from_cloud(["fake_id"])

        assert "default" in result["topic_data"]


class TestFetchAllGroups:
    def test_returns_all_groups(self, parser):
        parser._gserv_acc = MagicMock()
        ws = _make_worksheet("421602")
        sheet = _make_spreadsheet("ТЕСТ 2026", [ws])
        parser._gserv_acc.open_by_key.return_value = sheet

        with patch.object(parser, "_parse_group_info", return_value=[{"topic": "ИИ"}]):
            result = parser.fetch_all_groups(["fake_id"])

        assert "421602" in result

    def test_skips_non_group_worksheets(self, parser):
        parser._gserv_acc = MagicMock()
        ws = _make_worksheet("Темы")
        sheet = _make_spreadsheet("ТЕСТ 2026", [ws])
        parser._gserv_acc.open_by_key.return_value = sheet

        with patch.object(parser, "_parse_group_info", return_value=None):
            result = parser.fetch_all_groups(["fake_id"])

        assert result == {}

    def test_multiple_spreadsheets(self, parser):
        parser._gserv_acc = MagicMock()
        ws1 = _make_worksheet("421701")
        ws2 = _make_worksheet("421602")
        sheet1 = _make_spreadsheet("ТЕСТ 2025", [ws1])
        sheet2 = _make_spreadsheet("ТЕСТ 2026", [ws2])
        parser._gserv_acc.open_by_key.side_effect = [sheet1, sheet2]

        with patch.object(
            parser,
            "_parse_group_info",
            side_effect=[[{"topic": "Г1"}], [{"topic": "Г2"}]],
        ):
            result = parser.fetch_all_groups(["id1", "id2"])

        assert "421701" in result
        assert "421602" in result


class TestFetchExaminerSchedule:
    def test_returns_schedule_by_year(self, parser):
        parser._gserv_acc = MagicMock()
        ws = _make_worksheet("График опроцентов")
        sheet = _make_spreadsheet("ТЕСТ 2026", [ws])
        parser._gserv_acc.open_by_key.return_value = sheet

        with patch.object(
            parser, "_parse_milestone_schedule_info", return_value={"milestone_1": []}
        ):
            result = parser.fetch_examiner_schedule(["fake_id"])

        assert "2026" in result

    def test_skips_empty_schedule(self, parser):
        parser._gserv_acc = MagicMock()
        ws = _make_worksheet("График опроцентов")
        sheet = _make_spreadsheet("ТЕСТ 2026", [ws])
        parser._gserv_acc.open_by_key.return_value = sheet

        with patch.object(parser, "_parse_milestone_schedule_info", return_value=None):
            result = parser.fetch_examiner_schedule(["fake_id"])

        assert result == {}

    def test_no_year_in_title_uses_default(self, parser):
        parser._gserv_acc = MagicMock()
        ws = _make_worksheet("График опроцентов")
        sheet = _make_spreadsheet("Без года", [ws])
        parser._gserv_acc.open_by_key.return_value = sheet

        with patch.object(
            parser, "_parse_milestone_schedule_info", return_value={"milestone_1": []}
        ):
            result = parser.fetch_examiner_schedule(["fake_id"])

        assert "default" in result


class TestAppendRowWithFormat:
    def test_appends_row_to_correct_spreadsheet(self, parser):
        parser._gserv_acc = MagicMock()
        doc = MagicMock()
        doc.title = "ТЕСТ 2026"
        ws = MagicMock()
        doc.worksheet.return_value = ws
        parser._gserv_acc.open_by_key.return_value = doc

        parser.append_row_with_format(
            spreadsheets_ids=["fake_id"],
            key_title="ТЕСТ 2026",
            worksheet_title="Темы",
            row_data=["Тема", "Описание", "Куратор", "Проверяющий"],
        )
        ws.append_row.assert_called_once_with(
            ["Тема", "Описание", "Куратор", "Проверяющий"],
            value_input_option="USER_ENTERED",
            insert_data_option="INSERT_ROWS",
        )

    def test_raises_exception_on_api_error(self, parser):
        parser._gserv_acc = MagicMock()
        doc = MagicMock()
        doc.title = "ТЕСТ 2026"
        ws = MagicMock()
        ws.append_row.side_effect = Exception("API error")
        doc.worksheet.return_value = ws
        parser._gserv_acc.open_by_key.return_value = doc

        with pytest.raises(Exception, match="Ошибка при добавлении строки"):
            parser.append_row_with_format(
                spreadsheets_ids=["fake_id"],
                key_title="ТЕСТ 2026",
                worksheet_title="Темы",
                row_data=["Тема"],
            )

    def test_no_matching_spreadsheet_row_appended_anyway(self, parser):
        """Если подходящая таблица не найдена, spreadsheet_id остаётся пустым
        и код пытается открыть open_by_key(""). Если mock это позволяет — строка добавится."""
        parser._gserv_acc = MagicMock()
        doc_wrong = MagicMock()
        doc_wrong.title = "Другое название"
        doc_empty = MagicMock()
        ws = MagicMock()
        doc_empty.worksheet.return_value = ws
        # Первый вызов — для поиска совпадения (не совпало)
        # Второй — open_by_key("") — успешно, т.к. это МОК
        parser._gserv_acc.open_by_key.side_effect = [doc_wrong, doc_empty]
        # Ошибки нет, строка просто добавляется в "пустую" таблицу
        parser.append_row_with_format(
            spreadsheets_ids=["fake_id"],
            key_title="ТЕСТ 2026",
            worksheet_title="Темы",
            row_data=["Тема"],
        )
        ws.append_row.assert_called_once()


class TestDeleteRowByTopic:
    def test_deletes_row_when_topic_found(self, parser):
        parser._gserv_acc = MagicMock()
        doc = MagicMock()
        doc.title = "ТЕСТ 2026"
        ws = MagicMock()
        cell = MagicMock()
        cell.row = 5
        ws.find.return_value = cell
        doc.worksheet.return_value = ws
        parser._gserv_acc.open_by_key.return_value = doc

        result = parser.delete_row_by_topic(
            spreadsheets_ids=["fake_id"],
            key_title="ТЕСТ 2026",
            worksheet_title="Темы",
            theme_title="ML система",
        )
        ws.delete_rows.assert_called_once_with(5)
        assert result is True

    def test_returns_false_when_topic_not_found(self, parser):
        parser._gserv_acc = MagicMock()
        doc = MagicMock()
        doc.title = "ТЕСТ 2026"
        ws = MagicMock()
        ws.find.side_effect = Exception("CellNotFound")
        doc.worksheet.return_value = ws
        parser._gserv_acc.open_by_key.return_value = doc

        result = parser.delete_row_by_topic(
            spreadsheets_ids=["fake_id"],
            key_title="ТЕСТ 2026",
            worksheet_title="Темы",
            theme_title="Несуществующая тема",
        )
        assert result is False

    def test_returns_false_on_outer_exception(self, parser):
        parser._gserv_acc = MagicMock()
        doc = MagicMock()
        doc.title = "ТЕСТ 2026"
        doc.worksheet.side_effect = Exception("Worksheet not found")
        parser._gserv_acc.open_by_key.return_value = doc

        result = parser.delete_row_by_topic(
            spreadsheets_ids=["fake_id"],
            key_title="ТЕСТ 2026",
            worksheet_title="НесуществующийЛист",
            theme_title="Тема",
        )
        assert result is False
