from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from database import redeem_coupon

coupons_router = Router()

class CouponStates(StatesGroup):
    waiting_for_coupon = State()

@coupons_router.callback_query(F.data == "cmd:use_coupon")
async def ask_coupon(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(CouponStates.waiting_for_coupon)
    await callback.message.answer("🎟️ أدخل رمز الكوبون الخاص بك (مثال: `COUPON-XXXXXX`):", parse_mode="Markdown")

@coupons_router.message(CouponStates.waiting_for_coupon)
async def process_coupon(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    success, msg = redeem_coupon(message.from_user.id, code)
    await message.answer(msg)
    await state.clear()