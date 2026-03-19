from __future__ import annotations

import logging

import aiohttp

import config

log = logging.getLogger(__name__)


async def add_product(url: str) -> dict | None:
    """
    POST http://scraper:8080/api/products/add
    Body: {"url": "<ссылка>"}

    Ожидаемый ответ (200): {"id": 5, "current_price": 14500.00}
    Возвращает dict с данными или None при ошибке.
    """
    endpoint = f"{config.SCRAPER_BASE_URL}/api/products/add"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, json={"url": url}) as resp:
                if resp.status != 200:
                    log.warning("Scraper returned %s for url=%s", resp.status, url)
                    return None
                return await resp.json()
    except aiohttp.ClientError:
        log.exception("Scraper Service unavailable")
        return None
