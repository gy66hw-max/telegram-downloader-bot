import time
from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject, Message, CallbackQuery
from config import ADMIN_ID
from database import is_user_banned

class AntiSpamMiddleware(BaseMiddleware):
    def __init__(self, limit: float = 1.5):
        self.limit = limit
        self.users = {}  # {user_id: [last_time, warning_count]}

    async def __call__(self, handler, event: TelegramObject, data: dict):
        user = data.get("event_from_user")
        bot: Bot = data.get("bot")

        if not user or user.id == ADMIN_ID:
            return await handler(event, data)

        current_time = time.time()
        user_id = user.id
        user_data = self.users.get(user_id, [0, 0])
        last_time, warnings = user_data[0], user_data[1]

        # إذا كانت الفترة بين الطلبات أقل من المسموح
        if current_time - last_time < self.limit:
            warnings += 1
            self.users[user_id] = [current_time, warnings]

            # عند التكرار المسيء (مثلاً 4 مرات متتالية) يتم تحذير الأدمن فوراً
            if warnings == 4:
                username = f"@{user.username}" if user.username else "لا يوجد"
                alert_text = (
                    f"🚨 <b>تنبيه محاولة سبام / هجوم!</b>\n\n"
                    f"👤 الاسم: <b>{user.first_name}</b>\n"
                    f"🏷️ اليوزر: {username}\n"
                    f"🆔 المعرف: <code>{user.id}</code>\n\n"
                    f"⚡ للحظر المباشر اضغط على الأمر التالي:\n"
                    f"<code>/ban {user.id}</code>"
                )
                await bot.send_message(chat_id=ADMIN_ID, text=alert_text, parse_mode="HTML")

            return  # تجاهل الطلب لحماية البوت من الضغط

        # إعادة الترتيب في حال التزم المستخدم بالوقت المسموح
        self.users[user_id] = [current_time, 0]
        return await handler(event, data)

class BanCheckMiddleware(BaseMiddleware):
    """فحص المحظورين قبل تنفيذ أي أمر في البوت"""
    async def __call__(self, handler, event: TelegramObject, data: dict):
        user = data.get("event_from_user")
        if user and is_user_banned(user.id):
            if isinstance(event, Message):
                await event.answer("❌ أنت محظور من استخدام هذا البوت.")
            elif isinstance(event, CallbackQuery):
                await event.answer("❌ حسابك محظور.", show_alert=True)
            return
        return await handler(event, data)
