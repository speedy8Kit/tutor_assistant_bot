"""Use cases for chat settings management."""

from __future__ import annotations

import datetime

from tutor_assistant.application.ports import IChatSettingsRepository
from tutor_assistant.domain.entities import ChatSettingsData


async def get_settings(repo: IChatSettingsRepository, chat_id: int) -> ChatSettingsData:
    """Return settings for a chat, creating defaults if none exist."""
    settings = await repo.get(chat_id)
    if settings is None:
        settings = ChatSettingsData(chat_id=chat_id)
    return settings


async def set_daily_reminder(
    repo: IChatSettingsRepository,
    chat_id: int,
    reminder_time: datetime.time | None,
) -> ChatSettingsData:
    """Enable daily reminder at the given time, or disable if time is None."""
    settings = await get_settings(repo, chat_id)
    settings.daily_reminder_enabled = reminder_time is not None
    settings.daily_reminder_time = reminder_time
    return await repo.upsert(settings)


async def set_pre_class_reminder(
    repo: IChatSettingsRepository,
    chat_id: int,
    minutes_before: int | None,
) -> ChatSettingsData:
    """Enable pre-class reminder N minutes before class, or disable if None."""
    settings = await get_settings(repo, chat_id)
    settings.pre_class_reminder_enabled = minutes_before is not None
    settings.pre_class_reminder_minutes = minutes_before
    return await repo.upsert(settings)
