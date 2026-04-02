"""Logger builder with stdout/file, JSON/text formats and Sentry hook."""

from __future__ import annotations

import json
import logging
import sys
from logging import Logger
from pathlib import Path
from typing import ClassVar

from pythonjsonlogger import jsonlogger

from tutor_assistant.logger_config import LOGGER_CONFIG



class _StramColorFormatter(logging.Formatter):
    """Форматирование логов с цветами ANSI для терминала.

    Добавляет цветовое выделение в зависимости от уровня логирования
    и выравнивает элементы для лучшей читаемости.
    """

    # ANSI escape codes для цветов
    _GREY = "\x1b[38;20m"
    _GREEN = "\x1b[92m"
    _YELLOW = "\x1b[93m"
    _RED = "\x1b[31;20m"
    _BOLD_RED = "\x1b[31;1m"

    _RESET = "\x1b[0m"
    _BLUE = "\x1b[34;20m"

    _FORMAT = "{asctime} | {name:12} | {levelname:8} | {message}"

    _COLORS: ClassVar[dict[int, str]] = {
        logging.DEBUG: _GREY,
        logging.INFO: _GREEN,
        logging.WARNING: _YELLOW,
        logging.ERROR: _RED,
        logging.CRITICAL: _BOLD_RED,
    }

    def format(self, record: logging.LogRecord) -> str:
        """Форматирует запись лога цветовым выделением.

        Args:
            record: Запись лога для форматирования.

        Returns:
            Отформатированная цветная строка лога.
        """
        color = self._COLORS.get(record.levelno, self._GREY)

        log_fmt = color + self._FORMAT + self._RESET
        formatter = logging.Formatter(log_fmt, style="{")
        return formatter.format(record)


_LEVEL_MAP = {
    "dev": logging.DEBUG,
    "debug": logging.DEBUG,
    "staging": logging.INFO,
    "info": logging.INFO,
    "prod": logging.WARNING,
    "warning": logging.WARNING,
    "warn": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}

class JsonlFormatter(logging.Formatter):
    """Пишет dict как JSON строку.
    
    Пока под вопросом
    """

    def format(self, record: logging.LogRecord) -> str:
        """Преобразует данные в правильный вид."""
        return json.dumps(record.msg, ensure_ascii=False)


class Utf8JsonFormatter(jsonlogger.JsonFormatter):
    """JSON formatter that disables ASCII escaping for better UTF-8 support."""

    def __init__(self, *fmt_args: str, **fmt_kwargs: str) -> None:
        """Initialize formatter, disabling ASCII-escaping to support UTF-8.

        Args:
            *fmt_args: Positional arguments passed to parent class.
            **fmt_kwargs: Keyword arguments passed to parent class.
        """
        fmt_kwargs.setdefault("json_ensure_ascii", False)
        super().__init__(*fmt_args, **fmt_kwargs)


def _resolve_level(value: str | None, fallback: int = logging.INFO) -> int:
    if not value:
        return fallback
    v = value.strip().lower()
    return _LEVEL_MAP.get(v, getattr(logging, value.upper(), fallback))


def _build_stream_handler(level: int) -> logging.Handler:
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(_StramColorFormatter())
    return handler


def _build_file_handler(
    path: str, level: int
) -> logging.Handler:
    if Path(path).parent:
        Path.mkdir(Path(path).parent, exist_ok=True, parents=True)
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setLevel(level)
    formatter = Utf8JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    handler.setFormatter(formatter)
    return handler


def get_logger(name: str = "app_logger") -> Logger:
    """Create configured logger."""
    level = _resolve_level(LOGGER_CONFIG.logger_console_level, fallback=logging.INFO)
    log_file_path = LOGGER_CONFIG.logger_file_path

    logger = logging.getLogger(name)

    if getattr(logger, "is_configured", False):
        return logger

    logger.setLevel(level)
    logger.propagate = False

    ignored = LOGGER_CONFIG.logger_consele_ignored or []
    if name not in ignored:
        logger.addHandler(_build_stream_handler(level))

    if log_file_path:
        logger.addHandler(_build_file_handler(log_file_path, level))

    logger.is_configured = True
    return logger
