import html
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.exceptions import TelegramBadRequest
from config import ADMIN_ID, DEV_USERNAME
from database import (
    get_or_create_user, check_sub_status, increment_usage, 
    get_user_ref_count, is_user_banned
)
from keyboards import get_main_keyboard, get_sub_purchase_inline
from services import download_queue

users_router = Router()

class UserStates(StatesGroup):
    waiting_for_link = State()

@users_router.message(CommandStart())
async def start_cmd(message: Message, command: CommandObject, state: FSMContext):
    await state.clear()

    # 1. فحص الحظر
    if is_user_banned(message.from_user.id):
        await message.answer("🚫 **عذراً، لقد تم حظرك من استخدام هذا البوت.**", parse_mode="Markdown")
        return

    referrer_id = None
    if command.args and command.args.startswith("ref_"):
        try:
            referrer_id = int(command.args.split("_")[1])
        except ValueError:
            pass
    
    user, is_new, referrer_info = get_or_create_user(
        user_id=message.from_user.id,
        first_name=message.from_user.first_name,
        username=message.from_user.username,
        referrer_id=referrer_id
    )

    if is_new:
        safe_name = html.escape(message.from_user.first_name or "مستخدم")
        username_str = f"@{message.from_user.username}" if message.from_user.username else "بدون معرف"
        
        if referrer_info:
            try:
                ref_msg = (
                    f"🎉 <b>إحالة جديدة!</b>\n\n"
                    f"👤 انضم <b>{safe_name}</b> عبر رابط الدعوة الخاص بك.\n"
                    f"🪙 تمت إضافة <b>+2 عملة</b> إلى رصيدك بنجاح!\n"
                    f"💡 <i>ستحصل على +3 عملات إضافية فور تفعيله لأي اشتراك (المجموع: 5 عملات).</i>"
                )
                await message.bot.send_message(chat_id=referrer_info['user_id'], text=ref_msg, parse_mode="HTML")
            except Exception as e:
                print(f"فشل إرسال إشعار الداعي: {e}")

            ref_name = html.escape(referrer_info['first_name'] or "مستخدم")
            ref_user = f"(@{html.escape(referrer_info['username'])})" if referrer_info['username'] else ""
            ref_status = f"🔗 <b>عن طريق إحالة من:</b> {ref_name} {ref_user} [<code>{referrer_info['user_id']}</code>]"
        else:
            ref_status = "🚪 <b>دخول مباشر</b> (بدون رابط إحالة)"

        admin_notice = (
            f"🔔 <b>انضم مستخدم جديد للبوت!</b>\n\n"
            f"👤 <b>الاسم:</b> {safe_name}\n"
            f"🏷️ <b>المعرف:</b> {username_str}\n"
            f"🆔 <b>المعرف الرقمي:</b> <code>{message.from_user.id}</code>\n\n"
            f"{ref_status}"
        )
        try:
            await message.bot.send_message(chat_id=ADMIN_ID, text=admin_notice, parse_mode="HTML")
        except Exception as e:
            print(f"فشل إرسال إشعار الأدمن: {e}")

    ref_count = get_user_ref_count(message.from_user.id)
    user_coins = user['coins']
    safe_user_name = html.escape(message.from_user.first_name or "مستخدم")

    welcome_text = (
        f"👋 <b>أهلاً بك يا {safe_user_name} في بوت الخدمات والتحميل السريع!</b>\n\n"
        f"📊 <b>إحصائيات حسابك:</b>\n"
        f"👥 <b>عدد الأشخاص الذين دخلوا عبر رابطك:</b> {ref_count} شخص\n"
        f"🪙 <b>رصيد عملاتك الحالي:</b> {user_coins} عملة\n\n"
        f"اختر من القائمة أدناه للبدء:"
    )

    await message.answer(welcome_text, parse_mode="HTML", reply_markup=get_main_keyboard(message.from_user.id))

@users_router.callback_query(F.data == "cmd:main_menu")
async def back_home_callback(callback: CallbackQuery, state: FSMContext):
    if is_user_banned(callback.from_user.id):
        await callback.answer("🚫 أنت محظور من استخدام البوت", show_alert=True)
        return
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        "القائمة الرئيسية:",
        reply_markup=get_main_keyboard(callback.from_user.id)
    )

