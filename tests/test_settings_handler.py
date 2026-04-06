"""Unit tests for /settings ConversationHandler."""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram.ext import ConversationHandler

from tests.conftest import make_async_session
from tutor_assistant.domain.entities import ChatSettingsData
from tutor_assistant.interfaces.telegram.conversations.settings import (
    SET_DAILY_TIME,
    SET_PRE_CLASS_MINUTES,
    SHOW_MENU,
    _pick_option,
    _set_daily_time,
    _set_pre_class_minutes,
    _show_settings_menu,
)

_MOD = "tutor_assistant.interfaces.telegram.conversations.settings"


def _settings(**kwargs) -> ChatSettingsData:
    return ChatSettingsData(chat_id=111, **kwargs)


@pytest.mark.asyncio
class TestShowSettingsMenu:
    async def test_shows_disabled_status(self, make_update, make_context):
        update = make_update(chat_id=111)
        ctx = make_context()
        repo_mock = MagicMock()

        with patch(f"{_MOD}.async_session_factory", return_value=make_async_session(repo_mock)), \
             patch(f"{_MOD}.SqlAlchemyChatSettingsRepository", return_value=repo_mock), \
             patch(f"{_MOD}.get_settings", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = _settings()
            state = await _show_settings_menu(update, ctx)

        assert state == SHOW_MENU
        text = update.message.reply_text.call_args[0][0]
        assert "выключено" in text

    async def test_shows_enabled_daily(self, make_update, make_context):
        update = make_update(chat_id=111)
        ctx = make_context()
        repo_mock = MagicMock()

        with patch(f"{_MOD}.async_session_factory", return_value=make_async_session(repo_mock)), \
             patch(f"{_MOD}.SqlAlchemyChatSettingsRepository", return_value=repo_mock), \
             patch(f"{_MOD}.get_settings", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = _settings(
                daily_reminder_enabled=True,
                daily_reminder_time=datetime.time(7, 0),
            )
            await _show_settings_menu(update, ctx)

        text = update.message.reply_text.call_args[0][0]
        assert "07:00" in text

    async def test_shows_enabled_preclass(self, make_update, make_context):
        update = make_update(chat_id=111)
        ctx = make_context()
        repo_mock = MagicMock()

        with patch(f"{_MOD}.async_session_factory", return_value=make_async_session(repo_mock)), \
             patch(f"{_MOD}.SqlAlchemyChatSettingsRepository", return_value=repo_mock), \
             patch(f"{_MOD}.get_settings", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = _settings(
                pre_class_reminder_enabled=True,
                pre_class_reminder_minutes=30,
            )
            await _show_settings_menu(update, ctx)

        text = update.message.reply_text.call_args[0][0]
        assert "30" in text


@pytest.mark.asyncio
class TestPickOption:
    async def test_invalid_choice(self, make_update, make_context):
        state = await _pick_option(make_update(text="9"), make_context())
        assert state == SHOW_MENU

    async def test_choice_1_goes_to_daily(self, make_update, make_context):
        state = await _pick_option(make_update(text="1"), make_context())
        assert state == SET_DAILY_TIME

    async def test_choice_2_goes_to_preclass(self, make_update, make_context):
        state = await _pick_option(make_update(text="2"), make_context())
        assert state == SET_PRE_CLASS_MINUTES


@pytest.mark.asyncio
class TestSetDailyTime:
    async def _call(self, text: str, make_update, make_context):
        update = make_update(text=text, chat_id=111)
        ctx = make_context()
        ctx.job_queue = MagicMock()
        ctx.job_queue.get_jobs_by_name = MagicMock(return_value=[])
        repo_mock = MagicMock()

        with patch(f"{_MOD}.async_session_factory", return_value=make_async_session(repo_mock)), \
             patch(f"{_MOD}.SqlAlchemyChatSettingsRepository", return_value=repo_mock), \
             patch(f"{_MOD}.set_daily_reminder", new_callable=AsyncMock) as mock_set, \
             patch(f"{_MOD}.schedule_morning_reminder") as mock_schedule, \
             patch(f"{_MOD}.cancel_morning_reminder") as mock_cancel:
            mock_set.return_value = _settings()
            state = await _set_daily_time(update, ctx)
        return state, mock_set, mock_schedule, mock_cancel

    async def test_valid_time_saves_and_schedules(self, make_update, make_context):
        state, mock_set, mock_schedule, _ = await self._call("07:30", make_update, make_context)
        assert state == ConversationHandler.END
        mock_set.assert_called_once()
        args = mock_set.call_args[0]
        assert args[2] == datetime.time(7, 30)
        mock_schedule.assert_called_once()

    async def test_disable_cancels_job(self, make_update, make_context):
        state, mock_set, _, mock_cancel = await self._call("/disable", make_update, make_context)
        assert state == ConversationHandler.END
        args = mock_set.call_args[0]
        assert args[2] is None
        mock_cancel.assert_called_once()

    async def test_invalid_format_stays(self, make_update, make_context):
        update = make_update(text="not-a-time", chat_id=111)
        ctx = make_context()
        state = await _set_daily_time(update, ctx)
        assert state == SET_DAILY_TIME

    async def test_out_of_range_hour_stays(self, make_update, make_context):
        update = make_update(text="25:00", chat_id=111)
        ctx = make_context()
        state = await _set_daily_time(update, ctx)
        assert state == SET_DAILY_TIME


@pytest.mark.asyncio
class TestSetPreClassMinutes:
    async def _call(self, text: str, make_update, make_context):
        update = make_update(text=text, chat_id=111)
        ctx = make_context()
        repo_mock = MagicMock()

        with patch(f"{_MOD}.async_session_factory", return_value=make_async_session(repo_mock)), \
             patch(f"{_MOD}.SqlAlchemyChatSettingsRepository", return_value=repo_mock), \
             patch(f"{_MOD}.set_pre_class_reminder", new_callable=AsyncMock) as mock_set:
            mock_set.return_value = _settings()
            state = await _set_pre_class_minutes(update, ctx)
        return state, mock_set

    async def test_valid_minutes_saves(self, make_update, make_context):
        state, mock_set = await self._call("30", make_update, make_context)
        assert state == ConversationHandler.END
        args = mock_set.call_args[0]
        assert args[2] == 30

    async def test_disable_saves_none(self, make_update, make_context):
        state, mock_set = await self._call("/disable", make_update, make_context)
        assert state == ConversationHandler.END
        args = mock_set.call_args[0]
        assert args[2] is None

    async def test_zero_is_invalid(self, make_update, make_context):
        update = make_update(text="0", chat_id=111)
        ctx = make_context()
        state = await _set_pre_class_minutes(update, ctx)
        assert state == SET_PRE_CLASS_MINUTES

    async def test_over_120_is_invalid(self, make_update, make_context):
        update = make_update(text="121", chat_id=111)
        ctx = make_context()
        state = await _set_pre_class_minutes(update, ctx)
        assert state == SET_PRE_CLASS_MINUTES

    async def test_non_digit_is_invalid(self, make_update, make_context):
        update = make_update(text="abc", chat_id=111)
        ctx = make_context()
        state = await _set_pre_class_minutes(update, ctx)
        assert state == SET_PRE_CLASS_MINUTES
