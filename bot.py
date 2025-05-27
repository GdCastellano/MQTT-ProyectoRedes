from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from config import TELEGRAM_TOKEN, PING_COUNT
from network_monitor import ping_host, parse_ping_output
from monitoring_service import MonitoringService

# Diccionario para guardar servicios de monitoreo por usuario
monitoring_services = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bienvenido al bot de monitoreo. Usa /destino <host> para comenzar.")

async def destino(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        if update.message:
            await update.message.reply_text("Debes especificar un host. Ejemplo: /destino 8.8.8.8")
        return
    host = context.args[0]
    output = ping_host(host, PING_COUNT)
    latency, ttl, reachable = parse_ping_output(output)
    if update.message:
        if reachable:
            await update.message.reply_text(
                f"Latencia promedio a {host}: {latency} ms\nSaltos (TTL): {ttl}"
            )
        else:
            await update.message.reply_text(f"No se pudo alcanzar el host {host}.")

async def monitorear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Debes especificar un host. Ejemplo: /monitorear 8.8.8.8")
        return
    host = context.args[0]
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    def alert_callback(msg):
        # Enviar alerta al usuario
        context.application.create_task(context.bot.send_message(chat_id=chat_id, text=msg))

    # Detener monitoreo previo si existe
    if user_id in monitoring_services:
        monitoring_services[user_id].stop()
    service = MonitoringService(host, alert_callback)
    monitoring_services[user_id] = service
    service.start()
    await update.message.reply_text(f"Monitoreo iniciado para {host}.")

async def detener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in monitoring_services:
        monitoring_services[user_id].stop()
        del monitoring_services[user_id]
        await update.message.reply_text("Monitoreo detenido.")
    else:
        await update.message.reply_text("No hay monitoreo activo.")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("destino", destino))
    app.add_handler(CommandHandler("monitorear", monitorear))
    app.add_handler(CommandHandler("detener", detener))
    app.run_polling()

if __name__ == "__main__":
    main()
