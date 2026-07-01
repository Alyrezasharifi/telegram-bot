import os
import json
import io
import csv
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ---- پیکربندی و مسیرها ----
BOT_TOKEN = os.getenv("BOT_TOKEN") or "YOUR_BOT_TOKEN_HERE"
ADMIN_FILE = "admin.json"           # برای ذخیره آیدی Admin در زمان اجرا (اختیاری)
USERS_FILE = "users_data.json"
FILES_DB = "files_db.json"
FILES_FOLDER = "uploaded_files"
PHOTOS_FOLDER = "user_photos"

os.makedirs(FILES_FOLDER, exist_ok=True)
os.makedirs(PHOTOS_FOLDER, exist_ok=True)

# ---- S3 configuration (اختیاری) ----
# اگر می‌خواهید از S3 استفاده کنید، این envها را ست کنید:
# AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION (اختیاری)، S3_BUCKET
S3_BUCKET = os.getenv("S3_BUCKET")
AWS_REGION = os.getenv("AWS_REGION")
USE_S3 = bool(S3_BUCKET)

s3_client = None
if USE_S3:
    try:
        session_kwargs = {}
        # boto3 از envها استفاده می‌کند؛ نیازی به ست کردن از اینجا نیست مگر بخوای مشخص بزنی
        if AWS_REGION:
            session_kwargs["region_name"] = AWS_REGION
        s3_client = boto3.client("s3", **session_kwargs)
        # می‌توان تست اولیه‌ای هم انجام داد اما از خطاهای بعدی مدیریت می‌کنیم
    except Exception as e:
        print("خطا در ساخت S3 client:", e)
        s3_client = None
        USE_S3 = False

