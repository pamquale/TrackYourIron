from __future__ import annotations

from decimal import Decimal

import asyncpg

from db.pool import get_pool


async def upsert_user(telegram_id: int, name: str | None = None) -> None:       
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO notifier_db.users (telegram_id, name)
        VALUES ($1, $2)
        ON CONFLICT (telegram_id) DO NOTHING
        """,
        telegram_id,
        name,
    )


async def add_follow(
    user_id: int,
    product_id: int,
    product_name: str = "Tracked Product",
    product_link: str = "",
    mode: str = "auto",
    set_price: Decimal | None = None,
) -> None:
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO notifier_db.follows (user_id, product_id, product_name, product_link, mode, set_price)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (user_id, product_id)
        DO UPDATE SET 
            mode = EXCLUDED.mode, 
            set_price = EXCLUDED.set_price,
            product_name = EXCLUDED.product_name,
            product_link = EXCLUDED.product_link
        """,
        user_id,
        product_id,
        product_name,
        product_link,
        mode,
        set_price,
    )


async def find_users_to_notify(
    product_id: int,
    new_price: Decimal,
) -> list[asyncpg.Record]:
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT f.user_id, f.mode, f.set_price
        FROM notifier_db.follows f
        WHERE f.product_id = $1
          AND (f.mode = 'auto' OR (f.mode = 'target' AND f.set_price >= $2))    
        """,
        product_id,
        new_price,
    )
    return rows


async def get_user_follows(user_id: int) -> list[asyncpg.Record]:
    pool = await get_pool()
    return await pool.fetch(
        """
        SELECT f.product_name as name, f.product_link as link, f.mode, f.set_price
        FROM notifier_db.follows f
        WHERE f.user_id = $1
        ORDER BY f.product_name ASC
        """,
        user_id,
    )


async def check_follow_exists(user_id: int, product_id: int) -> bool:
    pool = await get_pool()
    val = await pool.fetchval(
        "SELECT 1 FROM notifier_db.follows WHERE user_id = $1 AND product_id = $2",
        user_id,
        product_id,
    )
    return bool(val)
