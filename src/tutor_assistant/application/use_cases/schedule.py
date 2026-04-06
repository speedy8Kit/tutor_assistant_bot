"""Use cases for schedule management."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from tutor_assistant.application.ports import IStudentRepository
from tutor_assistant.domain.entities import SlotData, StudentData
from tutor_assistant.domain.exceptions import SlotConflict, StudentNotFound
from tutor_assistant.domain.schedule import check_conflicts


@dataclass
class ScheduledSlot:
    """A SlotData annotated with its concrete occurrence date."""

    slot: SlotData
    date: datetime.date
    datetime_start: datetime.datetime


async def get_schedule(
    repo: IStudentRepository, tutor_id: int, student_name: str
) -> StudentData:
    """Return a student with their schedule.

    Raises:
        StudentNotFound: if not found.
    """
    student = await repo.get_by_name(tutor_id, student_name)
    if student is None:
        raise StudentNotFound(student_name)
    return student


async def update_schedule(
    repo: IStudentRepository,
    tutor_id: int,
    student_name: str,
    new_slots: list[SlotData],
) -> StudentData:
    """Replace all slots for a student after checking for conflicts.

    Conflicts are checked against all OTHER students of this tutor
    (the student's own old slots are excluded).

    Raises:
        StudentNotFound: if student not found.
        SlotConflict: if any new slot overlaps with another student's slot.
    """
    student = await repo.get_by_name(tutor_id, student_name)
    if student is None:
        raise StudentNotFound(student_name)

    all_slots = await repo.get_all_slots(tutor_id)
    raw = [(s.day_of_week, s.time_start, s.duration_minutes) for s in new_slots]
    conflicts = check_conflicts(raw, all_slots, exclude_student_id=student.id)
    if conflicts:
        raise SlotConflict(conflicts)

    await repo.replace_slots(student.id, new_slots)
    updated = await repo.get_by_name(tutor_id, student_name)
    return updated  # type: ignore[return-value]


async def get_today_schedule(
    repo: IStudentRepository,
    tutor_id: int,
    today: datetime.date | None = None,
) -> list[ScheduledSlot]:
    """Return all slots for today, sorted by time_start."""
    if today is None:
        today = datetime.date.today()
    weekday = today.weekday()  # 0=Mon..6=Sun, matches SlotData.day_of_week

    all_slots = await repo.get_all_slots(tutor_id)
    today_slots = sorted(
        [s for s in all_slots if s.day_of_week == weekday],
        key=lambda s: s.time_start,
    )
    return [
        ScheduledSlot(
            slot=s,
            date=today,
            datetime_start=datetime.datetime.combine(today, s.time_start),
        )
        for s in today_slots
    ]


async def get_upcoming_schedule(
    repo: IStudentRepository,
    tutor_id: int,
    today: datetime.date | None = None,
) -> list[ScheduledSlot]:
    """Return all slots for the next 7 days (today inclusive), sorted chronologically."""
    if today is None:
        today = datetime.date.today()

    all_slots = await repo.get_all_slots(tutor_id)
    result: list[ScheduledSlot] = []

    for offset in range(7):
        target_date = today + datetime.timedelta(days=offset)
        weekday = target_date.weekday()
        for s in all_slots:
            if s.day_of_week == weekday:
                result.append(
                    ScheduledSlot(
                        slot=s,
                        date=target_date,
                        datetime_start=datetime.datetime.combine(target_date, s.time_start),
                    )
                )

    result.sort(key=lambda x: x.datetime_start)
    return result
