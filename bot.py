import os
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ BOT_TOKEN not found!")
    exit(1)

USERS_FILE = "users_data.json"
IMAGES_FOLDER = "user_images"
FILES_FOLDER = "files"

for folder in [IMAGES_FOLDER, FILES_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)


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
            safe_username = username if username != "ندارد" else first_name
            photo_filename = f"{IMAGES_FOLDER}/{user_id}_{safe_username}.jpg"
            await photo_file.download_to_drive(photo_filename)
            return photo_filename
        return None
    except Exception as e:
        logger.warning(f"خطا عکس: {e}")
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username or "ندارد"
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
            "profile_photo": photo_path,
            "registration_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        
        users = load_users_data()
        users.append(user_data)
        save_users_data(users)
        print(f"✅ کاربر جدید: {full_name}")
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎁 گزینه 1", callback_data="option_1"),
            InlineKeyboardButton("⚙️ گزینه 2", callback_data="option_2")
        ],
        [
            InlineKeyboardButton("📚 گزینه 3", callback_data="option_3")
        ]
    ])
    
    await update.message.reply_text(
        f"👋 سلام {first_name}!\n\nخوش‌آمدید! 🤖",
        reply_markup=keyboard
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /help"""
    help_text = """
🤖 دستورات ربات:

/start - شروع ربات
/help - راهنما
"""
    await update.message.reply_text(help_text)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "option_1":
        text = f"""
✨ گزینه 1

درباره شما:
👤 نام: {query.from_user.first_name}
🆔 ID: {query.from_user.id}
"""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_menu")]
        ])
        await query.edit_message_text(text=text, reply_markup=keyboard)
    
    elif query.data == "option_2":
        text = "⚡ محتوای گزینه 2"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_menu")]
        ])
        await query.edit_message_text(text=text, reply_markup=keyboard)
    
    elif query.data == "option_3":
        text = "📚 گزینه 3 - زیرشاخه‌ها"
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
                InlineKeyboardButton("🔙 بازگشت", callback_data="back_menu")
            ]
        ])
        await query.edit_message_text(text=text, reply_markup=keyboard)
    
    elif query.data.startswith("sub_"):
        sub_num = query.data.split("_")[1]
        text = f"🔹 زیرشاخه {sub_num}\n\nمحتوای خاص این قسمت"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ بازگشت", callback_data="option_3")]
        ])
        await query.edit_message_text(text=text, reply_markup=keyboard)
    
    elif query.data == "back_menu":
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎁 گزینه 1", callback_data="option_1"),
                InlineKeyboardButton("⚙️ گزینه 2", callback_data="option_2")
            ],
            [
                InlineKeyboardButton("📚 گزینه 3", callback_data="option_3")
            ]
        ])
        await query.message.edit_text(
            "👋 خوش‌آمدید!\n\nگزینه‌ای انتخاب کنید:",
            reply_markup=keyboard
        )


def main():
    print("🚀 ربات شروع شد...")
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
