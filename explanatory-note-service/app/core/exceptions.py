class ServiceError(Exception):
    """Базовая ошибка сервиса: сообщение на русском, без голого 500."""


class ConfigurationError(ServiceError):
    """Некорректная конфигурация сервиса (проверяется при старте)."""


class RulesLoadError(ServiceError):
    """Набор правил отсутствует или не соответствует схеме."""


class DocumentExtractionError(ServiceError):
    """Не удалось извлечь текст/структуру из входного документа."""


class NoteInputError(ServiceError):
    """Некорректный вход проверки записки (файлы, формат, размер)."""

    def __init__(self, message: str, status_code: int = 422):
        super().__init__(message)
        self.status_code = status_code
