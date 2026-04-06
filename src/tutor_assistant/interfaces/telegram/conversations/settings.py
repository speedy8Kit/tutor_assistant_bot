"""ConversationHandler for /settings — manage reminder preferences."""

from __future__ import annotations

import datetime
import re

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from tutor_assistant.application.use_cases.settings import (
    get_settings,
    set_daily_reminder,
    set_pre_class_reminder,
)
from tutor_assistant.infrastructure.database.engine import async_session_factory
from tutor_assistant.infrastructure.database.repository import (
    SqlAlchemyChatSettingsRepository,
)
from tutor_assistant.interfaces.shared.messages import (
    ACTION_CANCELLED,
    SETTINGS_ASK_DAILY_TIME,
    SETTINGS_ASK_PRE_CLASS_MINUTES,
    SETTINGS_DAILY_DISABLED,
    SETTINGS_DAILY_ENABLED,
    SETTINGS_INVALID_CHOICE,
    SETTINGS_INVALID_MINUTES,
    SETTINGS_INVALID_TIME,
    SETTINGS_PRE_CLASS_DISABLED,
    SETTINGS_PRE_CLASS_ENABLED,
    SETTINGS_SAVED,
    SETTINGS_SHOW,
)
from tutor_assistant.interfaces.telegram.reminders import (
    cancel_morning_reminder,
    schedule_morning_reminder,
)

SHOW_MENU, SET_DAILY_TIME, SET_PRE_CLASS_MINUTES = range(3)

_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})$")


async def _show_settings_menu(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    chat_id = update.effective_chat.id
    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyChatSettingsRepository(session)
            settings = await get_settings(repo, chat_id)

    if settings.daily_reminder_enabled and settings.daily_reminder_time:
        daily_status = SETTINGS_DAILY_ENABLED.format(
            time=settings.daily_reminder_time.strftime("%H:%M")
        )
    else:
        daily_status = SETTINGS_DAILY_DISABLED

    if settings.pre_class_reminder_enabled and settings.pre_class_reminder_minutes:
        pre_class_status = SETTINGS_PRE_CLASS_ENABLED.format(
            minutes=settings.pre_class_reminder_minutes
        )
    else:
        pre_class_status = SETTINGS_PRE_CLASS_DISABLED

    await update.message.reply_text(
        SETTINGS_SHOW.format(
            daily_status=daily_status, pre_class_status=pre_class_status
        ),
        parse_mode="HTML",
    )
    return SHOW_MENU


async def _pick_option(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text.strip()
    if choice == "1":
        await update.message.reply_text(SETTINGS_ASK_DAILY_TIME, parse_mode="HTML")
        return SET_DAILY_TIME
    elif choice == "2":
        await update.message.reply_text(
            SETTINGS_ASK_PRE_CLASS_MINUTES, parse_mode="HTML"
        )
        return SET_PRE_CLASS_MINUTES
    else:
        await update.message.reply_text(SETTINGS_INVALID_CHOICE)
        return SHOW_MENU


async def _set_daily_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    chat_id = update.effective_chat.id

    if text == "/disable":
        reminder_time = None
    else:
        m = _TIME_RE.match(text)
        if not m:
            await update.message.reply_text(SETTINGS_INVALID_TIME, parse_mode="HTML")
            return SET_DAILY_TIME
        hour, minute = int(m.group(1)), int(m.group(2))
        if hour > 23 or minute > 59:
            await update.message.reply_text(SETTINGS_INVALID_TIME, parse_mode="HTML")
            return SET_DAILY_TIME
        reminder_time = datetime.time(hour, minute)

    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyChatSettingsRepository(session)
            await set_daily_reminder(repo, chat_id, reminder_time)

    if reminder_time is not None:
        schedule_morning_reminder(context.job_queue, chat_id, reminder_time)
    else:
        cancel_morning_reminder(context.job_queue, chat_id)

    await update.message.reply_text(SETTINGS_SAVED)
    return ConversationHandler.END


async def _set_pre_class_minutes(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    text = update.message.text.strip()
    chat_id = update.effective_chat.id

    if text == "/disable":
        minutes = None
    else:
        if not text.isdigit() or not (1 <= int(text) <= 120):
            await update.message.reply_text(SETTINGS_INVALID_MINUTES, parse_mode="HTML")
            return SET_PRE_CLASS_MINUTES
        minutes = int(text)

    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyChatSettingsRepository(session)
            await set_pre_class_reminder(repo, chat_id, minutes)

    await update.message.reply_text(SETTINGS_SAVED)
    return ConversationHandler.END


async def _cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(ACTION_CANCELLED)
    return ConversationHandler.END


def build_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("settings", _show_settings_menu)],
        states={
            SHOW_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, _pick_option),
            ],
            SET_DAILY_TIME: [
                CommandHandler("disable", _set_daily_time),
                MessageHandler(filters.TEXT & ~filters.COMMAND, _set_daily_time),
            ],
            SET_PRE_CLASS_MINUTES: [
                CommandHandler("disable", _set_pre_class_minutes),
                MessageHandler(filters.TEXT & ~filters.COMMAND, _set_pre_class_minutes),
            ],
        },
        fallbacks=[CommandHandler("cancel", _cancel)],
        name="settings",
        persistent=False,
    )
