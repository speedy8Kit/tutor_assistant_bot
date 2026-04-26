"""Юнит-тесты для ConversationHandler student_editor."""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import make_async_session
from tutor_assistant.domain.entities import SlotData, StudentData
from tutor_assistant.interfaces.shared.keyboards import BTN_DELETE_NO, BTN_DELETE_YES
from tutor_assistant.interfaces.telegram.conversations.student_editor import (
    ADD_SLOT,
    CONFIRM_DELETE,
    EDIT_FIELD,
    EDIT_SLOT,
    SCHEDULE_VIEW,
    SHOW_CARD,
    SHOW_LIST,
    _KEY,
    _add_slot,
    _ask_delete_text,
    _back_to_card_cmd,
    _back_to_list_text,
    _cancel_delete_text,
    _confirm_delete_text,
    _delete_slot_cmd,
    _save_field,
    _save_slot,
    _show_card_cmd,
    _show_list,
    _show_schedule_text,
    _start_add_slot_cmd,
    _start_edit_field_text,
    _start_edit_slot_cmd,
)

_MOD = "tutor_assistant.interfaces.telegram.conversations.student_editor"


def _student(
    student_id: int = 1,
    name: str = "Иван",
    phone: str | None = None,
    slots: list[SlotData] | None = None,
) -> StudentData:
    return StudentData(
        id=student_id,
        name=name,
        tutor_chat_id=111,
        phone=phone,
        slots=slots or [],
    )


def _slot(slot_id: int = 10, day: int = 0, hour: int = 14) -> SlotData:
    return SlotData(
        id=slot_id,
        student_id=1,
        day_of_week=day,
        time_start=datetime.time(hour, 0),
        duration_minutes=60,
    )


# ---------------------------------------------------------------------------
# /list_students — точка входа
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestShowList:
    async def test_empty(self, make_update, make_context):
        update = make_update(chat_id=111)
        ctx = make_context()
        repo_mock = MagicMock()
        repo_mock.list_all = AsyncMock(return_value=[])

        with patch(
            f"{_MOD}.async_session_factory", return_value=make_async_session(repo_mock)
        ), patch(f"{_MOD}.SqlAlchemyStudentRepository", return_value=repo_mock):
            state = await _show_list(update, ctx)

        assert state == SHOW_LIST
        update.effective_message.reply_text.assert_awaited_once()

    async def test_with_students(self, make_update, make_context):
        update = make_update(chat_id=111)
        ctx = make_context()
        repo_mock = MagicMock()
        repo_mock.list_all = AsyncMock(
            return_value=[_student(1, "Иван"), _student(2, "Маша")]
        )

        with patch(
            f"{_MOD}.async_session_factory", return_value=make_async_session(repo_mock)
        ), patch(f"{_MOD}.SqlAlchemyStudentRepository", return_value=repo_mock):
            state = await _show_list(update, ctx)

        assert state == SHOW_LIST
        call_text = update.effective_message.reply_text.call_args[0][0]
        assert "/s_1" in call_text
        assert "/s_2" in call_text


