import datetime

from tutor_assistant.infrastructure.database import (
    add_slots,
    add_student,
    async_session_factory,
    list_students_with_slots,
)
from tutor_assistant.infrastructure.database.models import Student


async def create_student(
    name: str, tutor_id: int, slots: list[tuple[int, datetime.time]]
) -> None:
    async with async_session_factory() as session:
        async with session.begin():
            student = await add_student(session, name=name, tutor_chat_id=tutor_id)
            await add_slots(session, student_id=student.id, slots=slots)


async def get_students(tutor_id: int) -> list[Student]:
    async with async_session_factory() as session:
        return await list_students_with_slots(session, tutor_chat_id=tutor_id)
