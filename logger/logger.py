import os
from datetime import datetime


class Logger:
    """
    Класс логгер, пишущий в указанный файл.
    Каждый экземпляр пишет в свой файл.
    """

    def __init__(self, log_file_path, level="INFO"):
        """
        :param log_file_path: путь к файлу лога (абсолютный или относительный)
        :param level: минимальный уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """

        self.log_file_path = log_file_path
        self.level = level.upper()
        log_dir = os.path.dirname(log_file_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        try:
            with open(log_file_path, "a"):
                pass
        except Exception as e:
            raise PermissionError(f"Нет доступа к файлу {log_file_path}: {e}")

    def _log(self, level, message):
        """Внутренний метод для записи строки в файл."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{level.upper()}] {message}\n"
        try:
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(log_line)
        except Exception as e:
            print(f"Ошибка записи в лог-файл: {e}\nСообщение: {message}")

    def debug(self, message):
        if self.level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            self._log("DEBUG", message)

    def info(self, message):
        if self.level in ("INFO", "WARNING", "ERROR", "CRITICAL"):
            self._log("INFO", message)

    def warning(self, message):
        if self.level in ("WARNING", "ERROR", "CRITICAL"):
            self._log("WARNING", message)

    def error(self, message):
        if self.level in ("ERROR", "CRITICAL"):
            self._log("ERROR", message)

    def critical(self, message):
        if self.level == "CRITICAL":
            self._log("CRITICAL", message)
