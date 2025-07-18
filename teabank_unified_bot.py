
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بوت TeaBank الموحد الكامل - جميع الميزات في ملف واحد
نظام ذكي للتشغيل التلقائي مع منع التضارب
"""

import os
import sys
import logging
import asyncio
import threading
import time
import json
import re
import urllib.parse
import requests
import subprocess
import signal
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

# إعداد المسار
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# إعداد السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(current_dir / 'teabank_unified.log')
    ]
)
logger = logging.getLogger(__name__)

# إعداد البوت
BOT_TOKEN = "7933415597:AAFZ8xxV7NZFOGAwe8-k-kWsJxDfbHyhslc"
os.environ["BOT_TOKEN"] = BOT_TOKEN

# ======================== البيانات والمتغيرات العامة ========================
user_data: Dict[int, Dict] = {}
automation_threads: Dict[str, threading.Thread] = {}
should_stop: Dict[str, bool] = {}

# ======================== خدمة TeaBank API ========================
class TeaBankService:
    """خدمة شاملة للتعامل مع TeaBank API"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1'
        })
        
        # إعداد retry strategy
        retry_strategy = requests.adapters.Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = requests.adapters.HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def extract_init_data(self, webapp_link: str) -> Optional[Dict]:
        """استخراج بيانات التهيئة من رابط الويب"""
        try:
            if 'tgWebAppData=' in webapp_link:
                encoded_data = webapp_link.split('tgWebAppData=')[1].split('&')[0]
                init_data = urllib.parse.unquote(encoded_data)
                return {"initData": init_data}
            return None
        except Exception as e:
            logger.error(f"خطأ في استخراج البيانات: {e}")
            return None

    def get_token(self, extracted_data: Dict) -> Optional[str]:
        """الحصول على توكن من TeaBank"""
        try:
            url = "https://api.teabank.io/user-api/"

            # استخراج بيانات المستخدم
            init_data = extracted_data["initData"]
            match = re.search(r'user=([^&]+)', init_data)
            if not match:
                return None

            user_encoded = match.group(1)
            user_decoded = urllib.parse.unquote(user_encoded)
            user_data = json.loads(user_decoded)

            payload = {
                "user": user_data,
                "initData": init_data,
                "id": str(user_data.get("id", "")),
                "first_name": user_data.get("first_name", ""),
                "last_name": user_data.get("last_name", ""),
                "task": "checkOrRegisterUser"
            }

            headers = {
                'Content-Type': 'application/json',
                'Referer': 'https://app.teabank.io/',
                'Origin': 'https://app.teabank.io'
            }

            response = self.session.post(url, json=payload, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return data.get('token')

            return None

        except Exception as e:
            logger.error(f"خطأ في الحصول على التوكن: {e}")
            return None

    def start_farming(self, init_data: str, token: str) -> Dict:
        """بدء التعدين"""
        try:
            url = "https://api.teabank.io/user-api/"

            payload = {
                "task": "startFarming",
                "token": token
            }

            headers = {
                'Content-Type': 'application/json',
                'Referer': 'https://app.teabank.io/',
                'Origin': 'https://app.teabank.io'
            }

            response = self.session.post(url, json=payload, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return {"success": True, "data": data}

            return {"success": False, "error": f"HTTP {response.status_code}"}

        except Exception as e:
            logger.error(f"خطأ في بدء التعدين: {e}")
            return {"success": False, "error": str(e)}

    def perform_task(self, init_data: str, token: str, task_id: int) -> Dict:
        """تنفيذ مهمة واحدة"""
        try:
            url = "https://api.teabank.io/tasks-api/"

            task_data = {
                "task": "completeTask",
                "token": token,
                "taskId": task_id,
                "userData": init_data
            }

            headers = {
                'Content-Type': 'application/json',
                'Referer': 'https://app.teabank.io/',
                'Origin': 'https://app.teabank.io'
            }

            response = self.session.post(url, json=task_data, headers=headers, timeout=10)

            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            elif response.status_code == 429:
                return {"success": False, "rate_limit": True}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def watch_ads(self, init_data: str, token: str) -> Dict:
        """مشاهدة الإعلانات"""
        try:
            url = "https://api.teabank.io/ads-api/"

            ads_data = {
                "task": "watchAd",
                "token": token,
                "userData": init_data
            }

            headers = {
                'Content-Type': 'application/json',
                'Referer': 'https://app.teabank.io/',
                'Origin': 'https://app.teabank.io'
            }

            response = self.session.post(url, json=ads_data, headers=headers, timeout=10)

            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

# ======================== خدمة إدارة العمليات التلقائية ========================
class AutomationService:
    """خدمة إدارة العمليات التلقائية"""

    def __init__(self):
        self.teabank_service = TeaBankService()

    def start_mining_automation(self, user_id: int, init_data: str, token: str):
        """بدء التعدين التلقائي"""
        def mining_worker():
            logger.info(f"🔥 بدء التعدين للمستخدم {user_id}")

            while not should_stop.get(f"mining_{user_id}", False):
                try:
                    # بدء التعدين
                    result = self.teabank_service.start_farming(init_data, token)

                    if result.get("success"):
                        logger.info(f"✅ تم بدء التعدين للمستخدم {user_id}")
                    else:
                        logger.error(f"❌ فشل التعدين للمستخدم {user_id}: {result.get('error', 'خطأ غير معروف')}")

                    # انتظار 3 ساعات (10800 ثانية)
                    for _ in range(10800):
                        if should_stop.get(f"mining_{user_id}", False):
                            break
                        time.sleep(1)

                except Exception as e:
                    logger.error(f"❌ خطأ في التعدين للمستخدم {user_id}: {e}")
                    time.sleep(300)  # انتظار 5 دقائق عند الخطأ

            logger.info(f"🛑 تم إيقاف التعدين للمستخدم {user_id}")

        thread = threading.Thread(target=mining_worker, daemon=True)
        thread.start()
        automation_threads[f"mining_{user_id}"] = thread

    def start_tasks_automation(self, user_id: int, init_data: str, token: str):
        """بدء المهام التلقائية"""
        def tasks_worker():
            logger.info(f"📋 بدء المهام للمستخدم {user_id}")

            while not should_stop.get(f"tasks_{user_id}", False):
                try:
                    # التحقق من عدم تشغيل الإعلانات
                    if f"ads_{user_id}" in automation_threads:
                        logger.info(f"⏸️ توقف المهام مؤقتاً للمستخدم {user_id} - الإعلانات تعمل")
                        time.sleep(60)
                        continue

                    # تنفيذ المهام من 1 إلى 257
                    successful_tasks = 0
                    for task_id in range(1, 258):
                        if should_stop.get(f"tasks_{user_id}", False):
                            break

                        # التحقق من بدء الإعلانات
                        if f"ads_{user_id}" in automation_threads:
                            logger.info(f"⏸️ توقف المهام للمستخدم {user_id} - بدء الإعلانات")
                            break

                        result = self.teabank_service.perform_task(init_data, token, task_id)

                        if result.get("success"):
                            successful_tasks += 1

                        time.sleep(1)  # انتظار قصير بين المهام

                    if successful_tasks > 0:
                        logger.info(f"✅ تم إنجاز {successful_tasks} مهمة للمستخدم {user_id}")

                    # انتظار 30 دقيقة قبل الدورة التالية
                    for _ in range(1800):
                        if should_stop.get(f"tasks_{user_id}", False):
                            break
                        time.sleep(1)

                except Exception as e:
                    logger.error(f"❌ خطأ في المهام للمستخدم {user_id}: {e}")
                    time.sleep(300)

            logger.info(f"🛑 تم إيقاف المهام للمستخدم {user_id}")

        thread = threading.Thread(target=tasks_worker, daemon=True)
        thread.start()
        automation_threads[f"tasks_{user_id}"] = thread

    def start_ads_automation(self, user_id: int, init_data: str, token: str):
        """بدء الإعلانات التلقائية - 10 مرات فقط"""
        def ads_worker():
            logger.info(f"📺 بدء الإعلانات للمستخدم {user_id}")

            completed_ads = 0
            target_ads = 10

            while not should_stop.get(f"ads_{user_id}", False) and completed_ads < target_ads:
                try:
                    # تنفيذ مشاهدة الإعلان
                    result = self.teabank_service.watch_ads(init_data, token)
                    
                    if result.get("success"):
                        completed_ads += 1
                        logger.info(f"✅ تم مشاهدة إعلان {completed_ads}/10 للمستخدم {user_id}")
                    else:
                        logger.warning(f"⚠️ فشل في مشاهدة الإعلان للمستخدم {user_id}")

                    # انتظار دقيقة بين الإعلانات
                    for _ in range(60):
                        if should_stop.get(f"ads_{user_id}", False):
                            break
                        time.sleep(1)

                except Exception as e:
                    logger.error(f"❌ خطأ في الإعلانات للمستخدم {user_id}: {e}")
                    time.sleep(300)

            # إزالة من القائمة عند الانتهاء
            if f"ads_{user_id}" in automation_threads:
                del automation_threads[f"ads_{user_id}"]

            logger.info(f"🏁 انتهت الإعلانات للمستخدم {user_id}: {completed_ads}/{target_ads}")

        thread = threading.Thread(target=ads_worker, daemon=True)
        thread.start()
        automation_threads[f"ads_{user_id}"] = thread

    def stop_operation(self, user_id: int, operation: str):
        """إيقاف عملية محددة"""
        key = f"{operation}_{user_id}"
        should_stop[key] = True
        if key in automation_threads:
            del automation_threads[key]
        logger.info(f"🛑 تم إيقاف {operation} للمستخدم {user_id}")

    def stop_all_operations(self, user_id: int):
        """إيقاف جميع العمليات للمستخدم"""
        operations = ["mining", "tasks", "ads"]
        for operation in operations:
            self.stop_operation(user_id, operation)
        logger.info(f"🛑 تم إيقاف جميع العمليات للمستخدم {user_id}")

# ======================== رسائل البوت والكيبورد ========================
class BotMessages:
    """رسائل البوت"""

    @staticmethod
    def welcome_message() -> str:
        return """
🎉 مرحباً بك في بوت TeaBank الموحد الذكي!

🤖 النظام الذكي المطور:
• 🔥 التعدين: 24/7 مع دورات 3 ساعات
• 📋 المهام: تنفيذ مستمر (1-257) 
• 📺 الإعلانات: 10 مرات بالضبط
• 🧠 تنسيق ذكي لمنع التضارب

📱 أرسل رابط TeaBank للبدء
⚙️ البوت الموحد جاهز للاستخدام!
        """

    @staticmethod
    def help_message() -> str:
        return """
🤖 <b>مساعدة بوت TeaBank الموحد</b>

📋 <b>الأوامر المتاحة:</b>
/start - بدء استخدام البوت
/menu - عرض القائمة الرئيسية
/help - عرض هذه المساعدة
/status - عرض حالة العمليات

📎 <b>طريقة الاستخدام:</b>
1. أرسل رابط TeaBank WebApp
2. استخدم الأزرار للتحكم في العمليات
3. راقب التقدم والحالة

🔧 <b>العمليات المتاحة:</b>
• التعدين التلقائي (يعمل 24/7)
• المهام التلقائية (1-257)
• الإعلانات (10 مرات)

⚡ البوت الموحد يعمل بنظام ذكي لتنسيق العمليات وتجنب التضارب
        """

    @staticmethod
    def status_message(user_id: int) -> str:
        mining_status = "🔄 يعمل" if f"mining_{user_id}" in automation_threads else "⏸️ متوقف"
        tasks_status = "🔄 يعمل" if f"tasks_{user_id}" in automation_threads else "⏸️ متوقف"
        ads_status = "🔄 يعمل" if f"ads_{user_id}" in automation_threads else "⏸️ متوقف"

        return f"""
📊 حالة العمليات:

🔥 التعدين: {mining_status}
📋 المهام: {tasks_status}  
📺 الإعلانات: {ads_status}

⏰ آخر تحديث: {datetime.now().strftime('%H:%M:%S')}
🤖 البوت الموحد يعمل بكفاءة عالية
        """

def create_main_keyboard(user_id: int):
    """إنشاء لوحة التحكم الرئيسية"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    keyboard = [
        [
            InlineKeyboardButton("🔥 بدء التعدين", callback_data=f"start_mining_{user_id}"),
            InlineKeyboardButton("⏹️ إيقاف التعدين", callback_data=f"stop_mining_{user_id}")
        ],
        [
            InlineKeyboardButton("📋 بدء المهام", callback_data=f"start_tasks_{user_id}"),
            InlineKeyboardButton("⏹️ إيقاف المهام", callback_data=f"stop_tasks_{user_id}")
        ],
        [
            InlineKeyboardButton("📺 بدء الإعلانات", callback_data=f"start_ads_{user_id}"),
            InlineKeyboardButton("⏹️ إيقاف الإعلانات", callback_data=f"stop_ads_{user_id}")
        ],
        [
            InlineKeyboardButton("🚀 بدء الكل", callback_data=f"start_all_{user_id}"),
            InlineKeyboardButton("🛑 إيقاف الكل", callback_data=f"stop_all_{user_id}")
        ],
        [
            InlineKeyboardButton("📊 الحالة", callback_data=f"status_{user_id}"),
            InlineKeyboardButton("🔄 تحديث", callback_data=f"menu_{user_id}")
        ]
    ]

    return InlineKeyboardMarkup(keyboard)

# ======================== معالجات البوت ========================
automation_service = AutomationService()
messages = BotMessages()

async def start_command(update, context):
    """معالج أمر /start"""
    await update.message.reply_text(messages.welcome_message())

async def help_command(update, context):
    """أمر المساعدة"""
    await update.message.reply_text(messages.help_message(), parse_mode='HTML')

async def menu_command(update, context):
    """أمر القائمة الرئيسية"""
    user_id = update.effective_user.id

    if user_id not in user_data:
        await update.message.reply_text(
            "🔗 يرجى إرسال رابط TeaBank WebApp أولاً",
            parse_mode='HTML'
        )
        return

    reply_markup = create_main_keyboard(user_id)
    await update.message.reply_text(
        "🏠 <b>القائمة الرئيسية - البوت الموحد</b>\n\n"
        "اختر العملية التي تريد القيام بها:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def status_command(update, context):
    """معالج أمر /status"""
    user_id = update.effective_user.id

    if user_id not in user_data:
        await update.message.reply_text("❌ لم تقم بإعداد البوت بعد\nأرسل رابط TeaBank للبدء")
        return

    await update.message.reply_text(messages.status_message(user_id))

async def message_handler(update, context):
    """معالج الرسائل"""
    text = update.message.text
    user_id = update.effective_user.id

    if "app.teabank.io" in text:
        await update.message.reply_text("🔄 جاري معالجة الرابط...")

        # استخراج البيانات
        extracted_data = automation_service.teabank_service.extract_init_data(text)
        if not extracted_data:
            await update.message.reply_text("❌ فشل في استخراج البيانات من الرابط")
            return

        # الحصول على التوكن
        token = automation_service.teabank_service.get_token(extracted_data)
        if not token:
            await update.message.reply_text("❌ فشل في الحصول على التوكن")
            return

        # حفظ بيانات المستخدم
        user_data[user_id] = {
            "link": text,
            "init_data": extracted_data["initData"],
            "token": token,
            "created_at": datetime.now()
        }

        reply_markup = create_main_keyboard(user_id)
        await update.message.reply_text(
            "✅ تم إعداد البوت الموحد بنجاح!\n\n"
            "🎛️ استخدم الأزرار للتحكم في العمليات:",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "❌ يرجى إرسال رابط TeaBank صحيح\n\n"
            "📱 الرابط يجب أن يحتوي على: app.teabank.io"
        )

async def button_handler(update, context):
    """معالج الأزرار"""
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = update.effective_user.id

    if user_id not in user_data:
        await query.edit_message_text("❌ لم تقم بإعداد البوت بعد")
        return

    user_info = user_data[user_id]

    if data.startswith("start_mining_"):
        automation_service.start_mining_automation(user_id, user_info["init_data"], user_info["token"])
        await query.edit_message_text("🔥 تم بدء التعدين التلقائي!\n\n⏰ سيعمل على دورات 3 ساعات")

    elif data.startswith("start_tasks_"):
        automation_service.start_tasks_automation(user_id, user_info["init_data"], user_info["token"])
        await query.edit_message_text("📋 تم بدء المهام التلقائية!\n\n🔄 سيعمل بشكل مستمر مع توقف ذكي للإعلانات")

    elif data.startswith("start_ads_"):
        automation_service.start_ads_automation(user_id, user_info["init_data"], user_info["token"])
        await query.edit_message_text("📺 تم بدء الإعلانات التلقائية!\n\n🎯 سيعمل 10 مرات فقط ثم يتوقف")

    elif data.startswith("start_all_"):
        automation_service.start_mining_automation(user_id, user_info["init_data"], user_info["token"])
        automation_service.start_tasks_automation(user_id, user_info["init_data"], user_info["token"])
        await query.edit_message_text("🚀 تم بدء جميع العمليات في البوت الموحد!\n\n🤖 النظام الذكي يعمل الآن")

    elif data.startswith("stop_"):
        if data.startswith("stop_all_"):
            automation_service.stop_all_operations(user_id)
            await query.edit_message_text("🛑 تم إيقاف جميع العمليات")
        else:
            operation = data.split("_")[1]
            automation_service.stop_operation(user_id, operation)
            await query.edit_message_text(f"⏹️ تم إيقاف {operation}")

    elif data.startswith("status_"):
        await query.edit_message_text(messages.status_message(user_id))

    elif data.startswith("menu_"):
        reply_markup = create_main_keyboard(user_id)
        await query.edit_message_text(
            "🏠 <b>القائمة الرئيسية - البوت الموحد</b>\n\n"
            "اختر العملية التي تريد القيام بها:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

# ======================== إدارة البوت الآمنة ========================
def kill_existing_bots():
    """إيقاف جميع نسخ البوت الموجودة"""
    try:
        bot_files = [
            "teabank_bot.py",
            "main.py", 
            "bot_main.py",
            "run_bot.py",
            "start_bot.py",
            "safe_start.py"
        ]
        
        for bot_file in bot_files:
            subprocess.run(
                ["pkill", "-f", f"python.*{bot_file}"],
                capture_output=True
            )
            
        time.sleep(3)
        logger.info("✅ تم إيقاف جميع نسخ البوت السابقة")
        
    except Exception as e:
        logger.error(f"❌ خطأ في إيقاف العمليات: {e}")

def signal_handler(signum, frame):
    """معالج إشارة الإيقاف"""
    logger.info("🛑 تم استلام إشارة الإيقاف")
    
    # إيقاف جميع العمليات التلقائية
    for key in list(should_stop.keys()):
        should_stop[key] = True
    
    # انتظار انتهاء العمليات
    for thread in automation_threads.values():
        if thread.is_alive():
            thread.join(timeout=5)
    
    logger.info("✅ تم إيقاف البوت بأمان")
    sys.exit(0)

# ======================== الدالة الرئيسية ========================
def main():
    """الدالة الرئيسية للبوت الموحد"""
    
    # تسجيل معالج الإشارات
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

        logger.info("🤖 بوت TeaBank الموحد الذكي")
        logger.info("=" * 60)
        logger.info("📋 الميزات المتاحة:")
        logger.info("• التعدين التلقائي (24/7)")
        logger.info("• تنفيذ المهام (1-257)")
        logger.info("• مشاهدة الإعلانات (10 مرات)")
        logger.info("• نظام ذكي موحد لمنع التضارب")
        logger.info("• جميع الخدمات في ملف واحد")
        logger.info("=" * 60)

        # إيقاف أي نسخ سابقة
        kill_existing_bots()

        # إنشاء التطبيق
        application = Application.builder().token(BOT_TOKEN).build()

        # إضافة المعالجات
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("menu", menu_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
        application.add_handler(CallbackQueryHandler(button_handler))

        # بدء البوت
        logger.info("🚀 بدء تشغيل البوت الموحد...")
        logger.info("📱 البوت جاهز لاستقبال الرسائل!")

        # تشغيل البوت
        application.run_polling(
            allowed_updates=None,
            drop_pending_updates=True
        )

    except Exception as e:
        logger.error(f"❌ خطأ في تشغيل البوت: {e}")

if __name__ == "__main__":
    main()
