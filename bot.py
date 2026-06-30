import os
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8722012735:AAFy-w5zfhxOPH1BgVA5ptUXgjDejG-FU8k"
USERS_FILE = "users_data.json"
IMAGES_FOLDER = "user_images"
FILES_FOLDER = "files"  # پوشه فایل‌ها

if not os.path.exists(IMAGES_FOLDER):
    os.makedirs(IMAGES_FOLDER)

if not os.path.exists(FILES_FOLDER):
    os.makedirs(FILES_FOLDER)


def load_users_data():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []


def save_users_data(users):
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"خطا: {e}")


def user_exists(user_id):
    users = load_users_data()
    return any(user['user_id'] == user_id for user in users)


async def download_profile_photo(context, user_id, username, first_name):
    try:
        photos = await context.bot.get_user_profile_photos(user_id, limit=1)
        
        if photos.total_count > 0:
            photo_file = await photos.photos[0][-1].get_file()
            safe_username = username if username != "نام کاربری ندارد" else first_name
            photo_filename = f"{IMAGES_FOLDER}/{user_id}_{safe_username}.jpg"
            
            await photo_file.download_to_drive(photo_filename)
            logger.info(f"✅ عکس: {photo_filename}")
            return photo_filename
        else:
            return None
    except Exception as e:
        logger.warning(f"خطا عکس: {e}")
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع ربات - منو اصلی"""
    user = update.effective_user
    user_id = user.id
    username = user.username or "نام کاربری ندارد"
    first_name = user.first_name or "نام"
    last_name = user.last_name or ""
    full_name = f"{first_name} {last_name}".strip()
    
    is_new_user = not user_exists(user_id)
    
    if is_new_user:
        photo_path = await download_profile_photo(context, user_id, username, first_name)
        
        user_data = {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "full_name": full_name,
            "is_bot": user.is_bot,
            "language_code": user.language_code or "نامشخص",
            "profile_photo": photo_path,
            "registration_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "deep_link_param": context.args[0] if context.args else None
        }
        
        users = load_users_data()
        users.append(user_data)
        save_users_data(users)
        
        logger.info(f"✅ کاربر: {full_name} ({user_id})")
        print(f"\n📝 ثبت شد: {full_name}\n   ID: {user_id}\n   @{username}\n")
    
    welcome_message = f"""
👋 سلام {first_name}!

به ربات من خوش‌آمدید! 🤖

لطفاً یکی از گزینه‌های زیر را انتخاب کنید:
"""
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎁 گزینه 1", callback_data="option_1"),
            InlineKeyboardButton("⚙️ گزینه 2", callback_data="option_2")
        ],
        [
            InlineKeyboardButton("📚 گزینه 3", callback_data="option_3")
        ]
    ])
    
    await update.message.reply_text(welcome_message, reply_markup=keyboard)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت کلیک روی دکمه‌ها"""
    query = update.callback_query
    user = query.from_user
    await query.answer()
    
    # گزینه 1
    if query.data == "option_1":
        text = f"""
✨ شما گزینه 1 را انتخاب کردید!

━━━━━━━━━━━━━━━━━━
👤 اطلاعات شما:
🆔 ID: {user.id}
📝 نام: {user.first_name}
📱 نام کاربری: @{user.username or 'ندارد'}

این گزینه برای نمایش پروفایل و اطلاعات شماست.
━━━━━━━━━━━━━━━━━━
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")]
        ])
        
        await query.edit_message_text(text=text, reply_markup=keyboard)
    
    # گزینه 2
    elif query.data == "option_2":
        text = """
⚡ شما گزینه 2 را انتخاب کردید!

━━━━━━━━━━━━━━━━━━
📋 محتوای گزینه 2:

این یک متن توضیحی برای گزینه 2 است.
می‌توانید اطلاعات مفیدی در اینجا قرار دهید.

