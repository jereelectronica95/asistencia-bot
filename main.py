
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application, CommandHandler, ContextTypes, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters
)
from datetime import datetime
import pandas as pd
import os
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

TOKEN = "7648235489:AAEmozaPfdWuzzkr5rhpnyiwD9F4Z8fNU9M"
registro_path = "data/registro.csv"
os.makedirs("data", exist_ok=True)

application = Application.builder().token(TOKEN).concurrent_updates(False).build()
scheduler = AsyncIOScheduler()
chat_id_admin = 555786610
reintentos = {}
INTENTOS_MAX = 20

# === Comandos base ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 ¡Hola! Este es el bot de asistencia.\n\n"
        "Comandos disponibles:\n"
        "/hoy – Registrar asistencia de hoy\n"
        "/agendar – Registrar fecha pasada\n"
        "/ver_hoy – Ver asistencia de hoy\n"
        "/ver_fecha YYYY-MM-DD – Ver asistencia de otra fecha\n"
        "/exportar – Exportar Excel\n"
        "/start – Ver este mensaje"
    )

async def hola(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Estoy vivo!")

async def ver_hoy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fecha = datetime.now().strftime("%Y-%m-%d")
    await mostrar_registro(update, fecha)

async def ver_fecha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Usá /ver_fecha YYYY-MM-DD")
        return
    fecha = context.args[0]
    await mostrar_registro(update, fecha)

async def mostrar_registro(update, fecha):
    if not os.path.exists(registro_path):
        await update.message.reply_text("No hay registros guardados.")
        return
    df = pd.read_csv(registro_path)
    df_dia = df[df["fecha"] == fecha]
    if df_dia.empty:
        await update.message.reply_text(f"No hay registros para el día {fecha}.")
        return
    texto = f"**Registro del {fecha}:**\n"
    for _, fila in df_dia.iterrows():
        if fila["asistencia"] == "TRABAJO":
            texto += f"✔ {fila['operario']}: trabajó (tijeras: {fila['tijeras']})\n"
        elif fila["asistencia"] == "PRESENTE":
            texto += f"🟡 {fila['operario']}: solo presente\n"
        elif fila["asistencia"] == "FALTO":
            texto += f"❌ {fila['operario']}: faltó\n"
        elif fila["asistencia"] == "NO_LABORABLE":
            texto += "🟥 Día marcado como NO LABORABLE\n"
        else:
            texto += f"- {fila['operario']}: {fila['asistencia']}\n"
    if "comentario" in df_dia.columns and str(df_dia['comentario'].values[0]).strip():
        texto += f"Comentario: {df_dia['comentario'].values[0]}\n"
    await update.message.reply_text(texto, parse_mode="Markdown")

# === Mensaje automático ===
async def mensaje_automatico():
    try:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Sí", callback_data="lab_si")],
            [InlineKeyboardButton("❌ No", callback_data="lab_no")]
        ])
        await application.bot.send_message(chat_id=chat_id_admin, text="¿Se trabaja hoy?", reply_markup=keyboard)
        reintentos["intento"] = 1
        reintentos["ok"] = False
        await reintentar_si_no_responde()
    except Exception as e:
        print(f"Error en mensaje automático: {e}")

async def reintentar_si_no_responde():
    while reintentos["intento"] <= INTENTOS_MAX:
        await asyncio.sleep(120)
        if reintentos["ok"]:
            return
        await application.bot.send_message(chat_id=chat_id_admin, text="⏰ ¿Se trabaja hoy? Confirmá por favor.")
        reintentos["intento"] += 1

async def callback_trabajo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not reintentos.get("ok"):
        reintentos["ok"] = True
        if query.data == "lab_no":
            fecha = datetime.now().strftime("%Y-%m-%d")
            df = pd.DataFrame([[fecha, "", "NO_LABORABLE", "", "", ""]], columns=["fecha", "operario", "asistencia", "comentario", "foto", "tijeras"])
            if os.path.exists(registro_path):
                df.to_csv(registro_path, mode="a", header=False, index=False)
            else:
                df.to_csv(registro_path, index=False)
            await query.edit_message_text("🟥 Marcado como NO LABORABLE.")
        elif query.data == "lab_si":
            await query.edit_message_text("✅ ¡Listo! Ya podés usar /hoy para registrar.")

# === on_startup para iniciar scheduler ===
async def on_startup(app):
    scheduler.add_job(mensaje_automatico, CronTrigger(hour=0, minute=0))
    scheduler.start()
    print("🕓 Scheduler iniciado.")

# === Handlers ===
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("hola", hola))
application.add_handler(CommandHandler("ver_hoy", ver_hoy))
application.add_handler(CommandHandler("ver_fecha", ver_fecha))
application.add_handler(CallbackQueryHandler(callback_trabajo, pattern="lab_.*"))

# === Iniciar bot con on_startup ===
application.run_polling(on_startup=on_startup)
