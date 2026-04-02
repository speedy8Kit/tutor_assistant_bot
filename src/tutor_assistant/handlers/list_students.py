"""Handler for /list_students."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from tutor_assistant.database import async_session_factory, list_students_with_slots

_DAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


async def list_students(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    async with async_session_factory() as session:
        students = await list_students_with_slots(session, tutor_chat_id=chat_id)

    if not students:
        await update.message.reply_text("У тебя пока нет учеников. Добавь первого: /add_student")
        return

    lines: list[str] = []
    for s in students:
        if s.slots:
            slot_strs = [
                f"{_DAY_NAMES[sl.day_of_week]} {sl.time_start:%H:%M}"
                for sl in sorted(s.slots, key=lambda sl: (sl.day_of_week, sl.time_start))
            ]
            schedule = ", ".join(slot_strs)
        else:
            schedule = "нет расписания"
        lines.append(f"• {s.name} — {schedule}")

    await update.message.reply_text("Ученики:\n" + "\n".join(lines))
