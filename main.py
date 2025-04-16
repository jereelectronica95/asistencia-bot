import logging
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters
)
import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler

# Configuración básica
TOKEN = "7648235489:AAEmozaPfdWuzzkr5rhpnyiwD9F4Z8fNU9M"
ADMIN_ID = 555786610  # ID de Jere
operarios = ["Adrian", "Cesar", "Jere", "Belén"]
tijeras = [str(i) for i in range(1, 13)]
registro_path = "data/registro.csv"
asistencia_actual = {}
scheduler = BackgroundScheduler()
scheduler.start()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear CSV si no existe
if not os.path.exists("data"):
    os.mkdir("data")

if not os.path.exists(registro_path):
    df = pd.DataFrame(columns=["fecha", "operario", "tijera", "hora_actual", "uso_dia"])
    df.to_csv(registro_path, index=False)

# --- FUNCIONES ---

def guardar_registro(fecha, asistieron, tijeras_usadas, horas):
    df = pd.read_csv(registro_path)
    for tij, hora_actual in horas.items():
        hora_actual = float(hora_actual)
        uso = hora_actual - obtener_ultima_hora(tij)
        for op in asistieron:
            df.loc[len(df)] = [fecha, op, tij, hora_actual, max(0, uso)]
    df.to_csv(registro_path, index=False)

def obtener_ultima_hora(tijera):
    df = pd.read_csv(registro_path)
    filas = df[df["tijera"] == tijera]
    if len(filas) == 0:
        return 0
    return filas.sort_values("fecha").iloc[-1]["hora_actual"]

def build_keyboard(opciones, prefix):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{'✅' if asistencia_actual.get(prefix, {}).get(op, False) else ''} {op}",
                              callback_data=f"{prefix}:{op}")]
        for op in opciones
    ] + [[InlineKeyboardButton("✅ Confirmar", callback_data=f"{prefix}:confirmar")]])

# --- COMANDOS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("Bot de asistencia listo para usar. Usá /hoy o /agendar para registrar días.")

async def hoy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    fecha = datetime.now().strftime("%Y-%m-%d")
    asistencia_actual["fecha"] = fecha
    asistencia_actual["asistieron"] = {}
    await update.message.reply_text(
        f"¿Quiénes asistieron hoy ({fecha})?",
        reply_markup=build_keyboard(operarios, "asistencia")
    )

async def agendar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    hoy = datetime.now().date()
    ultimos = [(hoy - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, 4)]
    buttons = [[InlineKeyboardButton(f, callback_data=f"fecha:{f}")] for f in ultimos]
    await update.message.reply_text("¿Qué día querés registrar?", reply_markup=InlineKeyboardMarkup(buttons))

async def exportar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_document(document=open(registro_path, "rb"))

async def resumen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    df = pd.read_csv(registro_path)
    resumen_text = df.groupby("operario")["fecha"].nunique().to_string()
    await update.message.reply_text(f"Días trabajados:\n{resumen_text}")

async def ver_hoy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    fecha = datetime.now().strftime("%Y-%m-%d")
    df = pd.read_csv(registro_path)
    hoy_df = df[df["fecha"] == fecha]
    if hoy_df.empty:
        await update.message.reply_text("Hoy no se registró nada.")
    else:
        texto = hoy_df.to_string()
        await update.message.reply_text(f"Registro de hoy:\n{texto}")

# --- CALLBACKS ---

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("fecha:"):
        fecha = data.split(":")[1]
        asistencia_actual["fecha"] = fecha
        asistencia_actual["asistieron"] = {}
        await query.edit_message_text(
            f"¿Quiénes asistieron el {fecha}?",
            reply_markup=build_keyboard(operarios, "asistencia")
        )

    elif data.startswith("asistencia:"):
        op = data.split(":")[1]
        if op == "confirmar":
            await query.edit_message_text("Asistencia marcada. ¿Qué tijeras se usaron?",
                                          reply_markup=build_keyboard(tijeras, "tijera"))
        else:
            asistencia_actual.setdefault("asistieron", {})
            asistencia_actual["asistieron"][op] = not asistencia_actual["asistieron"].get(op, False)
            await query.edit_message_reply_markup(reply_markup=build_keyboard(operarios, "asistencia"))

    elif data.startswith("tijera:"):
        tj = data.split(":")[1]
        if tj == "confirmar":
            asistencia_actual.setdefault("tijeras", {})
            asistencia_actual["tijeras_usadas"] = [k for k, v in asistencia_actual["tijeras"].items() if v]
            asistencia_actual["horas"] = {}
            await query.edit_message_text("Ingresá las horas de cada tijera usada, por ejemplo:\n\n`1: 528\n3: 712.5`\n(Mandalo como mensaje de texto)",
                                          parse_mode="Markdown")
        else:
            asistencia_actual.setdefault("tijeras", {})
            asistencia_actual["tijeras"][tj] = not asistencia_actual["tijeras"].get(tj, False)
            await query.edit_message_reply_markup(reply_markup=build_keyboard(tijeras, "tijera"))

async def recibir_horas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if "tijeras_usadas" not in asistencia_actual:
        return
    texto = update.message.text
    for linea in texto.splitlines():
        if ":" in linea:
            t, h = linea.split(":")
            asistencia_actual["horas"][t.strip()] = float(h.strip())
    guardar_registro(asistencia_actual["fecha"],
                     [k for k, v in asistencia_actual["asistieron"].items() if v],
                     asistencia_actual["tijeras_usadas"],
                     asistencia_actual["horas"])
    await update.message.reply_text("Registro guardado correctamente ✅")

# --- INICIALIZACIÓN ---

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("hoy", hoy))
app.add_handler(CommandHandler("agendar", agendar))
app.add_handler(CommandHandler("exportar", exportar))
app.add_handler(CommandHandler("resumen", resumen))
app.add_handler(CommandHandler("ver_hoy", ver_hoy))
app.add_handler(CallbackQueryHandler(callback))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_horas))

# Tarea diaria
def tarea_diaria():
    import asyncio
    asyncio.run(hoy(
        Update(update_id=0, message=None),
        ContextTypes.DEFAULT_TYPE()
    ))

# Programar a las 23:55
scheduler.add_job(lambda: app.bot.send_message(chat_id=ADMIN_ID, text="¿Se trabaja esta madrugada? Usá /hoy"), "cron", day_of_week="sun-thu", hour=23, minute=55)

app.run_polling()
