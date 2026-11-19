import json
import pytest
from app.services.response_validator import parse_and_validate, InvalidModelResponse

def payload():
    return {
        "subject_area": "ignored",
        "ideas": [{
            "title": f"Проект номер {i}",
            "description": "Описание предлагаемой программной системы для решения задачи.",
            "goal": "Создать прототип программной системы.",
            "recommended_functionality": ["Функция один", "Функция два", "Функция три"],
        } for i in range(1, 6)]
    }

def test_accepts_five_ideas_and_uses_request_subject():
    result = parse_and_validate(json.dumps(payload(), ensure_ascii=False), "Экология")
    assert result.subject_area == "Экология"
    assert len(result.ideas) == 5

def test_rejects_invalid_json():
    with pytest.raises(InvalidModelResponse):
        parse_and_validate("{not json", "Экология")

def test_rejects_wrong_number_of_ideas():
    data = payload()
    data["ideas"].pop()
    with pytest.raises(InvalidModelResponse):
        parse_and_validate(json.dumps(data, ensure_ascii=False), "Экология")
