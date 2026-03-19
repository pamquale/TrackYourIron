import pytest
from unittest.mock import AsyncMock, patch
from decimal import Decimal
from db.queries import find_users_to_notify, add_follow

# Mocking the pool
@pytest.fixture
def mock_pool():
    pool = AsyncMock()
    return pool

@pytest.mark.asyncio
async def test_find_users_auto_mode():
    """Test that users with 'auto' mode are always notified."""
    # Setup
    pool = AsyncMock()
    pool.fetch = AsyncMock(return_value=[
        {'user_id': 1, 'mode': 'auto', 'set_price': None}
    ])
    
    with patch('db.queries.get_pool', new_callable=AsyncMock) as mock_get_pool:
        mock_get_pool.return_value = pool
        
        users = await find_users_to_notify(product_id=1, new_price=Decimal("10000"))
        
        assert len(users) == 1
        assert users[0]['user_id'] == 1
        pool.fetch.assert_called_once()
        
        # Check SQL arguments
        args = pool.fetch.call_args[0]
        assert "mode = 'auto'" in args[0]
        assert args[1] == 1 # product_id
        assert args[2] == Decimal("10000") # new_price

@pytest.mark.asyncio
async def test_find_users_target_mode_above_price():
    """Test that users with 'target' mode are NOT notified if price is above target."""
    # Setup
    pool = AsyncMock()
    pool.fetch = AsyncMock(return_value=[]) # DB should return empty list
    
    with patch('db.queries.get_pool', new_callable=AsyncMock) as mock_get_pool:
        mock_get_pool.return_value = pool
        
        # Target is 9000, new price is 10000
        # condition: set_price >= new_price -> 9000 >= 10000 is FALSE
        users = await find_users_to_notify(product_id=1, new_price=Decimal("10000"))
        
        assert len(users) == 0

@pytest.mark.asyncio
async def test_find_users_target_mode_below_price():
    """Test that users with 'target' mode ARE notified if price is below/equal target."""
    # Setup
    pool = AsyncMock()
    pool.fetch = AsyncMock(return_value=[
         {'user_id': 2, 'mode': 'target', 'set_price': Decimal("11000")}
    ])
    
    with patch('db.queries.get_pool', new_callable=AsyncMock) as mock_get_pool:
        mock_get_pool.return_value = pool
        
        # Target is 11000, new price is 10000
        # condition: set_price >= new_price -> 11000 >= 10000 is TRUE
        users = await find_users_to_notify(product_id=1, new_price=Decimal("10000"))
        
        assert len(users) == 1
        assert users[0]['user_id'] == 2

@pytest.mark.asyncio
async def test_add_follow_defaults():
    """Test add_follow uses 'auto' mode by default."""
    pool = AsyncMock()
    
    with patch('db.queries.get_pool', new_callable=AsyncMock) as mock_get_pool:
        mock_get_pool.return_value = pool
        
        await add_follow(user_id=123, product_id=5)
        
        pool.execute.assert_called_once()
        args = pool.execute.call_args[0]
        assert args[1] == 123
        assert args[2] == 5
        assert args[3] == "Tracked Product"  # Default product_name
        assert args[4] == ""                 # Default product_link
        assert args[5] == "auto"             # Default mode
        assert args[6] is None                # Default set_price
