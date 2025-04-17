import os
import logging
import pandas as pd
from datetime import datetime
from pytz import timezone
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
from apscheduler.schedulers.background import BackgroundScheduler

# --- CONFIGURACIÓN DEL BOT ---
TOKEN = "7648235489:AAEmozaPfdwuzzkr5rhpnyiwD9F4Z8fNU9M"
ADMIN_ID = 555786610
operarios = ["Adrian", "Cesar", "Jere", "Belén"]
tijeras = [str(i) for i in range(1, 13)]

# --- ZONA HORARIA ---
arg = timezone("America/Argentina/Buenos_Aires")

# --- VARIABLES GLOBALES ---
asistencia = {}
modo_silencio = False
reintento_activo = False

# --- ARCHIVOS Y CARPETAS ---
os.makedirs("data", exist_ok=True)
os.makedirs("fotos", exist_ok=True)

if not os.path.exists("data/registro.csv"):
    pd.DataFrame(columns=["fecha", "operario", "tijera", "hora", "comentario"]).to_csv("data/registro.csv", index=False)

if not os.path.exists("data/comentarios.csv"):
    pd.DataFrame(columns=["fecha", "comentario", "foto"]).to_csv("data/comentarios.csv", index=False)

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__) 
# --- COMANDO /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bienvenido al bot de asistencia.\nUsá /hoy para registrar el día o /agendar para cargar días anteriores."
    )

# --- COMANDO /hoy ---
async def hoy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fecha = datetime.now(arg).strftime("%d-%m-%Y")
    asistencia["fecha"] = fecha
    asistencia["presentes"] = []
    asistencia["horas"] = {}
    asistencia["jere_solo"] = False

    botones = [[InlineKeyboardButton(op, callback_data=f"op_{op}")] for op in operarios]
    botones.append([InlineKeyboardButton("✔️ Confirmar", callback_data="confirmar")])
    botones.append([InlineKeyboardButton("🟨 Jere presente sin operar", callback_data="jere_solo")])

    await update.message.reply_text("Seleccioná los operarios presentes:", reply_markup=InlineKeyboardMarkup(botones))

# --- COMANDO /nolab ---
async def nolab(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fecha = datetime.now(arg).strftime("%d-%m-%Y")
    df = pd.read_csv("data/registro.csv")
    for op in operarios:
        df.loc[len(df)] = [fecha, op, "", "", "DÍA NO LABORABLE"]
    df.to_csv("data/registro.csv", index=False)
    await update.message.reply_text("✅ Día marcado como NO LABORABLE.")

# --- CALLBACKS ---
async def manejar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("op_"):
        op = data[3:]
        if op in asistencia["presentes"]:
            asistencia["presentes"].remove(op)
        else:
            asistencia["presentes"].append(op)

        texto = "Seleccioná los operarios presentes:\n"
        texto += "✔️ " + ", ".join(asistencia["presentes"]) if asistencia["presentes"] else "(ninguno seleccionado)"
        botones = [[InlineKeyboardButton(op, callback_data=f"op_{op}")] for op in operarios]
        botones.append([InlineKeyboardButton("✔️ Confirmar", callback_data="confirmar")])
        botones.append([InlineKeyboardButton("🟨 Jere presente sin operar", callback_data="jere_solo")])
        await query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(botones))

    elif data == "jere_solo":
        asistencia["jere_solo"] = True
        await query.edit_message_text("✅ Jere marcado como presente sin operar.")

    elif data == "confirmar":
        await query.edit_message_text("Ahora mandá las horas de cada tijera usada, ejemplo:\n2: 300\n5: 240") 
      # --- GUARDAR HORAS ---
def guardar_horas():
    fecha = asistencia.get("fecha")
    df = pd.read_csv("data/registro.csv")

    for op in asistencia.get("presentes", []):
        horas_op = asistencia["horas"].get(op, {})
        for tij, hora in horas_op.items():
            df.loc[len(df)] = [fecha, op, tij, hora, ""]

    if asistencia.get("jere_solo"):
        df.loc[len(df)] = [fecha, "Jere", "", "", "Presente sin operar"]

    df.to_csv("data/registro.csv", index=False)

