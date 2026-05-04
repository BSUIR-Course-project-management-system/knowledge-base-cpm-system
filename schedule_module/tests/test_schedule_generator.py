import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from schedule_module.src.schedule_generator import SheduleGenerator
from schedule_module.src.config_parser import BaseParser
from schedule_module.src.date_checker import DateChecker


class TestSheduleGeneratorInit:
    def test_init_calls_parse_config(self):
        mock_parser = Mock(spec=BaseParser)
        mock_parser.parse_config.return_value = {
            "work_start": 9,
            "work_end": 18,
            "step": 30,
        }
        mock_date_checker = Mock(spec=DateChecker)

        generator = SheduleGenerator(mock_parser, mock_date_checker)

        mock_parser.parse_config.assert_called_once_with("config/settings.yaml")
        assert generator.WORK_START_HOUR == 9
        assert generator.WORK_END_HOUR == 18
        assert generator.STEP_MINUTES == 30

    def test_init_variables_missing_keys(self):
        mock_parser = Mock(spec=BaseParser)
        mock_parser.parse_config.return_value = {"work_start": 10}
        mock_date_checker = Mock(spec=DateChecker)

        with pytest.raises(KeyError):
            SheduleGenerator(mock_parser, mock_date_checker)


class TestSheduleGeneratorGenerateCandidateStarts:
    @pytest.fixture
    def generator(self):
        mock_parser = Mock(spec=BaseParser)
        mock_parser.parse_config.return_value = {
            "work_start": 9,
            "work_end": 17,
            "step": 60,
        }
        mock_date_checker = Mock(spec=DateChecker)
        mock_date_checker.is_work_day.return_value = True
        return SheduleGenerator(mock_parser, mock_date_checker)

    def test_candidates_simple(self, generator):
        start_dt = datetime(2024, 5, 2, 10, 0)
        end_dt = datetime(2024, 5, 2, 16, 0)
        duration = 30
        occupied = []

        result = generator.generate_candidate_starts(
            start_dt, end_dt, duration, occupied
        )

        expected = [
            datetime(2024, 5, 2, 10, 0),
            datetime(2024, 5, 2, 11, 0),
            datetime(2024, 5, 2, 12, 0),
            datetime(2024, 5, 2, 13, 0),
            datetime(2024, 5, 2, 14, 0),
            datetime(2024, 5, 2, 15, 0),
        ]
        assert result == expected

    def test_candidates_with_conflicts(self, generator):
        start_dt = datetime(2024, 5, 2, 10, 0)
        end_dt = datetime(2024, 5, 2, 14, 0)
        duration = 60
        occupied = [(datetime(2024, 5, 2, 11, 0), datetime(2024, 5, 2, 12, 0))]

        result = generator.generate_candidate_starts(
            start_dt, end_dt, duration, occupied
        )

        expected = [
            datetime(2024, 5, 2, 10, 0),
            datetime(2024, 5, 2, 12, 0),
            datetime(2024, 5, 2, 13, 0),
        ]
        assert result == expected

    def test_candidates_weekend_skipped(self, generator):
        generator.date_checker.is_work_day.side_effect = lambda d: d.weekday() < 5
        start_dt = datetime(2024, 5, 3, 9, 0)
        end_dt = datetime(2024, 5, 3, 12, 0)
        duration = 60
        occupied = []

        result = generator.generate_candidate_starts(
            start_dt, end_dt, duration, occupied
        )

        expected = [
            datetime(2024, 5, 3, 9, 0),
            datetime(2024, 5, 3, 10, 0),
            datetime(2024, 5, 3, 11, 0),
        ]
        assert result == expected

    def test_candidates_step_alignment(self, generator):
        start_dt = datetime(2024, 5, 2, 9, 22)
        end_dt = datetime(2024, 5, 2, 12, 0)
        duration = 30
        occupied = []

        result = generator.generate_candidate_starts(
            start_dt, end_dt, duration, occupied
        )

        expected = [
            datetime(2024, 5, 2, 10, 0),
            datetime(2024, 5, 2, 11, 0),
        ]
        assert result == expected


class TestSheduleGeneratorSelectSlots:
    @pytest.fixture
    def generator(self):
        mock_parser = Mock(spec=BaseParser)
        mock_parser.parse_config.return_value = {
            "work_start": 9,
            "work_end": 17,
            "step": 60,
        }
        mock_date_checker = Mock(spec=DateChecker)
        return SheduleGenerator(mock_parser, mock_date_checker)

    def test_select_slots_exact_match(self, generator):
        start_dt = datetime(2024, 5, 1, 9, 0)
        end_dt = datetime(2024, 5, 10, 17, 0)
        candidates = [
            start_dt + timedelta(days=2),
            start_dt + timedelta(days=5),
            start_dt + timedelta(days=8),
        ]
        result = generator.select_slots(candidates, start_dt, end_dt, num_points=3)
        expected = sorted(candidates)
        assert result == expected

    def test_select_slots_insufficient_candidates(self, generator):
        candidates = [datetime(2024, 5, 1), datetime(2024, 5, 2)]
        start_dt = datetime(2024, 5, 1)
        end_dt = datetime(2024, 5, 10)
        result = generator.select_slots(candidates, start_dt, end_dt, num_points=3)
        assert result is None

    def test_select_slots_fallback_to_equidistant(self, generator):
        start_dt = datetime(2024, 5, 1, 0, 0)
        end_dt = datetime(2024, 5, 10, 0, 0)
        candidates = [
            datetime(2024, 5, 1, 9, 0),
            datetime(2024, 5, 1, 10, 0),
            datetime(2024, 5, 1, 11, 0),
            datetime(2024, 5, 1, 12, 0),
            datetime(2024, 5, 1, 13, 0),
            datetime(2024, 5, 1, 14, 0),
            datetime(2024, 5, 1, 15, 0),
            datetime(2024, 5, 1, 16, 0),
            datetime(2024, 5, 1, 17, 0),
        ]
        result = generator.select_slots(candidates, start_dt, end_dt, num_points=3)
        step = len(candidates) / 4
        expected_indices = [int(step * (i + 1)) for i in range(3)]
        expected = [candidates[i] for i in expected_indices]
        assert result == expected

    def test_select_slots_respects_order_and_uniqueness(self, generator):
        start_dt = datetime(2024, 5, 1, 0, 0)
        end_dt = datetime(2024, 5, 5, 0, 0)
        candidates = [
            datetime(2024, 5, 1, 10, 0),
            datetime(2024, 5, 2, 10, 0),
            datetime(2024, 5, 3, 10, 0),
            datetime(2024, 5, 4, 10, 0),
        ]
        result = generator.select_slots(candidates, start_dt, end_dt, num_points=3)
        assert result == sorted(result)
        assert len(result) == 3
        assert len(set(result)) == 3
