"""Handler for /list_students."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from tutor_assistant.infrastructure.database import async_session_factory, list_students_with_slots


async def list_students(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    text = await get_list_studetns(chat_id)
    await update.message.reply_text(text)

_DAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

async def get_studetns(tutor_id: int):
    async with async_session_factory() as session:
        students = await list_students_with_slots(session, tutor_chat_id=tutor_id)
    return students


async def format_students(students):
    if not students:
        return "У тебя пока нет учеников. Добавь первого: /add_student"
    
    lines: list[str] = []
    for s in students:
        if s.slots:
            slot_strs = [
                f"{_DAY_NAMES[sl.day_of_week]} {sl.time_start:%H:%M}"
                for sl in sorted(
                    s.slots, key=lambda sl: (sl.day_of_week, sl.time_start)
                )
            ]
            schedule = ", ".join(slot_strs)
        else:
            schedule = "нет расписания"
        lines.append(f"• {s.name} — {schedule}")
    return "Ученики:\n" + "\n".join(lines)

async def get_list_studetns(tutor_id: int):
    students = await get_studetns(tutor_id)
    text = await format_students(students)
    return text
