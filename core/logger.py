import subprocess
import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from core.config import BASE_DIR

# Лог-файл будет лежать рядом с .exe (или в корне проекта при запуске из исходников)
LOG_FILE = os.path.join(BASE_DIR, "superdictate.log")

class StreamToLogger:
    """Перенаправляет sys.stdout и sys.stderr в логгер."""
    def __init__(self, logger, log_level=logging.INFO):
        self.logger = logger
        self.log_level = log_level

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.log_level, line.rstrip())

    def flush(self):
        pass

def setup_logger():
    """Настраивает запись логов в файл (с ротацией) и в консоль (если она есть)."""
    logger = logging.getLogger("SuperDictate")
    logger.setLevel(logging.INFO)

    # Защита от дублирования хендлеров при повторном вызове
    if not logger.handlers:
        # 1. Хендлер для файла (максимум 5 МБ, храним 2 старых файла)
        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=5*1024*1024, backupCount=2, encoding='utf-8'
        )
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # 2. Хендлер для консоли (только если мы запущены из исходников или console=True)
        if sys.stdout is not None:
            console_handler = logging.StreamHandler(sys.__stdout__)
            # В консоль выводим только само сообщение (как раньше делал print)
            console_handler.setFormatter(logging.Formatter('%(message)s'))
            logger.addHandler(console_handler)

    # Перехватываем все print() и ошибки в приложении
    sys.stdout = StreamToLogger(logger, logging.INFO)
    sys.stderr = StreamToLogger(logger, logging.WARNING)

    logger.info("--- Запуск SuperDictate ---")
    return logger
def open_log_file():
    """Открывает файл лога в системном просмотрщике."""
    if not os.path.exists(LOG_FILE):
        return
    try:
        if sys.platform == 'win32':
            os.startfile(LOG_FILE)
        else:
            subprocess.Popen(['xdg-open', LOG_FILE])
    except Exception as e:
        print(f"[Logger] Не удалось открыть лог: {e}")