# ---- بارگذاری/ذخیره Admin ----
def load_admin_id() -> int:
    env = os.getenv("ADMIN_ID")
    if env:
        try:
            return int(env)
        except:
            pass
    if os.path.exists(ADMIN_FILE):
        try:
            with open(ADMIN_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                return int(d.get("admin_id", 0))
        except:
            return 0
    return 0

def save_admin_id(admin_id: int):
    with open(ADMIN_FILE, "w", encoding="utf-8") as f:
        json.dump({"admin_id": admin_id}, f, ensure_ascii=False, indent=2)

# مقدار اولیه Admin (قابل بروزرسانی در زمان اجرا)
ADMIN_ID = load_admin_id()

# ---- توابع کمکی برای JSON DB ----
def load_json_file(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default

def save_json_file(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_users_data():
    return load_json_file(USERS_FILE, [])

def save_users_data(users):
    save_json_file(USERS_FILE, users)

def load_files_db():
    return load_json_file(FILES_DB, {})

def save_files_db(data):
    save_json_file(FILES_DB, data)

def find_user_record(users_list, user_id):
    for idx, u in enumerate(users_list):
        if u.get("user_id") == user_id:
            return idx, u
    return None, None

def is_admin(user_id):
    return ADMIN_ID != 0 and user_id == ADMIN_ID

# ---- S3 helpers (async wrapper around boto3) ----
async def upload_file_to_s3_async(local_path: str, s3_key: str) -> Optional[str]:
    """بارگذاری فایل به S3 و برگرداندن s3_key (یا None در صورت خطا).
       در صورت موفقیت، لینک presigned برای دانلود قابل تولید است."""
    if not s3_client or not S3_BUCKET:
        return None
    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(None, s3_client.upload_file, local_path, S3_BUCKET, s3_key)
        return s3_key
    except Exception as e:
        print("S3 upload error:", e)
        return None

def generate_presigned_url(s3_key: str, expires_in: int = 3600) -> Optional[str]:
    if not s3_client or not S3_BUCKET:
        return None
    try:
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": s3_key},
            ExpiresIn=expires_in,
        )
        return url
    except (BotoCoreError, ClientError) as e:
        print("Error generating presigned URL:", e)
        return None

# ---- CSV export helper ----
def users_to_csv_bytes(users_list):
    buf = io.StringIO()
    writer = csv.writer(buf)
    # header
    writer.writerow(["user_id", "username", "first_name", "last_name", "registration_date", "last_seen", "photo_path"])
    for u in users_list:
        writer.writerow([
            u.get("user_id"),
            u.get("username") or "",
            u.get("first_name") or "",
            u.get("last_name") or "",
            u.get("registration_date") or "",
            u.get("last_seen") or "",
            u.get("photo_path") or "",
        ])
    return buf.getvalue().encode("utf-8")

# ---- هندلرها ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ADMIN_ID
    user = update.effective_user
    if user is None:
        return

    user_id = user.id
    username = user.username or None
    first_name = user.first_name or None
    last_name = user.last_name or None

    # لاگ ID برای توسعه‌دهنده/شما
    print(f"[START] User ID: {user_id} | username: @{username} | name: {first_name} {last_name}")

    # دریافت عکس پروفایل (بزرگ‌ترین سایز) — اگر وجود داشت دانلود و ذخیره می‌شود
    photo_path = None
    try:
        photos = await context.bot.get_user_profile_photos(user_id, limit=1)
        if photos and photos.total_count > 0 and photos.photos:
            largest = photos.photos[0][-1]
            file = await context.bot.get_file(largest.file_id)
            timestamp = int(datetime.now().timestamp())
            filename = f"{user_id}_{timestamp}.jpg"
            photo_path = str(Path(PHOTOS_FOLDER) / filename)
            await file.download_to_drive(photo_path)
    except Exception as e:
        print("خطا در دریافت عکس پروفایل:", e)
        photo_path = None

    # ذخیره/به‌روزرسانی رکورد کاربر
    users = load_users_data()
    idx, existing = find_user_record(users, user_id)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    record = {
        "user_id": user_id,
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "registration_date": existing.get("registration_date") if existing else now_str,
        "last_seen": now_str,
        "photo_path": photo_path or (existing.get("photo_path") if existing else None),
    }

    if existing:
        users[idx] = {**existing, **record}
        print(f"[USER] Updated: {user_id}")
    else:
        users.append(record)
        print(f"[USER] New: {user_id}")

    save_users_data(users)

    # اگر Admin هنوز تنظیم نشده باشد، دکمه‌ای برای "ثبت به عنوان Admin" نمایش بده
    buttons = []
    if ADMIN_ID == 0:
        buttons.append([InlineKeyboardButton("🔐 ثبت به‌عنوان Admin", callback_data="become_admin")])

    # منو برای Admin / کاربران
    if is_admin(user_id):
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("🎁 گزینه 1", callback_data="option_1"),
                    InlineKeyboardButton("⚙️ گزینه 2", callback_data="option_2"),
                ],
                [InlineKeyboardButton("📚 گزینه 3", callback_data="option_3")],
                [
                    InlineKeyboardButton("👥 مدیریت کاربران", callback_data="admin_users_page_1"),
                    InlineKeyboardButton("📤 آپلود فایل", callback_data="admin_upload"),
                ],
                [
                    InlineKeyboardButton("👁️ مشاهده پروفایل کاربران", callback_data="admin_view_profiles_page_1"),
                    InlineKeyboardButton("📤 Export CSV", callback_data="export_users_csv"),
                ],
            ]
        )
        await update.message.reply_text(
            f"👋 سلام Admin {first_name or ''}!\n\n🆔 ID شما: {user_id}\n\nخوش‌آمدید! 🤖",
            reply_markup=keyboard,
        )
    else:
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("🎁 گزینه 1", callback_data="option_1"),
                    InlineKeyboardButton("⚙️ گزینه 2", callback_data="option_2"),
                ],
                [InlineKeyboardButton("📚 گزینه 3", callback_data="option_3")],
            ] + buttons
        )
        await update.message.reply_text(f"👋 سلام {first_name or ''}!\n\nخوش‌آمدید! 🤖", reply_markup=keyboard)

# --- تبدیل کاربر فعلی به Admin (اگر هنوز Admin تنظیم نشده) ---
async def become_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ADMIN_ID
    query = update.callback_query
    if query is None:
        return
    user_id = query.from_user.id

    if ADMIN_ID != 0:
        await query.answer("⚠️ قبلاً Admin تنظیم شده است.", show_alert=True)
        return

    ADMIN_ID = user_id
    try:
        save_admin_id(ADMIN_ID)
    except Exception as e:
        print("خطا در ذخیره admin.json:", e)
    await query.answer("✅ شما به‌عنوان Admin ثبت شدید.", show_alert=True)
    await query.edit_message_text(f"✅ شما به‌عنوان Admin ثبت شدید. ID: {ADMIN_ID}")

# --- نمایش لیست کاربران (صفحه‌بندی) ---
USERS_PER_PAGE = 10

