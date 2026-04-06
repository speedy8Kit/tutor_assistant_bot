"""Repository port — abstract interface for student persistence."""

from __future__ import annotations

from typing import Protocol

from tutor_assistant.domain.entities import ChatSettingsData, SlotData, StudentData


class IStudentRepository(Protocol):
    """Async repository interface for Student aggregate."""

    async def get_by_name(self, tutor_chat_id: int, name: str) -> StudentData | None:
        """Return student by name for the given tutor, or None."""
        ...

    async def list_all(self, tutor_chat_id: int) -> list[StudentData]:
        """Return all students for the given tutor, ordered by creation time."""
        ...

    async def get_all_slots(self, tutor_chat_id: int) -> list[SlotData]:
        """Return all schedule slots for the given tutor (across all students).

        SlotData.student_name is populated for use in conflict messages.
        """
        ...

    async def create(self, data: StudentData) -> StudentData:
        """Persist a new student with their slots. Returns the saved entity with id."""
        ...

    async def update(self, student_id: int, **fields: object) -> StudentData:
        """Update scalar fields of an existing student. Returns the updated entity."""
        ...

    async def delete(self, student_id: int) -> None:
        """Delete student and cascade-delete their slots."""
        ...

    async def replace_slots(self, student_id: int, slots: list[SlotData]) -> None:
        """Replace all slots for a student with the provided list."""
        ...


class IChatSettingsRepository(Protocol):
    """Async repository interface for per-chat settings."""

    async def get(self, chat_id: int) -> ChatSettingsData | None:
        """Return settings for a chat, or None if not found."""
        ...

    async def upsert(self, data: ChatSettingsData) -> ChatSettingsData:
        """Insert or update settings for a chat. Returns the saved entity."""
        ...

    async def list_all(self) -> list[ChatSettingsData]:
        """Return all chat settings rows."""
        ...