# ---------------------------------------------------------------------------
# SHOW_LIST → SHOW_CARD через команду /s_{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestShowCard:
    async def test_shows_card(self, make_update, make_context):
        update = make_update(text="/s_1", chat_id=111)
        ctx = make_context()

        with patch(f"{_MOD}._load_by_id", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = _student(1, "Иван")
            state = await _show_card_cmd(update, ctx)

        assert state == SHOW_CARD
        update.message.reply_text.assert_awaited_once()
        call_text = update.message.reply_text.call_args[0][0]
        assert "Иван" in call_text
        assert ctx.user_data[_KEY]["student_id"] == 1

    async def test_student_not_found(self, make_update, make_context):
        update = make_update(text="/s_999", chat_id=111)
        ctx = make_context()

        with patch(f"{_MOD}._load_by_id", new_callable=AsyncMock) as mock_load:
            from telegram.ext import ConversationHandler

            mock_load.return_value = None
            state = await _show_card_cmd(update, ctx)

        assert state == ConversationHandler.END


# ---------------------------------------------------------------------------
# SHOW_CARD → EDIT_FIELD через кнопку поля
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestStartEditField:
    async def test_sends_prompt(self, make_update, make_context):
        update = make_update(text="Телефон", chat_id=111)
        ctx = make_context(user_data={_KEY: {"student_id": 1}})

        state = await _start_edit_field_text(update, ctx)

        assert state == EDIT_FIELD
        update.message.reply_text.assert_awaited_once()
        assert ctx.user_data[_KEY]["field_key"] == "phone"
        assert ctx.user_data[_KEY]["field_label"] == "Телефон"


# ---------------------------------------------------------------------------
# EDIT_FIELD — сохранение поля
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestSaveField:
    async def test_saves_phone(self, make_update, make_context):
        update = make_update(text="+79991234567", chat_id=111)
        updated = _student(1, "Иван", phone="+79991234567")
        ctx = make_context(
            user_data={
                _KEY: {
                    "student_id": 1,
                    "field_key": "phone",
                    "field_label": "Телефон",
                }
            }
        )
        repo_mock = MagicMock()
        repo_mock.update = AsyncMock(return_value=updated)
        repo_mock.get_by_name = AsyncMock(return_value=None)

        with patch(
            f"{_MOD}.async_session_factory", return_value=make_async_session(repo_mock)
        ), patch(f"{_MOD}.SqlAlchemyStudentRepository", return_value=repo_mock):
            state = await _save_field(update, ctx)

        assert state == SHOW_CARD
        repo_mock.update.assert_awaited_once_with(1, phone="+79991234567")

    async def test_clear_sets_none(self, make_update, make_context):
        update = make_update(text="-", chat_id=111)
        updated = _student(1, "Иван", phone=None)
        ctx = make_context(
            user_data={
                _KEY: {
                    "student_id": 1,
                    "field_key": "phone",
                    "field_label": "Телефон",
                }
            }
        )
        repo_mock = MagicMock()
        repo_mock.update = AsyncMock(return_value=updated)

        with patch(
            f"{_MOD}.async_session_factory", return_value=make_async_session(repo_mock)
        ), patch(f"{_MOD}.SqlAlchemyStudentRepository", return_value=repo_mock):
            state = await _save_field(update, ctx)

        assert state == SHOW_CARD
        repo_mock.update.assert_awaited_once_with(1, phone=None)

    async def test_name_taken_stays(self, make_update, make_context):
        update = make_update(text="Маша", chat_id=111)
        ctx = make_context(
            user_data={
                _KEY: {
                    "student_id": 1,
                    "field_key": "name",
                    "field_label": "Имя",
                }
            }
        )
        existing = _student(2, "Маша")
        repo_mock = MagicMock()
        repo_mock.get_by_name = AsyncMock(return_value=existing)

        with patch(
            f"{_MOD}.async_session_factory", return_value=make_async_session(repo_mock)
        ), patch(f"{_MOD}.SqlAlchemyStudentRepository", return_value=repo_mock):
            state = await _save_field(update, ctx)

        assert state == EDIT_FIELD


# ---------------------------------------------------------------------------
# SHOW_CARD → CONFIRM_DELETE
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDeleteFlow:
    async def test_ask_delete_shows_confirm(self, make_update, make_context):
        update = make_update(text="Удалить", chat_id=111)
        ctx = make_context(user_data={_KEY: {"student_id": 1}})

        with patch(f"{_MOD}._load_by_id", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = _student(1)
            state = await _ask_delete_text(update, ctx)

        assert state == CONFIRM_DELETE
        update.message.reply_text.assert_awaited_once()
        call_text = update.message.reply_text.call_args[0][0]
        assert "Удалить" in call_text

    async def test_confirm_delete_calls_repo(self, make_update, make_context):
        update = make_update(text=BTN_DELETE_YES, chat_id=111)
        ctx = make_context(user_data={_KEY: {"student_id": 1}})
        repo_mock = MagicMock()
        repo_mock.delete = AsyncMock()
        repo_mock.list_all = AsyncMock(return_value=[])

        with patch(
            f"{_MOD}.async_session_factory", return_value=make_async_session(repo_mock)
        ), patch(f"{_MOD}.SqlAlchemyStudentRepository", return_value=repo_mock):
            state = await _confirm_delete_text(update, ctx)

        assert state == SHOW_LIST
        repo_mock.delete.assert_awaited_once_with(1)

    async def test_cancel_delete_returns_card(self, make_update, make_context):
        update = make_update(text=BTN_DELETE_NO, chat_id=111)
        ctx = make_context(user_data={_KEY: {"student_id": 1}})

        with patch(f"{_MOD}._load_by_id", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = _student(1)
            state = await _cancel_delete_text(update, ctx)

        assert state == SHOW_CARD


# ---------------------------------------------------------------------------
# SHOW_CARD → SCHEDULE_VIEW
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestScheduleView:
    async def test_show_schedule(self, make_update, make_context):
        update = make_update(text="Расписание", chat_id=111)
        ctx = make_context(user_data={_KEY: {"student_id": 1}})
        student = _student(1, "Иван", slots=[_slot(10)])

        with patch(f"{_MOD}._load_by_id", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = student
            state = await _show_schedule_text(update, ctx)

        assert state == SCHEDULE_VIEW
        update.effective_message.reply_text.assert_awaited_once()


# ---------------------------------------------------------------------------
# SCHEDULE_VIEW — удаление слота
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDeleteSlot:
    async def test_removes_slot(self, make_update, make_context):
        update = make_update(text="/sd_10", chat_id=111)
        ctx = make_context(user_data={_KEY: {"student_id": 1}})
        student = _student(1, slots=[_slot(10)])
        updated = _student(1, slots=[])
        repo_mock = MagicMock()
        repo_mock.replace_slots = AsyncMock()
        repo_mock.get_by_id = AsyncMock(return_value=updated)

        with patch(f"{_MOD}._load_by_id", new_callable=AsyncMock) as mock_load, patch(
            f"{_MOD}.async_session_factory", return_value=make_async_session(repo_mock)
        ), patch(f"{_MOD}.SqlAlchemyStudentRepository", return_value=repo_mock):
            mock_load.return_value = student
            state = await _delete_slot_cmd(update, ctx)

        assert state == SCHEDULE_VIEW
        repo_mock.replace_slots.assert_awaited_once()
        new_slots = repo_mock.replace_slots.call_args[0][1]
        assert all(s.id != 10 for s in new_slots)


# ---------------------------------------------------------------------------
# SCHEDULE_VIEW → ADD_SLOT → сохранение
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestAddSlot:
    async def test_prompts_for_slot(self, make_update, make_context):
        update = make_update(text="/sadd", chat_id=111)
        ctx = make_context(user_data={_KEY: {"student_id": 1}})

        state = await _start_add_slot_cmd(update, ctx)

        assert state == ADD_SLOT
        update.message.reply_text.assert_awaited_once()

    async def test_invalid_format_stays(self, make_update, make_context):
        update = make_update(text="not a slot", chat_id=111)
        ctx = make_context(user_data={_KEY: {"student_id": 1}})
        student = _student(1, slots=[])

        with patch(f"{_MOD}._load_by_id", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = student
            state = await _add_slot(update, ctx)

        assert state == ADD_SLOT

    async def test_valid_slot_saved(self, make_update, make_context):
        update = make_update(text="ПН 14:00", chat_id=111)
        ctx = make_context(user_data={_KEY: {"student_id": 1}})
        student = _student(1, slots=[])
        updated = _student(1, slots=[_slot(10)])
        repo_mock = MagicMock()
        repo_mock.get_all_slots = AsyncMock(return_value=[])
        repo_mock.replace_slots = AsyncMock()
        repo_mock.get_by_id = AsyncMock(return_value=updated)

        with patch(f"{_MOD}._load_by_id", new_callable=AsyncMock) as mock_load, patch(
            f"{_MOD}.async_session_factory", return_value=make_async_session(repo_mock)
        ), patch(f"{_MOD}.SqlAlchemyStudentRepository", return_value=repo_mock):
            mock_load.return_value = student
            state = await _add_slot(update, ctx)

        assert state == SCHEDULE_VIEW
        repo_mock.replace_slots.assert_awaited_once()


# ---------------------------------------------------------------------------
# SCHEDULE_VIEW — редактирование слота
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestEditSlot:
    async def test_prompts_for_new_time(self, make_update, make_context):
        update = make_update(text="/se_10", chat_id=111)
        ctx = make_context(user_data={_KEY: {"student_id": 1}})

        state = await _start_edit_slot_cmd(update, ctx)

        assert state == EDIT_SLOT
        update.message.reply_text.assert_awaited_once()
        assert ctx.user_data[_KEY]["slot_id"] == 10

    async def test_saves_new_slot(self, make_update, make_context):
        update = make_update(text="ВТ 16:00", chat_id=111)
        ctx = make_context(
            user_data={_KEY: {"student_id": 1, "slot_id": 10}}
        )
        student = _student(1, slots=[_slot(10, day=0, hour=14)])
        updated = _student(1, slots=[_slot(10, day=1, hour=16)])
        repo_mock = MagicMock()
        repo_mock.get_all_slots = AsyncMock(return_value=[])
        repo_mock.replace_slots = AsyncMock()
        repo_mock.get_by_id = AsyncMock(return_value=updated)

        with patch(f"{_MOD}._load_by_id", new_callable=AsyncMock) as mock_load, patch(
            f"{_MOD}.async_session_factory", return_value=make_async_session(repo_mock)
        ), patch(f"{_MOD}.SqlAlchemyStudentRepository", return_value=repo_mock):
            mock_load.return_value = student
            state = await _save_slot(update, ctx)

        assert state == SCHEDULE_VIEW
        repo_mock.replace_slots.assert_awaited_once()


# ---------------------------------------------------------------------------
# Навигация
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestNavigation:
    async def test_back_to_list(self, make_update, make_context):
        update = make_update(text="← Список", chat_id=111)
        ctx = make_context()
        repo_mock = MagicMock()
        repo_mock.list_all = AsyncMock(return_value=[_student(1)])

        with patch(
            f"{_MOD}.async_session_factory", return_value=make_async_session(repo_mock)
        ), patch(f"{_MOD}.SqlAlchemyStudentRepository", return_value=repo_mock):
            state = await _back_to_list_text(update, ctx)

        assert state == SHOW_LIST
        update.effective_message.reply_text.assert_awaited_once()

    async def test_back_to_card(self, make_update, make_context):
        update = make_update(text="/sback", chat_id=111)
        ctx = make_context(user_data={_KEY: {"student_id": 1}})

        with patch(f"{_MOD}._load_by_id", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = _student(1)
            state = await _back_to_card_cmd(update, ctx)

        assert state == SHOW_CARD
        update.effective_message.reply_text.assert_awaited_once()
