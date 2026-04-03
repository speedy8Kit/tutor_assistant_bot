"""Unit tests for the list_students handler."""

from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch

from tutor_assistant.application.handlers.list_students import list_students

_HANDLER_PATH = "tutor_assistant.application.handlers.list_students"


def _make_student(name: str, slots: list[tuple[int, datetime.time]]) -> MagicMock:
    student = MagicMock()
    student.name = name
    student.slots = [MagicMock(day_of_week=d, time_start=t) for d, t in slots]
    return student


class TestListStudents:
    async def test_no_students_sends_hint(
        self, make_update, make_context, mock_db_session
    ):
        update = make_update(chat_id=1)
        session_cm, _ = mock_db_session

        with (
            patch(f"{_HANDLER_PATH}.async_session_factory", session_cm),
            patch(f"{_HANDLER_PATH}.list_students_with_slots", return_value=[]),
        ):
            await list_students(update, make_context())

        reply = update.message.reply_text.call_args[0][0]
        assert "/add_student" in reply

    async def test_one_student_with_slots(
        self, make_update, make_context, mock_db_session
    ):
        update = make_update(chat_id=1)
        session_cm, _ = mock_db_session
        student = _make_student(
            "Иван", [(0, datetime.time(14, 30)), (2, datetime.time(16, 0))]
        )

        with (
            patch(f"{_HANDLER_PATH}.async_session_factory", session_cm),
            patch(f"{_HANDLER_PATH}.list_students_with_slots", return_value=[student]),
        ):
            await list_students(update, make_context())

        reply = update.message.reply_text.call_args[0][0]
        assert "Иван" in reply
        assert "Пн" in reply
        assert "14:30" in reply
        assert "Ср" in reply
        assert "16:00" in reply

    async def test_student_without_slots_shows_placeholder(
        self, make_update, make_context, mock_db_session
    ):
        update = make_update(chat_id=1)
        session_cm, _ = mock_db_session
        student = _make_student("Маша", [])

        with (
            patch(f"{_HANDLER_PATH}.async_session_factory", session_cm),
            patch(f"{_HANDLER_PATH}.list_students_with_slots", return_value=[student]),
        ):
            await list_students(update, make_context())

        reply = update.message.reply_text.call_args[0][0]
        assert "Маша" in reply
        assert "нет расписания" in reply

    async def test_multiple_students(self, make_update, make_context, mock_db_session):
        update = make_update(chat_id=1)
        session_cm, _ = mock_db_session
        students = [
            _make_student("Алёша", [(0, datetime.time(9, 0))]),
            _make_student("Саша", [(4, datetime.time(18, 30))]),
        ]

        with (
            patch(f"{_HANDLER_PATH}.async_session_factory", session_cm),
            patch(f"{_HANDLER_PATH}.list_students_with_slots", return_value=students),
        ):
            await list_students(update, make_context())

        reply = update.message.reply_text.call_args[0][0]
        assert "Алёша" in reply
        assert "Саша" in reply

    async def test_queries_by_correct_chat_id(
        self, make_update, make_context, mock_db_session
    ):
        update = make_update(chat_id=42)
        session_cm, mock_session = mock_db_session

        with (
            patch(f"{_HANDLER_PATH}.async_session_factory", session_cm),
            patch(
                f"{_HANDLER_PATH}.list_students_with_slots", return_value=[]
            ) as mock_query,
        ):
            await list_students(update, make_context())

        mock_query.assert_awaited_once_with(mock_session, tutor_chat_id=42)
