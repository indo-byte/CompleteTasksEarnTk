import sqlite3
import random
import string
import pyotp
import cv2
import numpy as np
from pyzbar.pyzbar import decode
from PIL import Image
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
TOKEN = "8640804264:AAEJ9f8cfe16Qf1Ebp9B8IbmwiJD9h58SMU"
ADMIN_ID = 1781001349
REFER_BONUS = 0.0002
MIN_WITHDRAW = 0.00002
RECOVERY_EMAILS = ["hshanto804@gmail.com", "hasibulha9@gmail.com", "ab1584836@gmail.com"]

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('task_ultra_final.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS used_info (username TEXT PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0, hold REAL DEFAULT 0.0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS subs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, type TEXT, price REAL)''')
    
    try:
        c.execute("ALTER TABLE users ADD COLUMN referrals INTEGER DEFAULT 0")
        c.execute("ALTER TABLE users ADD COLUMN referred_by INTEGER")
    except sqlite3.OperationalError:
        pass
        
    conn.commit()
    conn.close()

init_db()

# --- UNIQUE INFO GENERATOR ---
def generate_unique_info():
    conn = sqlite3.connect('task_ultra_final.db')
    c = conn.cursor()
    while True:
        user_part = "".join(random.choices(string.ascii_lowercase, k=6)) + str(random.randint(100, 999))
        c.execute("SELECT username FROM used_info WHERE username=?", (user_part,))
        if not c.fetchone():
            c.execute("INSERT INTO used_info VALUES (?)", (user_part,))
            conn.commit()
            conn.close()
            return {
                "name": f"User {user_part.capitalize()}",
                "user": user_part,
                "pass": "".join(random.choices(string.ascii_letters + string.digits, k=12)),
                "dob": f"{random.randint(1,28)}/{random.randint(1,12)}/1998"
            }