# --- RECIBIR HORAS POR TEXTO ---
async def recibir_horas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    try:
        lineas = texto.splitlines()
        for linea in lineas:
            if ":" in linea:
                tij, hora = linea.split(":")
                tij = tij.strip()
                hora = float(hora.strip())
                for op in asistencia["presentes"]:
                    asistencia.setdefault("horas", {}).setdefault(op, {})[tij] = hora
        guardar_horas()
        await update.message.reply_text("✅ Registro guardado correctamente.")
    except:
        await update.message.reply_text("❌ Error en el formato. Usá: número_tijera: horas")

# --- EXPORTAR EXCEL AVANZADO ---
async def exportar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    df = pd.read_csv("data/registro.csv")
    resumen = df.groupby(["fecha", "operario"]).size().reset_index(name="Registros")

    with pd.ExcelWriter("data/asistencia.xlsx", engine="xlsxwriter") as writer:
        for op in operarios:
            df[df["operario"] == op].to_excel(writer, sheet_name=op, index=False)

        resumen.to_excel(writer, sheet_name="Resumen", index=False)
        workbook = writer.book
        sheet = writer.sheets["Resumen"]

        chart = workbook.add_chart({"type": "column"})
        chart.add_series({
            "categories": ["Resumen", 1, 0, len(resumen), 0],
            "values":     ["Resumen", 1, 2, len(resumen), 2],
            "name": "Registros por operario"
        })
        sheet.insert_chart("E2", chart)

    await update.message.reply_document(InputFile("data/asistencia.xlsx"), filename="asistencia.xlsx")

# --- VER ASISTENCIA DE HOY ---
async def ver_hoy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fecha = datetime.now(arg).strftime("%d-%m-%Y")
    df = pd.read_csv("data/registro.csv")
    hoy = df[df["fecha"] == fecha]
    if hoy.empty:
        await update.message.reply_text("❌ No hay registro para hoy.")
    else:
        texto = hoy[["operario", "tijera", "hora"]].to_string(index=False)
        await update.message.reply_text(f"📋 Asistencia de hoy:\n\n{texto}")

# --- VER ASISTENCIA POR FECHA ---
async def ver_fecha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("📅 Usá: /ver_fecha dd-mm-aaaa")
        return
    fecha = context.args[0]
    df = pd.read_csv("data/registro.csv")
    f = df[df["fecha"] == fecha]
    if f.empty:
        await update.message.reply_text("❌ No hay registro para esa fecha.")
    else:
        texto = f[["operario", "tijera", "hora"]].to_string(index=False)
        await update.message.reply_text(f"📋 Asistencia de {fecha}:\n\n{texto}")

# --- BORRAR FECHA COMPLETA ---
async def borrar_fecha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("🧽 Usá: /borrar_fecha dd-mm-aaaa")
        return
    fecha = context.args[0]
    df = pd.read_csv("data/registro.csv")
    df = df[df["fecha"] != fecha]
    df.to_csv("data/registro.csv", index=False)
    await update.message.reply_text(f"🧽 Registros del {fecha} eliminados.") 
  # --- AGENDAR DÍA ANTERIOR ---
async def agendar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("📅 Usá: /agendar dd-mm-aaaa")
        return
    fecha = context.args[0]
    asistencia["fecha"] = fecha
    asistencia["presentes"] = []
    asistencia["horas"] = {}
    asistencia["jere_solo"] = False

    botones = [[InlineKeyboardButton(op, callback_data=f"op_{op}")] for op in operarios]
    botones.append([InlineKeyboardButton("✔️ Confirmar", callback_data="confirmar")])
    botones.append([InlineKeyboardButton("🟨 Jere presente sin operar", callback_data="jere_solo")])

    await update.message.reply_text(f"Agendando para {fecha}. Seleccioná los presentes:",
                                    reply_markup=InlineKeyboardMarkup(botones))

# --- AGREGAR COMENTARIO ---
async def comentario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("✏️ Usá: /comentario Tu texto aquí")
        return
    texto = " ".join(context.args)
    fecha = asistencia.get("fecha", datetime.now(arg).strftime("%d-%m-%Y"))
    df = pd.read_csv("data/comentarios.csv")
    df.loc[len(df)] = [fecha, texto, ""]
    df.to_csv("data/comentarios.csv", index=False)
    await update.message.reply_text("✅ Comentario guardado.")

