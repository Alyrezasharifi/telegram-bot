import os
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

USERS_FILE = "users_data.json"
FILES_FOLDER = "uploaded_files"

if not os.path.exists(FILES_FOLDER):
    os.makedirs(FILES_FOLDER)

FILES_DB = "files_db.json"

def load_files_db():
    if os.path.exists(FILES_DB):
        try:
            with open(FILES_DB, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_files_db(data):
    with open(FILES_DB, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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
            InlineKeyboardButton("𓇳𓄂", callback_data="option_1"),
            InlineKeyboardButton("𓅊𓂍", callback_data="option_2")
        ],
        [
            InlineKeyboardButton("°8", callback_data="option_3")
        ]
    ])
    
    await update.message.reply_text(
        f" {first_name}!\n\nu R in! 🤖",
        reply_markup=keyboard
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "option_1":
        await query.edit_message_text("nope!")
    
    elif query.data == "option_2":
        await query.edit_message_text("R u serious?!")
    
    elif query.data == "option_3":
        text = "click on 4"
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔸 زیر 1", callback_data="sub_1"),
                InlineKeyboardButton("🔹 زیر 2", callback_data="sub_2")
            ],
            [
                InlineKeyboardButton("🔶 زیر 3", callback_data="sub_3"),
                InlineKeyboardButton("Do u trust me?💀", callback_data="sub_4")
            ],
            [
                InlineKeyboardButton("🟡 زیر 5", callback_data="sub_5"),
                InlineKeyboardButton("🟢 زیر 6", callback_data="sub_6")
            ]
        ])
        await query.edit_message_text(text=text, reply_markup=keyboard)
    
    # 6 زیرشاخه اصلی
    elif query.data.startswith("sub_") and len(query.data) == 5:
        sub_num = query.data.split("_")[1]
        
        text = f"🔹 زیرشاخه {sub_num}\n\n13 زیر‌زیرشاخه را انتخاب کنید:"
        
        # 13 زیر‌زیرشاخه برای هر زیرشاخه
        buttons = []
        for i in range(1, 14):
            buttons.append(InlineKeyboardButton(f"📌 {i}", callback_data=f"subsub_{sub_num}_{i}"))
            if i % 2 == 0:
                buttons_row = buttons[i-2:i]
                keyboard_buttons = [buttons_row]
        
        # اضافه کردن دکمه‌های دو تایی
        keyboard_buttons = []
        for i in range(1, 14, 2):
            if i + 1 <= 13:
                keyboard_buttons.append([
                    InlineKeyboardButton(f"📌 {i}", callback_data=f"subsub_{sub_num}_{i}"),
                    InlineKeyboardButton(f"📌 {i+1}", callback_data=f"subsub_{sub_num}_{i+1}")
                ])
            else:
                keyboard_buttons.append([
                    InlineKeyboardButton(f"📌 {i}", callback_data=f"subsub_{sub_num}_{i}")
                ])
        
        keyboard_buttons.append([InlineKeyboardButton("⬅️ بازگشت", callback_data="option_3")])
        keyboard = InlineKeyboardMarkup(keyboard_buttons)
        
        await query.edit_message_text(text=text, reply_markup=keyboard)
    
    # 13 زیر‌زیرشاخه
    elif query.data.startswith("subsub_"):
        parts = query.data.split("_")
        sub_num = parts[1]
        subsub_num = parts[2]
        
        files_db = load_files_db()
        file_key = f"sub_{sub_num}_subsub_{subsub_num}"
        
        text = f"📌 زیر‌زیرشاخه {subsub_num} از زیرشاخه {sub_num}\n\n"
        
        # نمایش فایل‌های موجود
        if file_key in files_db and files_db[file_key]:
            text += "📂 فایل‌های موجود:\n"
            for i, file_info in enumerate(files_db[file_key], 1):
                text += f"{i}. {file_info['name']}\n"
        else:
            text += "❌ هنوز فایلی آپلود نشده\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 دانلود فایل", callback_data=f"download_{sub_num}_{subsub_num}")],
            [InlineKeyboardButton("⬅️ بازگشت", callback_data=f"sub_{sub_num}")]
        ])
        await query.edit_message_text(text=text, reply_markup=keyboard)
    
    elif query.data.startswith("download_"):
        parts = query.data.split("_")
        sub_num = parts[1]
        subsub_num = parts[2]
        
        files_db = load_files_db()
        file_key = f"sub_{sub_num}_subsub_{subsub_num}"
        
        if file_key not in files_db or not files_db[file_key]:
            await query.message.reply_text("❌ هیچ فایلی برای دانلود وجود ندارد!")
            return
        
        # نمایش دکمه‌های دانلود برای هر فایل
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"📄 {file_info['name']}", callback_data=f"get_file_{sub_num}_{subsub_num}_{i}")]
            for i, file_info in enumerate(files_db[file_key])
        ])
        keyboard.inline_keyboard.append([InlineKeyboardButton("⬅️ بازگشت", callback_data=f"subsub_{sub_num}_{subsub_num}")])
        
        await query.edit_message_text(
            text=f"📥 فایل‌های این بخش:",
            reply_markup=keyboard
        )
    
    elif query.data.startswith("get_file_"):
        parts = query.data.split("_")
        sub_num = parts[2]
        subsub_num = parts[3]
        file_idx = int(parts[4])
        
        files_db = load_files_db()
        file_key = f"sub_{sub_num}_subsub_{subsub_num}"
        
        if file_key in files_db and file_idx < len(files_db[file_key]):
            file_info = files_db[file_key][file_idx]
            file_path = file_info['path']
            
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'rb') as f:
                        await query.message.reply_document(
                            document=f,
                            filename=file_info['name'],
                            caption=f"✅ فایل: {file_info['name']}"
                        )
                except Exception as e:
                    await query.message.reply_text(f"❌ خطا: {e}")
            else:
                await query.message.reply_text("❌ فایل حذف شده است!")

