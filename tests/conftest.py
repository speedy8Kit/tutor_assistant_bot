"""Shared test fixtures."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Update
from telegram.ext import ContextTypes


@pytest.fixture
def make_update():
    def _factory(
        text: str = "", chat_id: int = 111, args: list[str] | None = None
    ) -> MagicMock:
        update = MagicMock(spec=Update)
        update.message.text = text
        update.message.reply_text = AsyncMock()
        update.effective_chat.id = chat_id
        return update

    return _factory


@pytest.fixture
def make_context():
    def _factory(
        user_data: dict | None = None, args: list[str] | None = None
    ) -> MagicMock:
        ctx = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        ctx.user_data = user_data if user_data is not None else {}
        ctx.args = args or []
        return ctx

    return _factory


def make_async_session(repo_mock: MagicMock) -> MagicMock:
    """Create a properly structured async session context manager mock."""
    begin_cm = MagicMock()
    begin_cm.__aenter__ = AsyncMock(return_value=None)
    begin_cm.__aexit__ = AsyncMock(return_value=False)

    session = MagicMock()
    session.begin = MagicMock(return_value=begin_cm)

    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=False)

    return session_cm
