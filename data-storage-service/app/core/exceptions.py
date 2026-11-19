class CacheNotReadyError(Exception):
    """Кэша ещё нет: первая синхронизация не завершена."""


class RefreshInProgressError(Exception):
    """Обновление кэша уже идёт."""
