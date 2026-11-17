import logging
from functools import lru_cache

import torch
from sentence_transformers import SentenceTransformer

from app.core.config import settings

logger = logging.getLogger(__name__)


def select_device() -> str:
    """Выбирает доступное ускорение: Apple Silicon, NVIDIA GPU или CPU."""
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    """Загружает модель один раз на процесс и повторно использует её."""
    device = select_device()
    logger.info("Loading embedding model %s on %s", settings.MODEL_NAME, device)
    # При первом локальном запуске модель скачивается из Hugging Face.
    # В Docker она уже помещена в образ на этапе сборки.
    return SentenceTransformer(settings.MODEL_NAME, device=device)


def encode_texts(texts: list[str]):
    """Возвращает нормализованные embeddings для списка текстов."""
    model = get_model()
    return model.encode(
        texts,
        batch_size=32,
        show_progress_bar=False,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
