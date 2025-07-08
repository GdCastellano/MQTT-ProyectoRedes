import logging
import os
import threading
from datetime import datetime, timedelta
from pathlib import Path
import json


class BotLogger:
    """
    Servicio de logging para el bot de monitoreo de red.
    Genera logs detallados de todas las actividades, comandos, monitoreo y alertas.
    """
    
    def __init__(self, logs_dir="logs"):
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(exist_ok=True)
        
        # Diccionario para tracking de sesiones por usuario
        self._user_sessions = {}
        self._lock = threading.Lock()
        
        # Configurar logger principal
        self._setup_main_logger()
        
        # Configurar logger para actividades específicas
        self._setup_activity_logger()
    
    def _setup_main_logger(self):
        """Configura el logger principal del sistema."""
        self.main_logger = logging.getLogger('bot_main')
        self.main_logger.setLevel(logging.INFO)
        
        # Evitar duplicar handlers
        if not self.main_logger.handlers:
            # Handler para archivo principal
            main_log_file = self.logs_dir / f"bot_main_{datetime.now().strftime('%Y%m%d')}.log"
            main_handler = logging.FileHandler(main_log_file, encoding='utf-8')
            main_handler.setLevel(logging.INFO)
            
            # Formato detallado
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            main_handler.setFormatter(formatter)
            self.main_logger.addHandler(main_handler)
    
    def _setup_activity_logger(self):
        """Configura logger para actividades por usuario."""
        self.activity_logger = logging.getLogger('bot_activity')
        self.activity_logger.setLevel(logging.INFO)
        
        if not self.activity_logger.handlers:
            # Handler que será configurado dinámicamente por sesión
            pass
    
    def start_user_session(self, user_id, username=None, chat_id=None):
        """
        Inicia una nueva sesión de logging para un usuario.
        
        Args:
            user_id: ID del usuario de Telegram
            username: Nombre de usuario (opcional)
            chat_id: ID del chat
        """
        with self._lock:
            session_start = datetime.now()
            session_id = f"user_{user_id}_{session_start.strftime('%Y%m%d_%H%M%S')}"
            
            # Crear archivo de log específico para esta sesión
            log_filename = f"sesion_{session_id}.log"
            log_filepath = self.logs_dir / log_filename
            
            # Configurar handler para esta sesión
            session_handler = logging.FileHandler(log_filepath, encoding='utf-8')
            session_handler.setLevel(logging.INFO)
            
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            session_handler.setFormatter(formatter)
            
            # Crear logger específico para esta sesión
            session_logger = logging.getLogger(f'session_{session_id}')
            session_logger.setLevel(logging.INFO)
            session_logger.addHandler(session_handler)
            
            # Guardar información de la sesión
            self._user_sessions[user_id] = {
                'session_id': session_id,
                'start_time': session_start,
                'log_file': log_filepath,
                'logger': session_logger,
                'handler': session_handler,
                'username': username,
                'chat_id': chat_id,
                'commands_count': 0,
                'ping_count': 0,
                'alerts_count': 0
            }
            
            # Log inicial de la sesión
            session_info = {
                'event': 'session_start',
                'user_id': user_id,
                'username': username,
                'chat_id': chat_id,
                'session_start': session_start.isoformat()
            }
            
            session_logger.info(f"=== INICIO DE SESIÓN ===")
            session_logger.info(f"Usuario: {username} (ID: {user_id})")
            session_logger.info(f"Chat ID: {chat_id}")
            session_logger.info(f"Fecha inicio: {session_start}")
            session_logger.info(f"Archivo log: {log_filename}")
            session_logger.info("=" * 50)
            
            self.main_logger.info(f"Nueva sesión iniciada: {json.dumps(session_info, ensure_ascii=False)}")
    
    def end_user_session(self, user_id):
        """
        Finaliza la sesión de logging para un usuario.
        Renombra el archivo con fecha de inicio y fin.
        """
        with self._lock:
            if user_id not in self._user_sessions:
                return
            
            session = self._user_sessions[user_id]
            session_end = datetime.now()
            duration = session_end - session['start_time']
            
            # Log final de la sesión
            session['logger'].info("=" * 50)
            session['logger'].info(f"=== FIN DE SESIÓN ===")
            session['logger'].info(f"Fecha fin: {session_end}")
            session['logger'].info(f"Duración: {duration}")
            session['logger'].info(f"Comandos ejecutados: {session['commands_count']}")
            session['logger'].info(f"Pings realizados: {session['ping_count']}")
            session['logger'].info(f"Alertas enviadas: {session['alerts_count']}")
            session['logger'].info("=" * 50)
            
            # Cerrar handler
            session['handler'].close()
            session['logger'].removeHandler(session['handler'])
            
            # Renombrar archivo con fechas de inicio y fin
            start_str = session['start_time'].strftime('%Y%m%d_%H%M%S')
            end_str = session_end.strftime('%Y%m%d_%H%M%S')
            new_filename = f"user_{user_id}_{start_str}-{end_str}.log"
            new_filepath = self.logs_dir / new_filename
            
            try:
                session['log_file'].rename(new_filepath)
                self.main_logger.info(f"Sesión finalizada. Archivo guardado como: {new_filename}")
            except Exception as e:
                self.main_logger.error(f"Error al renombrar archivo de log: {e}")
            
            # Limpiar sesión
            del self._user_sessions[user_id]
    
    def log_command(self, user_id, command, args=None, username=None):
        """Registra un comando recibido del usuario."""
        if user_id not in self._user_sessions:
            self.start_user_session(user_id, username)
        
        session = self._user_sessions[user_id]
        session['commands_count'] += 1
        
        command_info = {
            'event': 'command_received',
            'command': command,
            'args': args or [],
            'user_id': user_id,
            'username': username
        }
        
        args_str = ' '.join(args) if args else ''
        session['logger'].info(f"COMANDO: /{command} {args_str}")
        self.main_logger.info(f"Comando ejecutado: {json.dumps(command_info, ensure_ascii=False)}")
    
    def log_ping_result(self, user_id, host, latency, ttl, reachable, output=None):
        """Registra el resultado de un ping."""
        if user_id not in self._user_sessions:
            return
        
        session = self._user_sessions[user_id]
        session['ping_count'] += 1
        
        result_info = {
            'event': 'ping_result',
            'host': host,
            'latency': latency,
            'ttl': ttl,
            'reachable': reachable,
            'user_id': user_id
        }
        
        if reachable:
            session['logger'].info(f"PING OK: {host} - Latencia: {latency}ms, TTL: {ttl}")
        else:
            session['logger'].warning(f"PING FALLO: {host} - Host inalcanzable")
        
        # Log detallado solo en main logger para no saturar logs de sesión
        if output:
            self.main_logger.debug(f"Salida ping completa para {host}: {output}")
        
        self.main_logger.info(f"Resultado ping: {json.dumps(result_info, ensure_ascii=False)}")
    
    def log_monitoring_start(self, user_id, host):
        """Registra el inicio del monitoreo de un host."""
        if user_id not in self._user_sessions:
            return
        
        session = self._user_sessions[user_id]
        session['logger'].info(f"MONITOREO INICIADO: {host}")
        
        monitor_info = {
            'event': 'monitoring_started',
            'host': host,
            'user_id': user_id
        }
        self.main_logger.info(f"Monitoreo iniciado: {json.dumps(monitor_info, ensure_ascii=False)}")
    
    def log_monitoring_stop(self, user_id, host=None):
        """Registra la detención del monitoreo."""
        if user_id not in self._user_sessions:
            return
        
        session = self._user_sessions[user_id]
        session['logger'].info(f"MONITOREO DETENIDO: {host or 'todos los hosts'}")
        
        monitor_info = {
            'event': 'monitoring_stopped',
            'host': host,
            'user_id': user_id
        }
        self.main_logger.info(f"Monitoreo detenido: {json.dumps(monitor_info, ensure_ascii=False)}")
    
    def log_alert(self, user_id, host, message):
        """Registra una alerta enviada al usuario."""
        if user_id not in self._user_sessions:
            return
        
        session = self._user_sessions[user_id]
        session['alerts_count'] += 1
        session['logger'].warning(f"ALERTA ENVIADA: {message}")
        
        alert_info = {
            'event': 'alert_sent',
            'host': host,
            'message': message,
            'user_id': user_id
        }
        self.main_logger.warning(f"Alerta enviada: {json.dumps(alert_info, ensure_ascii=False)}")
    
    def log_mqtt_publish(self, user_id, host, data):
        """Registra una publicación MQTT."""
        if user_id not in self._user_sessions:
            return
        
        session = self._user_sessions[user_id]
        session['logger'].info(f"MQTT PUBLICADO: {host} - {data}")
        
        mqtt_info = {
            'event': 'mqtt_published',
            'host': host,
            'data': data,
            'user_id': user_id
        }
        self.main_logger.info(f"MQTT publicado: {json.dumps(mqtt_info, ensure_ascii=False)}")
    
    def log_error(self, user_id, error, context=None):
        """Registra un error del sistema."""
        error_info = {
            'event': 'error',
            'error': str(error),
            'context': context,
            'user_id': user_id
        }
        
        if user_id in self._user_sessions:
            session = self._user_sessions[user_id]
            session['logger'].error(f"ERROR: {error} - Contexto: {context}")
        
        self.main_logger.error(f"Error registrado: {json.dumps(error_info, ensure_ascii=False)}")
    
    def log_system_event(self, event, details=None):
        """Registra eventos del sistema general."""
        system_info = {
            'event': 'system_event',
            'type': event,
            'details': details
        }
        
        self.main_logger.info(f"Evento sistema: {json.dumps(system_info, ensure_ascii=False)}")
    
    def cleanup_old_logs(self, days=30):
        """Limpia logs antiguos (por defecto más de 30 días)."""
        cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
        deleted_files = []
        
        for log_file in self.logs_dir.glob("*.log"):
            if log_file.stat().st_mtime < cutoff_date:
                try:
                    log_file.unlink()
                    deleted_files.append(log_file.name)
                    self.main_logger.info(f"Log antiguo eliminado: {log_file.name}")
                except Exception as e:
                    self.main_logger.error(f"Error eliminando log antiguo {log_file.name}: {e}")
        
        return deleted_files
    
    def get_user_log_files(self, user_id):
        """Obtiene lista de archivos de log para un usuario específico."""
        pattern = f"user_{user_id}_*.log"
        return list(self.logs_dir.glob(pattern))
    
    def get_user_session_summary(self, user_id):
        """Obtiene un resumen de la sesión actual del usuario."""
        if user_id not in self._user_sessions:
            return None
        
        session = self._user_sessions[user_id]
        current_time = datetime.now()
        duration = current_time - session['start_time']
        
        return {
            'session_id': session['session_id'],
            'start_time': session['start_time'],
            'duration': str(duration).split('.')[0],  # Sin microsegundos
            'commands_count': session['commands_count'],
            'ping_count': session['ping_count'],
            'alerts_count': session['alerts_count'],
            'username': session['username'],
            'log_file': session['log_file'].name
        }
    
    def get_logs_directory_info(self):
        """Obtiene información del directorio de logs."""
        log_files = list(self.logs_dir.glob("*.log"))
        total_size = sum(f.stat().st_size for f in log_files if f.exists())
        
        return {
            'directory': str(self.logs_dir),
            'total_files': len(log_files),
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'oldest_log': min((f.stat().st_mtime for f in log_files), default=None),
            'newest_log': max((f.stat().st_mtime for f in log_files), default=None)
        }


# Instancia global del logger
try:
    from config import LOGS_DIRECTORY
    bot_logger = BotLogger(LOGS_DIRECTORY)
except ImportError:
    bot_logger = BotLogger() 