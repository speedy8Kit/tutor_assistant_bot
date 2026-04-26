"""In-memory repository implementations for unit tests."""

from __future__ import annotations

from tutor_assistant.domain.entities import ChatSettingsData, SlotData, StudentData


class InMemoryStudentRepository:
    """Simple dict-based repository implementing IStudentRepository protocol."""

    def __init__(self) -> None:
        self._students: dict[int, StudentData] = {}
        self._next_id = 1

    async def get_by_id(self, student_id: int) -> StudentData | None:
        return self._students.get(student_id)

    async def get_by_name(self, tutor_chat_id: int, name: str) -> StudentData | None:
        for s in self._students.values():
            if s.tutor_chat_id == tutor_chat_id and s.name == name:
                return s
        return None

    async def list_all(self, tutor_chat_id: int) -> list[StudentData]:
        return [s for s in self._students.values() if s.tutor_chat_id == tutor_chat_id]

    async def get_all_slots(self, tutor_chat_id: int) -> list[SlotData]:
        slots = []
        for s in self._students.values():
            if s.tutor_chat_id == tutor_chat_id:
                for slot in s.slots:
                    slots.append(
                        SlotData(
                            day_of_week=slot.day_of_week,
                            time_start=slot.time_start,
                            duration_minutes=slot.duration_minutes,
                            id=slot.id,
                            student_id=s.id,
                            student_name=s.name,
                        )
                    )
        return slots

    async def create(self, data: StudentData) -> StudentData:
        student_id = self._next_id
        self._next_id += 1
        slots = [
            SlotData(
                day_of_week=s.day_of_week,
                time_start=s.time_start,
                duration_minutes=s.duration_minutes,
                id=student_id * 100 + i,
                student_id=student_id,
                student_name=data.name,
            )
            for i, s in enumerate(data.slots)
        ]
        student = StudentData(
            id=student_id,
            name=data.name,
            tutor_chat_id=data.tutor_chat_id,
            phone=data.phone,
            full_name=data.full_name,
            comment=data.comment,
            telegram_link=data.telegram_link,
            slots=slots,
        )
        self._students[student_id] = student
        return student

    async def update(self, student_id: int, **fields: object) -> StudentData:
        s = self._students[student_id]
        updated = StudentData(
            id=s.id,
            name=str(fields.get("name", s.name)),
            tutor_chat_id=s.tutor_chat_id,
            phone=fields.get("phone", s.phone) if "phone" in fields else s.phone,  # type: ignore[assignment]
            full_name=fields.get("full_name", s.full_name)
            if "full_name" in fields
            else s.full_name,  # type: ignore[assignment]
            comment=fields.get("comment", s.comment)
            if "comment" in fields
            else s.comment,  # type: ignore[assignment]
            telegram_link=fields.get("telegram_link", s.telegram_link)
            if "telegram_link" in fields
            else s.telegram_link,  # type: ignore[assignment]
            slots=s.slots,
        )
        self._students[student_id] = updated
        return updated

    async def delete(self, student_id: int) -> None:
        self._students.pop(student_id, None)

    async def replace_slots(self, student_id: int, slots: list[SlotData]) -> None:
        s = self._students[student_id]
        new_slots = [
            SlotData(
                day_of_week=sl.day_of_week,
                time_start=sl.time_start,
                duration_minutes=sl.duration_minutes,
                id=student_id * 100 + i,
                student_id=student_id,
                student_name=s.name,
            )
            for i, sl in enumerate(slots)
        ]
        self._students[student_id] = StudentData(
            id=s.id,
            name=s.name,
            tutor_chat_id=s.tutor_chat_id,
            phone=s.phone,
            full_name=s.full_name,
            comment=s.comment,
            telegram_link=s.telegram_link,
            slots=new_slots,
        )


class InMemoryChatSettingsRepository:
    """Simple dict-based repository implementing IChatSettingsRepository protocol."""

    def __init__(self) -> None:
        self._data: dict[int, ChatSettingsData] = {}

    async def get(self, chat_id: int) -> ChatSettingsData | None:
        return self._data.get(chat_id)

    async def upsert(self, data: ChatSettingsData) -> ChatSettingsData:
        self._data[data.chat_id] = data
        return data

    async def list_all(self) -> list[ChatSettingsData]:
        return list(self._data.values())
