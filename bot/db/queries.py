from __future__ import annotations

from decimal import Decimal

import asyncpg

from db.pool import get_pool


async def upsert_user(telegram_id: int, name: str | None = None) -> None:
    """Регистрация пользователя (INSERT ... ON CONFLICT — идемпотентно)."""
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO users (telegram_id, name)
        VALUES ($1, $2)
        ON CONFLICT (telegram_id) DO NOTHING
        """,
        telegram_id,
        name,
    )


async def add_follow(
    user_id: int,
    product_id: int,
    mode: str = "auto",
    set_price: Decimal | None = None,
) -> None:
    """Добавление подписки на товар."""
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO follows (user_id, product_id, mode, set_price)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (user_id, product_id)
        DO UPDATE SET mode = EXCLUDED.mode, set_price = EXCLUDED.set_price
        """,
        user_id,
        product_id,
        mode,
        set_price,
    )


async def find_users_to_notify(
    product_id: int,
    new_price: Decimal,
) -> list[asyncpg.Record]:
    """
    Поиск подписчиков, которых нужно уведомить:
      - mode = 'auto'  → уведомляем при любом изменении цены
      - mode = 'target' → уведомляем, только если new_price <= set_price
    """
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT f.user_id, f.mode, f.set_price
        FROM follows f
        WHERE f.product_id = $1
          AND (f.mode = 'auto' OR (f.mode = 'target' AND f.set_price >= $2))
        """,
        product_id,
        new_price,
    )
    return rows


async def get_user_follows(user_id: int) -> list[asyncpg.Record]:
    """Список всех отслеживаемых товаров пользователя."""
    pool = await get_pool()
    return await pool.fetch(
        """
        SELECT p.name, p.link, f.mode, f.set_price
        FROM follows f
        JOIN products p ON f.product_id = p.id
        WHERE f.user_id = $1
        ORDER BY p.name ASC
        """,
        user_id,
    )


async def check_follow_exists(user_id: int, product_id: int) -> bool:
    """Проверка наличия подписки."""
    pool = await get_pool()
    val = await pool.fetchval(
        "SELECT 1 FROM follows WHERE user_id = $1 AND product_id = $2",
        user_id,
        product_id,
    )
    return val is not None
