"""Конфигурация логгера без циклических зависимостей."""

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

_env_config = {
    **dotenv_values(".env"),
    **os.environ,
}


def _get_env_value(value_name: str) -> str:
    value = _env_config.get(value_name)
    if value is None:
        msg = f"ENV {value_name} is not set!"
        raise RuntimeError(msg)
    return value


_config_file_name = _get_env_value("APP_CONFIG_FILE")


@dataclass(frozen=True)
class LoggerConfig:
    """Настройки логгера, которые можно импортировать без зависимостей."""

    logger_file_level: str = "INFO"
    logger_file_path: str | None = None
    logger_console_level: str = "INFO"
    logger_console_ignored: list[str] | None = None

    @classmethod
    def from_toml(cls, config_path: str | Path) -> "LoggerConfig":
        """Читает конфиг логгера из TOML файла."""
        with Path(config_path).open("rb") as f:
            data = tomllib.load(f)
        main_config = data.get("main_config", {}).get("logger_config", {})
        return cls(
            logger_file_level=main_config.get("logger_file_level", "INFO"),
            logger_file_path=main_config.get("logger_file_path"),
            logger_console_level=main_config.get("logger_console_level", "INFO"),
            logger_console_ignored=main_config.get("logger_console_ignored"),
        )


LOGGER_CONFIG = LoggerConfig.from_toml(_config_file_name)
