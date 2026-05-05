def clear_logs(filename: str) -> None:
    """Вспомогательная функция для очистки лог-файла

    Args:
        filename (str): Имя лог-файла, который надо очистить
    """
    with open(filename, "w") as f:
        f.truncate(0)
