"""Use cases for student management."""

from __future__ import annotations

from tutor_assistant.application.ports import IStudentRepository
from tutor_assistant.domain.entities import SlotData, StudentData
from tutor_assistant.domain.exceptions import (
    StudentNameTaken,
    StudentNotFound,
    SlotConflict,
)
from tutor_assistant.domain.schedule import check_conflicts


async def create_student(
    repo: IStudentRepository,
    tutor_id: int,
    name: str,
    slots: list[SlotData],
    *,
    phone: str | None = None,
    full_name: str | None = None,
    comment: str | None = None,
    telegram_link: str | None = None,
) -> StudentData:
    """Create a new student for the tutor.

    Raises:
        StudentNameTaken: if this name already exists for the tutor.
        SlotConflict: if any slot overlaps with the tutor's existing schedule.
    """
    existing = await repo.get_by_name(tutor_id, name)
    if existing is not None:
        raise StudentNameTaken(name)

    if slots:
        all_slots = await repo.get_all_slots(tutor_id)
        raw = [(s.day_of_week, s.time_start, s.duration_minutes) for s in slots]
        conflicts = check_conflicts(raw, all_slots)
        if conflicts:
            raise SlotConflict(conflicts)

    return await repo.create(
        StudentData(
            name=name,
            tutor_chat_id=tutor_id,
            phone=phone,
            full_name=full_name,
            comment=comment,
            telegram_link=telegram_link,
            slots=slots,
        )
    )


async def get_student(
    repo: IStudentRepository, tutor_id: int, name: str
) -> StudentData:
    """Get a student by name.

    Raises:
        StudentNotFound: if not found.
    """
    student = await repo.get_by_name(tutor_id, name)
    if student is None:
        raise StudentNotFound(name)
    return student


async def list_students(repo: IStudentRepository, tutor_id: int) -> list[StudentData]:
    """Return all students for the tutor."""
    return await repo.list_all(tutor_id)


async def update_student(
    repo: IStudentRepository,
    tutor_id: int,
    student_name: str,
    **fields: object,
) -> StudentData:
    """Update scalar fields of a student.

    Raises:
        StudentNotFound: if student not found.
        StudentNameTaken: if the new name is already used by another student.
    """
    student = await repo.get_by_name(tutor_id, student_name)
    if student is None:
        raise StudentNotFound(student_name)

    new_name = fields.get("name")
    if new_name and new_name != student_name:
        conflict = await repo.get_by_name(tutor_id, str(new_name))
        if conflict is not None:
            raise StudentNameTaken(str(new_name))

    return await repo.update(student.id, **fields)


async def delete_student(
    repo: IStudentRepository, tutor_id: int, student_name: str
) -> None:
    """Delete a student by name.

    Raises:
        StudentNotFound: if student not found.
    """
    student = await repo.get_by_name(tutor_id, student_name)
    if student is None:
        raise StudentNotFound(student_name)
    await repo.delete(student.id)
