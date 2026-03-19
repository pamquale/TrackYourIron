from __future__ import annotations

import json
import logging
from decimal import Decimal

import nats
from aiogram import Bot

import config
from db import queries

log = logging.getLogger(__name__)

SUBJECT = "events.price_dropped"


async def start_consumer(bot: Bot) -> None:
    """
    Подключается к NATS, подписывается на events.price_dropped
    и обрабатывает входящие события в бесконечном цикле.

    Payload: {"product_id": 5, "new_price": 14000.00}
    """
    nc = await nats.connect(config.NATS_URL)
    sub = await nc.subscribe(SUBJECT)
    log.info("NATS: subscribed to %s", SUBJECT)

    async for msg in sub.messages:
        try:
            payload = json.loads(msg.data.decode())
            product_id: int = payload["product_id"]
            new_price = Decimal(str(payload["new_price"]))

            rows = await queries.find_users_to_notify(product_id, new_price)
            for row in rows:
                text = (
                    f"Цена на товар (ID {product_id}) снизилась!\n"
                    f"Новая цена: {new_price} ₽"
                )
                try:
                    await bot.send_message(chat_id=row["user_id"], text=text)
                except Exception:
                    log.exception("Failed to send message to %s", row["user_id"])

        except Exception:
            log.exception("Error processing NATS message on %s", SUBJECT)
