"""ConversationHandler for the /add_student flow."""

from __future__ import annotations

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from tutor_assistant.application.handlers.telegram.common import cancel
from tutor_assistant.application.services.students_service import create_student
from tutor_assistant.application.flows.add_student import (
    MSG_ASK_NAME,
    MSG_ASK_SLOTS,
    MSG_ASK_SAVE,
    MSG_SLOT_ADDED,
    NAME_EMPTY,
    NO_SLOTS_YET,
    SLOT_FORMAT_ERROR,
    STUDENT_SAVED,
)
from tutor_assistant.domain.schedule import DAY_NAMES, format_slots, parse_slot

# Conversation states
ASK_NAME, ASK_SLOTS, CONFIRM = range(3)


async def _add_student_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(MSG_ASK_NAME)
    return ASK_NAME


async def _received_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text(NAME_EMPTY)
        return ASK_NAME
    context.user_data["student_name"] = name
    context.user_data["slots"] = []
    await update.message.reply_text(
        f"Ученик: <b>{name}</b>\n\n{MSG_ASK_SLOTS}", parse_mode="HTML"
    )
    return ASK_SLOTS


async def _received_slot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    parsed = parse_slot(update.message.text)
    if parsed is None:
        await update.message.reply_text(SLOT_FORMAT_ERROR, parse_mode="HTML")
        return ASK_SLOTS
    context.user_data["slots"].append(parsed)
    day, t = parsed
    await update.message.reply_text(
        MSG_SLOT_ADDED.format(
            day=DAY_NAMES[day], t=t, len_slots=len(context.user_data["slots"])
        ),
        parse_mode="HTML",
    )
    return ASK_SLOTS


async def _slots_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    slots: list = context.user_data.get("slots", [])
    name: str = context.user_data.get("student_name", "")
    if not slots:
        await update.message.reply_text(NO_SLOTS_YET)
        return ASK_SLOTS
    await update.message.reply_text(
        MSG_ASK_SAVE.format(name=name, schedule=format_slots(slots)),
        parse_mode="HTML",
    )
    return CONFIRM


async def _confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name: str = context.user_data["student_name"]
    slots: list = context.user_data["slots"]
    await create_student(name, update.effective_chat.id, slots)
    context.user_data.clear()
    await update.message.reply_text(
        STUDENT_SAVED.format(name=name, count=len(slots)),
        parse_mode="HTML",
    )
    return ConversationHandler.END


def build_add_student_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("add_student", _add_student_start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, _received_name)],
            ASK_SLOTS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, _received_slot),
                CommandHandler("done", _slots_done),
            ],
            CONFIRM: [CommandHandler("confirm", _confirmed)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        name="add_student",
        persistent=False,
    )
