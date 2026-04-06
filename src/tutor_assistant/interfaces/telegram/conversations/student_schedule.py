"""ConversationHandler for /student_schedule — view and edit a student's schedule."""

from __future__ import annotations


from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from tutor_assistant.application.use_cases.schedule import update_schedule
from tutor_assistant.application.use_cases.students import list_students
from tutor_assistant.domain.entities import SlotData
from tutor_assistant.domain.exceptions import SlotConflict, StudentNotFound
from tutor_assistant.domain.schedule import DAY_NAMES, parse_slot
from tutor_assistant.infrastructure.database.engine import async_session_factory
from tutor_assistant.infrastructure.database.repository import (
    SqlAlchemyStudentRepository,
)
from tutor_assistant.interfaces.shared.formatters import (
    format_conflicts,
    format_student_names_list,
)
from tutor_assistant.interfaces.shared.messages import (
    ACTION_CANCELLED,
    SCHEDULE_ADD_PROMPT,
    SCHEDULE_ASK_STUDENT,
    SCHEDULE_CONFLICT_ERROR,
    SCHEDULE_EMPTY,
    SCHEDULE_NOT_FOUND,
    SCHEDULE_NO_STUDENTS,
    SCHEDULE_REMOVE_BAD_NUM,
    SCHEDULE_SAVED,
    SCHEDULE_SHOW,
    SCHEDULE_SLOT_FORMAT_ERROR,
)

PICK_STUDENT, SHOW_MENU, ADD_SLOT = range(3)

_KEY = "student_schedule"


def _data(context: ContextTypes.DEFAULT_TYPE) -> dict:
    return context.user_data.setdefault(_KEY, {})  # type: ignore[return-value]


def _slots_text(slots: list[SlotData]) -> str:
    sorted_slots = sorted(slots, key=lambda s: (s.day_of_week, s.time_start))
    return "\n".join(
        f"{i}. {DAY_NAMES[s.day_of_week]} {s.time_start:%H:%M} ({s.duration_minutes} мин)"
        for i, s in enumerate(sorted_slots, 1)
    )


async def _show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    d = _data(context)
    name = d["student_name"]
    slots: list[SlotData] = d.get("slots", [])

    if slots:
        msg = SCHEDULE_SHOW.format(name=name, slots=_slots_text(slots))
    else:
        msg = SCHEDULE_EMPTY.format(name=name)

    await update.message.reply_text(msg, parse_mode="HTML")
    return SHOW_MENU


async def _start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[_KEY] = {}
    tutor_id = update.effective_chat.id

    args = context.args
    if args:
        name = " ".join(args)
        return await _load_student(update, context, tutor_id, name)

    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyStudentRepository(session)
            students = await list_students(repo, tutor_id)

    if not students:
        await update.message.reply_text(SCHEDULE_NO_STUDENTS)
        return ConversationHandler.END

    _data(context)["students"] = [s.name for s in students]
    await update.message.reply_text(
        SCHEDULE_ASK_STUDENT.format(list=format_student_names_list(students)),
        parse_mode="HTML",
    )
    return PICK_STUDENT


async def _load_student(
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
        await update.message.reply_text(SCHEDULE_NOT_FOUND)
        return PICK_STUDENT

    d = _data(context)
    d["student_name"] = student.name
    # Work on a mutable copy of current slots
    d["slots"] = list(student.slots)
    return await _show_menu(update, context)


async def _pick_student(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    tutor_id = update.effective_chat.id
    names = _data(context).get("students", [])

    if text.isdigit():
        idx = int(text) - 1
        if 0 <= idx < len(names):
            name = names[idx]
        else:
            await update.message.reply_text(SCHEDULE_NOT_FOUND)
            return PICK_STUDENT
    else:
        name = text

    return await _load_student(update, context, tutor_id, name)


async def _cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(SCHEDULE_ADD_PROMPT, parse_mode="HTML")
    return ADD_SLOT


async def _received_slot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    parsed = parse_slot(update.message.text)
    if parsed is None:
        await update.message.reply_text(SCHEDULE_SLOT_FORMAT_ERROR, parse_mode="HTML")
        return ADD_SLOT

    day, t, dur = parsed
    tutor_id = update.effective_chat.id
    d = _data(context)
    student_name = d["student_name"]

    # Conflict check against repository (excluding this student)
    new_slot_data = SlotData(day_of_week=day, time_start=t, duration_minutes=dur)
    candidate = d.get("slots", []) + [new_slot_data]

    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyStudentRepository(session)
            student = await repo.get_by_name(tutor_id, student_name)
            if student is None:
                await update.message.reply_text(SCHEDULE_NOT_FOUND)
                return ConversationHandler.END
            all_slots = await repo.get_all_slots(tutor_id)

    from tutor_assistant.domain.schedule import check_conflicts

    raw = [(s.day_of_week, s.time_start, s.duration_minutes) for s in candidate]
    conflicts = check_conflicts(raw, all_slots, exclude_student_id=student.id)
    if conflicts:
        await update.message.reply_text(
            SCHEDULE_CONFLICT_ERROR.format(conflicts=format_conflicts(conflicts)),
            parse_mode="HTML",
        )
        return ADD_SLOT

    d["slots"].append(new_slot_data)
    return await _show_menu(update, context)


async def _cmd_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /remove N — remove slot by 1-based index from buffer."""
    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text(SCHEDULE_REMOVE_BAD_NUM)
        return SHOW_MENU

    idx = int(args[0]) - 1
    d = _data(context)
    slots: list[SlotData] = d.get("slots", [])
    sorted_slots = sorted(slots, key=lambda s: (s.day_of_week, s.time_start))

    if idx < 0 or idx >= len(sorted_slots):
        await update.message.reply_text(SCHEDULE_REMOVE_BAD_NUM)
        return SHOW_MENU

    slot_to_remove = sorted_slots[idx]
    d["slots"] = [s for s in slots if s is not slot_to_remove]
    return await _show_menu(update, context)


async def _cmd_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    d = _data(context)
    student_name = d["student_name"]
    tutor_id = update.effective_chat.id
    new_slots: list[SlotData] = d.get("slots", [])

    try:
        async with async_session_factory() as session:
            async with session.begin():
                repo = SqlAlchemyStudentRepository(session)
                await update_schedule(repo, tutor_id, student_name, new_slots)
    except StudentNotFound:
        await update.message.reply_text(SCHEDULE_NOT_FOUND)
        return ConversationHandler.END
    except SlotConflict as exc:
        await update.message.reply_text(
            SCHEDULE_CONFLICT_ERROR.format(conflicts=format_conflicts(exc.conflicts)),
            parse_mode="HTML",
        )
        return SHOW_MENU

    context.user_data.pop(_KEY, None)
    await update.message.reply_text(
        SCHEDULE_SAVED.format(name=student_name), parse_mode="HTML"
    )
    return ConversationHandler.END


async def _cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop(_KEY, None)
    await update.message.reply_text(ACTION_CANCELLED)
    return ConversationHandler.END


def build_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("student_schedule", _start)],
        states={
            PICK_STUDENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, _pick_student)
            ],
            SHOW_MENU: [
                CommandHandler("add", _cmd_add),
                CommandHandler("remove", _cmd_remove),
                CommandHandler("done", _cmd_done),
            ],
            ADD_SLOT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, _received_slot),
            ],
        },
        fallbacks=[CommandHandler("cancel", _cancel)],
        name="student_schedule",
        persistent=False,
    )
