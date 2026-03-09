import sys
import os

# --- লাইব্রেরি চেক ---
try:
    import pyotp
    import numpy as np
    from PIL import Image
    from qreader import QReader
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
except ImportError as e:
    print(f"Error: {e}. Please check requirements.txt and wait for installation.")
    # লাইব্রেরি না থাকলে বট চালু হবে না, এরর কনসোলে দেখাবে
    sys.exit(1)

# QR Reader Initialize
qreader = QReader()
TOKEN = "8640804264:AAEJ9f8cfe16Qf1Ebp9B8IbmwiJD9h58SMU"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is online! Send a QR code photo.")

if __name__ == '__main__':
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    
    print("Bot is polling...")
    application.run_polling()
