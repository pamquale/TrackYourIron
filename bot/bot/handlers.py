from __future__ import annotations

import logging
import re
import html
from decimal import Decimal, InvalidOperation

from aiogram import F, Router, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext

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


# ── /start ───────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    await db.upsert_user(message.from_user.id, message.from_user.full_name)
    await message.answer(
        "Hello! I can help you track component prices.\n"
        "Choose an action from the menu:",
        reply_markup=start_kb,
    )


# ── Callback: add_tracker ────────────────────────────────────────────────────

@router.callback_query(F.data == "add_tracker")
async def cb_add_tracker(callback: types.CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(TrackerState.waiting_for_url)
    await callback.message.answer(
        "Send a direct link to the product (Telemart)."
    )


# ── Command: /help ───────────────────────────────────────────────────────────

@router.message(Command("help"))
async def cmd_help(message: types.Message) -> None:
    text = (
        "🤖 **Available commands:**\n\n"
        "/start - Main menu\n"
        "/help - Help\n"
        "/add - Add product\n"
        "/list - My subscriptions\n"
    )
    await message.answer(text, parse_mode="Markdown")


# ── Command: /add ────────────────────────────────────────────────────────────

@router.message(Command("add"))
async def cmd_add(message: types.Message, state: FSMContext) -> None:
    await state.set_state(TrackerState.waiting_for_url)
    await message.answer(
        "Send a direct link to the product."
    )


# ── Command: /list & Callback list_trackers ──────────────────────────────────

async def show_list(message: types.Message, user_id: int):
    try:
        follows = await db.get_user_follows(user_id)
        if not follows:
            await message.answer("Tracking list is empty.")
            return

        lines = ["📋 <b>Your subscriptions:</b>\n"]
        for i, f in enumerate(follows, start=1):
            mode_str = "Auto 🔔" if f["mode"] == "auto" else f"Target (< {f['set_price']}) 🎯"
            # Truncate long names
            raw_name = f["name"] or "Unknown Product"
            safe_name = html.escape(raw_name)
            name = safe_name[:50] + "..." if len(safe_name) > 50 else safe_name
            link = f["link"]
            
            lines.append(f"{i}. <a href='{link}'>{name}</a>\n   Mode: {mode_str}")

        text = "\n\n".join(lines)
        await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)
    except Exception as e:
        log.error(f"Error showing list: {e}")
        await message.answer("❌ Error retrieving your list. Please try again later.")


@router.message(Command("list"))
async def cmd_list(message: types.Message) -> None:
    await show_list(message, message.from_user.id)


@router.callback_query(F.data == "list_trackers")
async def cb_list_trackers(callback: types.CallbackQuery) -> None:
    await callback.answer()
    await show_list(callback.message, callback.from_user.id)


# ── FSM: waiting_for_url ─────────────────────────────────────────────────────

@router.message(TrackerState.waiting_for_url)
async def on_product_url(message: types.Message, state: FSMContext) -> None:
    url = message.text.strip() if message.text else ""

    if not _VALID_URL_RE.match(url):
        await message.answer(
            "Invalid link. Supported: Telemart.\n"
            "Try again or send /start to cancel."
        )
        return

    msg = await message.answer("⏳ Fetching product data...")

    # Request to Scraper Service
    try:
        product = await scraper_client.add_product(url)
    except Exception as e:
        log.error(f"Scraper error: {e}")
        product = None

    if product is None:
        await msg.edit_text(
            "Failed to get product data. Check the link."
        )
        await state.clear()
        return

    await msg.delete()

    product_id = product["id"]
    current_price = product.get("current_price") or 0
    name = product.get("name", "Product")

    # Check duplicates
    exists = await db.check_follow_exists(message.from_user.id, product_id)
    
    warning_text = ""
    if exists:
        warning_text = "⚠️ <b>You are already tracking this product.</b>\nSettings will be updated.\n\n"

    # Save to State
    current_price_dec = Decimal(str(current_price)) if current_price is not None else Decimal(0)

    await state.update_data(
        product_id=product_id,
        product_name=name,
        current_price=str(current_price_dec)
    )
    
    await state.set_state(TrackerState.waiting_for_mode)
    
    text = (
        f"{warning_text}"
        f"📦 <b>{name}</b>\n"
        f"💰 Current price: {current_price_dec} UAH.\n\n"
        "Choose tracking mode:"
    )
    await message.answer(text, reply_markup=mode_kb, parse_mode="HTML")


# ── FSM: waiting_for_mode ────────────────────────────────────────────────────

@router.callback_query(TrackerState.waiting_for_mode, F.data == "mode_auto")
async def on_mode_auto(callback: types.CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    pid = data["product_id"]
    
    await db.add_follow(callback.from_user.id, pid, mode="auto")
    await state.clear()
    
    await callback.message.edit_text(
        f"✅ Product <b>{data['product_name']}</b> added to tracking (Mode: Auto).",
        parse_mode="HTML"
    )
    await callback.message.answer(
        "Choose an action from the menu:",
        reply_markup=start_kb,
    )
    await callback.answer()


@router.callback_query(TrackerState.waiting_for_mode, F.data == "mode_target")
async def on_mode_target(callback: types.CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(TrackerState.waiting_for_price)
    
    data = await state.get_data()
    curr = data.get("current_price", 0)
    
    await callback.message.edit_text(
        f"Current price: {curr} UAH.\n"
        "Enter target price (number), below which to notify:"
    )


@router.callback_query(TrackerState.waiting_for_mode, F.data == "cancel_add")
async def on_cancel_mode(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("❌ Add cancelled.")
    await callback.answer()


# ── FSM: waiting_for_price ───────────────────────────────────────────────────

@router.message(TrackerState.waiting_for_price)
async def on_price_input(message: types.Message, state: FSMContext) -> None:
    text = message.text.replace(",", ".").strip()
    try:
        price = Decimal(text)
        if price <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        await message.answer("Please enter a valid positive number.")
        return

    data = await state.get_data()
    pid = data["product_id"]
    name = data["product_name"]
    current_price_str = data.get("current_price") or "0"
    try:
        current_price = Decimal(current_price_str)
    except:
        current_price = Decimal(0)

    # If current price is known, prevent setting target price higher than current
    if current_price > 0 and price >= current_price:
        await message.answer(
            f"❌ Target price ({price}) must be <b>lower</b> than current price ({current_price} UAH).\n"
            "Please enter a lower price:",
            parse_mode="HTML"
        )
        return

    await db.add_follow(message.from_user.id, pid, mode="target", set_price=price)
    await state.clear()
    
    await message.answer(
        f"✅ Subscription set!\n"
        f"Product: <b>{name}</b>\n"
        f"Will notify when price is below {price} UAH.",
        parse_mode="HTML"
    )
    await message.answer(
        "Choose an action from the menu:",
        reply_markup=start_kb,
    )
