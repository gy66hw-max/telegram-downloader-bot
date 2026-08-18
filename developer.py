import random
import string
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from config import ADMIN_ID
from database import create_coupon, get_stats, get_top_users, reset_competition
from keyboards import get_developer_keyboard, get_coupon_gen_inline, get_clean_confirm_inline
from services import download_queue

dev_router = Router()

class DevStates(StatesGroup):
    waiting_for_top_limit = State()

@dev_router.callback_query(F.data == "cmd:dev_panel", F.from_user.id == ADMIN_ID)
async def dev_panel(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text("👨‍💻 أهلاً بك في لوحة المطور الخاصة بالإدارة:", reply_markup=get_developer_keyboard())

@dev_router.callback_query(F.data == "dev:stats", F.from_user.id == ADMIN_ID)
async def show_stats(callback: CallbackQuery):
    await callback.answer()
    users, usage, refs = get_stats()
    q_size = download_queue.qsize()
    msg = (
        f"📊 **إحصائيات البوت العامة:**\n\n"
        f"👥 إجمالي المستخدمين: `{users}`\n"
        f"📥 إجمالي التحميلات: `{usage}`\n"
        f"🔗 إجمالي الإحالات: `{refs}`\n\n"
        f"⚙️ **حالة Engine التحميل:**\n"
        f"📥 الطلبات المنتظرة بـ Queue: `{q_size}`\n"
        f"⚡ عدد Workers النواة: `3`"
    )
    await callback.message.edit_text(msg, parse_mode="Markdown", reply_markup=get_developer_keyboard())

@dev_router.callback_query(F.data == "dev:top_users", F.from_user.id == ADMIN_ID)
async def ask_top_limit(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(DevStates.waiting_for_top_limit)
    await callback.message.answer("🏆 أدخل عدد أكثر المستخدمين استخداماً المراد عرضهم (مثلاً: 5 أو 10 أو 70):")

@dev_router.message(DevStates.waiting_for_top_limit, F.from_user.id == ADMIN_ID)
async def top_users(message: Message, state: FSMContext):
    try:
        limit = int(message.text.strip())
        top = get_top_users(limit)
        text = f"🏆 **أفضل {limit} مستخدم حسب الاستخدام:**\n\n"
        for idx, row in enumerate(top, 1):
            name = row['first_name'] or "مستخدم"
            username_str = f" (@{row['username']})" if row['username'] else ""
            text += f"{idx}. **{name}**{username_str}\n   └ المعرف: `{row['user_id']}` | الاستخدامات: `{row['usage_count']}`\n"
        await message.answer(text, parse_mode="Markdown", reply_markup=get_developer_keyboard())
    except ValueError:
        await message.answer("❌ يرجى إدخال رقم صحيح.")
    await state.clear()

@dev_router.callback_query(F.data == "dev:coupons", F.from_user.id == ADMIN_ID)
async def coupon_mgmt(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text("اختر نوع الكوبون المراد إنشاؤه:", reply_markup=get_coupon_gen_inline())

@dev_router.callback_query(F.data.startswith("gen_coupon:"), F.from_user.id == ADMIN_ID)
async def generate_coupon(callback: CallbackQuery):
    await callback.answer()
    c_type = callback.data.split(":")[1]
    code = "COUPON-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    create_coupon(code, c_type)
    await callback.message.edit_text(
        f"🎉 **تم إنشاء كوبون {c_type} جديد بنجاح!**\n\nالكود:\n`{code}`",
        parse_mode="Markdown",
        reply_markup=get_developer_keyboard()
    )

@dev_router.callback_query(F.data == "dev:clean_prompt", F.from_user.id == ADMIN_ID)
async def clean_prompt(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "⚠️ **تأكيد مسح البيانات:**\n"
        "هل أنت تأكيداً تريد مسح جميع إحصائيات استخدام الخدمة والإحالات لبدء مسابقة جديدة؟\n"
        "*(سيتم الحفاظ الكامل على بيانات الحسابات والاشتراكات والعملات)*",
        parse_mode="Markdown",
        reply_markup=get_clean_confirm_inline()
    )

@dev_router.callback_query(F.data == "dev:confirm_clean", F.from_user.id == ADMIN_ID)
async def confirm_clean(callback: CallbackQuery):
    await callback.answer()
    reset_competition()
    await callback.message.edit_text(
        "✅ **تم تصفير جميع الاستخدامات والإحالات بنجاح وبدء مسابقة جديدة!**",
        reply_markup=get_developer_keyboard()
    )