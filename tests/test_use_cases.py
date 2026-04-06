"""Tests for application/use_cases/ using InMemoryStudentRepository."""

from __future__ import annotations

import datetime

import pytest

from tests.helpers import InMemoryStudentRepository
from tutor_assistant.application.use_cases.students import (
    create_student,
    delete_student,
    get_student,
    list_students,
    update_student,
)
from tutor_assistant.application.use_cases.schedule import update_schedule
from tutor_assistant.domain.entities import SlotData
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
