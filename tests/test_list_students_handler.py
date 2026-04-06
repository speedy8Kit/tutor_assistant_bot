"""Tests for /list_students Telegram handler."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import make_async_session
from tutor_assistant.interfaces.telegram.handlers.common import cmd_list_students
from tutor_assistant.domain.entities import StudentData

_MOD = "tutor_assistant.interfaces.telegram.handlers.common"


def _make_student(name: str) -> StudentData:
    return StudentData(id=1, name=name, tutor_chat_id=111, slots=[])


@pytest.mark.asyncio
class TestListStudents:
    async def test_empty_list(self, make_update, make_context):
        update = make_update(chat_id=111)
        ctx = make_context()
        repo_mock = MagicMock()

        with patch(
            f"{_MOD}.async_session_factory", return_value=make_async_session(repo_mock)
        ), patch(f"{_MOD}.SqlAlchemyStudentRepository", return_value=repo_mock), patch(
            f"{_MOD}.list_students", new_callable=AsyncMock
        ) as mock_ls:
            mock_ls.return_value = []
            await cmd_list_students(update, ctx)

        update.message.reply_text.assert_awaited_once()
        call_args = update.message.reply_text.call_args[0][0]
        assert "add_student" in call_args or "нет" in call_args.lower()

    async def test_with_students(self, make_update, make_context):
        update = make_update(chat_id=111)
        ctx = make_context()
        repo_mock = MagicMock()
        students = [_make_student("Иван"), _make_student("Петр")]

        with patch(
            f"{_MOD}.async_session_factory", return_value=make_async_session(repo_mock)
        ), patch(f"{_MOD}.SqlAlchemyStudentRepository", return_value=repo_mock), patch(
            f"{_MOD}.list_students", new_callable=AsyncMock
        ) as mock_ls:
            mock_ls.return_value = students
            await cmd_list_students(update, ctx)

        update.message.reply_text.assert_awaited_once()
        call_args = update.message.reply_text.call_args[0][0]
        assert "Иван" in call_args
        assert "Петр" in call_args