# --- SUBIR FOTO DEL DÍA ---
async def foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("📸 Enviá una foto junto al comando /foto")
        return
    fecha = asistencia.get("fecha", datetime.now(arg).strftime("%d-%m-%Y"))
    file_id = update.message.photo[-1].file_id
    nombre = f"fotos/{fecha.replace('/', '-')}_{file_id}.jpg"
    await update.message.photo[-1].get_file().download_to_drive(nombre)

    df = pd.read_csv("data/comentarios.csv")
    df.loc[len(df)] = [fecha, "Foto cargada", nombre]
    df.to_csv("data/comentarios.csv", index=False)
    await update.message.reply_text("✅ Foto guardada.")

# --- MODO SILENCIO ---
async def silencio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global modo_silencio
    modo_silencio = True
    await update.message.reply_text("🔕 Modo silencio activado para hoy.")

# --- RECORDATORIO AUTOMÁTICO + REINTENTO ---
async def enviar_recordatorio(context: ContextTypes.DEFAULT_TYPE):
    global reintento_activo
    if modo_silencio:
        return
    fecha = datetime.now(arg).strftime("%d-%m-%Y")
    asistencia["fecha"] = fecha
    asistencia["estado_confirmado"] = False
    botones = [[InlineKeyboardButton("✅ Sí", callback_data="trabaja_si"),
                InlineKeyboardButton("❌ No", callback_data="trabaja_no")]]
    await context.bot.send_message(chat_id=ADMIN_ID, text="¿Se trabaja esta madrugada?", reply_markup=InlineKeyboardMarkup(botones))
    reintento_activo = True

async def reintentar(context: ContextTypes.DEFAULT_TYPE):
    if reintento_activo and not asistencia.get("estado_confirmado") and not modo_silencio:
        botones = [[InlineKeyboardButton("✅ Sí", callback_data="trabaja_si"),
                    InlineKeyboardButton("❌ No", callback_data="trabaja_no")]]
        await context.bot.send_message(chat_id=ADMIN_ID, text="⏰ Seguimos esperando confirmación: ¿se trabaja?", reply_markup=InlineKeyboardMarkup(botones))

# --- CALLBACK EXTRA PARA SÍ / NO ---
async def decision_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "trabaja_si":
        asistencia["estado_confirmado"] = True
        await query.edit_message_text("✅ Confirmado que se trabaja. Usá /hoy para registrar.")
    elif query.data == "trabaja_no":
        asistencia["estado_confirmado"] = True
        await nolab(update, context)
        await query.edit_message_text("❌ Confirmado como día NO LABORABLE.")

# --- CONEXIÓN DE FUNCIONES ---
app = ApplicationBuilder().token(TOKEN).build()

# Comandos
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("hoy", hoy))
app.add_handler(CommandHandler("nolab", nolab))
app.add_handler(CommandHandler("agendar", agendar))
app.add_handler(CommandHandler("exportar", exportar))
app.add_handler(CommandHandler("ver_hoy", ver_hoy))
app.add_handler(CommandHandler("ver_fecha", ver_fecha))
app.add_handler(CommandHandler("borrar_fecha", borrar_fecha))
app.add_handler(CommandHandler("comentario", comentario))
app.add_handler(CommandHandler("foto", foto))
app.add_handler(CommandHandler("silencio", silencio))

# Respuesta a mensajes de texto (para horas)
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_horas))

# Callbacks de botones
app.add_handler(CallbackQueryHandler(manejar_callback, pattern="^(op_|confirmar|jere_solo)$"))
app.add_handler(CallbackQueryHandler(decision_callback, pattern="^(trabaja_si|trabaja_no)$"))

# --- PROGRAMACIÓN DIARIA AUTOMÁTICA ---
scheduler = BackgroundScheduler()

# --- FUNCIONES PROGRAMADAS ---
def enviar_recordatorio():
    if not modo_silencio:
        app.bot.send_message(chat_id=ADMIN_ID, text='¿Se trabaja esta madrugada? Usá /hoy o /nolab')

def reintentar():
    if not modo_silencio and not asistencia.get('respondido'):
        app.bot.send_message(chat_id=ADMIN_ID, text='⚠️ Recordatorio: ¿Se trabaja esta madrugada? Usá /hoy o /nolab')
scheduler.add_job(enviar_recordatorio, "cron", day_of_week="sun-thu", hour=0, minute=0, timezone=arg)
scheduler.add_job(reintentar, "interval", minutes=2)
scheduler.start()

# --- INICIO DEL BOT ---
if __name__ == "__main__":
    print("✅ Bot de asistencia corriendo correctamente.")
    app.run_polling()

