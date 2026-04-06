"""Simple Telegram command handlers: /start, /cancel, /list_students, /today, /upcoming."""

from __future__ import annotations

import datetime

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from tutor_assistant.application.use_cases.schedule import (
    get_today_schedule,
    get_upcoming_schedule,
)
from tutor_assistant.application.use_cases.students import list_students
from tutor_assistant.infrastructure.database.engine import async_session_factory
from tutor_assistant.infrastructure.database.repository import (
    SqlAlchemyStudentRepository,
)
from tutor_assistant.interfaces.shared.formatters import (
    format_student_list,
    format_today_schedule,
    format_upcoming_schedule,
)
from tutor_assistant.interfaces.shared.messages import (
    ACTION_CANCELLED,
    LIST_EMPTY,
    LIST_HEADER,
    TODAY_EMPTY,
    TODAY_HEADER,
    UPCOMING_EMPTY,
    UPCOMING_HEADER,
    WELCOME,
)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME, parse_mode="HTML")


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(ACTION_CANCELLED)
    return ConversationHandler.END


async def cmd_list_students(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tutor_id = update.effective_chat.id
    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyStudentRepository(session)
            students = await list_students(repo, tutor_id)

    if not students:
        await update.message.reply_text(LIST_EMPTY)
        return

    header = LIST_HEADER.format(count=len(students))
    body = format_student_list(students)
    await update.message.reply_text(header + body, parse_mode="HTML")


async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tutor_id = update.effective_chat.id
    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyStudentRepository(session)
            slots = await get_today_schedule(repo, tutor_id)

    if not slots:
        await update.message.reply_text(TODAY_EMPTY)
        return

    today = datetime.date.today()
    header = TODAY_HEADER.format(date=today.strftime("%d.%m.%Y"))
    body = format_today_schedule(slots)
    await update.message.reply_text(header + body, parse_mode="HTML")


async def cmd_upcoming(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tutor_id = update.effective_chat.id
    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyStudentRepository(session)
            slots = await get_upcoming_schedule(repo, tutor_id)

    if not slots:
        await update.message.reply_text(UPCOMING_EMPTY)
        return

    body = format_upcoming_schedule(slots)
    await update.message.reply_text(UPCOMING_HEADER + body, parse_mode="HTML")
