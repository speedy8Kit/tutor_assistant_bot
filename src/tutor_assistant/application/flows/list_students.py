"""Pure formatter for the student list (used by Telegram and CLI handlers)."""

from tutor_assistant.domain.schedule import DAY_NAMES
from tutor_assistant.infrastructure.database.models import Student

NO_STUDENTS = "У тебя пока нет учеников. Добавь первого: /add_student"


def format_students(students: list[Student]) -> str:
    if not students:
        return NO_STUDENTS

    lines: list[str] = []
    for s in students:
        if s.slots:
            slot_strs = [
                f"{DAY_NAMES[sl.day_of_week]} {sl.time_start:%H:%M}"
                for sl in sorted(
                    s.slots, key=lambda sl: (sl.day_of_week, sl.time_start)
                )
            ]
            schedule = ", ".join(slot_strs)
        else:
            schedule = "нет расписания"
        lines.append(f"• {s.name} — {schedule}")

    return "Ученики:\n" + "\n".join(lines)
