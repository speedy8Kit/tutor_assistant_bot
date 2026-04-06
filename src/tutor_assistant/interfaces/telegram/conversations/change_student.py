"""ConversationHandler for /change_student."""

from __future__ import annotations

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from tutor_assistant.application.use_cases.students import list_students, update_student
from tutor_assistant.domain.exceptions import StudentNameTaken, StudentNotFound
from tutor_assistant.infrastructure.database.engine import async_session_factory
from tutor_assistant.infrastructure.database.repository import (
    SqlAlchemyStudentRepository,
)
from tutor_assistant.interfaces.shared.formatters import format_student_names_list
from tutor_assistant.interfaces.shared.messages import (
    ACTION_CANCELLED,
    CHANGE_ASK_NEW_VALUE,
    CHANGE_ASK_STUDENT,
    CHANGE_INVALID_FIELD,
    CHANGE_NAME_TAKEN,
    CHANGE_NOT_FOUND,
    CHANGE_NO_STUDENTS,
    CHANGE_PICK_FIELD,
    CHANGE_SAVED,
)

PICK_STUDENT, PICK_FIELD, ASK_NEW_VALUE = range(3)

_KEY = "change_student"
_FIELDS = {
    "1": ("name", "Имя"),
    "2": ("phone", "Телефон"),
    "3": ("full_name", "ФИО"),
    "4": ("comment", "Комментарий"),
    "5": ("telegram_link", "Telegram"),
}


def _data(context: ContextTypes.DEFAULT_TYPE) -> dict:
    return context.user_data.setdefault(_KEY, {})  # type: ignore[return-value]


async def _start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[_KEY] = {}
    tutor_id = update.effective_chat.id

    # Check if name passed as argument: /change_student Имя
    args = context.args
    if args:
        name = " ".join(args)
        return await _resolve_student(update, context, tutor_id, name)

    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyStudentRepository(session)
            students = await list_students(repo, tutor_id)

    if not students:
        await update.message.reply_text(CHANGE_NO_STUDENTS)
        return ConversationHandler.END

    _data(context)["students"] = [s.name for s in students]
    await update.message.reply_text(
        CHANGE_ASK_STUDENT.format(list=format_student_names_list(students)),
        parse_mode="HTML",
    )
    return PICK_STUDENT


async def _resolve_student(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    tutor_id: int,
    name: str,
) -> int:
    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyStudentRepository(session)
            student = await repo.get_by_name(tutor_id, name)

    if student is None:
        await update.message.reply_text(CHANGE_NOT_FOUND)
        return PICK_STUDENT

    _data(context)["student_name"] = student.name
    await update.message.reply_text(
        CHANGE_PICK_FIELD.format(name=student.name), parse_mode="HTML"
    )
    return PICK_FIELD


async def _pick_student(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    tutor_id = update.effective_chat.id
    names = _data(context).get("students", [])

    # Accept number or exact name
    if text.isdigit():
        idx = int(text) - 1
        if 0 <= idx < len(names):
            name = names[idx]
        else:
            await update.message.reply_text(CHANGE_NOT_FOUND)
            return PICK_STUDENT
    else:
        name = text

    return await _resolve_student(update, context, tutor_id, name)


async def _pick_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text.strip()
    if choice not in _FIELDS:
        await update.message.reply_text(CHANGE_INVALID_FIELD)
        return PICK_FIELD

    field_key, field_label = _FIELDS[choice]
    _data(context)["field_key"] = field_key
    _data(context)["field_label"] = field_label
    await update.message.reply_text(CHANGE_ASK_NEW_VALUE)
    return ASK_NEW_VALUE


async def _set_new_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    new_value = None if text == "/clear" else text

    d = _data(context)
    field_key = d["field_key"]
    student_name = d["student_name"]
    tutor_id = update.effective_chat.id

    try:
        async with async_session_factory() as session:
            async with session.begin():
                repo = SqlAlchemyStudentRepository(session)
                updated = await update_student(
                    repo, tutor_id, student_name, **{field_key: new_value}
                )
    except StudentNotFound:
        await update.message.reply_text(CHANGE_NOT_FOUND)
        return ConversationHandler.END
    except StudentNameTaken:
        await update.message.reply_text(
            CHANGE_NAME_TAKEN.format(name=new_value), parse_mode="HTML"
        )
        return ASK_NEW_VALUE

    context.user_data.pop(_KEY, None)
    await update.message.reply_text(
        CHANGE_SAVED.format(name=updated.name), parse_mode="HTML"
    )
    return ConversationHandler.END


async def _cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop(_KEY, None)
    await update.message.reply_text(ACTION_CANCELLED)
    return ConversationHandler.END


def build_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("change_student", _start)],
        states={
            PICK_STUDENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, _pick_student)
            ],
            PICK_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, _pick_field)],
            ASK_NEW_VALUE: [
                CommandHandler("clear", _set_new_value),
                MessageHandler(filters.TEXT & ~filters.COMMAND, _set_new_value),
            ],
        },
        fallbacks=[CommandHandler("cancel", _cancel)],
        name="change_student",
        persistent=False,
    )
