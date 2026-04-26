"""Simple Telegram command handlers: /start, /cancel, /today, /upcoming."""

from __future__ import annotations

import datetime

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from tutor_assistant.application.use_cases.schedule import (
    get_today_schedule,
    get_upcoming_schedule,
)
from tutor_assistant.infrastructure.database.engine import async_session_factory
from tutor_assistant.infrastructure.database.repository import (
    SqlAlchemyStudentRepository,
)
from tutor_assistant.infrastructure.logging.logger import get_logger
from tutor_assistant.interfaces.shared.formatters import (
    format_today_schedule,
    format_upcoming_schedule,
)
from tutor_assistant.interfaces.shared.keyboards import main_menu_keyboard
from tutor_assistant.interfaces.shared.messages import (
    ACTION_CANCELLED,
    TODAY_EMPTY,
    TODAY_HEADER,
    TOMORROW_EMPTY,
    TOMORROW_HEADER,
    UPCOMING_EMPTY,
    UPCOMING_HEADER,
    WELCOME,
)

_logger = get_logger()

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        WELCOME, parse_mode="HTML", reply_markup=main_menu_keyboard()
    )


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(ACTION_CANCELLED, reply_markup=main_menu_keyboard())
    return ConversationHandler.END


async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tutor_id = update.effective_chat.id
    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyStudentRepository(session)
            slots = await get_today_schedule(repo, tutor_id)

    if not slots:
        await update.message.reply_text(TODAY_EMPTY, reply_markup=main_menu_keyboard())
        return

    today = datetime.date.today()
    header = TODAY_HEADER.format(date=today.strftime("%d.%m.%Y"))
    body = format_today_schedule(slots)
    await update.message.reply_text(
        header + body, parse_mode="HTML", reply_markup=main_menu_keyboard()
    )


async def cmd_tomorrow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tutor_id = update.effective_chat.id
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyStudentRepository(session)
            slots = await get_today_schedule(repo, tutor_id, today=tomorrow)

    if not slots:
        await update.message.reply_text(TOMORROW_EMPTY, reply_markup=main_menu_keyboard())
        return

    header = TOMORROW_HEADER.format(date=tomorrow.strftime("%d.%m.%Y"))
    body = format_today_schedule(slots)
    await update.message.reply_text(
        header + body, parse_mode="HTML", reply_markup=main_menu_keyboard()
    )


async def cmd_upcoming(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tutor_id = update.effective_chat.id
    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyStudentRepository(session)
            slots = await get_upcoming_schedule(repo, tutor_id)

    if not slots:
        await update.message.reply_text(UPCOMING_EMPTY, reply_markup=main_menu_keyboard())
        return

    body = format_upcoming_schedule(slots)
    await update.message.reply_text(
        UPCOMING_HEADER + body, parse_mode="HTML", reply_markup=main_menu_keyboard()
    )
