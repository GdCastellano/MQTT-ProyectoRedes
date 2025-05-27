import os
from dotenv import load_dotenv

# Cargar variables desde el archivo .env
load_dotenv()

# Token del bot de Telegram (reemplazar por el real)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Configuración del broker MQTT
MQTT_BROKER = os.getenv("MQTT_BROKER")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC")

# Parámetros de monitoreo
PING_COUNT = int(os.getenv("PING_COUNT", 4))
MONITOR_INTERVAL = int(os.getenv("MONITOR_INTERVAL", 5))  # segundos
