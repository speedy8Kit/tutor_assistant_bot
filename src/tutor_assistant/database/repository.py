"""Data-access functions. Each accepts an AsyncSession; callers own the transaction."""

from __future__ import annotations

import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from tutor_assistant.database.models import ScheduleSlot, Student


async def add_student(session: AsyncSession, name: str, tutor_chat_id: int) -> Student:
    student = Student(name=name, tutor_chat_id=tutor_chat_id)
    session.add(student)
    await session.flush()  # populate student.id before adding slots
    return student


async def add_slots(
    session: AsyncSession,
    student_id: int,
    slots: list[tuple[int, datetime.time]],
) -> list[ScheduleSlot]:
    objects = [
        ScheduleSlot(student_id=student_id, day_of_week=day, time_start=t)
        for day, t in slots
    ]
    session.add_all(objects)
    return objects


async def list_students_with_slots(session: AsyncSession, tutor_chat_id: int) -> list[Student]:
    result = await session.execute(
        select(Student)
        .where(Student.tutor_chat_id == tutor_chat_id)
        .options(selectinload(Student.slots))
        .order_by(Student.created_at)
    )
    return list(result.scalars().all())
