"""Unified ConversationHandler: список → карточка ученика → редактирование полей / расписание.

Список и расписание: кликабельные команды в тексте.
Карточка и подтверждение удаления: ReplyKeyboardMarkup (кнопки внизу).
Текстовый ввод используется только для ввода новых значений.
"""

from __future__ import annotations

import re

from telegram import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from tutor_assistant.domain.entities import SlotData, StudentData
from tutor_assistant.domain.schedule import DAY_NAMES, check_conflicts, parse_slot
from tutor_assistant.infrastructure.database.engine import async_session_factory
from tutor_assistant.infrastructure.database.repository import (
    SqlAlchemyStudentRepository,
)
from tutor_assistant.interfaces.shared.formatters import format_slot
from tutor_assistant.interfaces.shared.keyboards import (
    BTN_DELETE_NO,
    BTN_DELETE_YES,
    confirm_delete_keyboard,
    main_menu_keyboard,
)
from tutor_assistant.interfaces.shared.messages import (
    ACTION_CANCELLED,
    LIST_EMPTY,
    SCHEDULE_CONFLICT_ERROR,
    SCHEDULE_SLOT_FORMAT_ERROR,
)

# ---------------------------------------------------------------------------
# States
# ---------------------------------------------------------------------------
(
    SHOW_LIST,
    SHOW_CARD,
    CONFIRM_DELETE,
    EDIT_FIELD,
    SCHEDULE_VIEW,
    EDIT_SLOT,
    ADD_SLOT,
) = range(7)

_KEY = "student_editor"

# ---------------------------------------------------------------------------
# Field definitions
# ---------------------------------------------------------------------------
_FIELDS: list[tuple[str, str]] = [
    ("name", "Имя"),
    ("full_name", "ФИО"),
    ("phone", "Телефон"),
    ("comment", "Комментарий"),
    ("telegram_link", "Telegram"),
]

# label → field_key mapping for card button handling
_FIELD_LABELS: dict[str, str] = {label: key for key, label in _FIELDS}


def _data(context: ContextTypes.DEFAULT_TYPE) -> dict:
    return context.user_data.setdefault(_KEY, {})  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _compact_schedule(student: StudentData) -> str:
    if not student.slots:
        return "нет"
    sorted_slots = sorted(student.slots, key=lambda s: (s.day_of_week, s.time_start))
    return ", ".join(
        f"{DAY_NAMES[s.day_of_week]} {s.time_start:%H:%M}" for s in sorted_slots
    )


def _fmt_list(students: list[StudentData]) -> str:
    lines = [f"Твои ученики ({len(students)}):"]
    lines.append("")
    for s in students:
        lines.append(f"/s_{s.id} — {s.name}")
    lines.append("")
    lines.append("/start — ← Меню")
    return "\n".join(lines)


def _fmt_card(student: StudentData) -> str:
    lines = [f"<b>{student.name}</b>", ""]
    for field_key, label in _FIELDS:
        value = getattr(student, field_key) or "—"
        lines.append(f"{label}: {value}")
    lines.append(f"Расписание: {_compact_schedule(student)}")
    return "\n".join(lines)


def _fmt_schedule(student: StudentData) -> str:
    lines: list[str] = []
    if student.slots:
        lines.append(f"Расписание <b>{student.name}</b>:")
        lines.append("")
        sorted_slots = sorted(student.slots, key=lambda s: (s.day_of_week, s.time_start))
        for i, slot in enumerate(sorted_slots, 1):
            lines.append(f"{i}. {format_slot(slot)}")
            lines.append(f"/se_{slot.id} — изменить   /sd_{slot.id} — удалить")
    else:
        lines.append(f"У <b>{student.name}</b> нет расписания.")
    lines.append("")
    lines.append("/sadd — Добавить занятие")
    lines.append(f"/sback — ← Назад к карточке")
    return "\n".join(lines)


def _fmt_confirm_delete(student: StudentData) -> str:
    return (
        f"Удалить ученика <b>{student.name}</b>?\n\n"
        "Это действие БЕЗВОЗВРАТНО — все данные и расписание будут удалены."
    )


# ---------------------------------------------------------------------------
# Keyboard builders
# ---------------------------------------------------------------------------


