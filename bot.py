import os
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

USERS_FILE = "users_data.json"

def load_users_data():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_users_data(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def user_exists(user_id):
    users = load_users_data()
    return any(user['user_id'] == user_id for user in users)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username or "ندارد"
    first_name = user.first_name or "نام"
    
    if not user_exists(user_id):
        users = load_users_data()
        users.append({
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "registration_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        save_users_data(users)
        print(f"✅ کاربر جدید: {first_name}")
    
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

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "option_1":
        await query.edit_message_text("✨ گزینه 1 انتخاب شد!")
    elif query.data == "option_2":
        await query.edit_message_text("⚡ گزینه 2 انتخاب شد!")
    elif query.data == "option_3":
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
            ]
        ])
        await query.edit_message_text("📚 گزینه 3", reply_markup=keyboard)
    elif query.data.startswith("sub_"):
        sub_num = query.data.split("_")[1]
        await query.edit_message_text(f"🔹 زیرشاخه {sub_num}")

def main():
    print("🚀 ربات شروع شد...")
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
