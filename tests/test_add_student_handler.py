"""Unit tests for the add_student ConversationHandler."""

from __future__ import annotations

import datetime
from unittest.mock import patch

from telegram.ext import ConversationHandler

from tutor_assistant.application.handlers.telegram.add_student import (
    ASK_NAME,
    ASK_SLOTS,
    CONFIRM,
    _add_student_start,
    _confirmed,
    _received_name,
    _received_slot,
    _slots_done,
)

_HANDLER_PATH = "tutor_assistant.application.handlers.telegram.add_student"


class TestAddStudentStart:
    async def test_clears_user_data_and_returns_ask_name(
        self, make_update, make_context
    ):
        update = make_update()
        ctx = make_context(user_data={"leftover": "data"})

        state = await _add_student_start(update, ctx)

        assert state == ASK_NAME
        assert ctx.user_data == {}
        update.message.reply_text.assert_awaited_once()


class TestReceivedName:
    async def test_empty_name_stays_in_ask_name(self, make_update, make_context):
        state = await _received_name(make_update(text="   "), make_context())
        assert state == ASK_NAME

    async def test_valid_name_stored_and_transitions(self, make_update, make_context):
        ctx = make_context()
        state = await _received_name(make_update(text="Иван Петров"), ctx)

        assert state == ASK_SLOTS
        assert ctx.user_data["student_name"] == "Иван Петров"
        assert ctx.user_data["slots"] == []

    async def test_name_is_stripped(self, make_update, make_context):
        ctx = make_context()
        await _received_name(make_update(text="  Анна  "), ctx)
        assert ctx.user_data["student_name"] == "Анна"


class TestReceivedSlot:
    async def test_valid_slot_appended_stays_in_ask_slots(
        self, make_update, make_context
    ):
        ctx = make_context(user_data={"slots": []})
        state = await _received_slot(make_update(text="ПН 14:30"), ctx)

        assert state == ASK_SLOTS
        assert ctx.user_data["slots"] == [(0, datetime.time(14, 30))]

    async def test_second_slot_appended(self, make_update, make_context):
        ctx = make_context(user_data={"slots": [(0, datetime.time(14, 30))]})
        await _received_slot(make_update(text="СР 16:00"), ctx)

        assert len(ctx.user_data["slots"]) == 2
        assert ctx.user_data["slots"][1] == (2, datetime.time(16, 0))

    async def test_invalid_slot_sends_error_and_stays(self, make_update, make_context):
        ctx = make_context(user_data={"slots": []})
        update = make_update(text="завтра в три")
        state = await _received_slot(update, ctx)

        assert state == ASK_SLOTS
        assert ctx.user_data["slots"] == []
        update.message.reply_text.assert_awaited_once()


class TestSlotsDone:
    async def test_no_slots_warns_and_stays(self, make_update, make_context):
        ctx = make_context(user_data={"student_name": "Алёша", "slots": []})
        state = await _slots_done(make_update(), ctx)

        assert state == ASK_SLOTS

    async def test_with_slots_transitions_to_confirm(self, make_update, make_context):
        slots = [(0, datetime.time(14, 30)), (2, datetime.time(16, 0))]
        update = make_update()
        ctx = make_context(user_data={"student_name": "Мария", "slots": slots})

        state = await _slots_done(update, ctx)

        assert state == CONFIRM
        reply = update.message.reply_text.call_args[0][0]
        assert "Мария" in reply
        assert "Пн" in reply
        assert "14:30" in reply


class TestConfirmed:
    async def test_calls_service_and_returns_end(self, make_update, make_context):
        slots = [(0, datetime.time(14, 30))]
        update = make_update(chat_id=999)
        ctx = make_context(user_data={"student_name": "Денис", "slots": slots})

        with patch(f"{_HANDLER_PATH}.create_student") as mock_create:
            state = await _confirmed(update, ctx)

        assert state == ConversationHandler.END
        mock_create.assert_awaited_once_with("Денис", 999, slots)

    async def test_clears_user_data_after_save(self, make_update, make_context):
        ctx = make_context(
            user_data={"student_name": "Ольга", "slots": [(1, datetime.time(10, 0))]}
        )
        with patch(f"{_HANDLER_PATH}.create_student"):
            await _confirmed(make_update(chat_id=1), ctx)

        assert ctx.user_data == {}

    async def test_success_message_contains_student_name(
        self, make_update, make_context
    ):
        ctx = make_context(
            user_data={"student_name": "Василий", "slots": [(3, datetime.time(11, 0))]}
        )
        update = make_update(chat_id=1)

        with patch(f"{_HANDLER_PATH}.create_student"):
            await _confirmed(update, ctx)

        reply = update.message.reply_text.call_args[0][0]
        assert "Василий" in reply
