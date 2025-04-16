
import logging
import os
from datetime import datetime, timedelta
from pytz import timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes,
    MessageHandler, filters
)
import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler

# --- Configuración ---
TOKEN = "7648235489:AAEmozaPfdIwuzzkr5rhpnvjwD9F4Z8fNU9M"
ADMIN_ID = 555786610
operarios = ["Adrian", "Cesar", "Jere", "Belén"]
tijeras = [str(i) for i in range(1, 13)]
registro_path = "data/registro.csv"
asistencia_actual = {}
scheduler = BackgroundScheduler()
scheduler.start()

# --- Comando /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bot de asistencia listo para usar. Usá /hoy o /agendar para registrar días."
    )

# --- Registro del handler ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()

if __name__ == "__main__":
    main()
