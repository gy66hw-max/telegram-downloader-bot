import asyncio
import logging
import html
import os
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

from aiogram import Bot, Dispatcher
from aiogram.types import ErrorEvent

from config import BOT_TOKEN, ADMIN_ID
from database import init_db
from users import users_router
from coins import coins_router
from coupons import coupons_router
from developer import dev_router
from services import worker
from middlewares import AntiSpamMiddleware, BanCheckMiddleware

# خادم ويب وهمي متكامل لإرضاء Render وتمرير فحص الصحة (Health Check)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is live!")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()

    # إخفاء سجلات طلبات الفحص المتكررة لتعديل وتنظيف الـ Logs
    def log_message(self, format, *args):
        return

def run_health_check_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

# تشغيل خادم الويب في خيط مستقل (Thread) في الخلفية
Thread(target=run_health_check_server, daemon=True).start()

logging.basicConfig(level=logging.INFO)

async def main():
    # إنشاء جداول قاعدة البيانات
    init_db()
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # 1. تفعيل فحص المحظورين عالمياً
    dp.message.outer_middleware(BanCheckMiddleware())
    dp.callback_query.outer_middleware(BanCheckMiddleware())

    # 2. تفعيل نظام منع السبام (الفترة المسموحة: ثانية واحدة بين الطلبات)
    dp.message.middleware(AntiSpamMiddleware(limit=1.0))
    dp.callback_query.middleware(AntiSpamMiddleware(limit=1.0))

    # 3. معالج الأخطاء العام لمنع انهيار البوت وتنبيه المطور
    @dp.error()
    async def global_error_handler(event: ErrorEvent):
        logging.error(f"حدث خطأ غير متوقع: {event.exception}", exc_info=True)
        
        user = None
        if event.update.message:
            user = event.update.message.from_user
        elif event.update.callback_query:
            user = event.update.callback_query.from_user

        user_info = f"👤 المستخدم: {user.first_name} (<code>{user.id}</code>)" if user else "غير معروف"

        error_msg = (
            f"⚠️ <b>حدث خطأ برمجي في البوت!</b>\n\n"
            f"{user_info}\n"
            f"🛠️ الخطأ: <code>{html.escape(str(event.exception))}</code>"
        )
        
        try:
            await bot.send_message(chat_id=ADMIN_ID, text=error_msg, parse_mode="HTML")
        except Exception:
            pass

    # تسجيل الموجهات
    dp.include_router(users_router)
    dp.include_router(coins_router)
    dp.include_router(coupons_router)
    dp.include_router(dev_router)

    # تشغيل 3 عمال تزامنيين (Workers) لإدارة طابور التحميل
    for w_id in range(1, 4):
        asyncio.create_task(worker(bot, w_id))

    print("🚀 البوت يعمل بنجاح الآن...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
