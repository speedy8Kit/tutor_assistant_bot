"""SQLAlchemy implementation of IStudentRepository."""

from __future__ import annotations


from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from tutor_assistant.domain.entities import ChatSettingsData, SlotData, StudentData
from tutor_assistant.infrastructure.database.models import ChatSettings, ScheduleSlot, Student


def _slot_to_data(slot: ScheduleSlot, student_name: str | None = None) -> SlotData:
    return SlotData(
        day_of_week=slot.day_of_week,
        time_start=slot.time_start,
        duration_minutes=slot.duration_minutes,
        id=slot.id,
        student_id=slot.student_id,
        student_name=student_name,
    )


def _student_to_data(student: Student) -> StudentData:
    return StudentData(
        id=student.id,
        name=student.name,
        tutor_chat_id=student.tutor_chat_id,
        phone=student.phone,
        full_name=student.full_name,
        comment=student.comment,
        telegram_link=student.telegram_link,
        created_at=student.created_at,
        slots=[_slot_to_data(s, student.name) for s in student.slots],
    )


class SqlAlchemyStudentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_name(self, tutor_chat_id: int, name: str) -> StudentData | None:
        result = await self._session.execute(
            select(Student)
            .where(Student.tutor_chat_id == tutor_chat_id, Student.name == name)
            .options(selectinload(Student.slots))
        )
        student = result.scalar_one_or_none()
        return _student_to_data(student) if student else None

    async def list_all(self, tutor_chat_id: int) -> list[StudentData]:
        result = await self._session.execute(
            select(Student)
            .where(Student.tutor_chat_id == tutor_chat_id)
            .options(selectinload(Student.slots))
            .order_by(Student.created_at)
        )
        return [_student_to_data(s) for s in result.scalars().all()]

    async def get_all_slots(self, tutor_chat_id: int) -> list[SlotData]:
        result = await self._session.execute(
            select(ScheduleSlot, Student.name)
            .join(Student, ScheduleSlot.student_id == Student.id)
            .where(Student.tutor_chat_id == tutor_chat_id)
        )
        return [_slot_to_data(slot, name) for slot, name in result.all()]

    async def create(self, data: StudentData) -> StudentData:
        student = Student(
            name=data.name,
            tutor_chat_id=data.tutor_chat_id,
            phone=data.phone,
            full_name=data.full_name,
            comment=data.comment,
            telegram_link=data.telegram_link,
        )
        self._session.add(student)
        await self._session.flush()

        slots = [
            ScheduleSlot(
                student_id=student.id,
                day_of_week=s.day_of_week,
                time_start=s.time_start,
                duration_minutes=s.duration_minutes,
            )
            for s in data.slots
        ]
        self._session.add_all(slots)
        await self._session.flush()

        # Refresh to populate slots relationship
        await self._session.refresh(student, ["slots"])
        return _student_to_data(student)

    async def update(self, student_id: int, **fields: object) -> StudentData:
        result = await self._session.execute(
            select(Student)
            .where(Student.id == student_id)
            .options(selectinload(Student.slots))
        )
        student = result.scalar_one()
        _ALLOWED = {"name", "phone", "full_name", "comment", "telegram_link"}
        for key, value in fields.items():
            if key in _ALLOWED:
                setattr(student, key, value)
        await self._session.flush()
        return _student_to_data(student)

    async def delete(self, student_id: int) -> None:
        await self._session.execute(delete(Student).where(Student.id == student_id))

    async def replace_slots(self, student_id: int, slots: list[SlotData]) -> None:
        await self._session.execute(
            delete(ScheduleSlot).where(ScheduleSlot.student_id == student_id)
        )
        new_slots = [
            ScheduleSlot(
                student_id=student_id,
                day_of_week=s.day_of_week,
                time_start=s.time_start,
                duration_minutes=s.duration_minutes,
            )
            for s in slots
        ]
        self._session.add_all(new_slots)
        await self._session.flush()


def _settings_to_data(row: ChatSettings) -> ChatSettingsData:
    return ChatSettingsData(
        chat_id=row.chat_id,
        daily_reminder_enabled=row.daily_reminder_enabled,
        daily_reminder_time=row.daily_reminder_time,
        pre_class_reminder_enabled=row.pre_class_reminder_enabled,
        pre_class_reminder_minutes=row.pre_class_reminder_minutes,
    )


class SqlAlchemyChatSettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, chat_id: int) -> ChatSettingsData | None:
        result = await self._session.execute(
            select(ChatSettings).where(ChatSettings.chat_id == chat_id)
        )
        row = result.scalar_one_or_none()
        return _settings_to_data(row) if row else None

    async def upsert(self, data: ChatSettingsData) -> ChatSettingsData:
        result = await self._session.execute(
            select(ChatSettings).where(ChatSettings.chat_id == data.chat_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = ChatSettings(chat_id=data.chat_id)
            self._session.add(row)
        row.daily_reminder_enabled = data.daily_reminder_enabled
        row.daily_reminder_time = data.daily_reminder_time
        row.pre_class_reminder_enabled = data.pre_class_reminder_enabled
        row.pre_class_reminder_minutes = data.pre_class_reminder_minutes
        await self._session.flush()
        return _settings_to_data(row)

    async def list_all(self) -> list[ChatSettingsData]:
        result = await self._session.execute(select(ChatSettings))
        return [_settings_to_data(r) for r in result.scalars().all()]
