"""Minimal echo bot for experiments."""

import os

from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    await update.message.reply_text(f'Я получил "{text}"')


def main() -> None:
    token = os.environ["BOT_TOKEN"]
    app = Application.builder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    app.run_polling()


if __name__ == "__main__":
    main()
