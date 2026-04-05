"""Handler for /list_students."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from tutor_assistant.application.services.students_service import get_students
from tutor_assistant.application.flows.list_students import format_students


async def list_students(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    students = await get_students(update.effective_chat.id)
    await update.message.reply_text(format_students(students))
