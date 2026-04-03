from tutor_assistant.infrastructure.database import add_slots, add_student, async_session_factory


async def add_students_bd(name: str, tutor_id: int, slots: list) -> None:
    async with async_session_factory() as session:
        async with session.begin():
            student = await add_student(session, name=name, tutor_chat_id=tutor_id)
            await add_slots(session, student_id=student.id, slots=slots)
