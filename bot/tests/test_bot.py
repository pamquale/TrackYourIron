import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import types
from bot.handlers import cmd_start, cmd_help, cb_add_tracker, cmd_add, cmd_list
from bot.states import TrackerState

@pytest.mark.asyncio
async def test_cmd_start():
    message = AsyncMock(spec=types.Message)
    # Configure nested attributes
    user = MagicMock()
    user.id = 123
    user.full_name = "Test User"
    message.from_user = user
    
    # Configure awaitable answer
    message.answer = AsyncMock()

    state = AsyncMock()

    # Mock DB call
    # Note: imported 'db' in handlers.py is 'bot.handlers.db'
    with patch('bot.handlers.db.upsert_user', new_callable=AsyncMock) as mock_upsert:
        await cmd_start(message, state)
        
        state.clear.assert_called_once()
        mock_upsert.assert_called_once_with(123, "Test User")
        message.answer.assert_called_once()
        assert "Привет!" in message.answer.call_args[0][0]

@pytest.mark.asyncio
async def test_cmd_help():
    message = AsyncMock(spec=types.Message)
    message.answer = AsyncMock()
    
    await cmd_help(message)
    
    message.answer.assert_called_once()
    assert "/start" in message.answer.call_args[0][0]

@pytest.mark.asyncio
async def test_cb_add_tracker():
    callback = AsyncMock(spec=types.CallbackQuery)
    message = AsyncMock(spec=types.Message)
    message.answer = AsyncMock()
    callback.message = message
    callback.answer = AsyncMock()
    state = AsyncMock()

    await cb_add_tracker(callback, state)

    callback.answer.assert_called_once()
    state.set_state.assert_called_once_with(TrackerState.waiting_for_url)
    message.answer.assert_called_once()
    assert "Telemart" in message.answer.call_args[0][0]

@pytest.mark.asyncio
async def test_cmd_add():
    message = AsyncMock(spec=types.Message)
    # Configure awaitable answer
    message.answer = AsyncMock()
    state = AsyncMock()

    await cmd_add(message, state)

    state.set_state.assert_called_once_with(TrackerState.waiting_for_url)
    message.answer.assert_called_once()
    # Use 'Telemart' because it's in the response string
    assert "Telemart" in message.answer.call_args[0][0]

@pytest.mark.asyncio
async def test_cmd_list():
    message = AsyncMock(spec=types.Message)
    message.from_user.id = 123
    message.answer = AsyncMock()

    # Mock DB call
    with patch('bot.handlers.db.get_user_follows', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = [
            {"name": "Test Product", "link": "http://test.com", "mode": "auto", "set_price": 0}
        ]
        await cmd_list(message)

        message.answer.assert_called_once()
        assert "Test Product" in message.answer.call_args[0][0]

