"""ConversationHandler for adding a student with a weekly schedule."""

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

from tutor_assistant.database import add_slots, add_student, async_session_factory
from tutor_assistant.handlers.common import cancel

# Conversation states
ASK_NAME, ASK_SLOTS, CONFIRM = range(3)

_DAY_MAP: dict[str, int] = {
    "ПН": 0, "ВТ": 1, "СР": 2, "ЧТ": 3, "ПТ": 4, "СБ": 5, "ВС": 6,
}
_DAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
_SLOT_RE = re.compile(r"^(ПН|ВТ|СР|ЧТ|ПТ|СБ|ВС)\s+(\d{1,2}):(\d{2})$", re.IGNORECASE)


def _parse_slot(text: str) -> tuple[int, datetime.time] | None:
    m = _SLOT_RE.match(text.strip().upper())
    if not m:
        return None
    day = _DAY_MAP[m.group(1)]
    hour, minute = int(m.group(2)), int(m.group(3))
    if hour > 23 or minute > 59:
        return None
    return day, datetime.time(hour, minute)


def _format_slots(slots: list[tuple[int, datetime.time]]) -> str:
    return "\n".join(f"  {_DAY_NAMES[d]} {t:%H:%M}" for d, t in slots)


async def add_student_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text("Введи имя ученика:")
    return ASK_NAME


async def received_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text("Имя не может быть пустым. Попробуй ещё раз:")
        return ASK_NAME

    context.user_data["student_name"] = name
    context.user_data["slots"] = []

    await update.message.reply_text(
        f"Ученик: <b>{name}</b>\n\n"
        "Теперь добавь расписание занятий. Отправляй каждый слот отдельным сообщением в формате:\n"
        "<code>ПН 14:30</code>\n\n"
        "Дни: ПН ВТ СР ЧТ ПТ СБ ВС\n\n"
        "Когда закончишь — отправь /done",
        parse_mode="HTML",
    )
    return ASK_SLOTS


async def received_slot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    parsed = _parse_slot(update.message.text)
    if parsed is None:
        await update.message.reply_text(
            "Не понял формат. Пример: <code>ПН 14:30</code>\n"
            "Когда закончишь — /done",
            parse_mode="HTML",
        )
        return ASK_SLOTS

    slots: list[tuple[int, datetime.time]] = context.user_data["slots"]
    slots.append(parsed)

    day, t = parsed
    await update.message.reply_text(
        f"✅ Добавлено: {_DAY_NAMES[day]} {t:%H:%M}\n"
        f"Всего слотов: {len(slots)}. Ещё или /done"
    )
    return ASK_SLOTS


async def slots_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    slots: list[tuple[int, datetime.time]] = context.user_data.get("slots", [])
    if not slots:
        await update.message.reply_text(
            "Ты ещё не добавил ни одного слота. Введи расписание или /cancel для отмены."
        )
        return ASK_SLOTS

    name = context.user_data["student_name"]
    await update.message.reply_text(
        f"Сохранить ученика?\n\n"
        f"Имя: <b>{name}</b>\n"
        f"Расписание:\n{_format_slots(slots)}\n\n"
        "/confirm — сохранить\n"
        "/cancel — отменить",
        parse_mode="HTML",
    )
    return CONFIRM


async def confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name: str = context.user_data["student_name"]
    slots: list[tuple[int, datetime.time]] = context.user_data["slots"]
    chat_id = update.effective_chat.id

    async with async_session_factory() as session:
        async with session.begin():
            student = await add_student(session, name=name, tutor_chat_id=chat_id)
            await add_slots(session, student_id=student.id, slots=slots)

    context.user_data.clear()
    await update.message.reply_text(
        f"✅ Ученик <b>{name}</b> сохранён!\n"
        f"Занятий в неделю: {len(slots)}\n\n"
        "Смотри список: /list_students",
        parse_mode="HTML",
    )
    return ConversationHandler.END


def build_add_student_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("add_student", add_student_start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_name)],
            ASK_SLOTS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, received_slot),
                CommandHandler("done", slots_done),
            ],
            CONFIRM: [CommandHandler("confirm", confirmed)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="add_student",
        persistent=False,
    )
