"""Shared handlers: /start and /cancel."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ConversationHandler, ContextTypes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я твой помощник-репетитор.\n\n"
        "/add_student — добавить ученика с расписанием\n"
        "/list_students — список учеников\n"
        "/cancel — отменить текущее действие"
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Действие отменено.")
    return ConversationHandler.END
