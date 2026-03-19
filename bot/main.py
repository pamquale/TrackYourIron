from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher

import config
from bot.handlers import router
from db.pool import close_pool, get_pool
from services.nats_consumer import start_consumer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger(__name__)


async def main() -> None:
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    # Инициализируем connection pool при старте
    await get_pool()
    log.info("Database pool initialized")

    # Запускаем NATS-консьюмер как фоновую задачу
    nats_task = asyncio.create_task(start_consumer(bot))
    log.info("NATS consumer started")

    try:
        await dp.start_polling(bot)
    finally:
        nats_task.cancel()
        await close_pool()
        await bot.session.close()
        log.info("Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
