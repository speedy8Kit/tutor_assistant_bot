"""CLI interactive REPL helpers for each flow."""

from __future__ import annotations

from tutor_assistant.application.ports import IStudentRepository
from tutor_assistant.application.use_cases.schedule import get_schedule, update_schedule
from tutor_assistant.application.use_cases.students import (
    create_student,
    delete_student,
    get_student,
    list_students,
    update_student,
)
from tutor_assistant.domain.entities import SlotData
from tutor_assistant.domain.exceptions import (
    SlotConflict,
    StudentNameTaken,
    StudentNotFound,
)
from tutor_assistant.domain.schedule import DAY_NAMES, parse_slot
from tutor_assistant.interfaces.shared.formatters import (
    format_conflicts,
    format_student_list,
    format_student_names_list,
    html_strip,
)
from tutor_assistant.interfaces.shared.messages import (
    ADD_ASK_COMMENT,
    ADD_ASK_NAME,
    ADD_ASK_PHONE,
    ADD_ASK_SLOTS,
    ADD_ASK_TELEGRAM,
    ADD_ASK_FULL_NAME,
    ADD_NAME_EMPTY,
    ADD_NAME_TAKEN,
    ADD_SAVED,
    ADD_SLOT_FORMAT_ERROR,
    ADD_CONFLICT_ERROR,
    ACTION_CANCELLED,
    CHANGE_PICK_FIELD,
    CHANGE_ASK_NEW_VALUE,
    CHANGE_SAVED,
    CHANGE_NAME_TAKEN,
    DELETE_CONFIRM,
    DELETE_DONE,
    DELETE_NOT_FOUND,
    LIST_EMPTY,
    LIST_HEADER,
    SCHEDULE_ADD_PROMPT,
    SCHEDULE_CONFLICT_ERROR,
    SCHEDULE_REMOVE_BAD_NUM,
    SCHEDULE_SAVED,
    SCHEDULE_SLOT_FORMAT_ERROR,
)


def _in(prompt: str) -> str:
    return input(html_strip(prompt) + " ").strip()


def _print(text: str) -> None:
    print(html_strip(text))


# ---------------------------------------------------------------------------
# add-student REPL
# ---------------------------------------------------------------------------
async def run_add_student(repo: IStudentRepository, tutor_id: int) -> None:
    _print(ADD_ASK_NAME)
    while True:
        name = input("> ").strip()
        if not name:
            _print(ADD_NAME_EMPTY)
            continue
        existing = await repo.get_by_name(tutor_id, name)
        if existing:
            _print(ADD_NAME_TAKEN.format(name=name))
            continue
        break

    def _optional(prompt: str) -> str | None:
        _print(prompt)
        val = input("> ").strip()
        return None if val in ("", "/skip") else val

    phone = _optional(ADD_ASK_PHONE)
    full_name = _optional(ADD_ASK_FULL_NAME)
    comment = _optional(ADD_ASK_COMMENT)
    telegram_link = _optional(ADD_ASK_TELEGRAM)

    _print(ADD_ASK_SLOTS)
    slots: list[SlotData] = []
    while True:
        raw = input("> ").strip()
        if raw == "/done":
            break
        if raw == "/cancel":
            _print(ACTION_CANCELLED)
            return
        parsed = parse_slot(raw)
        if parsed is None:
            _print(ADD_SLOT_FORMAT_ERROR)
            continue
        day, t, dur = parsed
        slots.append(SlotData(day_of_week=day, time_start=t, duration_minutes=dur))
        print(
            f"  Добавлен: {DAY_NAMES[day]} {t:%H:%M} ({dur} мин). Всего: {len(slots)}"
        )

    try:
        student = await create_student(
            repo,
            tutor_id,
            name,
            slots,
            phone=phone,
            full_name=full_name,
            comment=comment,
            telegram_link=telegram_link,
        )
    except SlotConflict as exc:
        _print(
            ADD_CONFLICT_ERROR.format(
                conflicts=html_strip(format_conflicts(exc.conflicts))
            )
        )
        return

    _print(ADD_SAVED.format(name=student.name, count=len(student.slots)))


# ---------------------------------------------------------------------------
# change-student REPL
# ---------------------------------------------------------------------------
_FIELDS = {
    "1": ("name", "Имя"),
    "2": ("phone", "Телефон"),
    "3": ("full_name", "ФИО"),
    "4": ("comment", "Комментарий"),
    "5": ("telegram_link", "Telegram"),
}


async def run_change_student(repo: IStudentRepository, tutor_id: int) -> None:
    students = await list_students(repo, tutor_id)
    if not students:
        _print(LIST_EMPTY)
        return

    _print(LIST_HEADER.format(count=len(students)) + format_student_list(students))
    name = input("Имя или номер: ").strip()
    if name.isdigit():
        idx = int(name) - 1
        if 0 <= idx < len(students):
            name = students[idx].name
        else:
            _print(DELETE_NOT_FOUND)
            return

    try:
        student = await get_student(repo, tutor_id, name)
    except StudentNotFound:
        _print(DELETE_NOT_FOUND)
        return

    _print(CHANGE_PICK_FIELD.format(name=student.name))
    choice = input("> ").strip()
    if choice not in _FIELDS:
        print("Нет такого пункта.")
        return

    field_key, _ = _FIELDS[choice]
    _print(CHANGE_ASK_NEW_VALUE)
    new_val_raw = input("> ").strip()
    new_value = None if new_val_raw == "/clear" else new_val_raw

    try:
        updated = await update_student(repo, tutor_id, name, **{field_key: new_value})
    except StudentNameTaken:
        _print(CHANGE_NAME_TAKEN.format(name=new_value))
        return

    _print(CHANGE_SAVED.format(name=updated.name))