@users_router.callback_query(F.data == "cmd:my_sub")
async def my_sub(callback: CallbackQuery):
    if is_user_banned(callback.from_user.id):
        await callback.answer("🚫 أنت محظور من استخدام البوت", show_alert=True)
        return
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
    if is_user_banned(callback.from_user.id):
        await callback.answer("🚫 أنت محظور من استخدام البوت", show_alert=True)
        return
    
    bot_info = await callback.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{callback.from_user.id}"
    
    ref_text = (
        f"🔗 <b>رابط الإحالة الخاص بك:</b>\n"
        f"<code>{link}</code>\n\n"
        f"🎁 <b>نظام مكافآت الإحالة الجديد:</b>\n"
        f"• عند دخول شخص عبر رابطك: تحصل على <b>+2 عملة</b> فوراً.\n"
        f"• عند تفعيل هذا الشخص لأي اشتراك: تحصل على <b>+3 عملات إضافية</b>.\n"
        f"✨ <i>إجمالي المكافأة: <b>5 عملات</b> لكل شخص تدعوه!</i>"
    )
    
    try:
        await callback.message.edit_text(
            ref_text, 
            parse_mode="HTML",
            reply_markup=get_main_keyboard(callback.from_user.id)
        )
        await callback.answer() # تم التعديل بنجاح
    except TelegramBadRequest:
        # إذا لم يتغير المحتوى، لا تفعل شيئاً سوى إغلاق التنبيه
        await callback.answer("أنت تشاهد الرسالة بالفعل.")
        
@users_router.callback_query(F.data == "cmd:use_service")
async def ask_for_link(callback: CallbackQuery, state: FSMContext):
    if is_user_banned(callback.from_user.id):
        await callback.answer("🚫 أنت محظور من استخدام البوت", show_alert=True)
        return
    await callback.answer()
    
    is_active, _ = check_sub_status(callback.from_user.id)
    if not is_active:
        warning_msg = (
            f"⚠️ <b>يرجى الاشتراك أولاً لاستخدام خدمات التحميل!</b>\n\n"
            f"للتواصل مع المطور أو لتفعيل الاشتراك المباشر:\n"
            f"📩 <b>المطور:</b> @{DEV_USERNAME}\n\n"
            f"👇 <b>أو اختر إحدى الباقات التالية للتفعيل باستخدام العملات:</b>"
        )
        await callback.message.answer(warning_msg, parse_mode="HTML", reply_markup=get_sub_purchase_inline())
        return

    await state.set_state(UserStates.waiting_for_link)
    user, _, _ = get_or_create_user(callback.from_user.id, callback.from_user.first_name, callback.from_user.username)
    
    text = (
        f"📊 <b>إحصائياتك الشخصية:</b>\n"
        f"• عدد مرات استخدامك للخدمة: <code>{user['usage_count']}</code> مرة\n\n"
        f"📥 <b>قم بإرسال رابط المحتوى المراد تحميله الآن:</b>\n"
        f"(Instagram, TikTok, YouTube, Facebook)"
    )
    await callback.message.answer(text, parse_mode="HTML")

@users_router.message(F.text.startswith("http"))
async def process_link(message: Message, state: FSMContext):
    if is_user_banned(message.from_user.id):
        await message.answer("🚫 **عذراً، أنت محظور من استخدام البوت.**", parse_mode="Markdown")
        return

    is_active, _ = check_sub_status(message.from_user.id)
    if not is_active:
        await state.clear()
        warning_msg = (
            f"⚠️ <b>يرجى الاشتراك أولاً لاستخدام البوت وتحميل الروابط!</b>\n\n"
            f"للتواصل مع المطور أو لتفعيل الاشتراك المباشر:\n"
            f"📩 <b>المطور:</b> @{DEV_USERNAME}\n\n"
            f"👇 <b>أو يمكنك الاشتراك عبر باقات العملات أدناه:</b>"
        )
        await message.answer(warning_msg, parse_mode="HTML", reply_markup=get_sub_purchase_inline())
        return

    status_msg = await message.answer("🔍 جاري فحص الرابط وإضافته لطابور التحميل...")
    increment_usage(message.from_user.id)
    await download_queue.put((message.chat.id, message.text.strip(), status_msg.message_id))
    await state.clear()
