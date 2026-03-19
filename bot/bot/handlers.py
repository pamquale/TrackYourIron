from __future__ import annotations

import logging
import re
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
    r"https?://(?:www\.)?(?:telemart\.ua|rozetka\.com\.ua)/\S+",
    re.IGNORECASE,
)


# ── /start ───────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    await db.upsert_user(message.from_user.id, message.from_user.full_name)
    await message.answer(
        "Привет! Я помогу отслеживать цены на комплектующие.\n"
        "Выбери действие в меню:",
        reply_markup=start_kb,
    )


# ── Callback: add_tracker ────────────────────────────────────────────────────

@router.callback_query(F.data == "add_tracker")
async def cb_add_tracker(callback: types.CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(TrackerState.waiting_for_url)
    await callback.message.answer(
        "Пришли прямую ссылку на товар (Telemart / Rozetka)."
    )


# ── Command: /help ───────────────────────────────────────────────────────────

@router.message(Command("help"))
async def cmd_help(message: types.Message) -> None:
    text = (
        "🤖 **Доступные команды:**\n\n"
        "/start - Главное меню\n"
        "/help - Справка\n"
        "/add - Добавить товар\n"
        "/list - Мои подписки\n"
    )
    await message.answer(text, parse_mode="Markdown")


# ── Command: /add ────────────────────────────────────────────────────────────

@router.message(Command("add"))
async def cmd_add(message: types.Message, state: FSMContext) -> None:
    await state.set_state(TrackerState.waiting_for_url)
    await message.answer(
        "Пришли прямую ссылку на товар."
    )


# ── Command: /list & Callback list_trackers ──────────────────────────────────

async def show_list(message: types.Message, user_id: int):
    follows = await db.get_user_follows(user_id)
    if not follows:
        await message.answer("Список отслеживания пуст.")
        return

    lines = ["📋 <b>Ваши подписки:</b>\n"]
    for i, f in enumerate(follows, start=1):
        mode_str = "Auto 🔔" if f["mode"] == "auto" else f"Target (< {f['set_price']}) 🎯"
        # Truncate long names
        name = f["name"][:50] + "..." if len(f["name"]) > 50 else f["name"]
        lines.append(f"{i}. <a href='{f['link']}'>{name}</a>\n   Режим: {mode_str}")

    text = "\n\n".join(lines)
    await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)


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
            "Ссылка не подходит. Поддерживаются Telemart и Rozetka.\n"
            "Попробуй снова или отправь /start для отмены."
        )
        return

    msg = await message.answer("⏳ Получаю данные о товаре...")

    # Запрос к Scraper Service
    try:
        product = await scraper_client.add_product(url)
    except Exception as e:
        log.error(f"Scraper error: {e}")
        product = None

    if product is None:
        await msg.edit_text(
            "Не удалось получить данные о товаре. Проверьте ссылку."
        )
        await state.clear()
        return

    await msg.delete()

    product_id = product["id"]
    current_price = product.get("current_price") or 0
    name = product.get("name", "Товар")

    # Проверка дубликатов
    exists = await db.check_follow_exists(message.from_user.id, product_id)
    
    warning_text = ""
    if exists:
        warning_text = "⚠️ <b>Вы уже отслеживаете этот товар.</b>\nНастройки будут обновлены.\n\n"

    # Сохраняем в State
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
        f"💰 Текущая цена: {current_price_dec} грн.\n\n"
        "Выберите режим отслеживания:"
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
        f"✅ Товар <b>{data['product_name']}</b> добавлен в отслеживание (Режим: Auto).",
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(TrackerState.waiting_for_mode, F.data == "mode_target")
async def on_mode_target(callback: types.CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(TrackerState.waiting_for_price)
    
    data = await state.get_data()
    curr = data.get("current_price", 0)
    
    await callback.message.edit_text(
        f"Текущая цена: {curr} грн.\n"
        "Введите целевую цену (число), при которой нужно уведомить:"
    )


@router.callback_query(TrackerState.waiting_for_mode, F.data == "cancel_add")
async def on_cancel_mode(callback: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("❌ Добавление отменено.")
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
        await message.answer("Пожалуйста, введите корректное положительное число.")
        return

    data = await state.get_data()
    pid = data["product_id"]
    name = data["product_name"]

    await db.add_follow(message.from_user.id, pid, mode="target", set_price=price)
    await state.clear()
    
    await message.answer(
        f"✅ Подписка оформлена!\n"
        f"Товар: <b>{name}</b>\n"
        f"Уведомим, когда цена станет ниже {price} грн.",
        parse_mode="HTML"
    )
