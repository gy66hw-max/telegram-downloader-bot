import random
import string
import html
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from config import ADMIN_ID
from database import (
    create_coupon, get_stats, get_top_users, 
    reset_competition, ban_user, unban_user
)
from keyboards import get_developer_keyboard, get_coupon_gen_inline, get_clean_confirm_inline
from services import download_queue

dev_router = Router()

class DevStates(StatesGroup):
    waiting_for_top_limit = State()

# 🚫 أمر حظر مستخدم (مثال: /ban 123456789 أو /ban @username)
@dev_router.message(Command("ban"), F.from_user.id == ADMIN_ID)
async def cmd_ban_user(message: Message, command: CommandObject):
    if not command.args:
        await message.answer(
            "❌ <b>طريقة الاستخدام الصحيحة:</b>\n"
            "• <code>/ban 123456789</code>\n"
            "• <code>/ban @username</code>",
            parse_mode="HTML"
        )
        return
    
    target = command.args.strip()
    clean_target = target.lstrip("@")
    
    if clean_target == str(ADMIN_ID):
        await message.answer("❌ لا يمكنك حظر نفسك!")
        return

    success = ban_user(target)
    if success:
        await message.answer(f"🚫 <b>تم حظر المستخدم بنجاح!</b>\n🎯 الهدف: <code>{target}</code>", parse_mode="HTML")
    else:
        await message.answer(f"❌ لم يتم العثور على مستخدم بهذا المعرف أو اليوزر: <code>{target}</code>", parse_mode="HTML")

# ✅ أمر إلغاء حظر مستخدم (مثال: /unban 123456789 أو /unban @username)
@dev_router.message(Command("unban"), F.from_user.id == ADMIN_ID)
async def cmd_unban_user(message: Message, command: CommandObject):
    if not command.args:
        await message.answer(
            "❌ <b>طريقة الاستخدام الصحيحة:</b>\n"
            "• <code>/unban 123456789</code>\n"
            "• <code>/unban @username</code>",
            parse_mode="HTML"
        )
        return
    
    target = command.args.strip()
    success = unban_user(target)
    if success:
        await message.answer(f"✅ <b>تم إلغاء حظر المستخدم بنجاح!</b>\n🎯 الهدف: <code>{target}</code>", parse_mode="HTML")
    else:
        await message.answer(f"❌ لم يتم العثور على مستخدم بهذا المعرف أو اليوزر: <code>{target}</code>", parse_mode="HTML")

@dev_router.callback_query(F.data == "cmd:dev_panel", F.from_user.id == ADMIN_ID)
async def dev_panel(callback: CallbackQuery):
    await callback.answer()
    panel_text = (
        "👨‍💻 <b>أهلاً بك في لوحة المطور الخاصة بالإدارة:</b>\n\n"
        "🛠️ <b>أوامر الحظر المباشرة:</b>\n"
        "• <code>/ban ID أو @username</code> : لحظر مستخدم\n"
        "• <code>/unban ID أو @username</code> : لإلغاء حظر مستخدم"
    )
    await callback.message.edit_text(panel_text, parse_mode="HTML", reply_markup=get_developer_keyboard())

@dev_router.callback_query(F.data == "dev:stats", F.from_user.id == ADMIN_ID)
async def show_stats(callback: CallbackQuery):
    await callback.answer()
    users, usage, refs = get_stats()
    q_size = download_queue.qsize()
    msg = (
        f"📊 <b>إحصائيات البوت العامة:</b>\n\n"
        f"👥 إجمالي المستخدمين: <code>{users}</code>\n"
        f"📥 إجمالي التحميلات: <code>{usage}</code>\n"
        f"🔗 إجمالي الإحالات: <code>{refs}</code>\n\n"
        f"⚙️ <b>حالة Engine التحميل:</b>\n"
        f"📥 الطلبات المنتظرة بـ Queue: <code>{q_size}</code>\n"
        f"⚡ عدد Workers النواة: <code>3</code>"
    )
    await callback.message.edit_text(msg, parse_mode="HTML", reply_markup=get_developer_keyboard())

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
        text = f"🏆 <b>أفضل {limit} مستخدم حسب الاستخدام:</b>\n\n"
        for idx, row in enumerate(top, 1):
            name = html.escape(row['first_name'] or "مستخدم")
            username_str = f" (@{html.escape(row['username'])})" if row['username'] else ""
            text += f"{idx}. <b>{name}</b>{username_str}\n   └ المعرف: <code>{row['user_id']}</code> | الاستخدامات: <code>{row['usage_count']}</code>\n"
        await message.answer(text, parse_mode="HTML", reply_markup=get_developer_keyboard())
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
        f"🎉 <b>تم إنشاء كوبون {c_type} جديد بنجاح!</b>\n\nالكود:\n<code>{code}</code>",
        parse_mode="HTML",
        reply_markup=get_developer_keyboard()
    )

@dev_router.callback_query(F.data == "dev:clean_prompt", F.from_user.id == ADMIN_ID)
async def clean_prompt(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "⚠️ <b>تأكيد مسح البيانات:</b>\n"
        "هل أنت تأكيداً تريد مسح جميع إحصائيات استخدام الخدمة والإحالات لبدء مسابقة جديدة؟\n"
        "<i>(سيتم الحفاظ الكامل على بيانات الحسابات والاشتراكات والعملات)</i>",
        parse_mode="HTML",
        reply_markup=get_clean_confirm_inline()
    )

@dev_router.callback_query(F.data == "dev:confirm_clean", F.from_user.id == ADMIN_ID)
async def confirm_clean(callback: CallbackQuery):
    await callback.answer()
    reset_competition()
    await callback.message.edit_text(
        "✅ <b>تم تصفير جميع الاستخدامات والإحالات بنجاح وبدء مسابقة جديدة!</b>",
        reply_markup=get_developer_keyboard()
    )
