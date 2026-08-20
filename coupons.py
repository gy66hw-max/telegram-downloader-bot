import html
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
    success, msg, referrer_id = redeem_coupon(message.from_user.id, code)
    await message.answer(msg)
    await state.clear()
    
    # إرسال إشعار للداعي بحصوله على +3 عملات إضافية عند تفعيل اشتراك عبر كوبون
    if success and referrer_id:
        try:
            safe_name = html.escape(message.from_user.first_name or "مستخدم")
            sub_msg = (
                f"🔥 <b>مكافأة اشتراك إحالة!</b>\n\n"
                f"قام المستخدم <b>{safe_name}</b> (الذي انضم عبر رابطك) بتفعيل اشتراكه عبر كوبون! 🚀\n"
                f"🪙 تمت إضافة <b>+3 عملات إضافية</b> إلى رصيدك بنجاح!\n"
                f"✨ <i>اكتملت مكافأة الدعوة لهذا المستخدم (المجموع: 5 عملات).</i>"
            )
            await message.bot.send_message(chat_id=referrer_id, text=sub_msg, parse_mode="HTML")
        except Exception as e:
            print(f"فشل إرسال إشعار الداعي: {e}")
