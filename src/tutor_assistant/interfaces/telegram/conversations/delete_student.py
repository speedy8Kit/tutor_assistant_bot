"""ConversationHandler for /delete_student."""

from __future__ import annotations

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from tutor_assistant.application.use_cases.students import delete_student, list_students
from tutor_assistant.domain.exceptions import StudentNotFound
from tutor_assistant.infrastructure.database.engine import async_session_factory
from tutor_assistant.infrastructure.database.repository import (
    SqlAlchemyStudentRepository,
)
from tutor_assistant.interfaces.shared.formatters import format_student_names_list
from tutor_assistant.interfaces.shared.messages import (
    ACTION_CANCELLED,
    DELETE_ASK_STUDENT,
    DELETE_CONFIRM,
    DELETE_DONE,
    DELETE_NOT_FOUND,
    DELETE_NO_STUDENTS,
)

PICK_STUDENT, CONFIRM_DELETE = range(2)

_KEY = "delete_student"


def _data(context: ContextTypes.DEFAULT_TYPE) -> dict:
    return context.user_data.setdefault(_KEY, {})  # type: ignore[return-value]


async def _start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[_KEY] = {}
    tutor_id = update.effective_chat.id

    args = context.args
    if args:
        name = " ".join(args)
        return await _confirm_delete(update, context, tutor_id, name)

    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyStudentRepository(session)
            students = await list_students(repo, tutor_id)

    if not students:
        await update.message.reply_text(DELETE_NO_STUDENTS)
        return ConversationHandler.END

    _data(context)["students"] = [s.name for s in students]
    await update.message.reply_text(
        DELETE_ASK_STUDENT.format(list=format_student_names_list(students)),
        parse_mode="HTML",
    )
    return PICK_STUDENT


async def _confirm_delete(
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
        await update.message.reply_text(DELETE_NOT_FOUND)
        return PICK_STUDENT

    _data(context)["student_name"] = student.name
    await update.message.reply_text(
        DELETE_CONFIRM.format(name=student.name), parse_mode="HTML"
    )
    return CONFIRM_DELETE


async def _pick_student(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    tutor_id = update.effective_chat.id
    names = _data(context).get("students", [])

    if text.isdigit():
        idx = int(text) - 1
        if 0 <= idx < len(names):
            name = names[idx]
        else:
            await update.message.reply_text(DELETE_NOT_FOUND)
            return PICK_STUDENT
    else:
        name = text

    return await _confirm_delete(update, context, tutor_id, name)


async def _do_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    d = _data(context)
    student_name = d.get("student_name", "")
    tutor_id = update.effective_chat.id

    try:
        async with async_session_factory() as session:
            async with session.begin():
                repo = SqlAlchemyStudentRepository(session)
                await delete_student(repo, tutor_id, student_name)
    except StudentNotFound:
        await update.message.reply_text(DELETE_NOT_FOUND)
        return ConversationHandler.END

    context.user_data.pop(_KEY, None)
    await update.message.reply_text(
        DELETE_DONE.format(name=student_name), parse_mode="HTML"
    )
    return ConversationHandler.END


async def _cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop(_KEY, None)
    await update.message.reply_text(ACTION_CANCELLED)
    return ConversationHandler.END


def build_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("delete_student", _start)],
        states={
            PICK_STUDENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, _pick_student)
            ],
            CONFIRM_DELETE: [
                CommandHandler("confirm_delete", _do_delete),
            ],
        },
        fallbacks=[CommandHandler("cancel", _cancel)],
        name="delete_student",
        persistent=False,
    )
