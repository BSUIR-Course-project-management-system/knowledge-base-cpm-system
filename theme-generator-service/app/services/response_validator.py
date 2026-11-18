import json
from pydantic import ValidationError
from app.schemas import GenerateIdeasResponse

class InvalidModelResponse(Exception):
    pass

def parse_and_validate(content: str, subject_area: str) -> GenerateIdeasResponse:
    try:
        data = json.loads(content)
        data["subject_area"] = subject_area
        return GenerateIdeasResponse.model_validate(data)
    except (json.JSONDecodeError, ValidationError, TypeError, ValueError, KeyError) as exc:
        raise InvalidModelResponse(f"Ответ модели не прошёл проверку: {exc}") from exc
