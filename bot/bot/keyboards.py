from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

start_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Add Product", callback_data="add_tracker"),
            InlineKeyboardButton(text="📋 List", callback_data="list_trackers"),
        ],
    ]
)

mode_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📢 Auto (Any change)", callback_data="mode_auto"
            )
        ],
        [
            InlineKeyboardButton(
                text="🎯 Target Price (Below limit)", callback_data="mode_target"
            )
        ],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_add")],
    ]
)
