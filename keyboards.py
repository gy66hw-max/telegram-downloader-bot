from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_ID, REWARDS_CHANNEL, SUB_PRICES, DEV_USERNAME

def get_main_keyboard(user_id: int):
    buttons = [
        [InlineKeyboardButton(text="📥 استخدام الخدمة", callback_data="cmd:use_service")],
        [
            InlineKeyboardButton(text="🪙 رصيدي", callback_data="cmd:my_coins"),
            InlineKeyboardButton(text="📅 اشتراكي", callback_data="cmd:my_sub")
        ],
        [
            InlineKeyboardButton(text="🎟️ تفعيل كوبون", callback_data="cmd:use_coupon"),
            InlineKeyboardButton(text="🔗 رابط الإحالة", callback_data="cmd:ref_link")
        ],
        [
            InlineKeyboardButton(text="🏆 قناة المكافآت", url=REWARDS_CHANNEL),
            InlineKeyboardButton(text="💬 للتواصل مع المطور", url=f"https://t.me/{DEV_USERNAME}")
        ]
    ]
    if user_id == ADMIN_ID:
        buttons.append([InlineKeyboardButton(text="👨‍💻 لوحة المطور", callback_data="cmd:dev_panel")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_developer_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎁 إنشاء رابط مكافأة", callback_data="dev:create_gift")],
            [InlineKeyboardButton(text="🎟️ إدارة الكوبونات", callback_data="dev:coupons")],
            [
                InlineKeyboardButton(text="📊 الإحصائيات", callback_data="dev:stats"),
                InlineKeyboardButton(text="🏆 أفضل المستخدمين", callback_data="dev:top_users")
            ],
            [
                InlineKeyboardButton(text="🧹 إدارة البيانات", callback_data="dev:clean_prompt"),
                InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="cmd:main_menu")
            ]
        ]
    )

def get_clean_confirm_inline():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ نعم، تأكيد المسح", callback_data="dev:confirm_clean"),
                InlineKeyboardButton(text="❌ إلغاء", callback_data="cmd:dev_panel")
            ]
        ]
    )

def get_sub_purchase_inline():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"☀️ يومي ({SUB_PRICES['daily']} عملة)", callback_data="buy_sub:daily")],
            [InlineKeyboardButton(text=f"📆 أسبوعي ({SUB_PRICES['weekly']} عملة)", callback_data="buy_sub:weekly")],
            [InlineKeyboardButton(text=f"🗓️ شهري ({SUB_PRICES['monthly']} عملة)", callback_data="buy_sub:monthly")],
            [InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="cmd:main_menu")]
        ]
    )

def get_coupon_gen_inline():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎟️ كوبون يومي", callback_data="gen_coupon:daily")],
            [InlineKeyboardButton(text="🎟️ كوبون أسبوعي", callback_data="gen_coupon:weekly")],
            [InlineKeyboardButton(text="🎟️ كوبون شهري", callback_data="gen_coupon:monthly")],
            [InlineKeyboardButton(text="🔙 لوحة المطور", callback_data="cmd:dev_panel")]
        ]
    )

def get_rewards_inline():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="انضم للقناة 🏆", url=REWARDS_CHANNEL)],
            [InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="cmd:main_menu")]
        ]
    )
