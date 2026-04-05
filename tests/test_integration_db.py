"""Integration tests: real DB, real schema, real CRUD.

Run only when DATABASE_URL is available (skipped otherwise):
    docker exec tutor-bot pytest tests/test_integration_db.py -v
"""

from __future__ import annotations

import datetime
import os

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
async def _fresh_engine():
    """Give each test a fresh engine+pool to avoid event-loop/connection reuse across tests."""
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set — skipping integration tests")
    import tutor_assistant.infrastructure.database.engine as _eng

    # Dispose stale engine from previous test
    if _eng._engine is not None:
        await _eng._engine.dispose()
        _eng._engine = None
        _eng._session_maker = None
    from tutor_assistant.infrastructure.database.engine import init_db

    await init_db()
    yield
    # Dispose after test so the event loop can close cleanly
    if _eng._engine is not None:
        await _eng._engine.dispose()
        _eng._engine = None
        _eng._session_maker = None


@pytest.fixture
async def clean_tutor():
    """Provide an isolated tutor_id and clean up students after each test."""
    tutor_id = 777_999  # unlikely to collide with real data
    yield tutor_id
    # Teardown: delete all test students
    from tutor_assistant.infrastructure.database.engine import async_session_factory
    from tutor_assistant.infrastructure.database.models import Student
    from sqlalchemy import delete

    async with async_session_factory() as session:
        async with session.begin():
            await session.execute(
                delete(Student).where(Student.tutor_chat_id == tutor_id)
            )


class TestSchema:
    async def test_init_db_creates_students_table_with_name_column(self):
        """Catches schema drift: column 'name' must exist (not 'age' or anything else)."""
        from tutor_assistant.infrastructure.database.engine import async_session_factory
        from sqlalchemy import text

        async with async_session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'students' ORDER BY column_name"
                )
            )
            columns = {row[0] for row in result}
        assert (
            "name" in columns
        ), f"Column 'name' missing from students. Found: {columns}"
        assert "tutor_chat_id" in columns
        assert "created_at" in columns

    async def test_init_db_creates_schedule_slots_table(self):
        from tutor_assistant.infrastructure.database.engine import async_session_factory
        from sqlalchemy import text

        async with async_session_factory() as session:
            result = await session.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'schedule_slots' ORDER BY column_name"
                )
            )
            columns = {row[0] for row in result}
        assert "day_of_week" in columns
        assert "time_start" in columns
        assert "student_id" in columns


class TestStudentCRUD:
    async def test_create_and_list_student(self, clean_tutor):
        from tutor_assistant.application.services.students_service import (
            create_student,
            get_students,
        )

        slots = [(0, datetime.time(14, 30)), (2, datetime.time(16, 0))]
        await create_student("Интеграция Тест", clean_tutor, slots)

        students = await get_students(clean_tutor)

        assert len(students) == 1
        assert students[0].name == "Интеграция Тест"
        assert len(students[0].slots) == 2

    async def test_slots_saved_with_correct_day_and_time(self, clean_tutor):
        from tutor_assistant.application.services.students_service import (
            create_student,
            get_students,
        )

        await create_student("Слоты Тест", clean_tutor, [(4, datetime.time(18, 0))])

        students = await get_students(clean_tutor)
        slot = students[0].slots[0]

        assert slot.day_of_week == 4
        assert slot.time_start == datetime.time(18, 0)

    async def test_empty_tutor_returns_empty_list(self, clean_tutor):
        from tutor_assistant.application.services.students_service import get_students

        students = await get_students(clean_tutor)
        assert students == []

    async def test_multiple_students_all_returned(self, clean_tutor):
        from tutor_assistant.application.services.students_service import (
            create_student,
            get_students,
        )

        await create_student("Первый", clean_tutor, [(0, datetime.time(9, 0))])
        await create_student("Второй", clean_tutor, [(1, datetime.time(10, 0))])

        students = await get_students(clean_tutor)
        names = {s.name for s in students}

        assert names == {"Первый", "Второй"}
