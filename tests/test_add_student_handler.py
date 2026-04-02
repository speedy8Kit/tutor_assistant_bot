"""Unit tests for the add_student ConversationHandler."""

from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch

from telegram.ext import ConversationHandler

from tutor_assistant.handlers.add_student import (
    ASK_NAME,
    ASK_SLOTS,
    CONFIRM,
    add_student_start,
    confirmed,
    received_name,
    received_slot,
    slots_done,
)

_HANDLER_PATH = "tutor_assistant.handlers.add_student"


class TestAddStudentStart:
    async def test_clears_user_data_and_returns_ask_name(
        self, make_update, make_context
    ):
        update = make_update()
        ctx = make_context(user_data={"leftover": "data"})

        state = await add_student_start(update, ctx)

        assert state == ASK_NAME
        assert ctx.user_data == {}
        update.message.reply_text.assert_awaited_once()


class TestReceivedName:
    async def test_empty_name_stays_in_ask_name(self, make_update, make_context):
        state = await received_name(make_update(text="   "), make_context())
        assert state == ASK_NAME

    async def test_valid_name_stored_and_transitions(self, make_update, make_context):
        ctx = make_context()
        state = await received_name(make_update(text="Иван Петров"), ctx)

        assert state == ASK_SLOTS
        assert ctx.user_data["student_name"] == "Иван Петров"
        assert ctx.user_data["slots"] == []

    async def test_name_is_stripped(self, make_update, make_context):
        ctx = make_context()
        await received_name(make_update(text="  Анна  "), ctx)
        assert ctx.user_data["student_name"] == "Анна"


class TestReceivedSlot:
    async def test_valid_slot_appended_stays_in_ask_slots(
        self, make_update, make_context
    ):
        ctx = make_context(user_data={"slots": []})
        state = await received_slot(make_update(text="ПН 14:30"), ctx)

        assert state == ASK_SLOTS
        assert ctx.user_data["slots"] == [(0, datetime.time(14, 30))]

    async def test_second_slot_appended(self, make_update, make_context):
        ctx = make_context(user_data={"slots": [(0, datetime.time(14, 30))]})
        await received_slot(make_update(text="СР 16:00"), ctx)

        assert len(ctx.user_data["slots"]) == 2
        assert ctx.user_data["slots"][1] == (2, datetime.time(16, 0))

    async def test_invalid_slot_sends_error_and_stays(self, make_update, make_context):
        ctx = make_context(user_data={"slots": []})
        update = make_update(text="завтра в три")
        state = await received_slot(update, ctx)

        assert state == ASK_SLOTS
        assert ctx.user_data["slots"] == []
        update.message.reply_text.assert_awaited_once()


class TestSlotsDone:
    async def test_no_slots_warns_and_stays(self, make_update, make_context):
        ctx = make_context(user_data={"student_name": "Алёша", "slots": []})
        state = await slots_done(make_update(), ctx)

        assert state == ASK_SLOTS

    async def test_with_slots_transitions_to_confirm(self, make_update, make_context):
        slots = [(0, datetime.time(14, 30)), (2, datetime.time(16, 0))]
        update = make_update()
        ctx = make_context(user_data={"student_name": "Мария", "slots": slots})

        state = await slots_done(update, ctx)

        assert state == CONFIRM
        reply = update.message.reply_text.call_args[0][0]
        assert "Мария" in reply
        assert "Пн" in reply
        assert "14:30" in reply


class TestConfirmed:
    async def test_writes_to_db_and_returns_end(
        self, make_update, make_context, mock_db_session
    ):
        slots = [(0, datetime.time(14, 30))]
        update = make_update(chat_id=999)
        ctx = make_context(user_data={"student_name": "Денис", "slots": slots})
        session_cm, mock_session = mock_db_session

        mock_student = MagicMock()
        mock_student.id = 42

        with (
            patch(f"{_HANDLER_PATH}.async_session_factory", session_cm),
            patch(
                f"{_HANDLER_PATH}.add_student", return_value=mock_student
            ) as mock_add_student,
            patch(f"{_HANDLER_PATH}.add_slots") as mock_add_slots,
        ):
            state = await confirmed(update, ctx)

        assert state == ConversationHandler.END
        mock_add_student.assert_awaited_once_with(
            mock_session, name="Денис", tutor_chat_id=999
        )
        mock_add_slots.assert_awaited_once_with(
            mock_session, student_id=42, slots=slots
        )

    async def test_clears_user_data_after_save(
        self, make_update, make_context, mock_db_session
    ):
        ctx = make_context(
            user_data={"student_name": "Ольга", "slots": [(1, datetime.time(10, 0))]}
        )
        session_cm, _ = mock_db_session

        mock_student = MagicMock()
        mock_student.id = 7

        with (
            patch(f"{_HANDLER_PATH}.async_session_factory", session_cm),
            patch(f"{_HANDLER_PATH}.add_student", return_value=mock_student),
            patch(f"{_HANDLER_PATH}.add_slots"),
        ):
            await confirmed(make_update(chat_id=1), ctx)

        assert ctx.user_data == {}

    async def test_success_message_contains_student_name(
        self, make_update, make_context, mock_db_session
    ):
        ctx = make_context(
            user_data={"student_name": "Василий", "slots": [(3, datetime.time(11, 0))]}
        )
        update = make_update(chat_id=1)
        session_cm, _ = mock_db_session

        mock_student = MagicMock()
        mock_student.id = 5

        with (
            patch(f"{_HANDLER_PATH}.async_session_factory", session_cm),
            patch(f"{_HANDLER_PATH}.add_student", return_value=mock_student),
            patch(f"{_HANDLER_PATH}.add_slots"),
        ):
            await confirmed(update, ctx)

        reply = update.message.reply_text.call_args[0][0]
        assert "Василий" in reply
