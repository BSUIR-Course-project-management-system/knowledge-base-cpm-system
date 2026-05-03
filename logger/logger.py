import os
from datetime import datetime


class Logger:
    def __init__(self, log_file_path, level="INFO"):
        """Функция инициализации логгера"""
        self.log_file_path = log_file_path
        self.level = level.upper()
        self.levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        log_dir = os.path.dirname(log_file_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        try:
            with open(log_file_path, "a", encoding="utf-8"):
                pass
        except Exception as e:
            raise PermissionError(f"Нет доступа к файлу {log_file_path}: {e}")

    def _should_log(self, message_level):
        """Функция проверки уровня логгирования"""
        try:
            return self.levels.index(message_level) >= self.levels.index(self.level)
        except ValueError:
            return True

    def _log(self, level, message):
        """Функция записи логгов"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{level.upper()}] {message}\n"
        try:
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(log_line)
                f.flush()
        except Exception as e:
            print(f"Ошибка записи в лог-файл: {e}")

    def debug(self, message):
        """Функция записи логгов в debug"""
        if self._should_log("DEBUG"):
            self._log("DEBUG", message)

    def info(self, message):
        """Функция записи логгов в info"""
        if self._should_log("INFO"):
            self._log("INFO", message)

    def warning(self, message):
        """Функция записи логгов в warning"""
        if self._should_log("WARNING"):
            self._log("WARNING", message)

    def error(self, message):
        """Функция записи логгов в error"""
        if self._should_log("ERROR"):
            self._log("ERROR", message)

    def critical(self, message):
        """Функция записи логгов в critical"""
        if self._should_log("CRITICAL"):
            self._log("CRITICAL", message)
