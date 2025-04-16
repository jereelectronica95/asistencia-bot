import logging
import os
from datetime import datetime, timedelta
from pytz import timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters
)
import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler

# Configuración básica
TOKEN = "7648235489:AAEmozaPfdwuzzkr5rhpnvjwD9F4Z8fNU9M"
ADMIN_ID = 555786610  # ID de Jere
operarios = ["Adrian", "Cesar", "Jere", "Belén"]
tijeras = [str(i) for i in range(1, 13)]
registro_path = "data/registro.csv"
asistencia_actual = {}
scheduler = BackgroundScheduler()
scheduler.start()

# Aquí iría el resto del bot, funciones y comandos definidos