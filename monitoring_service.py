import threading
import time
from network_monitor import ping_host, parse_ping_output
from mqtt_client import MQTTClient
from config import PING_COUNT, MONITOR_INTERVAL
from logger_service import bot_logger

class MonitoringService:
    def __init__(self, host, alert_callback, user_id=None):
        self.host = host
        self.running = False
        self.thread = None
        self.alert_callback = alert_callback
        self.mqtt_client = MQTTClient()
        self.user_id = user_id

    def start(self):
        """
        Inicia el monitoreo en un hilo separado.
        """
        try:
            self.running = True
            self.thread = threading.Thread(target=self._monitor)
            self.thread.start()
            
            if self.user_id:
                bot_logger.log_system_event("monitoring_thread_started", {
                    "user_id": self.user_id,
                    "host": self.host,
                    "thread_id": self.thread.ident
                })
        except Exception as e:
            if self.user_id:
                bot_logger.log_error(self.user_id, f"Error iniciando hilo de monitoreo: {e}", f"Host: {self.host}")
            raise

    def stop(self):
        """
        Detiene el monitoreo.
        """
        try:
            self.running = False
            if self.thread:
                self.thread.join()
                
            if self.user_id:
                bot_logger.log_system_event("monitoring_thread_stopped", {
                    "user_id": self.user_id,
                    "host": self.host
                })
        except Exception as e:
            if self.user_id:
                bot_logger.log_error(self.user_id, f"Error deteniendo hilo de monitoreo: {e}", f"Host: {self.host}")

    def _monitor(self):
        """
        Ejecuta el ping periódicamente y envía alertas si el host no responde.
        Publica los resultados en MQTT.
        """
        ping_counter = 0
        consecutive_failures = 0
        
        while self.running:
            try:
                ping_counter += 1
                output = ping_host(self.host, PING_COUNT)
                latency, ttl, reachable = parse_ping_output(output)
                
                # Registrar resultado del ping en logs
                if self.user_id:
                    bot_logger.log_ping_result(self.user_id, self.host, latency, ttl, reachable)
                
                if not reachable:
                    consecutive_failures += 1
                    alert_msg = f"ALERTA: El host {self.host} está inalcanzable (fallo #{consecutive_failures})."
                    
                    # La alerta ya se registra en el callback del bot.py
                    self.alert_callback(alert_msg)
                    
                    if self.user_id:
                        bot_logger.log_system_event("monitoring_host_unreachable", {
                            "user_id": self.user_id,
                            "host": self.host,
                            "consecutive_failures": consecutive_failures,
                            "ping_number": ping_counter
                        })
                else:
                    # Reset contador de fallos consecutivos
                    if consecutive_failures > 0:
                        if self.user_id:
                            bot_logger.log_system_event("monitoring_host_recovered", {
                                "user_id": self.user_id,
                                "host": self.host,
                                "previous_failures": consecutive_failures,
                                "ping_number": ping_counter
                            })
                        consecutive_failures = 0
                    
                    # Preparar datos para MQTT
                    data = {
                        "host": self.host,
                        "latencia": latency,
                        "saltos": ttl,
                        "timestamp": time.time(),
                        "ping_number": ping_counter
                    }
                    
                    try:
                        self.mqtt_client.publish(data)
                        
                        # Registrar publicación MQTT
                        if self.user_id:
                            bot_logger.log_mqtt_publish(self.user_id, self.host, data)
                            
                    except Exception as mqtt_error:
                        if self.user_id:
                            bot_logger.log_error(self.user_id, f"Error publicando MQTT: {mqtt_error}", 
                                               f"Host: {self.host}, Data: {data}")
                
                time.sleep(MONITOR_INTERVAL)
                
            except Exception as e:
                if self.user_id:
                    bot_logger.log_error(self.user_id, f"Error en ciclo de monitoreo: {e}", 
                                       f"Host: {self.host}, Ping #{ping_counter}")
                time.sleep(MONITOR_INTERVAL)  # Esperar antes del siguiente intento