async def handle_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت فایل آپلود شده"""
    message = update.message
    
    if message.document:
        file = message.document
        file_name = file.file_name
        
        # دریافت فایل
        new_file = await context.bot.get_file(file.file_id)
        
        # ذخیره فایل
        file_path = os.path.join(FILES_FOLDER, file_name)
        await new_file.download_to_drive(file_path)
        
        # نمایش منوی انتخاب زیرشاخه
        keyboard_buttons = []
        for i in range(1, 7, 2):
            if i + 1 <= 6:
                keyboard_buttons.append([
                    InlineKeyboardButton(f"🔹 زیر {i}", callback_data=f"upload_select_sub_{i}"),
                    InlineKeyboardButton(f"🔹 زیر {i+1}", callback_data=f"upload_select_sub_{i+1}")
                ])
            else:
                keyboard_buttons.append([
                    InlineKeyboardButton(f"🔹 زیر {i}", callback_data=f"upload_select_sub_{i}")
                ])
        
        keyboard = InlineKeyboardMarkup(keyboard_buttons)
        
        # ذخیره مسیر فایل در context
        context.user_data['uploaded_file'] = {
            'name': file_name,
            'path': file_path
        }
        
        await message.reply_text(
            f"📄 فایل '{file_name}' دریافت شد!\n\n"
            "این فایل را برای کدام زیرشاخه اصلی ذخیره کنم؟",
            reply_markup=keyboard
        )
    else:
        await message.reply_text("❌ لطفاً فایل را آپلود کنید!")

async def handle_upload_select_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """انتخاب زیرشاخه برای آپلود"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("upload_select_sub_"):
        sub_num = query.data.split("_")[-1]
        
        context.user_data['upload_sub'] = sub_num
        
        # نمایش منوی انتخاب زیر‌زیرشاخه
        keyboard_buttons = []
        for i in range(1, 14, 2):
            if i + 1 <= 13:
                keyboard_buttons.append([
                    InlineKeyboardButton(f"📌 {i}", callback_data=f"upload_select_subsub_{i}"),
                    InlineKeyboardButton(f"📌 {i+1}", callback_data=f"upload_select_subsub_{i+1}")
                ])
            else:
                keyboard_buttons.append([
                    InlineKeyboardButton(f"📌 {i}", callback_data=f"upload_select_subsub_{i}")
                ])
        
        keyboard = InlineKeyboardMarkup(keyboard_buttons)
        
        await query.edit_message_text(
            f"اکنون زیر‌زیرشاخه را برای زیرشاخه {sub_num} انتخاب کنید:",
            reply_markup=keyboard
        )

async def handle_upload_select_subsub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """انتخاب زیر‌زیرشاخه و ذخیره فایل"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("upload_select_subsub_"):
        subsub_num = query.data.split("_")[-1]
        
        if 'uploaded_file' not in context.user_data or 'upload_sub' not in context.user_data:
            await query.message.reply_text("❌ ابتدا فایل را آپلود کنید!")
            return
        
        file_info = context.user_data['uploaded_file']
        sub_num = context.user_data['upload_sub']
        
        # ذخیره در پایگاه داده
        files_db = load_files_db()
        file_key = f"sub_{sub_num}_subsub_{subsub_num}"
        
        if file_key not in files_db:
            files_db[file_key] = []
        
        files_db[file_key].append({
            'name': file_info['name'],
            'path': file_info['path'],
            'upload_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        save_files_db(files_db)
        
        await query.edit_message_text(
            f"✅ فایل '{file_info['name']}' برای زیرشاخه {sub_num} → زیر‌زیرشاخه {subsub_num} ذخیره شد!\n\n"
            f"کاربران می‌توانند این فایل را دانلود کنند."
        )
        
        # پاک کردن فایل موقت از context
        del context.user_data['uploaded_file']
        del context.user_data['upload_sub']

def main():
    print("🚀 ربات شروع شد...")
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(CallbackQueryHandler(handle_upload_select_sub, pattern="^upload_select_sub_"))
    application.add_handler(CallbackQueryHandler(handle_upload_select_subsub, pattern="^upload_select_subsub_"))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_file_upload))
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
