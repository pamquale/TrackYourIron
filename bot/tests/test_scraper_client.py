import pytest
import aiohttp
from unittest.mock import AsyncMock, MagicMock, patch
from services.scraper_client import add_product
import config

@pytest.mark.asyncio
async def test_add_product_success():
    """Test successful product addition via Scraper API."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "id": 123,
        "current_price": 15000.50
    })
    
    # Setup mock session
    # session object itself (the context manager)
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    
    # session.post() returns a context manager, NOT a coroutine
    mock_post_cm = AsyncMock()
    mock_post_cm.__aenter__.return_value = mock_response
    mock_session.post = MagicMock(return_value=mock_post_cm)
    
    with patch("aiohttp.ClientSession", return_value=mock_session):
        url = "https://telemart.ua/products/some-gpu"
        
        # We need to patch config if it's used
        with patch.object(config, 'SCRAPER_BASE_URL', "http://scraper:8080"):
             result = await add_product(url)
        
        mock_session.post.assert_called_once()
        args = mock_session.post.call_args
        assert args[0][0] == f"http://scraper:8080/api/products/add"
        assert args[1]['json'] == {"url": url}
        
        assert result['id'] == 123
        assert result['current_price'] == 15000.50

@pytest.mark.asyncio
async def test_add_product_failure():
    """Test scraper API failure (e.g. 400 Bad Request)."""
    mock_response = AsyncMock()
    mock_response.status = 400
    
    # Setup mock session
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    
    mock_post_cm = AsyncMock()
    mock_post_cm.__aenter__.return_value = mock_response
    mock_session.post = MagicMock(return_value=mock_post_cm)
    
    with patch("aiohttp.ClientSession", return_value=mock_session):
        url = "https://invalid-url"
        result = await add_product(url)
        
        assert result is None

@pytest.mark.asyncio
async def test_add_product_connection_error():
    """Test scraper API connection error."""
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session

    # session.post() should raise ClientError immediately when called
    # OR session.post() returns a CM that raises on __aenter__
    # If connection error happens during request initiation (post call), side_effect on post works.
    
    # Case 1: post() raises immediately
    mock_session.post = MagicMock(side_effect=aiohttp.ClientError())
    
    with patch("aiohttp.ClientSession", return_value=mock_session):
        url = "https://telemart.ua/products/some-gpu"
        result = await add_product(url)
        
        assert result is None
