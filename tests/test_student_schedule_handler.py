"""Unit tests for /student_schedule ConversationHandler."""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import make_async_session
from tutor_assistant.interfaces.telegram.conversations.student_schedule import (
    ADD_SLOT,
    SHOW_MENU,
    _KEY,
    _cmd_add,
    _cmd_remove,
    _received_slot,
    _show_menu,
)
from tutor_assistant.domain.entities import SlotData, StudentData

_MOD = "tutor_assistant.interfaces.telegram.conversations.student_schedule"


def _slot(day: int, hour: int, dur: int = 60) -> SlotData:
    return SlotData(
        day_of_week=day,
        time_start=datetime.time(hour, 0),
        duration_minutes=dur,
        student_id=1,
        student_name="Иван",
    )


@pytest.mark.asyncio
class TestShowMenu:
    async def test_empty_slots(self, make_update, make_context):
        ctx = make_context(user_data={_KEY: {"student_name": "Иван", "slots": []}})
        update = make_update()
        state = await _show_menu(update, ctx)
        assert state == SHOW_MENU
        call_text = update.message.reply_text.call_args[0][0]
        assert "Иван" in call_text

    async def test_with_slots(self, make_update, make_context):
        ctx = make_context(
            user_data={
                _KEY: {
                    "student_name": "Иван",
                    "slots": [_slot(0, 10)],
                }
            }
        )
        update = make_update()
        state = await _show_menu(update, ctx)
        assert state == SHOW_MENU
        call_text = update.message.reply_text.call_args[0][0]
        assert "Иван" in call_text
        assert "10:00" in call_text


@pytest.mark.asyncio
class TestCmdAdd:
    async def test_transitions_to_add_slot(self, make_update, make_context):
        ctx = make_context(user_data={_KEY: {"student_name": "Иван", "slots": []}})
        state = await _cmd_add(make_update(), ctx)
        assert state == ADD_SLOT


@pytest.mark.asyncio
class TestCmdRemove:
    async def test_remove_valid(self, make_update, make_context):
        ctx = make_context(
            user_data={
                _KEY: {"student_name": "Иван", "slots": [_slot(0, 10), _slot(1, 11)]}
            },
            args=["1"],
        )
        update = make_update()
        state = await _cmd_remove(update, ctx)
        assert state == SHOW_MENU
        assert len(ctx.user_data[_KEY]["slots"]) == 1

    async def test_remove_bad_index(self, make_update, make_context):
        ctx = make_context(
            user_data={_KEY: {"student_name": "Иван", "slots": [_slot(0, 10)]}},
            args=["99"],
        )
        update = make_update()
        state = await _cmd_remove(update, ctx)
        assert state == SHOW_MENU
        assert len(ctx.user_data[_KEY]["slots"]) == 1


@pytest.mark.asyncio
class TestReceivedSlot:
    async def test_invalid_format(self, make_update, make_context):
        ctx = make_context(
            user_data={
                _KEY: {
                    "student_name": "Иван",
                    "slots": [],
                }
            }
        )
        state = await _received_slot(make_update(text="bad"), ctx)
        assert state == ADD_SLOT

    async def test_valid_slot_added(self, make_update, make_context):
        ctx = make_context(
            user_data={
                _KEY: {
                    "student_name": "Иван",
                    "slots": [],
                }
            }
        )
        update = make_update(text="ПН 14:30", chat_id=111)
        mock_student = StudentData(id=1, name="Иван", tutor_chat_id=111, slots=[])
        repo_mock = MagicMock()
        repo_mock.get_by_name = AsyncMock(return_value=mock_student)
        repo_mock.get_all_slots = AsyncMock(return_value=[])

        with patch(
            f"{_MOD}.async_session_factory", return_value=make_async_session(repo_mock)
        ), patch(f"{_MOD}.SqlAlchemyStudentRepository", return_value=repo_mock):
            state = await _received_slot(update, ctx)

        assert state == SHOW_MENU
        assert len(ctx.user_data[_KEY]["slots"]) == 1
