import threading
import time
import logging
from network_monitor import ping_host, parse_ping_output, NetworkError
from mqtt_client import SecureMQTTClient
from config import PING_COUNT, MONITOR_INTERVAL
from logger_service import bot_logger

class MonitoringService:
    def __init__(self, host, alert_callback, user_id=None):
        self.host = host
        self.running = False
        self.thread = None
        self.alert_callback = alert_callback
        self.user_id = user_id
        
        # Configurar cliente MQTT con ID único
        client_id = f"monitor_{user_id}_{int(time.time())}" if user_id else f"monitor_{int(time.time())}"
        self.mqtt_client = SecureMQTTClient(client_id)
        
        # Configurar logger específico
        self.logger = logging.getLogger(f'monitoring_service_{user_id or "unknown"}')
        self.logger.setLevel(logging.INFO)
        
        # Estadísticas de monitoreo
        self.stats = {
            'start_time': None,
            'total_pings': 0,
            'successful_pings': 0,
            'failed_pings': 0,
            'consecutive_failures': 0,
            'max_consecutive_failures': 0,
            'mqtt_publish_success': 0,
            'mqtt_publish_failures': 0,
            'average_latency': 0,
            'min_latency': float('inf'),
            'max_latency': 0
        }

    def start(self):
        """
        Inicia el monitoreo en un hilo separado.
        """
        try:
            # Intentar conectar MQTT al inicio
            mqtt_connected = self.mqtt_client.connect()
            if not mqtt_connected:
                self.logger.warning("No se pudo conectar al broker MQTT, continuando sin MQTT")
            
            self.running = True
            self.stats['start_time'] = time.time()
            self.thread = threading.Thread(target=self._monitor, daemon=True)
            self.thread.start()
            
            if self.user_id:
                bot_logger.log_system_event("monitoring_thread_started", {
                    "user_id": self.user_id,
                    "host": self.host,
                    "thread_id": self.thread.ident,
                    "mqtt_connected": mqtt_connected,
                    "monitor_interval": MONITOR_INTERVAL
                })
                
            self.logger.info(f"Monitoreo iniciado para {self.host} (usuario: {self.user_id})")
            
        except Exception as e:
            error_msg = f"Error iniciando hilo de monitoreo: {e}"
            self.logger.error(error_msg)
            if self.user_id:
                bot_logger.log_error(self.user_id, error_msg, f"Host: {self.host}")
            raise

    def stop(self):
        """
        Detiene el monitoreo.
        """
        try:
            self.running = False
            
            # Desconectar MQTT
            if hasattr(self, 'mqtt_client'):
                self.mqtt_client.disconnect()
            
            # Esperar que termine el hilo
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=5)  # Timeout para evitar bloqueos
                
            # Calcular estadísticas finales
            duration = time.time() - (self.stats['start_time'] or time.time())
            
            if self.user_id:
                bot_logger.log_system_event("monitoring_thread_stopped", {
                    "user_id": self.user_id,
                    "host": self.host,
                    "duration_seconds": round(duration, 2),
                    "total_pings": self.stats['total_pings'],
                    "success_rate": round((self.stats['successful_pings'] / max(1, self.stats['total_pings'])) * 100, 2),
                    "max_consecutive_failures": self.stats['max_consecutive_failures']
                })
                
            self.logger.info(f"Monitoreo detenido para {self.host}. Duración: {duration:.1f}s, Pings: {self.stats['total_pings']}")
            
        except Exception as e:
            error_msg = f"Error deteniendo hilo de monitoreo: {e}"
            self.logger.error(error_msg)
            if self.user_id:
                bot_logger.log_error(self.user_id, error_msg, f"Host: {self.host}")

    def _monitor(self):
        """
        Ejecuta el ping periódicamente y envía alertas si el host no responde.
        Publica los resultados en MQTT con manejo robusto de errores.
        """
        self.logger.info(f"Iniciando ciclo de monitoreo para {self.host}")
        latency_history = []
        
        while self.running:
            cycle_start = time.time()
            
            try:
                self.stats['total_pings'] += 1
                
                # Ejecutar ping con manejo de errores
                try:
                    output = ping_host(self.host, PING_COUNT)
                    latency, ttl, reachable, ping_stats = parse_ping_output(output)
                    
                    # Registrar resultado del ping en logs con estadísticas adicionales
                    if self.user_id:
                        bot_logger.log_ping_result(self.user_id, self.host, latency, ttl, reachable, output)
                    
                except NetworkError as net_err:
                    # Error de red específico
                    self.logger.warning(f"Error de red haciendo ping a {self.host}: {net_err}")
                    latency, ttl, reachable, ping_stats = None, None, False, {"error": str(net_err)}
                    
                    if self.user_id:
                        bot_logger.log_error(self.user_id, f"Error de red: {net_err}", f"Host: {self.host}")
                        
                except Exception as ping_err:
                    # Error genérico en ping
                    self.logger.error(f"Error inesperado ejecutando ping: {ping_err}")
                    latency, ttl, reachable, ping_stats = None, None, False, {"error": str(ping_err)}
                    
                    if self.user_id:
                        bot_logger.log_error(self.user_id, f"Error en ping: {ping_err}", f"Host: {self.host}")
                
                # Actualizar estadísticas
                if reachable and latency is not None:
                    self.stats['successful_pings'] += 1
                    self.stats['consecutive_failures'] = 0
                    
                    # Actualizar estadísticas de latencia
                    latency_history.append(latency)
                    if len(latency_history) > 100:  # Mantener solo los últimos 100 valores
                        latency_history.pop(0)
                    
                    self.stats['average_latency'] = sum(latency_history) / len(latency_history)
                    self.stats['min_latency'] = min(self.stats['min_latency'], latency)
                    self.stats['max_latency'] = max(self.stats['max_latency'], latency)
                    
                    # Preparar datos para MQTT con información extendida
                    mqtt_data = {
                        "host": self.host,
                        "latencia": latency,
                        "saltos": ttl,
                        "timestamp": time.time(),
                        "ping_number": self.stats['total_pings'],
                        "user_id": self.user_id,
                        "estadisticas": {
                            "latencia_promedio": round(self.stats['average_latency'], 2),
                            "latencia_minima": self.stats['min_latency'],
                            "latencia_maxima": self.stats['max_latency'],
                            "pings_exitosos": self.stats['successful_pings'],
                            "total_pings": self.stats['total_pings']
                        }
                    }
                    
                    # Agregar estadísticas adicionales del ping si están disponibles
                    if ping_stats and 'packet_loss' in ping_stats:
                        mqtt_data["packet_loss"] = ping_stats['packet_loss']
                    
                    # Intentar publicar en MQTT
                    try:
                        if self.mqtt_client.is_connected() or self.mqtt_client.connect():
                            success = self.mqtt_client.publish(mqtt_data)
                            if success:
                                self.stats['mqtt_publish_success'] += 1
                                if self.user_id:
                                    bot_logger.log_mqtt_publish(self.user_id, self.host, mqtt_data)
                            else:
                                self.stats['mqtt_publish_failures'] += 1
                                self.logger.warning(f"Falló publicación MQTT para {self.host}")
                        else:
                            self.stats['mqtt_publish_failures'] += 1
                            self.logger.warning(f"MQTT desconectado, no se puede publicar datos de {self.host}")
                            
                    except Exception as mqtt_error:
                        self.stats['mqtt_publish_failures'] += 1
                        error_msg = f"Error publicando MQTT: {mqtt_error}"
                        self.logger.error(error_msg)
                        
                        if self.user_id:
                            bot_logger.log_error(self.user_id, error_msg, f"Host: {self.host}, Data: {mqtt_data}")
                
                else:
                    # Host inalcanzable
                    self.stats['failed_pings'] += 1
                    self.stats['consecutive_failures'] += 1
                    self.stats['max_consecutive_failures'] = max(
                        self.stats['max_consecutive_failures'], 
                        self.stats['consecutive_failures']
                    )
                    
                    # Determinar tipo de alerta según fallos consecutivos
                    if self.stats['consecutive_failures'] == 1:
                        alert_level = "🔴 PRIMERA ALERTA"
                    elif self.stats['consecutive_failures'] <= 3:
                        alert_level = "🟡 ALERTA PERSISTENTE"
                    else:
                        alert_level = "💀 ALERTA CRÍTICA"
                    
                    alert_msg = (f"{alert_level}: El host {self.host} está inalcanzable.\n"
                               f"Fallos consecutivos: {self.stats['consecutive_failures']}\n"
                               f"Tiempo transcurrido: {time.time() - self.stats['start_time']:.0f}s")
                    
                    # Enviar alerta (se registra automáticamente en el callback)
                    try:
                        self.alert_callback(alert_msg)
                    except Exception as alert_err:
                        self.logger.error(f"Error enviando alerta: {alert_err}")
                    
                    if self.user_id:
                        bot_logger.log_system_event("monitoring_host_unreachable", {
                            "user_id": self.user_id,
                            "host": self.host,
                            "consecutive_failures": self.stats['consecutive_failures'],
                            "ping_number": self.stats['total_pings'],
                            "alert_level": alert_level
                        })
                
                # Log de recuperación si venía de fallos
                if reachable and hasattr(self, '_previous_state') and not self._previous_state:
                    recovery_msg = f"✅ RECUPERACIÓN: {self.host} vuelve a responder después de {self.stats['max_consecutive_failures']} fallos."
                    
                    try:
                        self.alert_callback(recovery_msg)
                    except Exception as alert_err:
                        self.logger.error(f"Error enviando alerta de recuperación: {alert_err}")
                    
                    if self.user_id:
                        bot_logger.log_system_event("monitoring_host_recovered", {
                            "user_id": self.user_id,
                            "host": self.host,
                            "previous_failures": self.stats['max_consecutive_failures'],
                            "ping_number": self.stats['total_pings']
                        })
                
                # Guardar estado anterior
                self._previous_state = reachable
                
                # Calcular tiempo de espera dinámico
                cycle_duration = time.time() - cycle_start
                sleep_time = max(0, MONITOR_INTERVAL - cycle_duration)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                else:
                    self.logger.warning(f"Ciclo de monitoreo tardó {cycle_duration:.2f}s, mayor que intervalo configurado de {MONITOR_INTERVAL}s")
                
            except Exception as e:
                # Error crítico en el ciclo de monitoreo
                error_msg = f"Error crítico en ciclo de monitoreo: {e}"
                self.logger.error(error_msg)
                
                if self.user_id:
                    bot_logger.log_error(self.user_id, error_msg, f"Host: {self.host}, Ping #{self.stats['total_pings']}")
                
                # Esperar antes del siguiente ciclo para evitar spam de errores
                time.sleep(min(MONITOR_INTERVAL, 30))
        
        self.logger.info(f"Ciclo de monitoreo terminado para {self.host}")
    
    def get_statistics(self):
        """Obtiene estadísticas del monitoreo."""
        duration = time.time() - (self.stats['start_time'] or time.time())
        
        return {
            **self.stats,
            'duration_seconds': round(duration, 2),
            'success_rate': round((self.stats['successful_pings'] / max(1, self.stats['total_pings'])) * 100, 2),
            'failure_rate': round((self.stats['failed_pings'] / max(1, self.stats['total_pings'])) * 100, 2),
            'mqtt_success_rate': round((self.stats['mqtt_publish_success'] / max(1, self.stats['mqtt_publish_success'] + self.stats['mqtt_publish_failures'])) * 100, 2),
            'host': self.host,
            'running': self.running
        }
