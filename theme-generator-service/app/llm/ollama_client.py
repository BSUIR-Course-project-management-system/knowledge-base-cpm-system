import httpx
from app.config import Settings
from app.llm.base import LLMClient

class OllamaClient(LLMClient):
    def __init__(self, settings: Settings):
        self.settings = settings

    async def generate(self, messages: list[dict[str, str]], response_schema: dict) -> str:
        payload = {
            "model": self.settings.llm_model,
            "messages": messages,
            "stream": False,
            "format": response_schema,
            "options": {
                "temperature": self.settings.llm_temperature,
                "num_predict": self.settings.llm_max_tokens,
            },
        }
        timeout = httpx.Timeout(self.settings.llm_timeout, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(self.settings.ollama_chat_url, json=payload)
            response.raise_for_status()
            data = response.json()
        # Не возвращаем отдельное поле thinking — только пользовательский content.
        content = data.get("message", {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Ollama вернула пустое message.content.")
        return content

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, connect=2.0)) as client:
                response = await client.get(self.settings.ollama_tags_url)
                response.raise_for_status()
                models = response.json().get("models", [])
            return any(
                m.get("name") == self.settings.llm_model
                or m.get("name", "").startswith(self.settings.llm_model + ":")
                for m in models
            )
        except (httpx.HTTPError, ValueError, TypeError):
            return False
