"""Integration tests — require a real PostgreSQL database via DATABASE_URL."""

from __future__ import annotations

import datetime
import os

import pytest
import pytest_asyncio
from sqlalchemy import delete

from tutor_assistant.domain.entities import SlotData, StudentData
from tutor_assistant.infrastructure.database import engine as _eng
from tutor_assistant.infrastructure.database.engine import (
    async_session_factory,
    init_db,
)
from tutor_assistant.infrastructure.database.models import Student
from tutor_assistant.infrastructure.database.repository import (
    SqlAlchemyStudentRepository,
)


@pytest_asyncio.fixture(autouse=True)
async def _fresh_engine():
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set — skipping integration tests")

    if _eng._engine is not None:
        await _eng._engine.dispose()
        _eng._engine = None
    if _eng._session_maker is not None:
        _eng._session_maker = None

    await init_db()
    yield

    if _eng._engine is not None:
        await _eng._engine.dispose()
        _eng._engine = None
    _eng._session_maker = None


@pytest_asyncio.fixture
async def clean_tutor():
    tutor_id = 777_999
    yield tutor_id
    async with async_session_factory() as session:
        async with session.begin():
            await session.execute(
                delete(Student).where(Student.tutor_chat_id == tutor_id)
            )


@pytest.mark.asyncio
async def test_create_and_list(clean_tutor):
    tutor_id = clean_tutor
    slot = SlotData(
        day_of_week=0, time_start=datetime.time(14, 30), duration_minutes=60
    )
    data = StudentData(name="Тест", tutor_chat_id=tutor_id, slots=[slot])

    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyStudentRepository(session)
            created = await repo.create(data)

    assert created.id is not None
    assert created.name == "Тест"
    assert len(created.slots) == 1
    assert created.slots[0].duration_minutes == 60

    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyStudentRepository(session)
            students = await repo.list_all(tutor_id)

    assert len(students) == 1
    assert students[0].name == "Тест"


@pytest.mark.asyncio
async def test_optional_fields_stored(clean_tutor):
    tutor_id = clean_tutor
    data = StudentData(
        name="Контакт",
        tutor_chat_id=tutor_id,
        phone="+7999",
        full_name="Иван Иванов",
        comment="VIP",
        telegram_link="@ivan",
    )

    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyStudentRepository(session)
            created = await repo.create(data)

    assert created.phone == "+7999"
    assert created.full_name == "Иван Иванов"
    assert created.comment == "VIP"
    assert created.telegram_link == "@ivan"


@pytest.mark.asyncio
async def test_get_by_name(clean_tutor):
    tutor_id = clean_tutor
    data = StudentData(name="Поиск", tutor_chat_id=tutor_id)

    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyStudentRepository(session)
            await repo.create(data)

    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyStudentRepository(session)
            found = await repo.get_by_name(tutor_id, "Поиск")
            not_found = await repo.get_by_name(tutor_id, "Нет")

    assert found is not None
    assert found.name == "Поиск"
    assert not_found is None


@pytest.mark.asyncio
async def test_update_student(clean_tutor):
    tutor_id = clean_tutor
    data = StudentData(name="Старое", tutor_chat_id=tutor_id)

    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyStudentRepository(session)
            created = await repo.create(data)
            updated = await repo.update(created.id, name="Новое", phone="+7000")

    assert updated.name == "Новое"
    assert updated.phone == "+7000"


@pytest.mark.asyncio
async def test_delete_student(clean_tutor):
    tutor_id = clean_tutor
    data = StudentData(name="Удалить", tutor_chat_id=tutor_id)

    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyStudentRepository(session)
            created = await repo.create(data)
            await repo.delete(created.id)
            students = await repo.list_all(tutor_id)

    assert students == []


@pytest.mark.asyncio
async def test_replace_slots(clean_tutor):
    tutor_id = clean_tutor
    old_slot = SlotData(
        day_of_week=0, time_start=datetime.time(10, 0), duration_minutes=60
    )
    data = StudentData(name="Расписание", tutor_chat_id=tutor_id, slots=[old_slot])

    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyStudentRepository(session)
            created = await repo.create(data)
            new_slot = SlotData(
                day_of_week=2, time_start=datetime.time(14, 0), duration_minutes=90
            )
            await repo.replace_slots(created.id, [new_slot])

    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyStudentRepository(session)
            student = await repo.get_by_name(tutor_id, "Расписание")

    assert student is not None
    assert len(student.slots) == 1
    assert student.slots[0].day_of_week == 2
    assert student.slots[0].duration_minutes == 90


@pytest.mark.asyncio
async def test_schema_has_new_columns(clean_tutor):
    """Verify all expected columns exist in the database schema."""
    tutor_id = clean_tutor
    data = StudentData(
        name="Схема",
        tutor_chat_id=tutor_id,
        phone="+7000",
        full_name="Тест Тестов",
        comment="тест",
        telegram_link="@test",
        slots=[
            SlotData(day_of_week=1, time_start=datetime.time(9, 0), duration_minutes=90)
        ],
    )

    async with async_session_factory() as session:
        async with session.begin():
            repo = SqlAlchemyStudentRepository(session)
            created = await repo.create(data)

    assert created.phone == "+7000"
    assert created.full_name == "Тест Тестов"
    assert created.comment == "тест"
    assert created.telegram_link == "@test"
    assert created.slots[0].duration_minutes == 90
