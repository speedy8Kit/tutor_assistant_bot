"""Logger builder with stdout/file, JSON/text formats and Sentry hook."""

from __future__ import annotations

import logging
import sys
from logging import Logger
from pathlib import Path

from pythonjsonlogger import jsonlogger
from bot.config import BASE_CONFIG



_LEVEL_MAP = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


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


def _build_stream_handler(level: int, log_format: logging.Formatter) -> logging.Handler:
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(log_format)
    return handler


def _build_file_handler(
    path: str, level: int, log_formatter: logging.Formatter
) -> logging.Handler:
    if Path(path).parent:
        Path.mkdir(Path(path).parent, exist_ok=True, parents=True)
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setLevel(level)
    handler.setFormatter(log_formatter)
    return handler


def get_logger(name: str = "app_logger") -> Logger:
    """Create configured logger."""

    app_level_raw = getattr(BASE_CONFIG.main_config, "logger_level", "INFO")
    level = _resolve_level(app_level_raw, fallback=logging.ERROR)

    # format
    use_json = BASE_CONFIG.main_config.logger_json

    # file path
    log_file_path = BASE_CONFIG.main_config.logger_file_path

    logger = logging.getLogger(name)

    if getattr(logger, "is_configured", False):
        return logger

    logger.setLevel(level)
    logger.propagate = False

    # stdout handler
    if use_json:
        log_format = "json"
    logger.addHandler(_build_stream_handler(level, log_format))

    # file handler (optional)
    if log_file_path:
        logger.addHandler(
            _build_file_handler(log_file_path, level, log_format)
        )

    logger.is_configured = True
    return logger
