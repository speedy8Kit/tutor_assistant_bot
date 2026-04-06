"""Tests for application/use_cases/ using InMemoryStudentRepository."""

from __future__ import annotations

import datetime

import pytest

from tests.helpers import InMemoryChatSettingsRepository, InMemoryStudentRepository
from tutor_assistant.application.use_cases.students import (
    create_student,
    delete_student,
    get_student,
    list_students,
    update_student,
)
from tutor_assistant.application.use_cases.schedule import (
    get_schedule,
    get_today_schedule,
    get_upcoming_schedule,
    update_schedule,
)
from tutor_assistant.application.use_cases.settings import (
    get_settings,
    set_daily_reminder,
    set_pre_class_reminder,
)
from tutor_assistant.domain.entities import ChatSettingsData, SlotData
from tutor_assistant.domain.exceptions import (
    SlotConflict,
    StudentNameTaken,
    StudentNotFound,
)

TUTOR = 42


def _slot(day: int, hour: int, minute: int, dur: int = 60) -> SlotData:
    return SlotData(
        day_of_week=day, time_start=datetime.time(hour, minute), duration_minutes=dur
    )


@pytest.mark.asyncio
class TestCreateStudent:
    async def test_creates_successfully(self):
        repo = InMemoryStudentRepository()
        student = await create_student(repo, TUTOR, "Иван", [])
        assert student.name == "Иван"
        assert student.id is not None

    async def test_raises_name_taken(self):
        repo = InMemoryStudentRepository()
        await create_student(repo, TUTOR, "Иван", [])
        with pytest.raises(StudentNameTaken):
            await create_student(repo, TUTOR, "Иван", [])

    async def test_different_tutors_same_name(self):
        repo = InMemoryStudentRepository()
        await create_student(repo, 1, "Иван", [])
        # Different tutor — should succeed
        student = await create_student(repo, 2, "Иван", [])
        assert student.name == "Иван"

    async def test_slot_conflict(self):
        repo = InMemoryStudentRepository()
        await create_student(repo, TUTOR, "Ваня", [_slot(0, 10, 0)])
        with pytest.raises(SlotConflict):
            await create_student(repo, TUTOR, "Петя", [_slot(0, 10, 30)])

    async def test_no_conflict_different_day(self):
        repo = InMemoryStudentRepository()
        await create_student(repo, TUTOR, "Ваня", [_slot(0, 10, 0)])
        student = await create_student(repo, TUTOR, "Петя", [_slot(1, 10, 0)])
        assert student.name == "Петя"

    async def test_optional_fields(self):
        repo = InMemoryStudentRepository()
        student = await create_student(
            repo, TUTOR, "Ваня", [], phone="123", full_name="Иван Иванов"
        )
        assert student.phone == "123"
        assert student.full_name == "Иван Иванов"


@pytest.mark.asyncio
class TestGetStudent:
    async def test_found(self):
        repo = InMemoryStudentRepository()
        await create_student(repo, TUTOR, "Иван", [])
        s = await get_student(repo, TUTOR, "Иван")
        assert s.name == "Иван"

    async def test_not_found(self):
        repo = InMemoryStudentRepository()
        with pytest.raises(StudentNotFound):
            await get_student(repo, TUTOR, "Несуществующий")


@pytest.mark.asyncio
class TestListStudents:
    async def test_empty(self):
        repo = InMemoryStudentRepository()
        assert await list_students(repo, TUTOR) == []

    async def test_lists_only_tutor_students(self):
        repo = InMemoryStudentRepository()
        await create_student(repo, TUTOR, "А", [])
        await create_student(repo, 999, "Б", [])
        result = await list_students(repo, TUTOR)
        assert len(result) == 1
        assert result[0].name == "А"


@pytest.mark.asyncio
class TestUpdateStudent:
    async def test_update_name(self):
        repo = InMemoryStudentRepository()
        await create_student(repo, TUTOR, "Иван", [])
        updated = await update_student(repo, TUTOR, "Иван", name="Петр")
        assert updated.name == "Петр"

    async def test_update_name_taken(self):
        repo = InMemoryStudentRepository()
        await create_student(repo, TUTOR, "Иван", [])
        await create_student(repo, TUTOR, "Петр", [])
        with pytest.raises(StudentNameTaken):
            await update_student(repo, TUTOR, "Иван", name="Петр")

    async def test_not_found(self):
        repo = InMemoryStudentRepository()
        with pytest.raises(StudentNotFound):
            await update_student(repo, TUTOR, "Несуществующий", phone="123")


