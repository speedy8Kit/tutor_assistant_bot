"""Terminal interface for testing bot logic without Telegram.

Both CLI and Telegram handlers call the same application/services/ layer.

Usage (inside container):
    python -m tutor_assistant cli --tutor-id 1
    python -m tutor_assistant cli --tutor-id 1 list-students
    python -m tutor_assistant cli --tutor-id 1 add-student
"""

from __future__ import annotations

import re

from tutor_assistant.application.services.students_service import (
    create_student,
    get_students,
)
from tutor_assistant.application.flows.add_student import AddStudentFlow, STUDENT_SAVED
from tutor_assistant.application.flows.list_students import format_students

_HELP = """\
Команды:
  list   — список учеников
  add    — добавить ученика
  help   — эта справка
  exit   — выйти"""


def html_print(html: str) -> None:
    print(">" * 30)
    print(re.sub(r"<.*?>", "", html))
    print("<" * 30)


async def cmd_add_student(tutor_id: int) -> None:
    flow = AddStudentFlow(tutor_id)
    html_print(flow.start())

    while not flow.name:
        name = input().strip()
        html_print(flow.set_name(name))

    while True:
        raw = input().strip()
        if not raw:
            break
        html_print(flow.add_slot(raw))

    html_print(flow.slots_done())
    if not flow.slots:
        return

    await create_student(flow.name, tutor_id, flow.slots)
    html_print(STUDENT_SAVED.format(name=flow.name, count=len(flow.slots)))


async def cmd_list_students(tutor_id: int) -> None:
    students = await get_students(tutor_id)
    html_print(format_students(students))