# --- PERSISTENT TAB-BAR MENU ---
def get_persistent_menu():
    keyboard = [
        [KeyboardButton("🚀 START EARNING")],
        [KeyboardButton("💳 WALLET"), KeyboardButton("👥 REFER")],
        [KeyboardButton("⚙️ PROFILE"), KeyboardButton("🆘 HELP")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)

# --- START COMMAND ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    referred_by = None
    if context.args:
        try:
            referred_by = int(context.args[0])
            if referred_by == user_id: referred_by = None
        except: pass

    conn = sqlite3.connect('task_ultra_final.db')
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE id=?", (user_id,))
    if not c.fetchone():
        c.execute("INSERT INTO users (id, referred_by) VALUES (?, ?)", (user_id, referred_by))
        if referred_by:
            c.execute("UPDATE users SET balance = balance + ?, referrals = referrals + 1 WHERE id = ?", (REFER_BONUS, referred_by))
    conn.commit()
    conn.close()
    
    await update.message.reply_text("📱 *TASK DASHBOARD READY*", reply_markup=get_persistent_menu(), parse_mode='Markdown')

# --- MAIN MESSAGE HANDLER ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    conn = sqlite3.connect('task_ultra_final.db')
    c = conn.cursor()
    c.execute("SELECT balance, hold, referrals FROM users WHERE id=?", (user_id,))
    u = c.fetchone()
    conn.close()

    if not u: return

    if text == "🚀 START EARNING":
        keyboard = [
            [InlineKeyboardButton("📘 FB + 2FA ($0.0002)", callback_data='setup_fb_0.0002')],
            [InlineKeyboardButton("📸 Insta + 2FA ($0.0003)", callback_data='setup_insta_0.0003')],
            [InlineKeyboardButton("📧 Gmail (No 2FA) ($0.15)", callback_data='setup_gm1_0.15')],
            [InlineKeyboardButton("🛡️ Gmail (With 2FA) ($0.25)", callback_data='setup_gm2_0.25')]
        ]
        await update.message.reply_text("📂 *SELECT YOUR TASK:*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif text == "💳 WALLET":
        msg = f"💳 *Wallet Overview*\n\n💰 Balance: `${u[0]:.6f}`\n⏳ Hold: `${u[1]:.6f}`\n\nMin Withdraw: ${MIN_WITHDRAW}"
        kb = [[InlineKeyboardButton("💸 Withdraw Now", callback_data='wd_req')]] if u[0] >= MIN_WITHDRAW else None
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb) if kb else None, parse_mode='Markdown')

    elif text == "👥 REFER":
        link = f"https://t.me/{(await context.bot.get_me()).username}?start={user_id}"
        await update.message.reply_text(f"👥 *Referral Program*\n\nBonus: `${REFER_BONUS}`\nRefers: `{u[2]}`\n\n🔗 *Link:* {link}", parse_mode='Markdown')

    elif text == "⚙️ PROFILE":
        msg = (f"👤 *USER PROFILE*\n\n🆔 ID: `{user_id}`\n📛 Name: `{update.effective_user.full_name}`\n"
               f"📧 User: `@{update.effective_user.username}`\n💰 Balance: `${u[0]:.6f}`\n👥 Refers: `{u[2]}`")
        await update.message.reply_text(msg, parse_mode='Markdown')

    elif text == "🆘 HELP":
        kb = [[InlineKeyboardButton("🕒 What is hold?", callback_data='h_hold')], [InlineKeyboardButton("👷 Support", url=f"tg://user?id={ADMIN_ID}")]]
        await update.message.reply_text("🆘 *Help Center*", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

    # 2FA Processing (Fixed Syntax)
    elif context.user_data.get('awaiting_2fa'):
        secret_key = None
        if update.message.photo:
            file = await context.bot.get_file(update.message.photo[-1].file_id)
            img_bytes = await file.download_as_bytearray()
            image = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
            decoded_objs = decode(image)
            for obj in decoded_objs:
                qr_data = obj.data.decode('utf-8')
                secret_key = qr_data.split("secret=")[1].split("&")[0] if "secret=" in qr_data else qr_data
        elif text:
            clean_text = text.strip().replace(" ", "").upper()
            if all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567" for c in clean_text) and len(clean_text) >= 16:
                secret_key = clean_text

        if secret_key:
            try:
                totp = pyotp.TOTP(secret_key)
                code = totp.now()
                context.user_data['awaiting_2fa'] = False
                await update.message.reply_text(f"✅ *2FA DETECTED!*\nCode: `{code}`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚀 SUBMIT", callback_data='final_sub')]]), parse_mode='Markdown')
            except Exception as e:
                print(f"2FA Error: {e}")
                await update.message.reply_text("❌ Invalid Secret Key!")

# --- CALLBACKS ---
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    await query.answer()

    if data.startswith('setup_'):
        _, p_type, price = data.split('_')
        info = generate_unique_info()
        context.user_data.update({'price': price, 'type': p_type, 'awaiting_2fa': False})
        msg = f"🛠 *TASK ({p_type.upper()}):*\n👤 Name: `{info['name']}`\n📧 Email: `{info['user']}@gmail.com`\n🔑 Pass: `{info['pass']}`"
        kb = [[InlineKeyboardButton("✅ SUBMIT", callback_data='final_sub')]] if p_type == 'gm1' else [[InlineKeyboardButton("🔐 NEXT: 2FA", callback_data='ask_2fa')]]
        await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(kb))
    elif data == 'ask_2fa':
        context.user_data['awaiting_2fa'] = True
        await query.edit_message_text("📸 Send QR or Secret Key:")
    elif data == 'final_sub':
        price = context.user_data.get('price', 0)
        conn = sqlite3.connect('task_ultra_final.db')
        c = conn.cursor()
        c.execute("UPDATE users SET hold = hold + ? WHERE id = ?", (float(price), user_id))
        conn.commit()
        conn.close()
        await query.edit_message_text("✅ *SUBMITTED!*")

# --- RUN ---
if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    print("Bot started successfully...")
    app.run_polling()