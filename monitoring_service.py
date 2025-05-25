import threading
import time
from network_monitor import ping_host, parse_ping_output
from mqtt_client import MQTTClient
from config import PING_COUNT, MONITOR_INTERVAL

class MonitoringService:
    def __init__(self, host, alert_callback):
        self.host = host
        self.running = False
        self.thread = None
        self.alert_callback = alert_callback
        self.mqtt_client = MQTTClient()

    def start(self):
        """
        Inicia el monitoreo en un hilo separado.
        """
        self.running = True
        self.thread = threading.Thread(target=self._monitor)
        self.thread.start()

    def stop(self):
        """
        Detiene el monitoreo.
        """
        self.running = False
        if self.thread:
            self.thread.join()

    def _monitor(self):
        """
        Ejecuta el ping periódicamente y envía alertas si el host no responde.
        Publica los resultados en MQTT.
        """
        while self.running:
            output = ping_host(self.host, PING_COUNT)
            latency, reachable = parse_ping_output(output)
            if not reachable:
                self.alert_callback(f"ALERTA: El host {self.host} está inalcanzable.")
            else:
                msg = f"Host: {self.host}, Latencia promedio: {latency} ms"
                self.mqtt_client.publish(msg)
            time.sleep(MONITOR_INTERVAL)
