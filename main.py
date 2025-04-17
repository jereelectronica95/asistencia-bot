# === VISUALIZACIÓN DE HISTORIAL ===

from telegram import Update
from telegram.ext import ContextTypes


async def ver_hoy(update: Update, context: ContextTypes.DEFAULT_TYPE):

    fecha = datetime.now(arg).strftime("%Y-%m-%d")
    await mostrar_registro(update, fecha)

async def ver_fecha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Usá el comando así: /ver_fecha YYYY-MM-DD")
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

    texto = f"**Registro del {fecha}:**\\n"

    for _, fila in df_dia.iterrows():
        if fila["asistencia"] == "TRABAJO":
            texto += f"✔ {fila['operario']}: trabajó (tijeras: {fila['tijeras']})\\n"
        elif fila["asistencia"] == "PRESENTE":
            texto += f"🟡 {fila['operario']}: solo presente\\n"
        elif fila["asistencia"] == "FALTO":
            texto += f"❌ {fila['operario']}: faltó\\n"
        else:
            texto += f"- {fila['operario']}: {fila['asistencia']}\\n"

    if str(df_dia['comentario'].values[0]).strip():
        texto += f"Comentario: {df_dia['comentario'].values[0]}\\n"

    await update.message.reply_text(texto, parse_mode="Markdown")

app.add_handler(CommandHandler("ver_hoy", ver_hoy))
app.add_handler(CommandHandler("ver_fecha", ver_fecha))
