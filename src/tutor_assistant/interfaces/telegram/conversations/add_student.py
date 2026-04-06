"""ConversationHandler for /add_student."""

from __future__ import annotations

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from tutor_assistant.application.use_cases.students import create_student
from tutor_assistant.domain.entities import SlotData
from tutor_assistant.domain.exceptions import SlotConflict, StudentNameTaken
from tutor_assistant.domain.schedule import DAY_NAMES, parse_slot
from tutor_assistant.infrastructure.database.engine import async_session_factory
from tutor_assistant.infrastructure.database.repository import (
    SqlAlchemyStudentRepository,
)
from tutor_assistant.interfaces.shared.formatters import (
    format_conflicts,
)
from tutor_assistant.interfaces.shared.messages import (
    ADD_ASK_COMMENT,
    ADD_ASK_NAME,
    ADD_ASK_PHONE,
    ADD_ASK_SLOTS,
    ADD_ASK_TELEGRAM,
    ADD_ASK_FULL_NAME,
    ADD_CONFIRM_NO_SLOTS,
    ADD_CONFIRM_PROMPT,
    ADD_CONFLICT_ERROR,
    ADD_NAME_EMPTY,
    ADD_NAME_TAKEN,
    ADD_SAVED,
    ADD_SLOT_ADDED,
    ADD_SLOT_FORMAT_ERROR,
    ACTION_CANCELLED,
)

# Conversation states
(
    ASK_NAME,
    ASK_PHONE,
    ASK_FULL_NAME,
    ASK_COMMENT,
    ASK_TELEGRAM,
    ASK_SLOTS,
    CONFIRM,
) = range(7)

_KEY = "add_student"


def _data(context: ContextTypes.DEFAULT_TYPE) -> dict:
    return context.user_data.setdefault(_KEY, {})  # type: ignore[return-value]


async def _start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[_KEY] = {}
    await update.message.reply_text(ADD_ASK_NAME)
    return ASK_NAME


async def _received_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text(ADD_NAME_EMPTY)
        return ASK_NAME

    tutor_id = update.effective_chat.id
    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyStudentRepository(session)
            existing = await repo.get_by_name(tutor_id, name)

    if existing is not None:
        await update.message.reply_text(
            ADD_NAME_TAKEN.format(name=name), parse_mode="HTML"
        )
        return ASK_NAME

    _data(context)["name"] = name
    await update.message.reply_text(ADD_ASK_PHONE)
    return ASK_PHONE


async def _received_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    _data(context)["phone"] = None if text == "/skip" else text
    await update.message.reply_text(ADD_ASK_FULL_NAME)
    return ASK_FULL_NAME


async def _received_full_name(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    text = update.message.text.strip()
    _data(context)["full_name"] = None if text == "/skip" else text
    await update.message.reply_text(ADD_ASK_COMMENT)
    return ASK_COMMENT


async def _received_comment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    _data(context)["comment"] = None if text == "/skip" else text
    await update.message.reply_text(ADD_ASK_TELEGRAM)
    return ASK_TELEGRAM


async def _received_telegram(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    _data(context)["telegram_link"] = None if text == "/skip" else text
    _data(context)["slots"] = []
    await update.message.reply_text(ADD_ASK_SLOTS, parse_mode="HTML")
    return ASK_SLOTS


async def _received_slot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    parsed = parse_slot(update.message.text)
    if parsed is None:
        await update.message.reply_text(ADD_SLOT_FORMAT_ERROR, parse_mode="HTML")
        return ASK_SLOTS

    day, t, dur = parsed
    _data(context)["slots"].append(parsed)
    count = len(_data(context)["slots"])
    await update.message.reply_text(
        ADD_SLOT_ADDED.format(day=DAY_NAMES[day], t=f"{t:%H:%M}", dur=dur, count=count)
    )
    return ASK_SLOTS


async def _slots_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    d = _data(context)
    slots = d.get("slots", [])
    name = d.get("name", "")

    if slots:
        schedule_text = "\n".join(
            f"  {DAY_NAMES[day]} {t:%H:%M} ({dur} мин)" for day, t, dur in slots
        )
        extra = _build_extra(d)
        msg = ADD_CONFIRM_PROMPT.format(name=name, extra=extra, schedule=schedule_text)
    else:
        extra = _build_extra(d)
        msg = ADD_CONFIRM_NO_SLOTS.format(name=name, extra=extra)

    await update.message.reply_text(msg, parse_mode="HTML")
    return CONFIRM


async def _confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    d = _data(context)
    name = d["name"]
    tutor_id = update.effective_chat.id
    raw_slots = d.get("slots", [])
    slot_data = [
        SlotData(day_of_week=day, time_start=t, duration_minutes=dur)
        for day, t, dur in raw_slots
    ]

    try:
        async with async_session_factory() as session:
            async with session.begin():
                repo = SqlAlchemyStudentRepository(session)
                student = await create_student(
                    repo,
                    tutor_id,
                    name,
                    slot_data,
                    phone=d.get("phone"),
                    full_name=d.get("full_name"),
                    comment=d.get("comment"),
                    telegram_link=d.get("telegram_link"),
                )
    except StudentNameTaken:
        await update.message.reply_text(
            ADD_NAME_TAKEN.format(name=name), parse_mode="HTML"
        )
        return ASK_NAME
    except SlotConflict as exc:
        await update.message.reply_text(
            ADD_CONFLICT_ERROR.format(conflicts=format_conflicts(exc.conflicts)),
            parse_mode="HTML",
        )
        d["slots"] = []
        await update.message.reply_text(ADD_ASK_SLOTS, parse_mode="HTML")
        return ASK_SLOTS

    context.user_data.pop(_KEY, None)
    await update.message.reply_text(
        ADD_SAVED.format(name=student.name, count=len(student.slots)),
        parse_mode="HTML",
    )
    return ConversationHandler.END


async def _cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop(_KEY, None)
    await update.message.reply_text(ACTION_CANCELLED)
    return ConversationHandler.END


def _build_extra(d: dict) -> str:
    lines: list[str] = []
    if d.get("full_name"):
        lines.append(f"ФИО: {d['full_name']}")
    if d.get("phone"):
        lines.append(f"Телефон: {d['phone']}")
    if d.get("telegram_link"):
        lines.append(f"Telegram: {d['telegram_link']}")
    if d.get("comment"):
        lines.append(f"Комментарий: {d['comment']}")
    return ("\n".join(lines) + "\n") if lines else ""


def build_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("add_student", _start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, _received_name)],
            ASK_PHONE: [
                CommandHandler("skip", _received_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, _received_phone),
            ],
            ASK_FULL_NAME: [
                CommandHandler("skip", _received_full_name),
                MessageHandler(filters.TEXT & ~filters.COMMAND, _received_full_name),
            ],
            ASK_COMMENT: [
                CommandHandler("skip", _received_comment),
                MessageHandler(filters.TEXT & ~filters.COMMAND, _received_comment),
            ],
            ASK_TELEGRAM: [
                CommandHandler("skip", _received_telegram),
                MessageHandler(filters.TEXT & ~filters.COMMAND, _received_telegram),
            ],
            ASK_SLOTS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, _received_slot),
                CommandHandler("done", _slots_done),
            ],
            CONFIRM: [CommandHandler("confirm", _confirmed)],
        },
        fallbacks=[CommandHandler("cancel", _cancel)],
        name="add_student",
        persistent=False,
    )
