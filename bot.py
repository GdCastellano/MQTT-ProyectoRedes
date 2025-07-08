from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from config import TELEGRAM_TOKEN, PING_COUNT, LOG_RETENTION_DAYS
from network_monitor import ping_host, parse_ping_output
from monitoring_service import MonitoringService
from logger_service import bot_logger
from datetime import datetime

# Diccionario para guardar servicios de monitoreo por usuario
monitoring_services = {}

# Diccionario para tracking de estados de conversación por usuario
user_states = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    chat_id = update.effective_chat.id
    
    # Registrar comando en logs
    bot_logger.log_command(user_id, "start", username=username)
    
    welcome_message = """🤖 **¡Bienvenido al Bot de Monitoreo de Red!**

📋 **Comandos disponibles:**

🏓 **Comandos de red:**
• `/destino <host>` - Hacer ping a un host
• `/monitorear <host>` - Iniciar monitoreo continuo
• `/detener` - Detener monitoreo activo

📊 **Comandos de logs:**
• `/logs` - Ver información de tu sesión actual
• `/estado_logs` - Estado general del sistema de logs
• `/limpiar_logs [días]` - Limpiar logs antiguos

🛠️ **Comandos de utilidad:**
• `/cancelar` - Cancelar operación en progreso
• `/ayuda` - Ver esta ayuda

ℹ️ **Ejemplo de uso:**
`/destino 8.8.8.8`
`/monitorear google.com`

🎯 **¡Tu sesión de logging ha comenzado automáticamente!**
Todos tus comandos y actividades quedarán registrados."""
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def destino(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    chat_id = update.effective_chat.id
    
    # Registrar comando en logs
    bot_logger.log_command(user_id, "destino", context.args, username=username)
    
    if not context.args:
        # Establecer estado de espera para el siguiente mensaje
        user_states[user_id] = {
            'command': 'destino',
            'timestamp': datetime.now()
        }
        bot_logger.log_system_event("user_state_set", {
            "user_id": user_id,
            "command": "destino",
            "waiting_for": "host_address"
        })
        if update.message:
            await update.message.reply_text(
                "🎯 **Por favor, envía la dirección del host:**\n\n"
                "Ejemplos válidos:\n"
                "• `8.8.8.8`\n"
                "• `google.com`\n"
                "• `192.168.1.1`\n\n"
                "📝 Envía solo la dirección en tu próximo mensaje.",
                parse_mode='Markdown'
            )
        return
    
    host = context.args[0]
    try:
        output = ping_host(host, PING_COUNT)
        latency, ttl, reachable = parse_ping_output(output)
        
        # Registrar resultado del ping
        bot_logger.log_ping_result(user_id, host, latency, ttl, reachable, output)
        
        if update.message:
            if reachable:
                await update.message.reply_text(
                    f"Latencia promedio a {host}: {latency} ms\nSaltos (TTL): {ttl}"
                )
            else:
                await update.message.reply_text(f"No se pudo alcanzar el host {host}.")
    except Exception as e:
        bot_logger.log_error(user_id, f"Error en comando destino: {e}", f"Host: {host}")
        if update.message:
            await update.message.reply_text(f"Error al hacer ping a {host}: {str(e)}")

async def monitorear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    chat_id = update.effective_chat.id
    
    # Registrar comando en logs
    bot_logger.log_command(user_id, "monitorear", context.args, username=username)
    
    if not context.args:
        # Establecer estado de espera para el siguiente mensaje
        user_states[user_id] = {
            'command': 'monitorear',
            'timestamp': datetime.now()
        }
        bot_logger.log_system_event("user_state_set", {
            "user_id": user_id,
            "command": "monitorear",
            "waiting_for": "host_address"
        })
        await update.message.reply_text(
            "🔍 **Por favor, envía la dirección del host a monitorear:**\n\n"
            "Ejemplos válidos:\n"
            "• `8.8.8.8`\n"
            "• `google.com`\n"
            "• `192.168.1.1`\n\n"
            "📝 Envía solo la dirección en tu próximo mensaje.\n"
            "⚡ El monitoreo iniciará automáticamente.",
            parse_mode='Markdown'
        )
        return
    
    host = context.args[0]

    def alert_callback(msg):
        # Registrar alerta en logs
        bot_logger.log_alert(user_id, host, msg)
        # Enviar alerta al usuario
        context.application.create_task(context.bot.send_message(chat_id=chat_id, text=msg))

    try:
        # Detener monitoreo previo si existe
        if user_id in monitoring_services:
            old_host = getattr(monitoring_services[user_id], 'host', 'unknown')
            monitoring_services[user_id].stop()
            bot_logger.log_monitoring_stop(user_id, old_host)
        
        service = MonitoringService(host, alert_callback, user_id)
        monitoring_services[user_id] = service
        service.start()
        
        # Registrar inicio de monitoreo
        bot_logger.log_monitoring_start(user_id, host)
        
        await update.message.reply_text(f"Monitoreo iniciado para {host}.")
        
    except Exception as e:
        bot_logger.log_error(user_id, f"Error iniciando monitoreo: {e}", f"Host: {host}")
        await update.message.reply_text(f"Error al iniciar monitoreo para {host}: {str(e)}")

async def detener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    # Registrar comando en logs
    bot_logger.log_command(user_id, "detener", username=username)
    
    try:
        if user_id in monitoring_services:
            host = getattr(monitoring_services[user_id], 'host', 'unknown')
            monitoring_services[user_id].stop()
            del monitoring_services[user_id]
            
            # Registrar detención de monitoreo
            bot_logger.log_monitoring_stop(user_id, host)
            
            await update.message.reply_text("Monitoreo detenido.")
        else:
            bot_logger.log_error(user_id, "Intento de detener monitoreo inexistente", "No hay monitoreo activo")
            await update.message.reply_text("No hay monitoreo activo.")
            
    except Exception as e:
        bot_logger.log_error(user_id, f"Error deteniendo monitoreo: {e}", "Comando detener")
        await update.message.reply_text(f"Error al detener monitoreo: {str(e)}")

async def logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra información de logs del usuario."""
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    bot_logger.log_command(user_id, "logs", username=username)
    
    try:
        # Obtener resumen de sesión actual
        session_summary = bot_logger.get_user_session_summary(user_id)
        
        if session_summary:
            message = f"""📊 **Resumen de tu sesión actual:**
            
🆔 ID Sesión: `{session_summary['session_id']}`
⏰ Inicio: {session_summary['start_time'].strftime('%Y-%m-%d %H:%M:%S')}
⏱️ Duración: {session_summary['duration']}
📝 Comandos: {session_summary['commands_count']}
🏓 Pings: {session_summary['ping_count']}
🚨 Alertas: {session_summary['alerts_count']}
📁 Archivo: `{session_summary['log_file']}`"""
        else:
            message = "ℹ️ No tienes una sesión activa. Usa cualquier comando para iniciar logging."
        
        # Obtener archivos de log anteriores del usuario
        user_logs = bot_logger.get_user_log_files(user_id)
        if user_logs:
            message += f"\n\n📚 **Logs anteriores:** {len(user_logs)} archivo(s)"
            # Mostrar los 3 más recientes
            recent_logs = sorted(user_logs, key=lambda x: x.stat().st_mtime, reverse=True)[:3]
            for log_file in recent_logs:
                mod_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                message += f"\n  • `{log_file.name}` ({mod_time.strftime('%Y-%m-%d %H:%M')})"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        bot_logger.log_error(user_id, f"Error en comando logs: {e}", "Comando logs")
        await update.message.reply_text(f"Error al obtener información de logs: {str(e)}")

async def limpiar_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Limpia logs antiguos (solo para administradores del sistema)."""
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    bot_logger.log_command(user_id, "limpiar_logs", context.args, username=username)
    
    try:
        # Por seguridad, este comando podría estar restringido a ciertos usuarios
        # En este ejemplo, permitimos que cualquier usuario limpie logs antiguos
        
        days = 30  # Valor por defecto
        if context.args:
            try:
                days = int(context.args[0])
                if days < 1:
                    raise ValueError("Los días deben ser mayor a 0")
            except ValueError:
                await update.message.reply_text("❌ Número de días inválido. Usa: /limpiar_logs [días]")
                return
        
        # Obtener info antes de limpiar
        logs_info = bot_logger.get_logs_directory_info()
        
        # Limpiar logs antiguos
        deleted_files = bot_logger.cleanup_old_logs(days)
        
        if deleted_files:
            message = f"🧹 **Limpieza completada:**\n"
            message += f"• Archivos eliminados: {len(deleted_files)}\n"
            message += f"• Antigüedad: más de {days} días\n"
            message += f"• Archivos restantes: {logs_info['total_files'] - len(deleted_files)}"
            
            bot_logger.log_system_event("logs_cleanup", {
                "user_id": user_id,
                "days_threshold": days,
                "files_deleted": len(deleted_files),
                "files_deleted_list": deleted_files
            })
        else:
            message = f"✅ No hay logs antiguos para eliminar (más de {days} días)."
        
        await update.message.reply_text(message)
        
    except Exception as e:
        bot_logger.log_error(user_id, f"Error en comando limpiar_logs: {e}", "Comando limpiar_logs")
        await update.message.reply_text(f"Error al limpiar logs: {str(e)}")

async def estado_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el estado general del sistema de logs."""
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    bot_logger.log_command(user_id, "estado_logs", username=username)
    
    try:
        logs_info = bot_logger.get_logs_directory_info()
        
        message = f"""📁 **Estado del Sistema de Logs:**

📂 Directorio: `{logs_info['directory']}`
📄 Total archivos: {logs_info['total_files']}
💾 Tamaño total: {logs_info['total_size_mb']} MB

"""
        
        if logs_info['oldest_log']:
            oldest = datetime.fromtimestamp(logs_info['oldest_log'])
            message += f"📅 Log más antiguo: {oldest.strftime('%Y-%m-%d %H:%M')}\n"
        
        if logs_info['newest_log']:
            newest = datetime.fromtimestamp(logs_info['newest_log'])
            message += f"🆕 Log más reciente: {newest.strftime('%Y-%m-%d %H:%M')}\n"
        
        # Contar sesiones activas
        active_sessions = len(bot_logger._user_sessions)
        message += f"🔄 Sesiones activas: {active_sessions}"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        bot_logger.log_error(user_id, f"Error en comando estado_logs: {e}", "Comando estado_logs")
        await update.message.reply_text(f"Error al obtener estado de logs: {str(e)}")

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja mensajes de texto cuando el usuario está en un estado de espera."""
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    # Verificar si el usuario tiene un estado de espera activo
    if user_id not in user_states:
        # Si no hay estado activo, ignorar el mensaje de texto
        return
    
    user_state = user_states[user_id]
    command = user_state['command']
    state_timestamp = user_state['timestamp']
    
    # Verificar que el estado no sea muy antiguo (más de 5 minutos)
    time_diff = datetime.now() - state_timestamp
    if time_diff.total_seconds() > 300:  # 5 minutos
        del user_states[user_id]
        bot_logger.log_system_event("user_state_expired", {
            "user_id": user_id,
            "command": command,
            "time_elapsed": time_diff.total_seconds()
        })
        await update.message.reply_text(
            "⏰ **Tiempo de espera agotado.**\n\n"
            "Por favor, usa el comando completo:\n"
            f"• `/{command} <dirección>`\n"
            f"• Ejemplo: `/{command} 8.8.8.8`",
            parse_mode='Markdown'
        )
        return
    
    # Obtener la dirección del mensaje de texto
    host = update.message.text.strip()
    
    # Validación básica de la dirección
    if not host or len(host.split()) > 1:
        await update.message.reply_text(
            "❌ **Dirección inválida.**\n\n"
            "Por favor, envía solo la dirección del host:\n"
            "• Sin espacios adicionales\n"
            "• Ejemplo: `google.com` o `8.8.8.8`",
            parse_mode='Markdown'
        )
        return
    
    # Limpiar estado del usuario
    del user_states[user_id]
    
    # Registrar el mensaje como continuación del comando
    bot_logger.log_command(user_id, f"{command}_continued", [host], username=username)
    bot_logger.log_system_event("user_state_completed", {
        "user_id": user_id,
        "command": command,
        "host": host
    })
    
    # Ejecutar el comando correspondiente con la dirección proporcionada
    if command == 'destino':
        await execute_destino(update, context, host, user_id, username)
    elif command == 'monitorear':
        await execute_monitorear(update, context, host, user_id, username)

async def execute_destino(update, context, host, user_id, username):
    """Ejecuta la lógica del comando destino con la dirección proporcionada."""
    chat_id = update.effective_chat.id
    
    try:
        # Informar que se está procesando
        processing_msg = await update.message.reply_text(f"🏓 Haciendo ping a `{host}`...", parse_mode='Markdown')
        
        output = ping_host(host, PING_COUNT)
        latency, ttl, reachable = parse_ping_output(output)
        
        # Registrar resultado del ping
        bot_logger.log_ping_result(user_id, host, latency, ttl, reachable, output)
        
        # Eliminar mensaje de procesamiento
        await context.bot.delete_message(chat_id=chat_id, message_id=processing_msg.message_id)
        
        if reachable:
            await update.message.reply_text(
                f"✅ **Ping exitoso a {host}:**\n\n"
                f"📊 Latencia promedio: **{latency} ms**\n"
                f"🔢 Saltos (TTL): **{ttl}**\n\n"
                f"💡 Usa `/monitorear {host}` para monitoreo continuo.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"❌ **No se pudo alcanzar el host {host}.**\n\n"
                "Posibles causas:\n"
                "• Host no responde a ping\n"
                "• Dirección incorrecta\n"
                "• Problemas de conectividad\n\n"
                "🔄 Intenta con otra dirección.",
                parse_mode='Markdown'
            )
    except Exception as e:
        bot_logger.log_error(user_id, f"Error en comando destino: {e}", f"Host: {host}")
        await update.message.reply_text(
            f"💥 **Error al hacer ping a {host}:**\n\n"
            f"Error: `{str(e)}`\n\n"
            "🔄 Intenta nuevamente.",
            parse_mode='Markdown'
        )

async def execute_monitorear(update, context, host, user_id, username):
    """Ejecuta la lógica del comando monitorear con la dirección proporcionada."""
    chat_id = update.effective_chat.id

    def alert_callback(msg):
        # Registrar alerta en logs
        bot_logger.log_alert(user_id, host, msg)
        # Enviar alerta al usuario
        context.application.create_task(context.bot.send_message(chat_id=chat_id, text=msg))

    try:
        # Informar que se está iniciando
        setup_msg = await update.message.reply_text(f"⚙️ Configurando monitoreo para `{host}`...", parse_mode='Markdown')
        
        # Detener monitoreo previo si existe
        if user_id in monitoring_services:
            old_host = getattr(monitoring_services[user_id], 'host', 'unknown')
            monitoring_services[user_id].stop()
            bot_logger.log_monitoring_stop(user_id, old_host)
        
        service = MonitoringService(host, alert_callback, user_id)
        monitoring_services[user_id] = service
        service.start()
        
        # Registrar inicio de monitoreo
        bot_logger.log_monitoring_start(user_id, host)
        
        # Eliminar mensaje de configuración
        await context.bot.delete_message(chat_id=chat_id, message_id=setup_msg.message_id)
        
        await update.message.reply_text(
            f"🔍 **Monitoreo iniciado para {host}:**\n\n"
            f"📊 Intervalo: cada **{5} segundos**\n"
            f"🚨 Recibirás alertas automáticas si hay fallos\n"
            f"📈 Los datos se publican en MQTT\n\n"
            f"⏹️ Usa `/detener` para finalizar el monitoreo.",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        bot_logger.log_error(user_id, f"Error iniciando monitoreo: {e}", f"Host: {host}")
        await update.message.reply_text(
            f"💥 **Error al iniciar monitoreo para {host}:**\n\n"
            f"Error: `{str(e)}`\n\n"
            "🔄 Intenta nuevamente.",
            parse_mode='Markdown'
        )

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela cualquier operación en progreso del usuario."""
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    bot_logger.log_command(user_id, "cancelar", username=username)
    
    if user_id in user_states:
        cancelled_command = user_states[user_id]['command']
        del user_states[user_id]
        
        bot_logger.log_system_event("user_state_cancelled", {
            "user_id": user_id,
            "cancelled_command": cancelled_command
        })
        
        await update.message.reply_text(
            f"❌ **Operación cancelada.**\n\n"
            f"Se canceló el comando: `/{cancelled_command}`\n\n"
            "✅ Puedes usar cualquier comando normalmente.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "ℹ️ **No hay operaciones en progreso para cancelar.**\n\n"
            "Puedes usar cualquier comando normalmente.",
            parse_mode='Markdown'
        )

def main():
    try:
        # Registrar inicio del sistema
        bot_logger.log_system_event("bot_startup", {"version": "1.0", "token_configured": bool(TELEGRAM_TOKEN)})
        
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("destino", destino))
        app.add_handler(CommandHandler("monitorear", monitorear))
        app.add_handler(CommandHandler("detener", detener))
        app.add_handler(CommandHandler("logs", logs))
        app.add_handler(CommandHandler("limpiar_logs", limpiar_logs))
        app.add_handler(CommandHandler("estado_logs", estado_logs))
        app.add_handler(CommandHandler("ayuda", start))  # Alias para start
        app.add_handler(CommandHandler("cancelar", cancelar))
        
        # Handler para mensajes de texto (debe ir después de los comandos)
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
        
        handlers_list = ["start", "destino", "monitorear", "detener", "logs", "limpiar_logs", "estado_logs", "ayuda", "cancelar", "text_handler"]
        bot_logger.log_system_event("bot_handlers_configured", {"handlers": handlers_list})
        
        print("🤖 Bot iniciado correctamente. Sistema de logging activado.")
        print("📁 Los logs se guardan en la carpeta 'logs/'")
        
        app.run_polling()
        
    except Exception as e:
        bot_logger.log_system_event("bot_startup_error", {"error": str(e)})
        print(f"❌ Error iniciando el bot: {e}")
        raise
    finally:
        # Finalizar todas las sesiones activas al cerrar el bot
        try:
            for user_id in list(bot_logger._user_sessions.keys()):
                bot_logger.end_user_session(user_id)
            bot_logger.log_system_event("bot_shutdown")
        except:
            pass

if __name__ == "__main__":
    main()