def _card_keyboard() -> ReplyKeyboardMarkup:
    field_buttons = [KeyboardButton(label) for _, label in _FIELDS]
    rows = [field_buttons[i : i + 2] for i in range(0, len(field_buttons), 2)]
    rows.append([KeyboardButton("Расписание")])
    rows.append([KeyboardButton("Удалить"), KeyboardButton("← Список")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)



# ---------------------------------------------------------------------------
# Load helper
# ---------------------------------------------------------------------------


async def _load_by_id(student_id: int) -> StudentData | None:
    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyStudentRepository(session)
            return await repo.get_by_id(student_id)


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------


async def _render_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    tutor_id = update.effective_chat.id
    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyStudentRepository(session)
            students = await repo.list_all(tutor_id)

    text = LIST_EMPTY if not students else _fmt_list(students)

    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="HTML")
    else:
        await update.effective_message.reply_text(
            text, parse_mode="HTML", reply_markup=ReplyKeyboardRemove()
        )
    return SHOW_LIST


async def _render_card(
    update: Update, context: ContextTypes.DEFAULT_TYPE, student: StudentData
) -> int:
    _data(context)["student_id"] = student.id
    text = _fmt_card(student)
    await update.effective_message.reply_text(
        text, reply_markup=_card_keyboard(), parse_mode="HTML"
    )
    return SHOW_CARD


async def _render_schedule(
    update: Update, context: ContextTypes.DEFAULT_TYPE, student: StudentData
) -> int:
    _data(context)["student_id"] = student.id
    text = _fmt_schedule(student)
    await update.effective_message.reply_text(
        text, parse_mode="HTML", reply_markup=ReplyKeyboardRemove()
    )
    return SCHEDULE_VIEW


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


async def _show_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data[_KEY] = {}
    return await _render_list(update, context)


