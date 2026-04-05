"""Builds and runs the Telegram Application."""

from __future__ import annotations

from telegram.ext import Application, CommandHandler

from tutor_assistant.application.handlers import build_add_student_handler, cancel, help
from tutor_assistant.config import BASE_CONFIG
from tutor_assistant.infrastructure.database import init_db
from tutor_assistant.application.handlers import (
    list_students,
)
from tutor_assistant.infrastructure.logging.logger import get_logger

logger = get_logger()


async def _post_init(app: Application) -> None:
    try:
        await init_db()
    except Exception:
        logger.exception("DB init failed")
        raise
    logger.info("Database initialised")


def _register_handlers(app: Application):
    app.add_handler(CommandHandler("start", help))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("list_students", list_students))
    app.add_handler(build_add_student_handler())
    return app


def build_application() -> Application:
    app = (
        Application.builder()
        .token(BASE_CONFIG.bot_config.bot_token)
        .post_init(_post_init)
        .build()
    )
    _register_handlers(app)
    return app
