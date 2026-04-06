"""Unit tests for /change_student ConversationHandler."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import make_async_session
from tutor_assistant.interfaces.telegram.conversations.change_student import (
    ASK_NEW_VALUE,
    PICK_FIELD,
    _KEY,
    _pick_field,
    _set_new_value,
)
from tutor_assistant.domain.entities import StudentData

_MOD = "tutor_assistant.interfaces.telegram.conversations.change_student"


def _student(name: str) -> StudentData:
    return StudentData(id=1, name=name, tutor_chat_id=111)


@pytest.mark.asyncio
class TestPickField:
    async def test_invalid_choice(self, make_update, make_context):
        ctx = make_context(user_data={_KEY: {"student_name": "Иван"}})
        state = await _pick_field(make_update(text="99"), ctx)
        assert state == PICK_FIELD

    async def test_valid_choice(self, make_update, make_context):
        ctx = make_context(user_data={_KEY: {"student_name": "Иван"}})
        state = await _pick_field(make_update(text="2"), ctx)
        assert state == ASK_NEW_VALUE
        assert ctx.user_data[_KEY]["field_key"] == "phone"


@pytest.mark.asyncio
class TestSetNewValue:
    async def test_clear_sets_none(self, make_update, make_context):
        ctx = make_context(
            user_data={
                _KEY: {
                    "student_name": "Иван",
                    "field_key": "phone",
                    "field_label": "Телефон",
                }
            }
        )
        update = make_update(text="/clear", chat_id=111)
        mock_student = _student("Иван")
        repo_mock = MagicMock()

        with patch(
            f"{_MOD}.async_session_factory", return_value=make_async_session(repo_mock)
        ), patch(f"{_MOD}.SqlAlchemyStudentRepository", return_value=repo_mock), patch(
            f"{_MOD}.update_student", new_callable=AsyncMock
        ) as mock_upd:
            mock_upd.return_value = mock_student
            from telegram.ext import ConversationHandler

            state = await _set_new_value(update, ctx)

        assert state == ConversationHandler.END
        call_kwargs = mock_upd.call_args[1]
        assert call_kwargs.get("phone") is None

    async def test_sets_value(self, make_update, make_context):
        ctx = make_context(
            user_data={
                _KEY: {
                    "student_name": "Иван",
                    "field_key": "phone",
                    "field_label": "Телефон",
                }
            }
        )
        update = make_update(text="+79991234567", chat_id=111)
        mock_student = _student("Иван")
        repo_mock = MagicMock()

        with patch(
            f"{_MOD}.async_session_factory", return_value=make_async_session(repo_mock)
        ), patch(f"{_MOD}.SqlAlchemyStudentRepository", return_value=repo_mock), patch(
            f"{_MOD}.update_student", new_callable=AsyncMock
        ) as mock_upd:
            mock_upd.return_value = mock_student
            from telegram.ext import ConversationHandler

            state = await _set_new_value(update, ctx)

        assert state == ConversationHandler.END
        call_kwargs = mock_upd.call_args[1]
        assert call_kwargs.get("phone") == "+79991234567"