✨ ویژگی‌های خاص:
• آیتم 1
• آیتم 2
• آیتم 3
━━━━━━━━━━━━━━━━━━
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")]
        ])
        
        await query.edit_message_text(text=text, reply_markup=keyboard)
    
    # گزینه 3 - منتقل به زیرشاخه‌ها
    elif query.data == "option_3":
        text = """
📚 گزینه 3 - زیرشاخه‌ها

لطفاً یکی از زیرشاخه‌های زیر را انتخاب کنید:
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔸 زیر 1", callback_data="sub_1"),
                InlineKeyboardButton("🔹 زیر 2", callback_data="sub_2")
            ],
            [
                InlineKeyboardButton("🔶 زیر 3", callback_data="sub_3"),
                InlineKeyboardButton("🟠 زیر 4", callback_data="sub_4")
            ],
            [
                InlineKeyboardButton("🟡 زیر 5", callback_data="sub_5"),
                InlineKeyboardButton("🟢 زیر 6", callback_data="sub_6")
            ],
            [
                InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")
            ]
        ])
        
        await query.edit_message_text(text=text, reply_markup=keyboard)
    
    # زیرشاخه 1 - با فایل
    elif query.data == "sub_1":
        text = """
🔸 زیرشاخه 1

━━━━━━━━━━━━━━━━━━
محتوای خاص زیرشاخه 1:

اینجا فایل‌های مربوط به این بخش قرار دارند.
برای دانلود فایل دکمه زیر را کلیک کنید.

✅ نکات مهم:
• نکته اول
• نکته دوم
• نکته سوم
━━━━━━━━━━━━━━━━━━
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 دانلود فایل", callback_data="download_file_1")],
            [InlineKeyboardButton("⬅️ بازگشت", callback_data="option_3")]
        ])
        
        await query.edit_message_text(text=text, reply_markup=keyboard)
    
    # زیرشاخه 2
    elif query.data == "sub_2":
        text = """
🔹 زیرشاخه 2

━━━━━━━━━━━━━━━━━━
محتوای خاص زیرشاخه 2:

این محتوا مخصوص دومین زیرشاخه است.
با ویژگی‌های منحصر به فرد خود.

📌 اطلاعات:
• اطلاع 1
• اطلاع 2
• اطلاع 3
━━━━━━━━━━━━━━━━━━
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 دانلود فایل", callback_data="download_file_2")],
            [InlineKeyboardButton("⬅️ بازگشت", callback_data="option_3")]
        ])
        
        await query.edit_message_text(text=text, reply_markup=keyboard)
    
    # زیرشاخه 3
    elif query.data == "sub_3":
        text = """
🔶 زیرشاخه 3

━━━━━━━━━━━━━━━━━━
محتوای خاص زیرشاخه 3:

این سومین زیرشاخه است.
دارای اطلاعات منحصر به فرد خود.

🎯 اهداف:
• هدف 1
• هدف 2
• هدف 3
━━━━━━━━━━━━━━━━━━
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 دانلود فایل", callback_data="download_file_3")],
            [InlineKeyboardButton("⬅️ بازگشت", callback_data="option_3")]
        ])
        
        await query.edit_message_text(text=text, reply_markup=keyboard)
    
    # زیرشاخه 4
    elif query.data == "sub_4":
        text = """
🟠 زیرشاخه 4

━━━━━━━━━━━━━━━━━━
محتوای خاص زیرشاخه 4:

این چهارمین زیرشاخه است.
با خصوصیات منحصر به فرد.

💡 ایده‌ها:
• ایده 1
• ایده 2
• ایده 3
━━━━━━━━━━━━━━━━━━
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 دانلود فایل", callback_data="download_file_4")],
            [InlineKeyboardButton("⬅️ بازگشت", callback_data="option_3")]
        ])
        
        await query.edit_message_text(text=text, reply_markup=keyboard)
    
    # زیرشاخه 5
    elif query.data == "sub_5":
        text = """
🟡 زیرشاخه 5

━━━━━━━━━━━━━━━━━━
محتوای خاص زیرشاخه 5:

این پنجمین زیرشاخه است.
دارای محتوای خاص خود.

