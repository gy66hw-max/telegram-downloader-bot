from aiogram import Router, F
from aiogram.types import CallbackQuery
from database import get_or_create_user, buy_sub_with_coins
from keyboards import get_sub_purchase_inline

coins_router = Router()

@coins_router.callback_query(F.data == "cmd:my_coins")
async def my_coins(callback: CallbackQuery):
    await callback.answer()
    user = get_or_create_user(callback.from_user.id)
    text = (
        f"🪙 **رصيد العملات:** `{user['coins']}` عملة\n\n"
        f"يمكنك شراء اشتراك جديد باستخدام رصيدك:"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=get_sub_purchase_inline())

@coins_router.callback_query(F.data.startswith("buy_sub:"))
async def process_sub_buy(callback: CallbackQuery):
    plan_type = callback.data.split(":")[1]
    success, msg = buy_sub_with_coins(callback.from_user.id, plan_type)
    await callback.answer(msg, show_alert=True)
    if success:
        await callback.message.edit_text(msg)