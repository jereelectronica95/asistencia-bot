import logging
import os
from datetime import datetime
from pytz import timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)
import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler

# --- CONFIGURACIÓN ---
TOKEN = "7648235489:AAEmozaPfdwuzzkr5rhpnyiwD9F4Z8fNU9M"
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

# --- INICIALIZAR ---
os.makedirs("data", exist_ok=True)
os.makedirs("fotos", exist_ok=True)
if not os.path.exists(registro_path):
    pd.DataFrame(columns=["fecha", "operario", "tijera", "hora"]).to_csv(registro_path, index=False)

# --- FUNCIONES AUXILIARES ---
def guardar_registro():
    fecha = asistencia.get("fecha")
    df = pd.read_csv(registro_path)
    for op in asistencia.get("presentes", []):
        horas = asistencia.get("horas", {}).get(op, {})
        for tij, h in horas.items():
            df.loc[len(df)] = [fecha, op, tij, h]
    if asistencia.get("jere_solo_presente"):
        df.loc[len(df)] = [fecha, "Jere", "", "Presente sin operar"]
    df.to_csv(registro_path, index=False)
