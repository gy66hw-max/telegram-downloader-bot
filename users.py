from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from database import get_or_create_user, check_sub_status, increment_usage
from keyboards import get_main_keyboard, get_rewards_inline, get_sub_purchase_inline
from services import download_queue

users_router = Router()

class UserStates(StatesGroup):
    waiting_for_link = State()

@users_router.message(CommandStart())
async def start_cmd(message: Message, command: CommandObject, state: FSMContext):
    await state.clear()
    referrer_id = None
    if command.args and command.args.startswith("ref_"):
        try:
            referrer_id = int(command.args.split("_")[1])
        except ValueError:
            pass
    
    get_or_create_user(
        user_id=message.from_user.id,
        first_name=message.from_user.first_name,
        username=message.from_user.username,
        referrer_id=referrer_id
    )
    await message.answer(
        "أهلاً بك في بوت تحميل الوسائط والخدمات الرقمية! 🚀\nاختر من القائمة أدناه للبدء:",
        reply_markup=get_main_keyboard(message.from_user.id)
    )

@users_router.callback_query(F.data == "cmd:main_menu")
async def back_home_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        "القائمة الرئيسية:",
        reply_markup=get_main_keyboard(callback.from_user.id)
    )

@users_router.callback_query(F.data == "cmd:my_sub")
async def my_sub(callback: CallbackQuery):
    await callback.answer()
    is_active, exp_dt = check_sub_status(callback.from_user.id)
    if is_active:
        await callback.message.edit_text(
            f"📅 **اشتراكك الحالي فعال!**\nتنتهي صلاحيته بتاريخ:\n`{exp_dt.strftime('%Y-%m-%d %H:%M')}`",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard(callback.from_user.id)
        )
    else:
        await callback.message.edit_text(
            "❌ **ليس لديك اشتراك فعال.**\nاختر أحد الخطط التالية لتفعيل اشتراكك باستخدام العملات:",
            parse_mode="Markdown",
            reply_markup=get_sub_purchase_inline()
        )

@users_router.callback_query(F.data == "cmd:ref_link")
async def ref_link(callback: CallbackQuery):
    await callback.answer()
    bot_info = await callback.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{callback.from_user.id}"
    await callback.message.edit_text(
        f"🔗 **رابط الإحالة الخاص بك:**\n`{link}`\n\n"
        f"🎁 **مكافآت نظام الإحالة:**\n"
        f"• عند دخول شخص عبر رابطك: تحصل على **+1 نقطة** فوراً.\n"
        f"• عند تفعيل هذا الشخص لاشتراك: تحصل على **+1 نقطة إضافية** (تصبح نقطتين إجمالاً).", 
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(callback.from_user.id)
    )

@users_router.callback_query(F.data == "cmd:use_service")
async def ask_for_link(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(UserStates.waiting_for_link)
    user = get_or_create_user(callback.from_user.id, callback.from_user.first_name, callback.from_user.username)
    
    text = (
        f"📊 **إحصائياتك الشخصية:**\n"
        f"• عدد مرات استخدامك للخدمة: `{user['usage_count']}` مرة\n\n"
        f"📥 **قم بإرسال رابط المحتوى المراد تحميله الآن:**\n"
        f"(Instagram, TikTok, YouTube, Facebook)"
    )
    await callback.message.answer(text, parse_mode="Markdown")

@users_router.message(UserStates.waiting_for_link, F.text.startswith("http"))
async def process_link(message: Message, state: FSMContext):
    status_msg = await message.answer("🔍 جاري فحص الرابط وإضافته لطابور التحميل...")
    increment_usage(message.from_user.id)
    await download_queue.put((message.chat.id, message.text.strip(), status_msg.message_id))
    await state.clear()