@pytest.mark.asyncio
class TestDeleteStudent:
    async def test_delete(self):
        repo = InMemoryStudentRepository()
        await create_student(repo, TUTOR, "Иван", [])
        await delete_student(repo, TUTOR, "Иван")
        assert await list_students(repo, TUTOR) == []

    async def test_not_found(self):
        repo = InMemoryStudentRepository()
        with pytest.raises(StudentNotFound):
            await delete_student(repo, TUTOR, "Нет")


@pytest.mark.asyncio
class TestUpdateSchedule:
    async def test_replace_slots(self):
        repo = InMemoryStudentRepository()
        await create_student(repo, TUTOR, "Иван", [_slot(0, 10, 0)])
        updated = await update_schedule(repo, TUTOR, "Иван", [_slot(1, 14, 0)])
        assert len(updated.slots) == 1
        assert updated.slots[0].day_of_week == 1

    async def test_conflict_with_other_student(self):
        repo = InMemoryStudentRepository()
        await create_student(repo, TUTOR, "Ваня", [_slot(0, 10, 0)])
        await create_student(repo, TUTOR, "Петя", [_slot(2, 12, 0)])
        with pytest.raises(SlotConflict):
            await update_schedule(repo, TUTOR, "Петя", [_slot(0, 10, 30)])

    async def test_no_conflict_with_own_slots(self):
        """Replacing same slot should not conflict with itself."""
        repo = InMemoryStudentRepository()
        await create_student(repo, TUTOR, "Иван", [_slot(0, 10, 0)])
        # Replacing with same time — no conflict (exclude_student_id)
        updated = await update_schedule(repo, TUTOR, "Иван", [_slot(0, 10, 0)])
        assert len(updated.slots) == 1


# Monday 2026-04-06
_MONDAY = datetime.date(2026, 4, 6)
_WEDNESDAY = datetime.date(2026, 4, 8)


@pytest.mark.asyncio
class TestGetSchedule:
    async def test_found(self):
        repo = InMemoryStudentRepository()
        await create_student(repo, TUTOR, "Иван", [_slot(0, 10, 0)])
        student = await get_schedule(repo, TUTOR, "Иван")
        assert student.name == "Иван"

    async def test_not_found(self):
        repo = InMemoryStudentRepository()
        with pytest.raises(StudentNotFound):
            await get_schedule(repo, TUTOR, "Нет")


@pytest.mark.asyncio
class TestGetTodaySchedule:
    async def test_returns_only_todays_slots(self):
        repo = InMemoryStudentRepository()
        await create_student(repo, TUTOR, "Аня", [_slot(0, 10, 0)])  # Monday
        await create_student(repo, TUTOR, "Боря", [_slot(2, 11, 0)])  # Wednesday
        result = await get_today_schedule(repo, TUTOR, today=_MONDAY)
        assert len(result) == 1
        assert result[0].slot.student_name == "Аня"

    async def test_empty_when_no_classes(self):
        repo = InMemoryStudentRepository()
        result = await get_today_schedule(repo, TUTOR, today=_MONDAY)
        assert result == []

    async def test_sorted_by_time(self):
        repo = InMemoryStudentRepository()
        await create_student(repo, TUTOR, "Аня", [_slot(0, 14, 0)])
        await create_student(repo, TUTOR, "Боря", [_slot(0, 9, 0)])
        result = await get_today_schedule(repo, TUTOR, today=_MONDAY)
        assert result[0].slot.time_start < result[1].slot.time_start

    async def test_annotated_with_correct_date(self):
        repo = InMemoryStudentRepository()
        await create_student(repo, TUTOR, "Аня", [_slot(0, 10, 0)])
        result = await get_today_schedule(repo, TUTOR, today=_MONDAY)
        assert result[0].date == _MONDAY
        assert result[0].datetime_start.date() == _MONDAY


