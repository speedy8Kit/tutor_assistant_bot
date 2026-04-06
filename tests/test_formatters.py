"""Tests for interfaces/shared/formatters.py"""

from __future__ import annotations

import datetime


from tutor_assistant.application.use_cases.schedule import ScheduledSlot
from tutor_assistant.domain.entities import SlotData, StudentData
from tutor_assistant.interfaces.shared.formatters import (
    format_conflicts,
    format_schedule,
    format_student_card,
    format_student_list,
    format_student_names_list,
    format_today_schedule,
    format_upcoming_schedule,
    html_strip,
)


def _make_student(name: str, slots=None, **kwargs) -> StudentData:
    return StudentData(
        id=1,
        name=name,
        tutor_chat_id=100,
        slots=slots or [],
        **kwargs,
    )


def _make_slot(day: int, hour: int, minute: int, dur: int = 60) -> SlotData:
    return SlotData(
        day_of_week=day,
        time_start=datetime.time(hour, minute),
        duration_minutes=dur,
        student_id=1,
    )


class TestHtmlStrip:
    def test_removes_tags(self):
        assert html_strip("<b>Bold</b>") == "Bold"
        assert html_strip("<code>code</code>") == "code"

    def test_plain_text_unchanged(self):
        assert html_strip("hello world") == "hello world"


class TestFormatStudentList:
    def test_empty(self):
        assert format_student_list([]) == ""

    def test_single_no_slots(self):
        s = _make_student("Иван")
        result = format_student_list([s])
        assert "Иван" in result
        assert "нет расписания" in result

    def test_with_slots(self):
        s = _make_student("Петр", slots=[_make_slot(0, 14, 30)])
        result = html_strip(format_student_list([s]))
        assert "Петр" in result
        assert "14:30" in result

    def test_numbered(self):
        students = [_make_student("А"), _make_student("Б")]
        result = format_student_list(students)
        assert "1." in result
        assert "2." in result


class TestFormatStudentCard:
    def test_name_present(self):
        s = _make_student("Вася")
        assert "Вася" in format_student_card(s)

    def test_optional_fields(self):
        s = _make_student("Вася", phone="123", full_name="Вася Иванов")
        result = html_strip(format_student_card(s))
        assert "123" in result
        assert "Вася Иванов" in result


class TestFormatSchedule:
    def test_empty(self):
        s = _make_student("X")
        assert "нет слотов" in format_schedule(s)

    def test_numbered_and_sorted(self):
        s = _make_student("X", slots=[_make_slot(2, 12, 0), _make_slot(0, 10, 0)])
        result = format_schedule(s)
        assert "1." in result
        assert "2." in result
        # Monday (0) should come before Wednesday (2)
        idx_mon = result.index("Пн")
        idx_wed = result.index("Ср")
        assert idx_mon < idx_wed


class TestFormatConflicts:
    def test_empty(self):
        assert format_conflicts([]) == ""

    def test_bullets(self):
        result = format_conflicts(["a", "b"])
        assert "• a" in result
        assert "• b" in result


class TestFormatStudentNamesList:
    def test_numbered(self):
        students = [_make_student("А"), _make_student("Б")]
        result = format_student_names_list(students)
        assert "1. А" in result
        assert "2. Б" in result


def _make_scheduled(
    student_name: str,
    day: int,
    hour: int,
    minute: int,
    date: datetime.date,
    dur: int = 60,
) -> ScheduledSlot:
    slot = SlotData(
        day_of_week=day,
        time_start=datetime.time(hour, minute),
        duration_minutes=dur,
        student_name=student_name,
    )
    return ScheduledSlot(
        slot=slot,
        date=date,
        datetime_start=datetime.datetime.combine(date, slot.time_start),
    )


_MON = datetime.date(2026, 4, 6)  # Monday
_WED = datetime.date(2026, 4, 8)  # Wednesday


class TestFormatTodaySchedule:
    def test_empty(self):
        assert format_today_schedule([]) == ""

    def test_single_entry(self):
        items = [_make_scheduled("Аня", 0, 10, 0, _MON)]
        result = html_strip(format_today_schedule(items))
        assert "1." in result
        assert "Аня" in result
        assert "10:00" in result
        assert "60 мин" in result

    def test_numbered(self):
        items = [
            _make_scheduled("Аня", 0, 9, 0, _MON),
            _make_scheduled("Боря", 0, 11, 0, _MON),
        ]
        result = format_today_schedule(items)
        assert "1." in result
        assert "2." in result

    def test_unknown_name_fallback(self):
        slot = SlotData(day_of_week=0, time_start=datetime.time(10, 0))
        item = ScheduledSlot(
            slot=slot, date=_MON, datetime_start=datetime.datetime(2026, 4, 6, 10)
        )
        result = html_strip(format_today_schedule([item]))
        assert "?" in result


class TestFormatUpcomingSchedule:
    def test_empty(self):
        assert format_upcoming_schedule([]) == ""

    def test_groups_by_date(self):
        items = [
            _make_scheduled("Аня", 0, 10, 0, _MON),
            _make_scheduled("Боря", 2, 11, 0, _WED),
        ]
        result = html_strip(format_upcoming_schedule(items))
        assert "Аня" in result
        assert "Боря" in result
        # Both dates should appear
        assert "06.04" in result
        assert "08.04" in result

    def test_day_name_in_header(self):
        items = [_make_scheduled("Аня", 0, 10, 0, _MON)]
        result = format_upcoming_schedule(items)
        assert "Пн" in result

    def test_no_trailing_blank_line(self):
        items = [_make_scheduled("Аня", 0, 10, 0, _MON)]
        result = format_upcoming_schedule(items)
        assert not result.endswith("\n")
