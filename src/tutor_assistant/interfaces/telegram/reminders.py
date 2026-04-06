"""Reminder scheduling: morning daily recap and pre-class notifications."""

from __future__ import annotations

import datetime
import os

import redis.asyncio as aioredis
from telegram.ext import ContextTypes, JobQueue

from tutor_assistant.application.use_cases.schedule import get_today_schedule
from tutor_assistant.infrastructure.database.engine import async_session_factory
from tutor_assistant.infrastructure.database.repository import (
    SqlAlchemyChatSettingsRepository,
    SqlAlchemyStudentRepository,
)
from tutor_assistant.interfaces.shared.formatters import format_today_schedule
from tutor_assistant.interfaces.shared.messages import (
    MORNING_REMINDER_EMPTY,
    MORNING_REMINDER_HEADER,
    PRE_CLASS_COMMENT_LINE,
    PRE_CLASS_REMINDER,
)
from tutor_assistant.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

_redis_client: aioredis.Redis | None = None
_PRECLASS_JOB_NAME = "preclass_global"
_PRECLASS_TTL_SECONDS = 25 * 3600  # 25h — expires before next day's occurrence


def _get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        _redis_client = aioredis.from_url(url, decode_responses=True)
    return _redis_client


def _morning_job_name(chat_id: int) -> str:
    return f"morning:{chat_id}"


def _preclass_redis_key(chat_id: int, slot_id: int | None, occurrence_date: datetime.date) -> str:
    return f"preclass:sent:{chat_id}:{slot_id}:{occurrence_date.isoformat()}"


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

async def morning_reminder_callback(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fires once daily at the configured time. context.job.data = chat_id."""
    chat_id: int = context.job.data  # type: ignore[assignment]
    try:
        async with async_session_factory() as session:
            async with session.begin():
                repo = SqlAlchemyStudentRepository(session)
                slots = await get_today_schedule(repo, chat_id)

        today = datetime.date.today()
        if not slots:
            await context.bot.send_message(chat_id=chat_id, text=MORNING_REMINDER_EMPTY)
        else:
            header = MORNING_REMINDER_HEADER.format(date=today.strftime("%d.%m.%Y"))
            body = format_today_schedule(slots)
            await context.bot.send_message(
                chat_id=chat_id, text=header + body, parse_mode="HTML"
            )
    except Exception:
        logger.exception("Morning reminder failed for chat_id=%s", chat_id)


async def preclass_checker_callback(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Global 60s tick: sends pre-class reminders for all configured chats."""
    now = datetime.datetime.now()
    today = now.date()
    redis = _get_redis()

    try:
        async with async_session_factory() as session:
            async with session.begin():
                settings_repo = SqlAlchemyChatSettingsRepository(session)
                all_settings = await settings_repo.list_all()
    except Exception:
        logger.exception("preclass_checker: failed to load settings")
        return

    for settings in all_settings:
        if not settings.pre_class_reminder_enabled or not settings.pre_class_reminder_minutes:
            continue

        target_dt = now + datetime.timedelta(minutes=settings.pre_class_reminder_minutes)

        try:
            async with async_session_factory() as session:
                async with session.begin():
                    slot_repo = SqlAlchemyStudentRepository(session)
                    today_slots = await get_today_schedule(slot_repo, settings.chat_id, today)
        except Exception:
            logger.exception(
                "preclass_checker: failed to load slots for chat_id=%s", settings.chat_id
            )
            continue

        for scheduled in today_slots:
            slot_dt = scheduled.datetime_start
            # Fire only within a ±30s window of the target time
            if abs((slot_dt - target_dt).total_seconds()) > 30:
                continue

            redis_key = _preclass_redis_key(settings.chat_id, scheduled.slot.id, today)
            try:
                already_sent = await redis.exists(redis_key)
            except Exception:
                logger.exception("preclass_checker: Redis check failed")
                continue
            if already_sent:
                continue

            # Fetch student comment
            comment_line = ""
            if scheduled.slot.student_name:
                try:
                    async with async_session_factory() as session:
                        async with session.begin():
                            student_repo = SqlAlchemyStudentRepository(session)
                            student = await student_repo.get_by_name(
                                settings.chat_id, scheduled.slot.student_name
                            )
                    if student and student.comment:
                        comment_line = PRE_CLASS_COMMENT_LINE.format(comment=student.comment)
                except Exception:
                    logger.exception("preclass_checker: failed to fetch student comment")

            text = PRE_CLASS_REMINDER.format(
                minutes=settings.pre_class_reminder_minutes,
                student_name=scheduled.slot.student_name or "Ученик",
                time=scheduled.slot.time_start.strftime("%H:%M"),
                comment_line=comment_line,
            )

            # Mark as sent BEFORE sending — delete key on send failure to allow retry
            try:
                await redis.setex(redis_key, _PRECLASS_TTL_SECONDS, "1")
            except Exception:
                logger.exception("preclass_checker: Redis setex failed")
                continue

            try:
                await context.bot.send_message(
                    chat_id=settings.chat_id, text=text, parse_mode="HTML"
                )
            except Exception:
                logger.exception(
                    "preclass_checker: send_message failed for chat_id=%s", settings.chat_id
                )
                # Roll back the mark so the next tick retries
                try:
                    await redis.delete(redis_key)
                except Exception:
                    pass


# ---------------------------------------------------------------------------
# Job management
# ---------------------------------------------------------------------------

def schedule_morning_reminder(
    job_queue: JobQueue,
    chat_id: int,
    reminder_time: datetime.time,
) -> None:
    """Cancel any existing morning job for this chat and create a new one."""
    cancel_morning_reminder(job_queue, chat_id)
    job_queue.run_daily(
        morning_reminder_callback,
        time=reminder_time,
        name=_morning_job_name(chat_id),
        data=chat_id,
    )


def cancel_morning_reminder(job_queue: JobQueue, chat_id: int) -> None:
    """Cancel the morning reminder job for a chat if it exists."""
    for job in job_queue.get_jobs_by_name(_morning_job_name(chat_id)):
        job.schedule_removal()


def schedule_preclass_global_job(job_queue: JobQueue) -> None:
    """Start the global pre-class check job (idempotent)."""
    if not job_queue.get_jobs_by_name(_PRECLASS_JOB_NAME):
        job_queue.run_repeating(
            preclass_checker_callback,
            interval=60,
            first=10,  # first fire 10s after startup
            name=_PRECLASS_JOB_NAME,
        )
