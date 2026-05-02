import pytest
from schedule_module.src.config_parser import YamlParser


class TestYamlParser:
    @pytest.fixture
    def parser(self):
        parser = YamlParser()
        return parser

    def test_parse_config(self, parser):
        data = parser.parse_config("schedule_module/tests/yaml_test/test.yaml")
        assert len(data) == 3
        assert data["first"] == 1
        assert data["second"] == 2
        assert data["third"] == 3