def build_users_page(users, page=1, page_size=USERS_PER_PAGE):
    total = len(users)
    pages = (total + page_size - 1) // page_size if total else 1
    page = max(1, min(page, pages))
    start = (page - 1) * page_size
    end = start + page_size
    subset = users[start:end]
    text = f"📊 کاربران (صفحه {page}/{pages}) — کل: {total}\n\n"
    for u in subset:
        uname = u.get("username") or "ندارد"
        fn = u.get("first_name") or ""
        uid = u.get("user_id")
        reg = u.get("registration_date", "—")
        text += f"• {fn} @{uname} — ID: {uid}\n   ثبت: {reg}\n\n"
    kb = []
    for u in subset:
        kb.append([InlineKeyboardButton(f"👁️ {u.get('user_id')}", callback_data=f"view_user_{u.get('user_id')}")])
    # navigation
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"admin_users_page_{page-1}"))
    if page < pages:
        nav.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"admin_users_page_{page+1}"))
    if nav:
        kb.append(nav)
    kb.append([InlineKeyboardButton("⬅️ بازگشت", callback_data="back_admin")])
    return text, InlineKeyboardMarkup(kb)

# --- نمایش و صفحه‌بندی پروفایل‌ها (مانند بالا اما با نمایش بیشتر) ---
def build_profiles_page(users, page=1, page_size=10):
    return build_users_page(users, page, page_size)

# --- ارسال CSV به Admin ---
async def export_users_csv_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query is None:
        return
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.answer("❌ شما Admin نیستید!", show_alert=True)
        return
    await query.answer()

    users = load_users_data()
    csv_bytes = users_to_csv_bytes(users)
    bio = io.BytesIO(csv_bytes)
    bio.name = f"users_export_{int(datetime.now().timestamp())}.csv"
    bio.seek(0)
    try:
        await query.message.reply_document(document=bio, filename=bio.name, caption="📤 خروجی کاربران (CSV)")
    except Exception as e:
        await query.message.reply_text(f"❌ خطا در ارسال CSV: {e}")

# --- مشاهده پروفایل‌ها (صفحه‌بندی) برای Admin ---
async def admin_view_profiles_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query is None:
        return
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.answer("❌ شما Admin نیستید!", show_alert=True)
        return
    await query.answer()
    # callback: admin_view_profiles_page_{n}
    parts = query.data.split("_")
    page = 1
    try:
        page = int(parts[-1])
    except:
        page = 1
    users = load_users_data()
    text, keyboard = build_profiles_page(users, page)
    await query.edit_message_text(text=text, reply_markup=keyboard)

# --- دیدن عکس کاربر توسط Admin ---
async def view_user_photo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query is None:
        return
    caller_id = query.from_user.id
    if not is_admin(caller_id):
        await query.answer("❌ شما Admin نیستید!", show_alert=True)
        return
    await query.answer()

    parts = query.data.split("_")
    try:
        target_id = int(parts[-1])
    except:
        await query.message.reply_text("❌ شناسه کاربر نامعتبر است.")
        return

    users = load_users_data()
    _, record = find_user_record(users, target_id)
    if not record:
        await query.message.reply_text("❌ کاربر یافت نشد.")
        return

    photo_path = record.get("photo_path")
    if photo_path and os.path.exists(photo_path):
        try:
            with open(photo_path, "rb") as f:
                await query.message.reply_photo(photo=f, caption=f"🖼️ پروفایل کاربر {target_id}")
        except Exception as e:
            await query.message.reply_text(f"❌ خطا در ارسال عکس: {e}")
    else:
        await query.message.reply_text("❌ این کاربر عکس پروفایل ندارد یا عکس حذف شده است.")

