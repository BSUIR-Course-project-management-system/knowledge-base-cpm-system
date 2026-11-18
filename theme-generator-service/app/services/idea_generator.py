from app.config import Settings
from app.llm.ollama_client import OllamaClient
from app.schemas import GenerateIdeasResponse
from app.services.prompt_builder import build_messages
from app.services.response_validator import parse_and_validate, InvalidModelResponse

class IdeaGenerator:
    def __init__(self, settings: Settings):
        if settings.llm_provider.lower() != "ollama":
            raise ValueError(f"Провайдер {settings.llm_provider!r} пока не поддерживается. Доступен ollama.")
        self.settings = settings
        self.client = OllamaClient(settings)

    async def generate(self, subject_area: str) -> GenerateIdeasResponse:
        messages = build_messages(subject_area)
        schema = GenerateIdeasResponse.model_json_schema()
        last_error = None
        for attempt in range(self.settings.llm_retries + 1):
            try:
                content = await self.client.generate(messages, schema)
                return parse_and_validate(content, subject_area)
            except (InvalidModelResponse, ValueError) as exc:
                last_error = exc
                if attempt < self.settings.llm_retries:
                    messages = messages + [{
                        "role": "user",
                        "content": "Исправь предыдущий ответ. Верни строго JSON по исходной схеме: ровно 5 идей и все обязательные поля.",
                    }]
        raise RuntimeError(str(last_error or "Не удалось получить корректный ответ модели."))
