"""Shared test fixtures."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Update
from telegram.ext import ContextTypes


@pytest.fixture
def make_update():
    """Factory that returns a mocked telegram Update."""
    def _factory(text: str = "", chat_id: int = 111) -> MagicMock:
        update = MagicMock(spec=Update)
        update.message = MagicMock()
        update.message.text = text
        update.message.reply_text = AsyncMock()
        update.effective_chat = MagicMock()
        update.effective_chat.id = chat_id
        return update

    return _factory


@pytest.fixture
def make_context():
    """Factory that returns a mocked handler context."""
    def _factory(user_data: dict | None = None) -> MagicMock:
        ctx = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        ctx.user_data = user_data if user_data is not None else {}
        return ctx

    return _factory


@pytest.fixture
def mock_db_session():
    """Returns (session_cm_factory, mock_session) for patching async_session_factory.

    Usage::

        def test_something(mock_db_session):
            session_cm, session = mock_db_session
            with patch("some.module.async_session_factory", session_cm):
                ...
    """
    mock_session = AsyncMock()

    @asynccontextmanager
    async def _begin():
        yield

    mock_session.begin = _begin

    @asynccontextmanager
    async def _session_cm():
        yield mock_session

    return _session_cm, mock_session
