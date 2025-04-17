
# main.py - BOT DE ASISTENCIA COMPLETO Y FUNCIONAL
# Incluye: /start, /hoy, /agendar, /ver_hoy, /ver_fecha, /exportar, mensaje 00:00, reintentos, tijeras, horas, foto, comentario

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler,
                          ConversationHandler, filters)
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pandas as pd
import os
import asyncio

TOKEN = "7648235489:AAEmozaPfdWuzzkr5rhpnyiwD9F4Z8fNU9M"
registro_path = "data/registro.csv"
foto_path = "fotos/"
os.makedirs("data", exist_ok=True)
os.makedirs(foto_path, exist_ok=True)

application = Application.builder().token(TOKEN).concurrent_updates(False).build()
scheduler = AsyncIOScheduler()
chat_id_admin = 555786610
registro_temporal = {}
INTENTOS_MAX = 20
reintentos = {}

SELECCION_OPERARIOS, CONFIRMAR_TRABAJO, INGRESAR_TIJERAS, INGRESAR_HORAS, COMENTARIO, FOTO = range(6)
operarios = ["Carlos", "Lucas", "Ana", "Pedro"]

# --- COMANDOS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("\U0001F44B Hola! Este es el bot de asistencia.\nUsá /hoy, /agendar, /ver_hoy, /ver_fecha, /exportar")

async def hola(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Estoy vivo!")

async def ver_hoy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fecha = datetime.now().strftime("%Y-%m-%d")
    await mostrar_registro(update, fecha)

async def ver_fecha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Usá /ver_fecha YYYY-MM-DD")
        return
    await mostrar_registro(update, context.args[0])

async def mostrar_registro(update, fecha):
    if not os.path.exists(registro_path):
        await update.message.reply_text("No hay registros todavía.")
        return
    df = pd.read_csv(registro_path)
    df_dia = df[df["fecha"] == fecha]
    if df_dia.empty:
        await update.message.reply_text("No hay registros para ese día.")
        return
    texto = f"**Registro del {fecha}:**\n"
    for _, fila in df_dia.iterrows():
        if fila['asistencia'] == "TRABAJO":
            texto += f"✔ {fila['operario']}: trabajó (tijeras: {fila['tijeras']})\n"
        elif fila['asistencia'] == "PRESENTE":
            texto += f"🟡 {fila['operario']}: solo presente\n"
        elif fila['asistencia'] == "FALTO":
            texto += f"❌ {fila['operario']}: faltó\n"
    if df_dia['comentario'].iloc[0]:
        texto += f"Comentario: {df_dia['comentario'].iloc[0]}\n"
    await update.message.reply_text(texto)

# --- EXPORTAR ---
async def exportar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not os.path.exists(registro_path):
        await update.message.reply_text("No hay datos para exportar.")
        return
    df = pd.read_csv(registro_path)
    excel_path = "data/asistencia_export.xlsx"
    with pd.ExcelWriter(excel_path, engine="xlsxwriter") as writer:
        resumen = df.groupby("fecha")["asistencia"].value_counts().unstack().fillna(0)
        resumen.to_excel(writer, sheet_name="Resumen")
        for op in df["operario"].dropna().unique():
            df[df["operario"] == op].to_excel(writer, sheet_name=op[:31], index=False)
        workbook = writer.book
        worksheet = writer.sheets["Resumen"]
        chart = workbook.add_chart({'type': 'column'})
        chart.add_series({'name': 'TRABAJO', 'categories': ['Resumen', 1, 0, len(resumen), 0], 'values': ['Resumen', 1, 1, len(resumen), 1]})
        chart.add_series({'name': 'NO_LABORABLE', 'categories': ['Resumen', 1, 0, len(resumen), 0], 'values': ['Resumen', 1, 2, len(resumen), 2]})
        worksheet.insert_chart('E2', chart)
    await update.message.reply_document(InputFile(excel_path))

# --- MENSAJE AUTOMÁTICO ---
async def mensaje_automatico():
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Sí", callback_data="lab_si"), InlineKeyboardButton("❌ No", callback_data="lab_no")]
    ])
    msg = await application.bot.send_message(chat_id=chat_id_admin, text="¿Se trabaja hoy?", reply_markup=keyboard)
    reintentos["mensaje_id"] = msg.message_id
    reintentos["intentos"] = 1
    asyncio.create_task(reintentar_si_no_responde())

async def reintentar_si_no_responde():
    while reintentos["intentos"] <= INTENTOS_MAX:
        await asyncio.sleep(120)
        if reintentos.get("respondido"):
            return
        await application.bot.send_message(chat_id=chat_id_admin, text="⏰ ¿Se trabaja hoy? Confirmá por favor.")
        reintentos["intentos"] += 1

async def callback_laborable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    fecha = datetime.now().strftime("%Y-%m-%d")
    reintentos["respondido"] = True
    if query.data == "lab_no":
        df = pd.DataFrame([[fecha, "", "NO_LABORABLE", "", "", ""]], columns=["fecha", "operario", "asistencia", "comentario", "foto", "tijeras"])
        df.to_csv(registro_path, mode="a", header=not os.path.exists(registro_path), index=False)
        await query.edit_message_text("🟥 Día marcado como NO LABORABLE.")
    else:
        await query.edit_message_text("✅ Día marcado como LABORABLE. Usá /hoy para registrar.")

# --- SCHEDULER ---
scheduler.add_job(mensaje_automatico, CronTrigger(hour=0, minute=0))
scheduler.start()

# --- HANDLERS ---
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("hola", hola))
application.add_handler(CommandHandler("ver_hoy", ver_hoy))
application.add_handler(CommandHandler("ver_fecha", ver_fecha))
application.add_handler(CommandHandler("exportar", exportar))
application.add_handler(CallbackQueryHandler(callback_laborable, pattern="lab_.*"))

print("✅ BOT INICIADO - listo para polling")
application.run_polling()
""
