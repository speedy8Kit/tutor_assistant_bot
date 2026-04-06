"""Formatters — convert domain entities to human-readable strings.

Used by both Telegram and CLI. HTML tags are present; CLI must call html_strip().
"""

from __future__ import annotations

import re
from itertools import groupby

from tutor_assistant.application.use_cases.schedule import ScheduledSlot
from tutor_assistant.domain.entities import SlotData, StudentData
from tutor_assistant.domain.schedule import DAY_NAMES


def html_strip(text: str) -> str:
    """Remove HTML tags for plain-text (CLI) output."""
    return re.sub(r"<[^>]+>", "", text)


def _extra_fields(student: StudentData) -> str:
    """Build optional-fields block for student card."""
    lines: list[str] = []
    if student.full_name:
        lines.append(f"ФИО: {student.full_name}")
    if student.phone:
        lines.append(f"Телефон: {student.phone}")
    if student.telegram_link:
        lines.append(f"Telegram: {student.telegram_link}")
    if student.comment:
        lines.append(f"Комментарий: {student.comment}")
    return ("\n".join(lines) + "\n") if lines else ""


def format_slot(slot: SlotData) -> str:
    return f"{DAY_NAMES[slot.day_of_week]} {slot.time_start:%H:%M} ({slot.duration_minutes} мин)"


def format_schedule(student: StudentData) -> str:
    """Return numbered slot list for schedule editor."""
    if not student.slots:
        return "(нет слотов)"
    sorted_slots = sorted(student.slots, key=lambda s: (s.day_of_week, s.time_start))
    return "\n".join(f"{i}. {format_slot(s)}" for i, s in enumerate(sorted_slots, 1))


def format_student_card(student: StudentData) -> str:
    """Detailed card: name, optional fields, schedule."""
    extra = _extra_fields(student)
    schedule = format_schedule(student)
    return f"<b>{student.name}</b>\n" f"{extra}" f"Расписание:\n{schedule}"


def format_student_list(students: list[StudentData]) -> str:
    """Numbered list of students with compact schedule."""
    if not students:
        return ""
    parts: list[str] = []
    for i, s in enumerate(students, 1):
        sorted_slots = sorted(s.slots, key=lambda sl: (sl.day_of_week, sl.time_start))
        schedule = (
            ", ".join(
                f"{DAY_NAMES[sl.day_of_week]} {sl.time_start:%H:%M}"
                for sl in sorted_slots
            )
            if sorted_slots
            else "нет расписания"
        )
        parts.append(f"{i}. <b>{s.name}</b> — {schedule}")
    return "\n".join(parts)


def format_slots_data(slots: list[SlotData]) -> str:
    """Format a list of SlotData into human-readable lines."""
    sorted_slots = sorted(slots, key=lambda s: (s.day_of_week, s.time_start))
    return "\n".join(f"  {format_slot(s)}" for s in sorted_slots)


def format_conflicts(conflicts: list[str]) -> str:
    return "\n".join(f"• {c}" for c in conflicts)


def format_student_names_list(students: list[StudentData]) -> str:
    """Numbered list of just names — for pick-student prompts."""
    return "\n".join(f"{i}. {s.name}" for i, s in enumerate(students, 1))


def format_today_schedule(slots: list[ScheduledSlot]) -> str:
    """Numbered list of today's classes."""
    lines: list[str] = []
    for i, item in enumerate(slots, 1):
        name = item.slot.student_name or "?"
        lines.append(
            f"{i}. <b>{name}</b> — {item.slot.time_start:%H:%M} ({item.slot.duration_minutes} мин)"
        )
    return "\n".join(lines)


def format_upcoming_schedule(slots: list[ScheduledSlot]) -> str:
    """Multi-day schedule grouped by date."""
    if not slots:
        return ""
    lines: list[str] = []
    for date, group in groupby(slots, key=lambda x: x.date):
        day_name = DAY_NAMES[date.weekday()]
        lines.append(f"<b>{day_name} {date.strftime('%d.%m')}</b>")
        for item in group:
            name = item.slot.student_name or "?"
            lines.append(
                f"  {item.slot.time_start:%H:%M} {name} ({item.slot.duration_minutes} мин)"
            )
        lines.append("")
    return "\n".join(lines).rstrip()
