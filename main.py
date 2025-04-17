from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Application, CommandHandler, ContextTypes, CallbackQueryHandler)
from telegram.constants import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import pandas as pd
import os
import asyncio

TOKEN = "7648235489:AAEmozaPfdWuzzkr5rhpnyiwD9F4Z8fNU9M"
registro_path = "data/registro.csv"

application = Application.builder().token(TOKEN).concurrent_updates(False).build()
scheduler = AsyncIOScheduler()

# ======================= FUNCIONES BÁSICAS =======================

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

# ======================= VISUALIZACIÓN =======================

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
        else:
            texto += f"- {fila['operario']}: {fila['asistencia']}\n"

    if "comentario" in df_dia.columns and str(df_dia['comentario'].values[0]).strip():
        texto += f"Comentario: {df_dia['comentario'].values[0]}\n"

    await update.message.reply_text(texto, parse_mode="Markdown")

# ======================= EXPORTACIÓN =======================

async def exportar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not os.path.exists(registro_path):
        await update.message.reply_text("No hay datos de asistencia para exportar.")
        return

    df = pd.read_csv(registro_path)
    excel_path = "data/asistencia_export.xlsx"

    with pd.ExcelWriter(excel_path, engine="xlsxwriter") as writer:
        resumen = df.groupby("fecha")["asistencia"].apply(lambda x: (x == "TRABAJO").sum()).reset_index(name="trabajados")
        resumen["no_trabajados"] = df.groupby("fecha")["asistencia"].apply(lambda x: (x == "NO").sum()).values
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
        chart.set_title({'name': 'Resumen de Días'})
        chart.set_x_axis({'name': 'Fecha'})
        chart.set_y_axis({'name': 'Cantidad'})
        worksheet.insert_chart('E2', chart)

        for op in df["operario"].dropna().unique():
            df[df["operario"] == op].to_excel(writer, sheet_name=op[:31], index=False)

    await update.message.reply_document(InputFile(excel_path), filename="asistencia_export.xlsx")

# ======================= AVISO AUTOMÁTICO 00:00 =======================

async def mensaje_diario():
    chat_id = 555786610
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Sí, se trabaja", callback_data="trabajar_si")],
        [InlineKeyboardButton("❌ No, día no laborable", callback_data="trabajar_no")]
    ])
    await application.bot.send_message(chat_id=chat_id, text="¿Se trabaja hoy?", reply_markup=keyboard)

async def callback_trabajo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "trabajar_si":
        await query.edit_message_text("🗓 Día confirmado como *laborable*.", parse_mode="Markdown")
    elif query.data == "trabajar_no":
        fecha = datetime.now().strftime("%Y-%m-%d")
        if not os.path.exists(registro_path):
            df = pd.DataFrame(columns=["fecha", "operario", "asistencia", "comentario", "foto", "tijeras"])
        else:
            df = pd.read_csv(registro_path)
        df = pd.concat([df, pd.DataFrame([[fecha, "", "NO", "", "", ""]], columns=df.columns)])
        df.to_csv(registro_path, index=False)
        await query.edit_message_text("📴 Día marcado como *no laborable*.", parse_mode="Markdown")

# ======================= HANDLERS =======================

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("hola", hola))
application.add_handler(CommandHandler("ver_hoy", ver_hoy))
application.add_handler(CommandHandler("ver_fecha", ver_fecha))
application.add_handler(CommandHandler("exportar", exportar))
application.add_handler(CallbackQueryHandler(callback_trabajo, pattern="^trabajar_"))

scheduler.add_job(mensaje_diario, trigger="cron", hour=0, minute=0)

# ======================= ARRANQUE CORRECTO =======================

async def main():
    print("✅ BOT INICIADO Y ESCUCHANDO COMANDOS...")
    scheduler.start()
    print("⏰ Scheduler iniciado correctamente.")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    await application.updater.idle()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())



