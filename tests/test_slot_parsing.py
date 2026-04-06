"""Tests for domain/schedule.py — parse_slot and check_conflicts."""

from __future__ import annotations

import datetime


from tutor_assistant.domain.schedule import parse_slot, check_conflicts
from tutor_assistant.domain.entities import SlotData


class TestParseSlot:
    def test_basic_slot(self):
        result = parse_slot("ПН 14:30")
        assert result == (0, datetime.time(14, 30), 60)

    def test_explicit_duration(self):
        result = parse_slot("ВТ 09:00 90")
        assert result == (1, datetime.time(9, 0), 90)

    def test_all_days(self):
        days = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
        for i, d in enumerate(days):
            result = parse_slot(f"{d} 10:00")
            assert result is not None
            assert result[0] == i

    def test_lowercase(self):
        result = parse_slot("пн 14:30")
        assert result is not None
        assert result[0] == 0

    def test_zero_width_space(self):
        result = parse_slot("ПН\u200b14:30")
        assert result is not None

    def test_invalid_format(self):
        assert parse_slot("Monday 14:30") is None
        assert parse_slot("") is None
        assert parse_slot("ПН 25:00") is None
        assert parse_slot("ПН 10:60") is None

    def test_pn_without_space_is_valid_via_clean(self):
        # _clean() inserts space between Cyrillic and digits — "ПН14:30" → "ПН 14:30"
        assert parse_slot("ПН14:30") is not None

    def test_invalid_duration_zero(self):
        assert parse_slot("ПН 10:00 0") is None

    def test_invalid_duration_too_large(self):
        assert parse_slot("ПН 10:00 500") is None

    def test_duration_boundary(self):
        assert parse_slot("ПН 10:00 480") is not None
        assert parse_slot("ПН 10:00 1") is not None


class TestCheckConflicts:
    def _slot(
        self, student_id: int, day: int, hour: int, minute: int, dur: int = 60
    ) -> SlotData:
        return SlotData(
            day_of_week=day,
            time_start=datetime.time(hour, minute),
            duration_minutes=dur,
            student_id=student_id,
            student_name=f"Ученик#{student_id}",
        )

    def test_no_conflicts(self):
        existing = [self._slot(1, 0, 10, 0, 60)]  # Пн 10:00-11:00
        new = [(0, datetime.time(11, 0), 60)]  # Пн 11:00-12:00 (back to back)
        assert check_conflicts(new, existing) == []

    def test_overlap_start(self):
        existing = [self._slot(1, 0, 10, 0, 60)]  # Пн 10:00-11:00
        new = [(0, datetime.time(10, 30), 60)]  # Пн 10:30-11:30
        assert len(check_conflicts(new, existing)) == 1

    def test_overlap_contained(self):
        existing = [self._slot(1, 0, 10, 0, 120)]  # Пн 10:00-12:00
        new = [(0, datetime.time(10, 30), 30)]  # Пн 10:30-11:00
        assert len(check_conflicts(new, existing)) == 1

    def test_different_day_no_conflict(self):
        existing = [self._slot(1, 0, 10, 0, 60)]  # Пн 10:00-11:00
        new = [(1, datetime.time(10, 0), 60)]  # Вт 10:00-11:00
        assert check_conflicts(new, existing) == []

    def test_exclude_student_id(self):
        existing = [self._slot(1, 0, 10, 0, 60)]  # Пн 10:00-11:00, student_id=1
        new = [(0, datetime.time(10, 0), 60)]  # Same slot
        # With exclusion — no conflict
        assert check_conflicts(new, existing, exclude_student_id=1) == []
        # Without exclusion — conflict
        assert len(check_conflicts(new, existing)) == 1

    def test_different_tutors_no_cross_check(self):
        # Caller is responsible for filtering by tutor_chat_id.
        # If existing only contains slots from one tutor, other tutors won't interfere.
        existing = [self._slot(1, 0, 10, 0, 60)]
        new = [(0, datetime.time(10, 0), 60)]
        # conflict detected because same slot passed in existing
        assert len(check_conflicts(new, existing)) == 1

    def test_self_conflict_in_new_slots(self):
        # Вт 14:50 (60 мин) → до 15:50, Вт 15:30 (60 мин) → пересечение
        new = [
            (1, datetime.time(14, 50), 60),
            (1, datetime.time(15, 30), 60),
        ]
        assert len(check_conflicts(new, [])) == 1

    def test_self_no_conflict_back_to_back(self):
        # Вт 14:00 (60 мин) и Вт 15:00 (60 мин) — вплотную, не пересекаются
        new = [
            (1, datetime.time(14, 0), 60),
            (1, datetime.time(15, 0), 60),
        ]
        assert check_conflicts(new, []) == []

    def test_self_conflict_different_days(self):
        # Один и тот же интервал, но разные дни — конфликта нет
        new = [
            (0, datetime.time(10, 0), 60),  # Пн
            (1, datetime.time(10, 0), 60),  # Вт
        ]
        assert check_conflicts(new, []) == []
