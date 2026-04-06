"""Domain entities — pure dataclasses, no external dependencies."""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field


@dataclass
class SlotData:
    day_of_week: int  # 0=Пн … 6=Вс
    time_start: datetime.time
    duration_minutes: int = 60
    id: int | None = None
    student_id: int | None = None
    student_name: str | None = None  # used in conflict messages


@dataclass
class StudentData:
    name: str
    tutor_chat_id: int
    id: int | None = None
    phone: str | None = None
    full_name: str | None = None
    comment: str | None = None
    telegram_link: str | None = None
    slots: list[SlotData] = field(default_factory=list)
    created_at: datetime.datetime | None = None


@dataclass
class ChatSettingsData:
    chat_id: int
    daily_reminder_enabled: bool = False
    daily_reminder_time: datetime.time | None = None
    pre_class_reminder_enabled: bool = False
    pre_class_reminder_minutes: int | None = None
