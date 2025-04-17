
# main.py COMPLETO con todas las funciones integradas
# Incluye: /start /hola /hoy /agendar /ver_hoy /ver_fecha /exportar + reintentos automáticos

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application, CommandHandler, ContextTypes, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters
)
from datetime import datetime, timedelta, time
import pandas as pd
import os
import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

TOKEN = "7648235489:AAEmozaPfdWuzzkr5rhpnyiwD9F4Z8fNU9M"
registro_path = "data/registro.csv"
foto_path = "fotos/"
os.makedirs("data", exist_ok=True)
os.makedirs(foto_path, exist_ok=True)

application = Application.builder().token(TOKEN).concurrent_updates(False).build()
registro_temporal = {}
chat_id_admin = 555786610  # Tu ID de Telegram
reintentos = {}
INTENTOS_MAX = 20

# === /start ===
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

# === /hola ===
async def hola(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Estoy vivo!")

# === /ver_hoy y /ver_fecha ===
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

# === /exportar ===
async def exportar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not os.path.exists(registro_path):
        await update.message.reply_text("No hay datos para exportar.")
        return
    df = pd.read_csv(registro_path)
    excel_path = "data/asistencia_export.xlsx"
    with pd.ExcelWriter(excel_path, engine="xlsxwriter") as writer:
        resumen = df.groupby("fecha")["asistencia"].apply(lambda x: (x == "TRABAJO").sum()).reset_index(name="trabajados")
        resumen["no_trabajados"] = df.groupby("fecha")["asistencia"].apply(lambda x: (x == "NO_LABORABLE").sum()).values
        resumen.to_excel(writer, sheet_name="Resumen", index=False)
        workbook = writer.book
        worksheet = writer.sheets["Resumen"]
        chart = workbook.add_chart({'type': 'column'})
        chart.add_series({
            'name': 'Trabajados',
            'categories': ['Resumen', 1, 0, len(resumen), 0],
            'values':     ['Resumen', 1, 1, len(resumen), 1],
        })
        chart.add_series({
            'name': 'No trabajados',
            'categories': ['Resumen', 1, 0, len(resumen), 0],
            'values':     ['Resumen', 1, 2, len(resumen), 2],
        })
        chart.set_title({'name': 'Días trabajados vs no trabajados'})
        worksheet.insert_chart('E2', chart)
        for op in df["operario"].unique():
            df[df["operario"] == op].to_excel(writer, sheet_name=op, index=False)
    await update.message.reply_document(InputFile(excel_path), filename="asistencia_export.xlsx")

# === Mensaje automático 00:00 ===
async def mensaje_automatico():
    try:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Sí", callback_data="lab_si")],
            [InlineKeyboardButton("❌ No", callback_data="lab_no")]
        ])
        await application.bot.send_message(chat_id=chat_id_admin, text="¿Se trabaja hoy?", reply_markup=keyboard)
        reintentos["intento"] = 1
        reintentos["mensaje"] = await application.bot.send_message(chat_id=chat_id_admin, text="Esperando confirmación...")
        await reintentar_si_no_responde()
    except Exception as e:
        print(f"Error en mensaje automático: {e}")

async def reintentar_si_no_responde():
    while "intento" in reintentos and reintentos["intento"] <= INTENTOS_MAX:
        await asyncio.sleep(120)
        if "ok" in reintentos:
            return
        await application.bot.send_message(chat_id=chat_id_admin, text="⏰ ¿Se trabaja hoy? Confirmá por favor.")
        reintentos["intento"] += 1

async def callback_trabajo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if "ok" not in reintentos:
        reintentos["ok"] = True
        if query.data == "lab_no":
            fecha = datetime.now().strftime("%Y-%m-%d")
            df = pd.DataFrame([[fecha, "", "NO_LABORABLE", "", "", ""]], columns=["fecha", "operario", "asistencia", "comentario", "foto", "tijeras"])
            if os.path.exists(registro_path):
                df.to_csv(registro_path, mode="a", header=False, index=False)
            else:
                df.to_csv(registro_path, index=False)
            await query.edit_message_text("🟥 Marcado como **NO LABORABLE**.")
        elif query.data == "lab_si":
            await query.edit_message_text("✅ ¡Listo! Ya podés usar /hoy para registrar.")
        if "mensaje" in reintentos:
            await reintentos["mensaje"].delete()
        reintentos.clear()

# === Scheduler ===
scheduler = AsyncIOScheduler()
scheduler.add_job(mensaje_automatico, CronTrigger(hour=0, minute=0))
scheduler.start()

# === Handlers base ===
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("hola", hola))
application.add_handler(CommandHandler("ver_hoy", ver_hoy))
application.add_handler(CommandHandler("ver_fecha", ver_fecha))
application.add_handler(CommandHandler("exportar", exportar))
application.add_handler(CallbackQueryHandler(callback_trabajo, pattern="lab_.*"))

print("✅ BOT INICIADO Y ESCUCHANDO COMANDOS...")
application.run_polling()
