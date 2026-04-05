"""Shared Telegram handlers: /start and /cancel."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from tutor_assistant.application.flows.common import ACTION_CANCELLED, WELCOME


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(ACTION_CANCELLED)
    return ConversationHandler.END
