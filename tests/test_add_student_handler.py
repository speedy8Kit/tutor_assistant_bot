"""Unit tests for /add_student Telegram ConversationHandler."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import make_async_session
from tutor_assistant.interfaces.telegram.conversations.add_student import (
    ASK_NAME,
    ASK_PHONE,
    ASK_SLOTS,
    CONFIRM,
    _KEY,
    _received_name,
    _received_phone,
    _received_slot,
    _slots_done,
    _start,
)

_MOD = "tutor_assistant.interfaces.telegram.conversations.add_student"


@pytest.mark.asyncio
class TestStart:
    async def test_clears_user_data(self, make_update, make_context):
        ctx = make_context(user_data={_KEY: {"junk": True}})
        await _start(make_update(), ctx)
        assert ctx.user_data.get(_KEY) == {}

    async def test_returns_ask_name(self, make_update, make_context):
        ctx = make_context()
        state = await _start(make_update(), ctx)
        assert state == ASK_NAME


@pytest.mark.asyncio
class TestReceivedName:
    async def test_empty_name_stays(self, make_update, make_context):
        ctx = make_context(user_data={_KEY: {}})
        state = await _received_name(make_update(text="  "), ctx)
        assert state == ASK_NAME

    async def test_name_taken(self, make_update, make_context):
        ctx = make_context(user_data={_KEY: {}})
        update = make_update(text="Иван", chat_id=123)
        fake_student = object()

        repo_mock = MagicMock()
        repo_mock.get_by_name = AsyncMock(return_value=fake_student)

        with patch(
            f"{_MOD}.async_session_factory", return_value=make_async_session(repo_mock)
        ), patch(f"{_MOD}.SqlAlchemyStudentRepository", return_value=repo_mock):
            state = await _received_name(update, ctx)

        assert state == ASK_NAME

    async def test_valid_name_advances(self, make_update, make_context):
        ctx = make_context(user_data={_KEY: {}})
        update = make_update(text="Иван", chat_id=123)

        repo_mock = MagicMock()
        repo_mock.get_by_name = AsyncMock(return_value=None)

        with patch(
            f"{_MOD}.async_session_factory", return_value=make_async_session(repo_mock)
        ), patch(f"{_MOD}.SqlAlchemyStudentRepository", return_value=repo_mock):
            state = await _received_name(update, ctx)

        assert state == ASK_PHONE
        assert ctx.user_data[_KEY]["name"] == "Иван"


@pytest.mark.asyncio
class TestReceivedPhone:
    async def test_skip(self, make_update, make_context):
        ctx = make_context(user_data={_KEY: {}})
        await _received_phone(make_update(text="/skip"), ctx)
        assert ctx.user_data[_KEY]["phone"] is None

    async def test_stores_phone(self, make_update, make_context):
        ctx = make_context(user_data={_KEY: {}})
        await _received_phone(make_update(text="+7999"), ctx)
        assert ctx.user_data[_KEY]["phone"] == "+7999"


@pytest.mark.asyncio
class TestReceivedSlot:
    async def test_invalid_format(self, make_update, make_context):
        ctx = make_context(user_data={_KEY: {"slots": []}})
        state = await _received_slot(make_update(text="bad input"), ctx)
        assert state == ASK_SLOTS
        assert ctx.user_data[_KEY]["slots"] == []

    async def test_valid_slot_appended(self, make_update, make_context):
        ctx = make_context(user_data={_KEY: {"slots": []}})
        state = await _received_slot(make_update(text="ПН 14:30"), ctx)
        assert state == ASK_SLOTS
        assert len(ctx.user_data[_KEY]["slots"]) == 1

    async def test_slot_with_duration(self, make_update, make_context):
        ctx = make_context(user_data={_KEY: {"slots": []}})
        await _received_slot(make_update(text="ВТ 10:00 90"), ctx)
        day, t, dur = ctx.user_data[_KEY]["slots"][0]
        assert dur == 90


@pytest.mark.asyncio
class TestSlotsDone:
    async def test_with_slots_shows_confirm(self, make_update, make_context):
        import datetime

        slots = [(0, datetime.time(14, 30), 60)]
        ctx = make_context(user_data={_KEY: {"name": "Иван", "slots": slots}})
        state = await _slots_done(make_update(), ctx)
        assert state == CONFIRM

    async def test_empty_slots_shows_confirm_no_slots(self, make_update, make_context):
        ctx = make_context(user_data={_KEY: {"name": "Иван", "slots": []}})
        state = await _slots_done(make_update(), ctx)
        assert state == CONFIRM
