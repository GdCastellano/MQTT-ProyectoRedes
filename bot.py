from telegram import Update, BotCommand, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from config import TELEGRAM_TOKEN, PING_COUNT
from network_monitor import ping_host, parse_ping_output
from monitoring_service import MonitoringService

# Diccionario para guardar servicios de monitoreo por usuario
monitoring_services = {}

# Definir los comandos y descripciones para el menú del bot
COMMANDS = [
    BotCommand("start", "Inicia el bot y muestra el mensaje de bienvenida"),
    BotCommand("destino", "Realiza un ping a un host/IP. Ej: /destino 8.8.8.8"),
    BotCommand("monitorear", "Inicia el monitoreo recurrente de un host"),
    BotCommand("detener", "Detiene el monitoreo activo"),
]

# Estados de la conversación
WAITING_HOST = 1
WAITING_MONITOR_HOST = 2

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Crear el teclado personalizado
    keyboard = [
        [KeyboardButton("/destino"), KeyboardButton("/monitorear")],
        [KeyboardButton("/detener")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    await update.message.reply_text(
        "Bienvenido al bot de monitoreo. Usa los botones o escribe /destino <host> para comenzar.",
        reply_markup=reply_markup
    )

async def destino(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Por favor, ingresa la dirección IP o el host a monitorear:")
        return WAITING_HOST
    
    host = context.args[0]
    await process_ping(update, host)
    return ConversationHandler.END

async def process_ping(update: Update, host: str):
    output = ping_host(host, PING_COUNT)
    latency, ttl, reachable = parse_ping_output(output)
    if update.message:
        if reachable:
            await update.message.reply_text(
                f"Latencia promedio a {host}: {latency} ms\nSaltos (TTL): {ttl}"
            )
        else:
            await update.message.reply_text(f"No se pudo alcanzar el host {host}.")

async def receive_host(update: Update, context: ContextTypes.DEFAULT_TYPE):
    host = update.message.text
    await process_ping(update, host)
    return ConversationHandler.END

async def monitorear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Por favor, ingresa la dirección IP o el host a monitorear:")
        return WAITING_MONITOR_HOST
    
    host = context.args[0]
    await start_monitoring(update, host)
    return ConversationHandler.END

async def start_monitoring(update: Update, host: str):
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

async def receive_monitor_host(update: Update, context: ContextTypes.DEFAULT_TYPE):
    host = update.message.text
    await start_monitoring(update, host)
    return ConversationHandler.END

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
    
    # Crear el manejador de conversación para el comando destino
    destino_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("destino", destino)],
        states={
            WAITING_HOST: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_host)],
        },
        fallbacks=[],
    )

    # Crear el manejador de conversación para el comando monitorear
    monitorear_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("monitorear", monitorear)],
        states={
            WAITING_MONITOR_HOST: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_monitor_host)],
        },
        fallbacks=[],
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(destino_conv_handler)
    app.add_handler(monitorear_conv_handler)
    app.add_handler(CommandHandler("detener", detener))

    # Registrar comandos en el menú del bot
    async def set_commands(app):
        await app.bot.set_my_commands(COMMANDS)
    app.post_init = set_commands

    app.run_polling()

if __name__ == "__main__":
    main()