async def _change_student_cmd(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    context.user_data[_KEY] = {}
    tutor_id = update.effective_chat.id
    args = context.args

    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyStudentRepository(session)
            students = await repo.list_all(tutor_id)

    if not students:
        await update.message.reply_text(LIST_EMPTY)
        return ConversationHandler.END

    if args and args[0].isdigit():
        idx = int(args[0]) - 1
        if 0 <= idx < len(students):
            return await _render_card(update, context, students[idx])

    await update.message.reply_text(_fmt_list(students), parse_mode="HTML")
    return SHOW_LIST


# ---------------------------------------------------------------------------
# SHOW_LIST state
# ---------------------------------------------------------------------------


async def _show_card_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """/s_{student_id} — показать карточку ученика."""
    m = re.match(r"^/s_(\d+)", update.message.text)
    if not m:
        return SHOW_LIST
    student_id = int(m.group(1))
    student = await _load_by_id(student_id)
    if student is None:
        await update.message.reply_text("Ученик не найден.")
        return ConversationHandler.END
    return await _render_card(update, context, student)


# ---------------------------------------------------------------------------
# SHOW_CARD state — обработчики кнопок (ReplyKeyboard)
# ---------------------------------------------------------------------------


async def _start_edit_field_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    field_label = update.message.text.strip()
    field_key = _FIELD_LABELS.get(field_label)
    if not field_key:
        return SHOW_CARD
    _data(context).update(field_key=field_key, field_label=field_label)
    await update.message.reply_text(
        f"Введи новое значение для поля <b>{field_label}</b>\n"
        f"(или <code>-</code> чтобы очистить):",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )
    return EDIT_FIELD


async def _show_schedule_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    student_id = _data(context)["student_id"]
    student = await _load_by_id(student_id)
    if student is None:
        await update.message.reply_text("Ученик не найден.")
        return ConversationHandler.END
    return await _render_schedule(update, context, student)


async def _ask_delete_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    student_id = _data(context)["student_id"]
    student = await _load_by_id(student_id)
    if student is None:
        await update.message.reply_text("Ученик не найден.")
        return ConversationHandler.END
    await update.message.reply_text(
        _fmt_confirm_delete(student),
        parse_mode="HTML",
        reply_markup=confirm_delete_keyboard(),
    )
    return CONFIRM_DELETE


async def _back_to_list_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    return await _render_list(update, context)


# ---------------------------------------------------------------------------
# CONFIRM_DELETE state — обработчики кнопок (ReplyKeyboard)
# ---------------------------------------------------------------------------


async def _confirm_delete_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    student_id: int = _data(context)["student_id"]
    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyStudentRepository(session)
            await repo.delete(student_id)
    context.user_data.pop(_KEY, None)
    return await _render_list(update, context)


async def _cancel_delete_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    student_id: int = _data(context)["student_id"]
    student = await _load_by_id(student_id)
    if student is None:
        await update.message.reply_text("Ученик не найден.")
        return ConversationHandler.END
    return await _render_card(update, context, student)


# ---------------------------------------------------------------------------
# EDIT_FIELD state
# ---------------------------------------------------------------------------


async def _save_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    new_value: str | None = None if text == "-" else text

    d = _data(context)
    student_id: int = d["student_id"]
    field_key: str = d["field_key"]
    tutor_id = update.effective_chat.id

    try:
        async with async_session_factory() as session:
            async with session.begin():
                repo = SqlAlchemyStudentRepository(session)
                if field_key == "name" and new_value:
                    existing = await repo.get_by_name(tutor_id, new_value)
                    if existing is not None and existing.id != student_id:
                        await update.message.reply_text(
                            f"Имя <b>{new_value}</b> уже занято. Введи другое:",
                            parse_mode="HTML",
                        )
                        return EDIT_FIELD
                student = await repo.update(student_id, **{field_key: new_value})
    except Exception:
        await update.message.reply_text("Ошибка при сохранении. Попробуй ещё раз.")
        return EDIT_FIELD

    await update.message.reply_text(
        _fmt_card(student), reply_markup=_card_keyboard(), parse_mode="HTML"
    )
    return SHOW_CARD


# ---------------------------------------------------------------------------
# SCHEDULE_VIEW state — команды в тексте
# ---------------------------------------------------------------------------


async def _start_edit_slot_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    m = re.match(r"^/se_(\d+)", update.message.text)
    slot_id = int(m.group(1))  # type: ignore[union-attr]
    _data(context)["slot_id"] = slot_id
    await update.message.reply_text(
        "Введи новое время занятия:\n"
        "<code>ПН 14:30</code> или <code>ПН 14:30 90</code>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )
    return EDIT_SLOT


async def _delete_slot_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    m = re.match(r"^/sd_(\d+)", update.message.text)
    slot_id = int(m.group(1))  # type: ignore[union-attr]
    student_id: int = _data(context)["student_id"]

    student = await _load_by_id(student_id)
    if student is None:
        await update.message.reply_text("Ученик не найден.")
        return ConversationHandler.END

    new_slots = [s for s in student.slots if s.id != slot_id]

    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyStudentRepository(session)
            await repo.replace_slots(student_id, new_slots)
            updated = await repo.get_by_id(student_id)

    return await _render_schedule(update, context, updated)  # type: ignore[arg-type]


async def _start_add_slot_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Введи новое занятие:\n"
        "<code>ПН 14:30</code> или <code>ПН 14:30 90</code>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ADD_SLOT


async def _back_to_card_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    student_id: int = _data(context)["student_id"]
    student = await _load_by_id(student_id)
    if student is None:
        await update.message.reply_text("Ученик не найден.")
        return ConversationHandler.END
    return await _render_card(update, context, student)


# ---------------------------------------------------------------------------
# EDIT_SLOT state
# ---------------------------------------------------------------------------


async def _save_slot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    parsed = parse_slot(update.message.text)
    if parsed is None:
        await update.message.reply_text(SCHEDULE_SLOT_FORMAT_ERROR, parse_mode="HTML")
        return EDIT_SLOT

    d = _data(context)
    student_id: int = d["student_id"]
    slot_id: int = d["slot_id"]
    tutor_id = update.effective_chat.id
    new_day, new_time, new_dur = parsed

    student = await _load_by_id(student_id)
    if student is None:
        await update.message.reply_text("Ученик не найден.")
        return ConversationHandler.END

    new_slots = [
        SlotData(
            day_of_week=new_day,
            time_start=new_time,
            duration_minutes=new_dur,
            student_id=student_id,
        )
        if s.id == slot_id
        else s
        for s in student.slots
    ]

    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyStudentRepository(session)
            all_slots = await repo.get_all_slots(tutor_id)

    raw = [(s.day_of_week, s.time_start, s.duration_minutes) for s in new_slots]
    conflicts = check_conflicts(raw, all_slots, exclude_student_id=student_id)
    if conflicts:
        from tutor_assistant.interfaces.shared.formatters import format_conflicts

        await update.message.reply_text(
            SCHEDULE_CONFLICT_ERROR.format(conflicts=format_conflicts(conflicts)),
            parse_mode="HTML",
        )
        return EDIT_SLOT

    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyStudentRepository(session)
            await repo.replace_slots(student_id, new_slots)
            updated = await repo.get_by_id(student_id)

    return await _render_schedule(update, context, updated)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# ADD_SLOT state
# ---------------------------------------------------------------------------


async def _add_slot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    parsed = parse_slot(update.message.text)
    if parsed is None:
        await update.message.reply_text(SCHEDULE_SLOT_FORMAT_ERROR, parse_mode="HTML")
        return ADD_SLOT

    d = _data(context)
    student_id: int = d["student_id"]
    tutor_id = update.effective_chat.id
    new_day, new_time, new_dur = parsed

    student = await _load_by_id(student_id)
    if student is None:
        await update.message.reply_text("Ученик не найден.")
        return ConversationHandler.END

    new_slot = SlotData(
        day_of_week=new_day,
        time_start=new_time,
        duration_minutes=new_dur,
        student_id=student_id,
    )
    new_slots = list(student.slots) + [new_slot]

    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyStudentRepository(session)
            all_slots = await repo.get_all_slots(tutor_id)

    raw = [(s.day_of_week, s.time_start, s.duration_minutes) for s in new_slots]
    conflicts = check_conflicts(raw, all_slots, exclude_student_id=student_id)
    if conflicts:
        from tutor_assistant.interfaces.shared.formatters import format_conflicts

        await update.message.reply_text(
            SCHEDULE_CONFLICT_ERROR.format(conflicts=format_conflicts(conflicts)),
            parse_mode="HTML",
        )
        return ADD_SLOT

    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyStudentRepository(session)
            await repo.replace_slots(student_id, new_slots)
            updated = await repo.get_by_id(student_id)

    return await _render_schedule(update, context, updated)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Fallback
# ---------------------------------------------------------------------------


async def _cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop(_KEY, None)
    await update.message.reply_text(ACTION_CANCELLED, reply_markup=main_menu_keyboard())
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Build handler
# ---------------------------------------------------------------------------


def build_handler() -> ConversationHandler:
    _field_labels = list(_FIELD_LABELS.keys())
    return ConversationHandler(
        entry_points=[
            CommandHandler("list_students", _show_list),
            CommandHandler("change_student", _change_student_cmd),
            MessageHandler(filters.Text(["Мои ученики"]), _show_list),
        ],
        states={
            SHOW_LIST: [
                MessageHandler(filters.Regex(r"^/s_\d+") & filters.COMMAND, _show_card_cmd),
            ],
            SHOW_CARD: [
                MessageHandler(filters.Text(_field_labels), _start_edit_field_text),
                MessageHandler(filters.Text(["Расписание"]), _show_schedule_text),
                MessageHandler(filters.Text(["Удалить"]), _ask_delete_text),
                MessageHandler(filters.Text(["← Список"]), _back_to_list_text),
            ],
            CONFIRM_DELETE: [
                MessageHandler(filters.Text([BTN_DELETE_YES]), _confirm_delete_text),
                MessageHandler(filters.Text([BTN_DELETE_NO]), _cancel_delete_text),
            ],
            EDIT_FIELD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, _save_field),
            ],
            SCHEDULE_VIEW: [
                MessageHandler(filters.Regex(r"^/se_\d+$") & filters.COMMAND, _start_edit_slot_cmd),
                MessageHandler(filters.Regex(r"^/sd_\d+$") & filters.COMMAND, _delete_slot_cmd),
                CommandHandler("sadd", _start_add_slot_cmd),
                CommandHandler("sback", _back_to_card_cmd),
            ],
            EDIT_SLOT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, _save_slot),
            ],
            ADD_SLOT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, _add_slot),
            ],
        },
        fallbacks=[CommandHandler("cancel", _cancel)],
        name="student_editor",
        persistent=False,
        allow_reentry=True,
    )
