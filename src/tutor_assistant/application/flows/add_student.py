"""Pure state machine for the add-student conversation (used by CLI)."""

from __future__ import annotations

import datetime

from tutor_assistant.domain.schedule import DAY_NAMES, format_slots, parse_slot

MSG_ASK_NAME = "Введи имя ученика:"
NAME_EMPTY = "Имя не может быть пустым. Попробуй ещё раз:"
MSG_ASK_SLOTS = (
    "Теперь добавь расписание занятий. Отправляй каждый слот отдельным сообщением в формате:\n"
    "<code>ПН 14:30</code>\n\n"
    "Дни: ПН ВТ СР ЧТ ПТ СБ ВС\n\n"
    "Когда закончишь — отправь /done"
)
SLOT_FORMAT_ERROR = (
    "Не понял формат. Пример: <code>ПН 14:30</code>\nКогда закончишь — /done"
)
NO_SLOTS_YET = (
    "Ты ещё не добавил ни одного слота. Введи расписание или /cancel для отмены."
)
MSG_SLOT_ADDED = (
    "✅ Добавлено: {day} {t:%H:%M}\nВсего слотов: {len_slots}. Ещё или /done"
)
MSG_ASK_SAVE = (
    "Сохранить ученика?\n\n"
    "Имя: <b>{name}</b>\n"
    "Расписание:\n{schedule}\n\n"
    "/confirm — сохранить\n"
    "/cancel — отменить"
)
STUDENT_SAVED = (
    "✅ Ученик <b>{name}</b> сохранён!\n"
    "Занятий в неделю: {count}\n\n"
    "Смотри список: /list_students"
)


class AddStudentFlow:
    """Stateful wizard for the add-student flow (used by the CLI interface)."""

    def __init__(self, tutor_id: int) -> None:
        self.tutor_id = tutor_id
        self.name: str | None = None
        self.slots: list[tuple[int, datetime.time]] = []

    def start(self) -> str:
        return MSG_ASK_NAME

    def set_name(self, name: str) -> str:
        if not name:
            return NAME_EMPTY
        self.name = name
        return f"Ученик: <b>{name}</b>\n\n{MSG_ASK_SLOTS}"

    def add_slot(self, text: str) -> str:
        parsed = parse_slot(text)
        if parsed is None:
            return SLOT_FORMAT_ERROR
        self.slots.append(parsed)
        day, t = parsed
        return MSG_SLOT_ADDED.format(day=DAY_NAMES[day], t=t, len_slots=len(self.slots))

    def slots_done(self) -> str:
        if not self.slots:
            return NO_SLOTS_YET
        return MSG_ASK_SAVE.format(
            name=self.name,
            schedule=format_slots(self.slots),
        )
