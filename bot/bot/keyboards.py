from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

start_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить товар", callback_data="add_tracker"),
            InlineKeyboardButton(text="📋 Список", callback_data="list_trackers"),
        ],
    ]
)

mode_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📢 Авто (Любое изменение)", callback_data="mode_auto"
            )
        ],
        [
            InlineKeyboardButton(
                text="🎯 Целевая цена (Ниже заданной)", callback_data="mode_target"
            )
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_add")],
    ]
)