⭐ ویژگی‌ها:
• ویژگی 1
• ویژگی 2
• ویژگی 3
━━━━━━━━━━━━━━━━━━
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 دانلود فایل", callback_data="download_file_5")],
            [InlineKeyboardButton("⬅️ بازگشت", callback_data="option_3")]
        ])
        
        await query.edit_message_text(text=text, reply_markup=keyboard)
    
    # زیرشاخه 6
    elif query.data == "sub_6":
        text = """
🟢 زیرشاخه 6

━━━━━━━━━━━━━━━━━━
محتوای خاص زیرشاخه 6:

این ششمین و آخرین زیرشاخه است.
محتوای نهایی و جامع.

🏆 بهترین‌ها:
• بهترین 1
• بهترین 2
• بهترین 3
━━━━━━━━━━━━━━━━━━
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 دانلود فایل", callback_data="download_file_6")],
            [InlineKeyboardButton("⬅️ بازگشت", callback_data="option_3")]
        ])
        
        await query.edit_message_text(text=text, reply_markup=keyboard)
    
    # دانلود فایل‌ها
    elif query.data.startswith("download_file_"):
        file_num = query.data.split("_")[-1]
        
        # نام‌های فایل‌ها
        files_info = {
            "1": {"name": "1.png", "display": "📄 زیرشاخه1"},
            "2": {"name": "2.txt", "display": "📄 زیرشاخه2"},
            "3": {"name": "document1", "display": "📄 زیرشاخه3"},
            "4": {"name": "document1", "display": "📄 زیرشاخه4"},
            "5": {"name": "document1", "display": "📄 زیرشاخه5"},
            "6": {"name": "document1", "display": "📄 زیرشاخه6"},
        }
        
        file_info = files_info.get(file_num, {})
        file_path = f"{FILES_FOLDER}/{file_info['name']}"
        
        # بررسی وجود فایل
        if os.path.exists(file_path):
            try:
                with open(file_path, 'rb') as f:
                    await query.message.reply_document(
                        document=f,
                        filename=file_info['name'],
                        caption=f"✅ {file_info['display']}\n\n دانلود شد!"
                    )
                logger.info(f"✅ فایل ارسال شد: {file_info['name']}")
            except Exception as e:
                await query.message.reply_text(f"❌ خطا در ارسال فایل: {e}")
                logger.error(f"خطا: {e}")
        else:
            await query.message.reply_text(
                f"❌ متاسفانه فایل '{file_info['name']}' در سیستم وجود ندارد!\n\n"
                f"📁 لطفاً فایل را در پوشه '{FILES_FOLDER}' قرار دهید."
            )
    
    # بازگشت به منو اصلی
    elif query.data == "back_to_menu":
        welcome_message = """
👋 خوش‌آمدید!

لطفاً یکی از گزینه‌های زیر را انتخاب کنید:
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎁 گزینه 1", callback_data="option_1"),
                InlineKeyboardButton("⚙️ گزینه 2", callback_data="option_2")
            ],
            [
                InlineKeyboardButton("📚 گزینه 3", callback_data="option_3")
            ]
        ])
        
        await query.edit_message_text(text=welcome_message, reply_markup=keyboard)


async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_users_data()
    msg = f"📊 کل: {len(users)}\n\n"
    
    for idx, u in enumerate(users, 1):
        msg += f"{idx}. {u['full_name']}\n   ID: {u['user_id']}\n   @{u['username']}\n   {u['registration_date']}\n\n"
    
    await update.message.reply_text(msg)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_users_data()
    total = len(users)
    with_photo = sum(1 for u in users if u['profile_photo'])
    
    msg = f"📈 آمار:\n👥 کل: {total}\n📸 عکس: {with_photo}"
    await update.message.reply_text(msg)


async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_users_data()
    if not users:
        await update.message.reply_text("❌ ندارد!")
        return
    
    data = {"export_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "total_users": len(users), "users": users}
    filename = f"users_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    with open(filename, 'rb') as f:
        await update.message.reply_document(document=f, filename=filename)


def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("users", users_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("export", export_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    print("\n🚀 ربات شروع شد...\n")
    print("📁 پوشه فایل‌ها: files/")
    print("   فایل‌های خود را در اینجا قرار دهید\n")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()