# ---------------------------------------------------------------------------
# delete-student REPL
# ---------------------------------------------------------------------------
async def run_delete_student(repo: IStudentRepository, tutor_id: int) -> None:
    students = await list_students(repo, tutor_id)
    if not students:
        _print(LIST_EMPTY)
        return

    _print(LIST_HEADER.format(count=len(students)) + format_student_list(students))
    name = input("Имя или номер: ").strip()
    if name.isdigit():
        idx = int(name) - 1
        if 0 <= idx < len(students):
            name = students[idx].name
        else:
            _print(DELETE_NOT_FOUND)
            return

    try:
        student = await get_student(repo, tutor_id, name)
    except StudentNotFound:
        _print(DELETE_NOT_FOUND)
        return

    _print(DELETE_CONFIRM.format(name=student.name))
    confirm = input("> ").strip()
    if confirm != "/confirm_delete":
        _print(ACTION_CANCELLED)
        return

    await delete_student(repo, tutor_id, name)
    _print(DELETE_DONE.format(name=name))


# ---------------------------------------------------------------------------
# show-schedule REPL
# ---------------------------------------------------------------------------
async def run_show_schedule(repo: IStudentRepository, tutor_id: int) -> None:
    students = await list_students(repo, tutor_id)
    if not students:
        _print(LIST_EMPTY)
        return

    print(html_strip(format_student_names_list(students)))
    name = input("Имя или номер: ").strip()
    if name.isdigit():
        idx = int(name) - 1
        if 0 <= idx < len(students):
            name = students[idx].name

    try:
        student = await get_schedule(repo, tutor_id, name)
    except StudentNotFound:
        print("Ученик не найден.")
        return

    slots = list(student.slots)
    while True:
        _print_schedule(student.name, slots)
        cmd = input("> ").strip()
        if cmd == "/done":
            break
        if cmd == "/cancel":
            _print(ACTION_CANCELLED)
            return
        if cmd == "/add":
            _print(SCHEDULE_ADD_PROMPT)
            raw = input("> ").strip()
            parsed = parse_slot(raw)
            if parsed is None:
                _print(SCHEDULE_SLOT_FORMAT_ERROR)
                continue
            day, t, dur = parsed
            new_slot = SlotData(day_of_week=day, time_start=t, duration_minutes=dur)
            all_existing = await repo.get_all_slots(tutor_id)
            from tutor_assistant.domain.schedule import check_conflicts

            conflicts = check_conflicts(
                [(day, t, dur)], all_existing, exclude_student_id=student.id
            )
            if conflicts:
                _print(
                    SCHEDULE_CONFLICT_ERROR.format(
                        conflicts=format_conflicts(conflicts)
                    )
                )
                continue
            slots.append(new_slot)
        elif cmd.startswith("/remove "):
            parts = cmd.split()
            if len(parts) == 2 and parts[1].isdigit():
                idx = int(parts[1]) - 1
                sorted_slots = sorted(
                    slots, key=lambda s: (s.day_of_week, s.time_start)
                )
                if 0 <= idx < len(sorted_slots):
                    to_remove = sorted_slots[idx]
                    slots = [s for s in slots if s is not to_remove]
                else:
                    _print(SCHEDULE_REMOVE_BAD_NUM)
            else:
                _print(SCHEDULE_REMOVE_BAD_NUM)
        else:
            print("Команды: /add, /remove N, /done, /cancel")

    try:
        await update_schedule(repo, tutor_id, name, slots)
    except SlotConflict as exc:
        _print(
            SCHEDULE_CONFLICT_ERROR.format(conflicts=format_conflicts(exc.conflicts))
        )
        return

    _print(SCHEDULE_SAVED.format(name=name))


def _print_schedule(name: str, slots: list[SlotData]) -> None:
    sorted_slots = sorted(slots, key=lambda s: (s.day_of_week, s.time_start))
    print(f"\nРасписание {name}:")
    if not sorted_slots:
        print("  (нет слотов)")
    else:
        for i, s in enumerate(sorted_slots, 1):
            print(
                f"  {i}. {DAY_NAMES[s.day_of_week]} {s.time_start:%H:%M} ({s.duration_minutes} мин)"
            )
    print()


# ---------------------------------------------------------------------------
# Interactive REPL (no subcommand)
# ---------------------------------------------------------------------------
async def run_repl(repo: IStudentRepository, tutor_id: int) -> None:
    print(f"Tutor Assistant CLI (tutor_id={tutor_id})")
    print(
        "Команды: add-student, list-students, change-student, delete-student, show-schedule, exit\n"
    )

    while True:
        try:
            cmd = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nВыход.")
            break

        if cmd in ("exit", "quit"):
            break
        elif cmd == "add-student":
            await run_add_student(repo, tutor_id)
        elif cmd == "list-students":
            students = await list_students(repo, tutor_id)
            if not students:
                _print(LIST_EMPTY)
            else:
                _print(
                    LIST_HEADER.format(count=len(students))
                    + format_student_list(students)
                )
        elif cmd == "change-student":
            await run_change_student(repo, tutor_id)
        elif cmd == "delete-student":
            await run_delete_student(repo, tutor_id)
        elif cmd == "show-schedule":
            await run_show_schedule(repo, tutor_id)
        else:
            print(
                "Неизвестная команда. Доступны: add-student, list-students, change-student, delete-student, show-schedule, exit"
            )
