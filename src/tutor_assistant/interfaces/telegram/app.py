"""Build and configure the Telegram Application."""

from __future__ import annotations

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, TypeHandler, filters

from tutor_assistant.config import BASE_CONFIG
from tutor_assistant.infrastructure.database.engine import (
    async_session_factory,
    init_db,
)
from tutor_assistant.infrastructure.logging.logger import get_logger
from tutor_assistant.interfaces.telegram.conversations.add_student import (
    build_handler as build_add_student,
)
from tutor_assistant.interfaces.telegram.conversations.settings import (
    build_handler as build_settings,
)
from tutor_assistant.interfaces.telegram.conversations.student_editor import (
    build_handler as build_student_editor,
)
from tutor_assistant.interfaces.telegram.handlers.common import (
    cmd_cancel,
    cmd_start,
    cmd_today,
    cmd_tomorrow,
    cmd_upcoming,
)
from tutor_assistant.interfaces.telegram.reminders import (
    schedule_morning_reminder,
    schedule_preclass_global_job,
)

logger = get_logger()


async def _log_update(update: Update, context: object) -> None:
    user = update.effective_user
    uid = user.id if user else "?"
    uname = f"@{user.username}" if (user and user.username) else ""

    if update.message:
        text = update.message.text or f"[{type(update.message.effective_attachment).__name__}]"
        logger.info("MSG  uid=%s%s  text=%r", uid, uname, text)
    elif update.callback_query:
        logger.info("CBQ  uid=%s%s  data=%r", uid, uname, update.callback_query.data)
    else:
        logger.debug("UPD  uid=%s%s  type=%s", uid, uname, type(update).__name__)


async def _post_init(app: Application) -> None:
    try:
        await init_db()
    except Exception:
        logger.exception("DB init failed")
        raise
    logger.info("Database initialised")

    try:
        from tutor_assistant.infrastructure.database.repository import (
            SqlAlchemyChatSettingsRepository,
        )

        async with async_session_factory() as session:
            async with session.begin():
                repo = SqlAlchemyChatSettingsRepository(session)
                all_settings = await repo.list_all()

        for settings in all_settings:
            if settings.daily_reminder_enabled and settings.daily_reminder_time:
                schedule_morning_reminder(
                    app.job_queue, settings.chat_id, settings.daily_reminder_time
                )

        schedule_preclass_global_job(app.job_queue)
        logger.info("Reminder jobs scheduled for %d chats", len(all_settings))
    except Exception:
        logger.exception("Reminder scheduling failed")
        raise


def build_application() -> Application:
    app = (
        Application.builder()
        .token(BASE_CONFIG.bot_config.bot_token)
        .post_init(_post_init)
        .build()
    )

    app.add_handler(TypeHandler(Update, _log_update), group=-1)

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(CommandHandler("today", cmd_today))
    app.add_handler(CommandHandler("tomorrow", cmd_tomorrow))
    app.add_handler(CommandHandler("upcoming", cmd_upcoming))
    app.add_handler(MessageHandler(filters.Text(["Сегодня"]), cmd_today))
    app.add_handler(MessageHandler(filters.Text(["Завтра"]), cmd_tomorrow))
    app.add_handler(MessageHandler(filters.Text(["На неделю"]), cmd_upcoming))
    app.add_handler(build_add_student())
    app.add_handler(build_student_editor())
    app.add_handler(build_settings())
    logger.info("init telegramm bot")
    return app