@pytest.mark.asyncio
class TestGetUpcomingSchedule:
    async def test_includes_today(self):
        repo = InMemoryStudentRepository()
        await create_student(repo, TUTOR, "Аня", [_slot(0, 10, 0)])  # Monday
        result = await get_upcoming_schedule(repo, TUTOR, today=_MONDAY)
        assert any(r.date == _MONDAY for r in result)

    async def test_includes_up_to_6_days_ahead(self):
        repo = InMemoryStudentRepository()
        # Sunday = weekday 6, which is today+6 from Monday
        await create_student(repo, TUTOR, "Аня", [_slot(6, 10, 0)])  # Sunday
        result = await get_upcoming_schedule(repo, TUTOR, today=_MONDAY)
        assert len(result) == 1
        assert result[0].date == _MONDAY + datetime.timedelta(days=6)

    async def test_excludes_day_7(self):
        repo = InMemoryStudentRepository()
        # Monday slot — appears once (today), not again next Monday (day 7)
        await create_student(repo, TUTOR, "Аня", [_slot(0, 10, 0)])
        result = await get_upcoming_schedule(repo, TUTOR, today=_MONDAY)
        dates = [r.date for r in result]
        assert _MONDAY + datetime.timedelta(days=7) not in dates
        assert len(result) == 1

    async def test_sorted_chronologically(self):
        repo = InMemoryStudentRepository()
        await create_student(repo, TUTOR, "Аня", [_slot(0, 14, 0), _slot(2, 9, 0)])
        result = await get_upcoming_schedule(repo, TUTOR, today=_MONDAY)
        for a, b in zip(result, result[1:]):
            assert a.datetime_start <= b.datetime_start

    async def test_empty(self):
        repo = InMemoryStudentRepository()
        assert await get_upcoming_schedule(repo, TUTOR, today=_MONDAY) == []


@pytest.mark.asyncio
class TestGetSettings:
    async def test_returns_defaults_when_missing(self):
        repo = InMemoryChatSettingsRepository()
        s = await get_settings(repo, 123)
        assert s.chat_id == 123
        assert s.daily_reminder_enabled is False
        assert s.pre_class_reminder_enabled is False
        assert s.daily_reminder_time is None
        assert s.pre_class_reminder_minutes is None

    async def test_returns_existing_settings(self):
        repo = InMemoryChatSettingsRepository()
        await repo.upsert(ChatSettingsData(chat_id=99, daily_reminder_enabled=True))
        s = await get_settings(repo, 99)
        assert s.daily_reminder_enabled is True


@pytest.mark.asyncio
class TestSetDailyReminder:
    async def test_enables_reminder(self):
        repo = InMemoryChatSettingsRepository()
        t = datetime.time(7, 0)
        s = await set_daily_reminder(repo, 123, t)
        assert s.daily_reminder_enabled is True
        assert s.daily_reminder_time == t

    async def test_disables_reminder(self):
        repo = InMemoryChatSettingsRepository()
        await set_daily_reminder(repo, 123, datetime.time(7, 0))
        s = await set_daily_reminder(repo, 123, None)
        assert s.daily_reminder_enabled is False
        assert s.daily_reminder_time is None

    async def test_persists_across_get(self):
        repo = InMemoryChatSettingsRepository()
        await set_daily_reminder(repo, 5, datetime.time(8, 30))
        s = await get_settings(repo, 5)
        assert s.daily_reminder_time == datetime.time(8, 30)


@pytest.mark.asyncio
class TestSetPreClassReminder:
    async def test_enables_reminder(self):
        repo = InMemoryChatSettingsRepository()
        s = await set_pre_class_reminder(repo, 123, 30)
        assert s.pre_class_reminder_enabled is True
        assert s.pre_class_reminder_minutes == 30

    async def test_disables_reminder(self):
        repo = InMemoryChatSettingsRepository()
        await set_pre_class_reminder(repo, 123, 30)
        s = await set_pre_class_reminder(repo, 123, None)
        assert s.pre_class_reminder_enabled is False
        assert s.pre_class_reminder_minutes is None
