import asyncio
import os
import glob
import yt_dlp
from aiogram import Bot
from aiogram.types import FSInputFile
from database import get_cached_file, save_file_cache

download_queue = asyncio.Queue()

async def worker(bot: Bot, worker_id: int):
    while True:
        task = await download_queue.get()
        chat_id, url, status_msg_id = task
        try:
            # 1. التحقق أولاً إذا كان الرابط محفوضاً سابقاً في التخزين المؤقت (File ID)
            cached = get_cached_file(url)
            if cached:
                await bot.edit_message_text(
                    "⚡ تم العثور على الوسائط فوراً من الأرشيف! جاري الإرسال...", 
                    chat_id=chat_id, 
                    message_id=status_msg_id
                )
                file_id, file_type = cached['file_id'], cached['file_type']
                
                if file_type == 'video':
                    await bot.send_video(chat_id=chat_id, video=file_id)
                elif file_type == 'photo':
                    await bot.send_photo(chat_id=chat_id, photo=file_id)
                else:
                    await bot.send_document(chat_id=chat_id, document=file_id)
                
                await bot.delete_message(chat_id=chat_id, message_id=status_msg_id)
                continue

            # 2. إذا لم يكن الفيديو مخزناً، نبدأ عملية التحميل المباشر
            await bot.edit_message_text(
                f"⏳ (Worker {worker_id}) جاري التحميل ومعالجة الوسائط...", 
                chat_id=chat_id, 
                message_id=status_msg_id
            )
            
            file_path = await asyncio.to_thread(download_media, url, chat_id)
            
            if file_path and os.path.exists(file_path):
                await bot.edit_message_text("📤 جاري إرسال الملف...", chat_id=chat_id, message_id=status_msg_id)
                
                ext = os.path.splitext(file_path)[1].lower()
                input_file = FSInputFile(file_path)

                # إرسال الملف وتخزين الـ file_id للاستخدام المستقبلي
                if ext in ['.mp4', '.mov', '.mkv', '.webm']:
                    sent_msg = await bot.send_video(chat_id=chat_id, video=input_file)
                    if sent_msg and sent_msg.video:
                        save_file_cache(url, sent_msg.video.file_id, 'video')
                elif ext in ['.jpg', '.jpeg', '.png', '.webp']:
                    sent_msg = await bot.send_photo(chat_id=chat_id, photo=input_file)
                    if sent_msg and sent_msg.photo:
                        save_file_cache(url, sent_msg.photo[-1].file_id, 'photo')
                else:
                    sent_msg = await bot.send_document(chat_id=chat_id, document=input_file)
                    if sent_msg and sent_msg.document:
                        save_file_cache(url, sent_msg.document.file_id, 'document')
                
                if os.path.exists(file_path):
                    os.remove(file_path)
                
                await bot.delete_message(chat_id=chat_id, message_id=status_msg_id)
            else:
                await bot.edit_message_text("❌ تعذر تحميل هذا الرابط أو أن المحتوى غير متاح.", chat_id=chat_id, message_id=status_msg_id)
        
        except Exception as e:
            await bot.edit_message_text(f"❌ حدث خطأ أثناء التحميل: {str(e)[:60]}", chat_id=chat_id, message_id=status_msg_id)
        finally:
            download_queue.task_done()

def download_media(url: str, chat_id: int) -> str:
    out_dir = f"downloads/{chat_id}"
    os.makedirs(out_dir, exist_ok=True)
    out_template = os.path.join(out_dir, "media.%(ext)s")

    ydl_opts = {
        'outtmpl': out_template,
        'format': 'best', 
        'quiet': True,
        'no_warnings': True,
        'max_filesize': 50 * 1024 * 1024,
        'noplaylist': True,
        'nocheckcertificate': True,
        # المحافظة الكاملة على إعدادات تجاوز حظر YouTube و TikTok
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'mweb']
            },
            'tiktok': {
                'app_version': '30.0.0',
                'manifest_app_version': '30.0.0'
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Sec-Fetch-Mode': 'navigate',
        }
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.extract_info(url, download=True)

    files = glob.glob(f"{out_dir}/*")
    if files:
        return files[0]
    return None