# ---- بقیه‌ی callbackها (منوها و دسته‌بندی‌ها) ----
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query is None:
        return
    user_id = query.from_user.id
    data = query.data or ""
    await query.answer()

    if data == "admin_upload":
        if not is_admin(user_id):
            await query.answer("❌ شما Admin نیستید!", show_alert=True)
            return
        await query.edit_message_text("📤 لطفاً فایل را ارسال کنید (Document یا Photo). پس از ارسال، دسته‌بندی را انتخاب خواهید کرد.")
        return

    if data.startswith("admin_users_page_"):
        # redirect to paged users view
        # transform to same callback as export/view: reuse build_users_page
        try:
            page = int(data.split("_")[-1])
        except:
            page = 1
        users = load_users_data()
        text, keyboard = build_users_page(users, page)
        await query.edit_message_text(text=text, reply_markup=keyboard)
        return

    if data == "back_admin":
        if not is_admin(user_id):
            await query.answer("❌ شما Admin نیستید!", show_alert=True)
            return
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("👥 مدیریت کاربران", callback_data="admin_users_page_1"),
                    InlineKeyboardButton("📤 آپلود فایل", callback_data="admin_upload"),
                ],
                [
                    InlineKeyboardButton("👁️ مشاهده پروفایل کاربران", callback_data="admin_view_profiles_page_1"),
                    InlineKeyboardButton("📤 Export CSV", callback_data="export_users_csv"),
                ],
            ]
        )
        await query.edit_message_text("📋 منوی Admin:", reply_markup=keyboard)
        return

    if data == "option_1":
        await query.edit_message_text("✨ گزینه 1 انتخاب شد!")
        return
    if data == "option_2":
        await query.edit_message_text("⚡ گزینه 2 انتخاب شد!")
        return
    if data == "option_3":
        text = "📚 گزینه 3 - 6 دسته اصلی"
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("🔸 دسته 1", callback_data="sub_1"),
                    InlineKeyboardButton("🔹 دسته 2", callback_data="sub_2"),
                ],
                [
                    InlineKeyboardButton("🔶 دسته 3", callback_data="sub_3"),
                    InlineKeyboardButton("🟠 دسته 4", callback_data="sub_4"),
                ],
                [
                    InlineKeyboardButton("🟡 دسته 5", callback_data="sub_5"),
                    InlineKeyboardButton("🟢 دسته 6", callback_data="sub_6"),
                ],
            ]
        )
        await query.edit_message_text(text=text, reply_markup=keyboard)
        return

    # دسته‌ها و زیردسته‌ها
    if data.startswith("sub_") and len(data) == 5:
        sub_num = data.split("_")[1]
        text = f"📌 دسته {sub_num}\n\n13 زیردسته را انتخاب کنید:"
        keyboard_buttons = []
        for i in range(1, 14, 2):
            if i + 1 <= 13:
                keyboard_buttons.append(
                    [
                        InlineKeyboardButton(f"📌 {i}", callback_data=f"subsub_{sub_num}_{i}"),
                        InlineKeyboardButton(f"📌 {i+1}", callback_data=f"subsub_{sub_num}_{i+1}"),
                    ]
                )
            else:
                keyboard_buttons.append([InlineKeyboardButton(f"📌 {i}", callback_data=f"subsub_{sub_num}_{i}")])
        keyboard_buttons.append([InlineKeyboardButton("⬅️ بازگشت", callback_data="option_3")])
        keyboard = InlineKeyboardMarkup(keyboard_buttons)
        await query.edit_message_text(text=text, reply_markup=keyboard)
        return

    if data.startswith("subsub_"):
        parts = data.split("_")
        if len(parts) >= 3:
            sub_num = parts[1]
            subsub_num = parts[2]
            files_db = load_files_db()
            file_key = f"sub_{sub_num}_subsub_{subsub_num}"
            text = f"📌 زیردسته {subsub_num} از دسته {sub_num}\n\n"
            if file_key in files_db and files_db[file_key]:
                text += "📂 فایل‌های موجود:\n"
                for i, file_info in enumerate(files_db[file_key], 1):
                    text += f"{i}. {file_info.get('name')}\n"
            else:
                text += "❌ هنوز فایلی آپلود نشده\n"

            keyboard = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("📥 دانلود فایل", callback_data=f"download_{sub_num}_{subsub_num}")],
                    [InlineKeyboardButton("⬅️ بازگشت", callback_data=f"sub_{sub_num}")],
                ]
            )
            await query.edit_message_text(text=text, reply_markup=keyboard)
            return

    if data.startswith("download_"):
        parts = data.split("_")
        if len(parts) >= 3:
            sub_num = parts[1]
            subsub_num = parts[2]
            files_db = load_files_db()
            file_key = f"sub_{sub_num}_subsub_{subsub_num}"
            if file_key not in files_db or not files_db[file_key]:
                await query.message.reply_text("❌ هیچ فایلی برای دانلود وجود ندارد!")
                return
            kb = []
            for i, file_info in enumerate(files_db[file_key]):
                kb.append([InlineKeyboardButton(f"📄 {file_info['name']}", callback_data=f"get_file_{sub_num}_{subsub_num}_{i}")])
            kb.append([InlineKeyboardButton("⬅️ بازگشت", callback_data=f"subsub_{sub_num}_{subsub_num}")])
            keyboard = InlineKeyboardMarkup(kb)
            await query.edit_message_text(text=f"📥 فایل‌های این بخش:", reply_markup=keyboard)
            return

    if data.startswith("get_file_"):
        parts = data.split("_")
        if len(parts) >= 5:
            sub_num = parts[2]
            subsub_num = parts[3]
            file_idx = int(parts[4])
            files_db = load_files_db()
            file_key = f"sub_{sub_num}_subsub_{subsub_num}"
            if file_key in files_db and 0 <= file_idx < len(files_db[file_key]):
                file_info = files_db[file_key][file_idx]
                # اگر فایل در S3 ذخیره شده باشد، لینک presigned بفرست
                s3_key = file_info.get("s3_key")
                if s3_key and USE_S3:
                    url = generate_presigned_url(s3_key, expires_in=3600)
                    if url:
                        kb = InlineKeyboardMarkup([[InlineKeyboardButton("دانلود از S3", url=url)], [InlineKeyboardButton("⬅️ بازگشت", callback_data=f"subsub_{sub_num}_{subsub_num}")]])
                        await query.message.reply_text(f"✅ فایل آماده است: {file_info.get('name')}\nلینک دانلود (یک ساعت معتبر):", reply_markup=kb)
                        return
                    else:
                        await query.message.reply_text("❌ خطا در تولید لینک دانلود S3.")
                        return
                # وگرنه اگر مسیر محلی موجود است، ارسال مستقیم
                file_path = file_info.get("path")
                if file_path and os.path.exists(file_path):
                    try:
                        with open(file_path, "rb") as f:
                            await query.message.reply_document(document=f, filename=file_info.get("name"), caption=f"✅ فایل: {file_info.get('name')}")
                    except Exception as e:
                        await query.message.reply_text(f"❌ خطا در ارسال فایل: {e}")
                else:
                    await query.message.reply_text("❌ فایل حذف شده یا یافت نشد!")
            return

