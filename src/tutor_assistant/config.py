"""Global app configuration."""

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import dacite
from dotenv import dotenv_values

from tutor_assistant.config_logs import LOGGER_CONFIG, LoggerConfig
from tutor_assistant.infrastructure.logging.logger import get_logger


_env_config = {
    **dotenv_values(".env"),
    **os.environ,
}
logger = get_logger()


def _get_env_value(value_name: str) -> str:
    value = _env_config.get(value_name)
    if value is None:
        msg = f"❌ ENV {value_name} is not set! Check .env file"
        logger.error(msg)
        raise RuntimeError(msg)
    return value


_bot_token = _get_env_value("BOT_TOKEN")


@dataclass(frozen=True)
class BotConfigs:
    bot_token: str = field(repr=False, default=_bot_token)


@dataclass(frozen=True)
class MainConfig:
    logger_config: LoggerConfig = LOGGER_CONFIG


@dataclass(frozen=True)
class AppConfig:
    main_config: MainConfig
    bot_config: BotConfigs = field(default_factory=BotConfigs)


_config_file_name = _get_env_value("APP_CONFIG_FILE")
with Path(_config_file_name).open("rb") as f:
    data = tomllib.load(f)

BASE_CONFIG = dacite.from_dict(
    data_class=AppConfig,
    data=data,
    config=dacite.Config(
        check_types=True,
        strict=True,
        type_hooks={},
    ),
)
