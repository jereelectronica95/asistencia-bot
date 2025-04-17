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
from apscheduler.triggers.cron import CronTrigger

# --- CONFIG ---
TOKEN = "7648235489:AAEmozaPfdWuzzkr5rhpnyiwD9F4Z8fNU9M"
ADMIN_ID = 555786610
registro_path = "data/registro.csv"
comentarios_path = "data/comentarios.csv"
operarios = ["Adrian", "Cesar", "Jere", "Belén"]
tijeras = [str(i) for i in range(1, 13)]
modo_silencio = False
asistencia = {}
respuesta_pendiente = {}

# --- INIT ---
app = ApplicationBuilder().token(TOKEN).build()
scheduler = BackgroundScheduler()
arg = timezone("America/Argentina/Buenos_Aires")
os.makedirs("data", exist_ok=True)
os.makedirs("fotos", exist_ok=True)

# --- COMANDOS BÁSICOS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot de asistencia listo para usar. Usá /hoy o /agendar para registrar días.")

async def hoy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Función de registro del día actual en desarrollo.")

async def agendar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Función de agendar días en desarrollo.")

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("hoy", hoy))
app.add_handler(CommandHandler("agendar", agendar))

# --- PREGUNTAR SI SE TRABAJA ---
async def preguntar_dia_laborable(context: ContextTypes.DEFAULT_TYPE):
    if modo_silencio:
        return
    chat_id = ADMIN_ID
    fecha_actual = datetime.now(arg).strftime("%Y-%m-%d")
    if respuesta_pendiente.get(fecha_actual) is not False:
        respuesta_pendiente[fecha_actual] = True
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Sí, se trabaja", callback_data="trabaja_si")],
            [InlineKeyboardButton("❌ No, no se trabaja", callback_data="trabaja_no")]
        ])
        await context.bot.send_message(chat_id=chat_id, text="¿Se trabaja hoy?", reply_markup=keyboard)
        context.job_queue.run_repeating(
            reintentar_pregunta,
            interval=120,
            first=120,
            data={"fecha": fecha_actual},
            name=f"reintento_{fecha_actual}"
        )

async def reintentar_pregunta(context: ContextTypes.DEFAULT_TYPE):
    fecha = context.job.data["fecha"]
    if respuesta_pendiente.get(fecha, False):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Sí, se trabaja", callback_data="trabaja_si")],
            [InlineKeyboardButton("❌ No, no se trabaja", callback_data="trabaja_no")]
        ])
        await context.bot.send_message(chat_id=ADMIN_ID, text="⏰ Reintento: ¿Se trabaja hoy?", reply_markup=keyboard)

async def manejar_respuesta_dia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    hoy = datetime.now(arg).strftime("%Y-%m-%d")
    if query.data == "trabaja_si":
        await query.edit_message_text("✅ Día marcado como *laborable*. Ya podés registrar asistencia.", parse_mode="Markdown")
    elif query.data == "trabaja_no":
        df = pd.DataFrame([[hoy, "NO", "Día no laborable", "", ""]], columns=["fecha", "asistencia", "comentario", "foto", "tijeras"])
        if os.path.exists(registro_path):
            df.to_csv(registro_path, mode="a", header=False, index=False)
        else:
            df.to_csv(registro_path, index=False)
        await query.edit_message_text("❌ Día registrado como *NO laborable*.", parse_mode="Markdown")
    respuesta_pendiente[hoy] = False
    # Cancelar reintento
    job_name = f"reintento_{hoy}"
    job = scheduler.get_job(job_name)
    if job:
        job.remove()

app.add_handler(CallbackQueryHandler(manejar_respuesta_dia, pattern="trabaja_"))

# --- CRON DIARIO ---
scheduler.add_job(preguntar_dia_laborable, CronTrigger(hour=0, minute=0, timezone=arg), args=[app.job_queue])
scheduler.start()

# --- RUN ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run_polling()
