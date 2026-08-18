import asyncio
import logging
from aiogram import Bot, Dispatcher

from config import BOT_TOKEN
from database import init_db
from users import users_router
from coins import coins_router
from coupons import coupons_router
from developer import dev_router
from services import worker
import os
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# خادم ويب وهمي لإرضاء Render وتوفير منفذ Port
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is live!")

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
