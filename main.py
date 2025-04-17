from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from datetime import datetime
import pandas as pd
import os

TOKEN = "7648235489:AAEmozaPfdWuzzkr5rhpnyiwD9F4Z8fNU9M"
registro_path = "data/registro.csv"  # Asegurate de crear esta carpeta/archivo

application = Application.builder().token(TOKEN).concurrent_updates(False).build()

# /ver_hoy
async def ver_hoy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fecha = datetime.now().strftime("%Y-%m-%d")
    await mostrar_registro(update, fecha)

# /ver_fecha
async def ver_fecha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Usá el comando así: /ver_fecha YYYY-MM-DD")
        return
    fecha = context.args[0]
    await mostrar_registro(update, fecha)

# mostrar_registro
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

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 ¡Hola! Este es el bot de asistencia.\n\n"
        "Usá los siguientes comandos:\n"
        "• /ver_hoy – Ver quién asistió hoy\n"
        "• /ver_fecha YYYY-MM-DD – Ver registro por fecha\n"
        "• /hola – Test para ver si el bot responde"
    )

# /hola
async def hola(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Estoy vivo!")

# Handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("hola", hola))
application.add_handler(CommandHandler("ver_hoy", ver_hoy))
application.add_handler(CommandHandler("ver_fecha", ver_fecha))

print("✅ BOT INICIADO Y ESCUCHANDO COMANDOS...")

# 🚀 ¡Arranca el bot!
application.run_polling()

