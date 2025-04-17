import logging
import os
from datetime import datetime, timedelta
from pytz import timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)
import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler

TOKEN = "7648235489:AAEmozaPfdWuzzkr5rhpnyiwD9F4Z8fNU9M"
ADMIN_ID = 555786610
registro_path = "data/registro.csv"
comentarios_path = "data/comentarios.csv"
operarios = ["Adrian", "Cesar", "Jere", "Belén"]
tijeras = [str(i) for i in range(1, 13)]
modo_silencio = False
asistencia = {}
app = ApplicationBuilder().token(TOKEN).build()
scheduler = BackgroundScheduler()
arg = timezone("America/Argentina/Buenos_Aires")

os.makedirs("data", exist_ok=True)
os.makedirs("fotos", exist_ok=True)
if not os.path.exists(registro_path):
    pd.DataFrame(columns=["fecha", "operario", "tijera", "hora"]).to_csv(registro_path, index=False)
if not os.path.exists(comentarios_path):
    pd.DataFrame(columns=["fecha", "comentario", "archivo"]).to_csv(comentarios_path, index=False)

# Código principal se define aquí...
print("Bot cargado correctamente")
# --- COMANDOS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot de asistencia listo para usar. Usá /hoy o /agendar para registrar días.")

# --- ASOCIAR HANDLERS ---
app.add_handler(CommandHandler("start", start))

# --- EJECUTAR BOT ---
if __name__ == "__main__":
    app.run_polling()