# ---- هندلر آپلود فایل (Document یا Photo) توسط Admin ----
async def handle_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if message is None:
        return
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await message.reply_text("❌ شما Admin نیستید!\n\nفقط Admin می‌تواند فایل آپلود کند.")
        return

    file_name = None
    saved_path = None
    try:
        if message.document:
            file = message.document
            file_name = file.file_name or f"file_{int(datetime.now().timestamp())}"
            new_file = await context.bot.get_file(file.file_id)
            file_path = os.path.join(FILES_FOLDER, file_name)
            if os.path.exists(file_path):
                file_path = os.path.join(FILES_FOLDER, f"{int(datetime.now().timestamp())}_{file_name}")
            await new_file.download_to_drive(file_path)
            saved_path = file_path
        elif message.photo:
            largest = message.photo[-1]
            file_name = f"photo_{int(datetime.now().timestamp())}.jpg"
            new_file = await context.bot.get_file(largest.file_id)
            file_path = os.path.join(FILES_FOLDER, file_name)
            await new_file.download_to_drive(file_path)
            saved_path = file_path
        else:
            await message.reply_text("❌ لطفا یک فایل ارسال کنید (Document یا Photo).")
            return
    except Exception as e:
        await message.reply_text(f"❌ خطا در دانلود فایل: {e}")
        print("خطا در دانلود فایل:", e)
        return

    context.user_data["uploaded_file"] = {"name": file_name, "path": saved_path}
    # انتخاب دسته اصلی
    keyboard_buttons = []
    for i in range(1, 7, 2):
        if i + 1 <= 6:
            keyboard_buttons.append(
                [
                    InlineKeyboardButton(f"🔹 دسته {i}", callback_data=f"upload_select_sub_{i}"),
                    InlineKeyboardButton(f"🔹 دسته {i+1}", callback_data=f"upload_select_sub_{i+1}"),
                ]
            )
        else:
            keyboard_buttons.append([InlineKeyboardButton(f"🔹 دسته {i}", callback_data=f"upload_select_sub_{i}")])
    keyboard_buttons.append([InlineKeyboardButton("❌ انصراف", callback_data="back_admin")])
    keyboard = InlineKeyboardMarkup(keyboard_buttons)
    await message.reply_text(f"📄 فایل '{file_name}' دریافت شد!\n\nاین فایل را برای کدام دسته ذخیره کنم؟", reply_markup=keyboard)

