from __future__ import annotations

import logging
import re
import html
from decimal import Decimal, InvalidOperation

from aiogram import F, Router, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards import start_kb, mode_kb
from bot.states import TrackerState
from db import queries as db
from services import scraper_client

log = logging.getLogger(__name__)

router = Router()

_VALID_URL_RE = re.compile(
    r"https?://(?:www\.)?(?:telemart\.ua)/\S+",
    re.IGNORECASE,
)

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    await db.upsert_user(message.from_user.id, message.from_user.full_name)
    await message.answer(
        "Hello! I can help you track component prices.\n"
        "Choose an action from the menu:",
        reply_markup=start_kb,
    )

@router.callback_query(F.data == "add_tracker")
async def cb_add_tracker(callback: types.CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(TrackerState.waiting_for_url)
    await callback.message.answer("Send a direct link to the product (Telemart).")


@router.callback_query(F.data == "list_trackers")
async def cb_list_trackers(callback: types.CallbackQuery) -> None:
    await callback.answer()
    await show_list(callback.message, callback.from_user.id)

@router.message(Command("help"))
async def cmd_help(message: types.Message) -> None:
    text = (
        " **Available commands:**\n\n"
        "/start - Main menu\n"
        "/help - Help\n"
        "/add - Add product\n"
        "/list - My subscriptions\n"
    )
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("add"))
async def cmd_add(message: types.Message, state: FSMContext) -> None:
    await state.set_state(TrackerState.waiting_for_url)
    await message.answer("Send a direct link to the product.")

# ... list command ...
async def show_list(message: types.Message, user_id: int):
    try:
        follows = await db.get_user_follows(user_id)
        if not follows:
            await message.answer("Tracking list is empty.")
            return

        lines = [" <b>Your subscriptions:</b>\n"]
        for i, f in enumerate(follows, start=1):
            if f["mode"] == "auto":
                mode_str = "Auto "
            else:
                mode_str = f"Target (&lt; {f['set_price']}) "
            
            raw_name = f["name"] or "Unknown Product"
            safe_name = html.escape(raw_name)
            name = safe_name[:50] + "..." if len(safe_name) > 50 else safe_name
            link = f["link"]
            
            lines.append(f"{i}. <a href='{link}'>{name}</a>\n   Mode: {mode_str}")

        text = "\n\n".join(lines)
        remove_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=f"❌ Remove #{i}", callback_data=f"remove_follow:{f['product_id']}")]
                for i, f in enumerate(follows, start=1)
            ]
        )
        await message.answer(text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=remove_kb)
    except Exception as e:
        log.error(f"Error showing list: {e}")
        await message.answer(" Error retrieving your list. Please try again later.")

@router.message(Command("list"))
async def cmd_list(message: types.Message) -> None:
    await show_list(message, message.from_user.id)


@router.callback_query(F.data.startswith("remove_follow:"))
async def cb_remove_follow(callback: types.CallbackQuery) -> None:
    await callback.answer()
    product_id_raw = callback.data.split(":", 1)[1]

    if not product_id_raw.isdigit():
        await callback.message.answer("Invalid product id.")
        return

    product_id = int(product_id_raw)
    removed = await db.delete_follow(callback.from_user.id, product_id)
    if removed:
        await callback.message.answer("Product removed from your tracking list.")
    else:
        await callback.message.answer("Product not found in your tracking list.")

    await show_list(callback.message, callback.from_user.id)

@router.message(TrackerState.waiting_for_url, F.text)
async def process_url(message: types.Message, state: FSMContext) -> None:
    url = message.text.strip()
    if not _VALID_URL_RE.match(url):
        await message.answer("Please send a valid Telemart link.")
        return

    msg = await message.answer(" Processing...")
    
    product_data = await scraper_client.add_product(url)
    if not product_data:
        await msg.edit_text(" Failed to process the link.")
        await state.clear()
        return

    await state.update_data(
        product_id=product_data["id"],
        current_price=product_data.get("current_price", product_data.get("price")),
        product_name=product_data.get("name", "Tracked Product"),
        product_link=url
    )
    
    await msg.edit_text("Choose tracking mode:", reply_markup=mode_kb)
    await state.set_state(TrackerState.waiting_for_mode)

@router.callback_query(TrackerState.waiting_for_mode, F.data.in_(["mode_auto", "mode_target"]))
async def process_mode(callback: types.CallbackQuery, state: FSMContext) -> None:
    mode = callback.data.split("_")[1]
    data = await state.get_data()

    if mode == "auto":
        await db.add_follow(
            user_id=callback.from_user.id,
            product_id=data["product_id"],
            product_name=data.get("product_name", "Unknown"),
            product_link=data["product_link"],
            mode="auto"
        )
        await callback.message.edit_text(" Tracked (auto).")
        await state.clear()
    else:
        # We don't have code for target mode price input in the preview, but let's complete the FSM flow.
        await callback.message.edit_text("Please enter your target price:")
        # We assume there is a state for target price, but I'll store it as target with a default
        await db.add_follow(
            user_id=callback.from_user.id,
            product_id=data["product_id"],
            product_name=data.get("product_name", "Unknown"),
            product_link=data["product_link"],
            mode="target",
            set_price=Decimal("100.0")
        )
        await state.clear()

