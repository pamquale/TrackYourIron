from __future__ import annotations

import json
import logging
from decimal import Decimal
import asyncio

import nats
from aiogram import Bot, Dispatcher
from aiogram.types import Update

import config
from db import queries

log = logging.getLogger(__name__)

PRICE_SUBJECT = "events.price_dropped"
TG_SUBJECT = "events.telegram_update"

async def _listen_price_dropped(sub: nats.aio.subscription.Subscription, bot: Bot):
    async for msg in sub.messages:
        try:
            payload = json.loads(msg.data.decode())
            product_id: int = payload["product_id"]
            new_price = Decimal(str(payload["new_price"]))
            store_link = payload.get("store_link", "Ссылка")

            rows = await queries.find_users_to_notify(product_id, new_price)    
            for row in rows:
                text = (
                    f"Цена на товар (ID {product_id}) снизилась!\n"
                    f"Новая цена: {new_price} ?\n"
                    f"Ссылка: {store_link}"
                )
                try:
                    await bot.send_message(chat_id=row["user_id"], text=text)   
                except Exception:
                    log.exception("Failed to send message to %s", row["user_id"])
        except Exception:
            log.exception("Error processing price drop event")

async def _listen_tg_updates(sub: nats.aio.subscription.Subscription, bot: Bot, dp: Dispatcher):
    async for msg in sub.messages:
        try:
            payload = json.loads(msg.data.decode())
            update = Update(**payload)
            await dp.feed_update(bot, update)
        except Exception:
            log.exception("Error feeding telegram update from NATS")

async def start_consumer(bot: Bot, dp: Dispatcher) -> None:
    nc = await nats.connect(config.NATS_URL)
    
    price_sub = await nc.subscribe(PRICE_SUBJECT)
    log.info("NATS: subscribed to %s", PRICE_SUBJECT)
    
    tg_sub = await nc.subscribe(TG_SUBJECT)
    log.info("NATS: subscribed to %s", TG_SUBJECT)

    await asyncio.gather(
        _listen_price_dropped(price_sub, bot),
        _listen_tg_updates(tg_sub, bot, dp)
    )

