"""Unit tests for /delete_student ConversationHandler."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import make_async_session
from tutor_assistant.interfaces.telegram.conversations.delete_student import (
    _KEY,
    _do_delete,
    _start,
)

_MOD = "tutor_assistant.interfaces.telegram.conversations.delete_student"


@pytest.mark.asyncio
class TestPickStudent:
    async def test_no_students_ends(self, make_update, make_context):
        update = make_update(chat_id=111)
        ctx = make_context(user_data={_KEY: {}})
        repo_mock = MagicMock()

        with patch(
            f"{_MOD}.async_session_factory", return_value=make_async_session(repo_mock)
        ), patch(f"{_MOD}.SqlAlchemyStudentRepository", return_value=repo_mock), patch(
            f"{_MOD}.list_students", new_callable=AsyncMock
        ) as mock_ls:
            mock_ls.return_value = []
            from telegram.ext import ConversationHandler

            state = await _start(update, ctx)

        assert state == ConversationHandler.END


@pytest.mark.asyncio
class TestDoDelete:
    async def test_deletes_student(self, make_update, make_context):
        update = make_update(chat_id=111)
        ctx = make_context(user_data={_KEY: {"student_name": "Иван"}})
        repo_mock = MagicMock()

        with patch(
            f"{_MOD}.async_session_factory", return_value=make_async_session(repo_mock)
        ), patch(f"{_MOD}.SqlAlchemyStudentRepository", return_value=repo_mock), patch(
            f"{_MOD}.delete_student", new_callable=AsyncMock
        ) as mock_del:
            mock_del.return_value = None
            from telegram.ext import ConversationHandler

            state = await _do_delete(update, ctx)

        assert state == ConversationHandler.END
        update.message.reply_text.assert_awaited_once()
        call_text = update.message.reply_text.call_args[0][0]
        assert "Иван" in call_text
