"""Schedule domain logic: parsing, formatting, conflict detection."""

from __future__ import annotations

import datetime
import re
import unicodedata

from tutor_assistant.domain.entities import SlotData


_DAY_MAP: dict[str, int] = {
    "ПН": 0,
    "ВТ": 1,
    "СР": 2,
    "ЧТ": 3,
    "ПТ": 4,
    "СБ": 5,
    "ВС": 6,
}
DAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

_SLOT_RE = re.compile(
    r"^(ПН|ВТ|СР|ЧТ|ПТ|СБ|ВС)\s+(\d{1,2}):(\d{2})(?:\s+(\d+))?$",
    re.IGNORECASE,
)


def _clean(text: str) -> str:
    """Remove invisible Unicode characters and normalize whitespace.

    Also inserts a space between Cyrillic letters and digits so that an
    invisible character used as separator (e.g. zero-width space) doesn't
    collapse 'ПН10:00' into an unrecognized token.
    """
    visible = "".join(ch for ch in text if not unicodedata.category(ch).startswith("C"))
    normalized = " ".join(visible.split()).upper()
    return re.sub(r"([А-ЯЁ]+)(\d)", r"\1 \2", normalized)


def parse_slot(text: str) -> tuple[int, datetime.time, int] | None:
    """Parse a slot string into (day_of_week, time_start, duration_minutes).

    Accepted formats:
      "ПН 14:30"       -> (0, time(14, 30), 60)
      "ПН 14:30 90"    -> (0, time(14, 30), 90)

    Returns None if the format is invalid.
    """
    m = _SLOT_RE.match(_clean(text))
    if not m:
        return None
    day = _DAY_MAP[m.group(1)]
    hour, minute = int(m.group(2)), int(m.group(3))
    if hour > 23 or minute > 59:
        return None
    duration = int(m.group(4)) if m.group(4) else 60
    if duration <= 0 or duration > 480:
        return None
    return day, datetime.time(hour, minute), duration


def format_slots(slots: list[tuple[int, datetime.time, int]]) -> str:
    """Format a list of (day, time, duration) tuples into a human-readable string."""
    return "\n".join(f"  {DAY_NAMES[d]} {t:%H:%M} ({dur} мин)" for d, t, dur in slots)


def _slot_start_minutes(time_start: datetime.time) -> int:
    return time_start.hour * 60 + time_start.minute


def check_conflicts(
    new_slots: list[tuple[int, datetime.time, int]],
    existing: list[SlotData],
    exclude_student_id: int | None = None,
) -> list[str]:
    """Check for time overlaps within a single tutor's schedule.

    Only compares slots belonging to the same tutor -- callers must pass only
    that tutor's existing slots (filtered by tutor_chat_id).

    Args:
        new_slots: List of (day_of_week, time_start, duration_minutes) to validate.
        existing: Current SlotData objects from the repository (same tutor).
        exclude_student_id: Omit slots for this student (used when editing).

    Returns:
        List of human-readable conflict descriptions. Empty list = no conflicts.
    """
    filtered = [s for s in existing if s.student_id != exclude_student_id]
    conflicts: list[str] = []

    for i, (new_day, new_time, new_dur) in enumerate(new_slots):
        new_start = _slot_start_minutes(new_time)
        new_end = new_start + new_dur

        for j, (other_day, other_time, other_dur) in enumerate(new_slots):
            if j <= i:
                continue
            if other_day != new_day:
                continue
            other_start = _slot_start_minutes(other_time)
            other_end = other_start + other_dur
            if new_start < other_end and other_start < new_end:
                conflicts.append(
                    f"{DAY_NAMES[new_day]} {new_time:%H:%M} ({new_dur} мин) "
                    f"пересекается с {DAY_NAMES[other_day]} {other_time:%H:%M} ({other_dur} мин)"
                )

        for ex in filtered:
            if ex.day_of_week != new_day:
                continue
            ex_start = _slot_start_minutes(ex.time_start)
            ex_end = ex_start + ex.duration_minutes

            if new_start < ex_end and ex_start < new_end:
                who = ex.student_name or f"студент #{ex.student_id}"
                conflicts.append(
                    f"{DAY_NAMES[new_day]} {new_time:%H:%M} ({new_dur} мин) "
                    f"пересекается с занятием {who} "
                    f"в {ex.time_start:%H:%M} ({ex.duration_minutes} мин)"
                )

    return conflicts
