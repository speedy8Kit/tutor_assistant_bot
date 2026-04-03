"""Builds and runs the Telegram Application."""

from __future__ import annotations

from telegram.ext import Application, CommandHandler

from tutor_assistant.application.handlers import build_add_student_handler, cancel, list_students, start
from tutor_assistant.config import BASE_CONFIG


def _register_handlers(app: Application):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("list_students", list_students))
    app.add_handler(build_add_student_handler())
    return app


def build_application() -> Application:
    app = (
        Application.builder()
        .token(BASE_CONFIG.bot_config.bot_token)
        .build()
    )
    _register_handlers(app)
    return app