async def handle_upload_select_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query is None:
        return
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.answer("❌ شما Admin نیستید!")
        return
    await query.answer()
    if query.data.startswith("upload_select_sub_"):
        sub_num = query.data.split("_")[-1]
        context.user_data["upload_sub"] = sub_num
        keyboard_buttons = []
        for i in range(1, 14, 2):
            if i + 1 <= 13:
                keyboard_buttons.append(
                    [
                        InlineKeyboardButton(f"📌 {i}", callback_data=f"upload_select_subsub_{i}"),
                        InlineKeyboardButton(f"📌 {i+1}", callback_data=f"upload_select_subsub_{i+1}"),
                    ]
                )
            else:
                keyboard_buttons.append([InlineKeyboardButton(f"📌 {i}", callback_data=f"upload_select_subsub_{i}")])
        keyboard_buttons.append([InlineKeyboardButton("⬅️ بازگشت", callback_data="admin_upload")])
        keyboard = InlineKeyboardMarkup(keyboard_buttons)
        await query.edit_message_text(f"اکنون زیردسته را برای دسته {sub_num} انتخاب کنید:", reply_markup=keyboard)

async def handle_upload_select_subsub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query is None:
        return
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.answer("❌ شما Admin نیستید!")
        return
    await query.answer()
    if query.data.startswith("upload_select_subsub_"):
        subsub_num = query.data.split("_")[-1]
        if "uploaded_file" not in context.user_data or "upload_sub" not in context.user_data:
            await query.message.reply_text("❌ ابتدا فایل را آپلود کنید!")
            return
        file_info = context.user_data["uploaded_file"]
        sub_num = context.user_data["upload_sub"]
        files_db = load_files_db()
        file_key = f"sub_{sub_num}_subsub_{subsub_num}"
        if file_key not in files_db:
            files_db[file_key] = []

        entry = {
            "name": file_info["name"],
            "path": file_info["path"],
            "upload_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        # اگر S3 فعال است، آپلود به S3 انجام بده و local را حذف کن و info S3 را ذخیره کن
        if USE_S3 and s3_client:
            s3_key = f"uploads/{int(datetime.now().timestamp())}_{file_info['name']}"
            uploaded = await upload_file_to_s3_async(file_info["path"], s3_key)
            if uploaded:
                entry["s3_key"] = s3_key
                # می‌توان آدرس نهایی را تولید نکرد و در زمان دانلود presigned ساخت
                # حذف فایل محلی (برای سبک شدن سرور)
                try:
                    os.remove(file_info["path"])
                    entry["path"] = None
                except Exception:
                    pass
            else:
                # در صورت خطا، همچنان مسیر محلی باقی می‌ماند و entry بدون s3_key ذخیره می‌شود
                print("خطا در آپلود S3 — فایل محلی نگه داشته شد.")

        files_db[file_key].append(entry)
        save_files_db(files_db)
        await query.edit_message_text(
            f"✅ فایل '{file_info['name']}' برای دسته {sub_num} → زیردسته {subsub_num} ذخیره شد!\n\nکاربران می‌توانند این فایل را دانلود کنند."
        )
        context.user_data.pop("uploaded_file", None)
        context.user_data.pop("upload_sub", None)

# ---- ثبت هندلرها و اجرای بات ----
def main():
    print("🚀 ربات شروع شد...")
    application = Application.builder().token(BOT_TOKEN).build()

    # هندلرهای pattern-specific را اول ثبت کن
    application.add_handler(CallbackQueryHandler(handle_upload_select_sub, pattern="^upload_select_sub_"))
    application.add_handler(CallbackQueryHandler(handle_upload_select_subsub, pattern="^upload_select_subsub_"))
    application.add_handler(CallbackQueryHandler(view_user_photo_callback, pattern="^view_user_\\d+$"))
    application.add_handler(CallbackQueryHandler(become_admin_callback, pattern="^become_admin$"))
    application.add_handler(CallbackQueryHandler(export_users_csv_callback, pattern="^export_users_csv$"))
    application.add_handler(CallbackQueryHandler(admin_view_profiles_callback, pattern="^admin_view_profiles_page_\\d+$"))
    # هندلر عمومی کال‌بک‌ها
    application.add_handler(CallbackQueryHandler(button_callback))

    application.add_handler(CommandHandler("start", start))
    # هندلر آپلود فایل‌ها (Document یا Photo)
    application.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, handle_file_upload))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
