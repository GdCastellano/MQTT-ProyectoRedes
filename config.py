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

# Configuración de seguridad MQTT
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MQTT_USE_SSL = os.getenv("MQTT_USE_SSL", "false").lower() == "true"
MQTT_CA_CERT = os.getenv("MQTT_CA_CERT")  # Ruta al certificado CA
MQTT_CERT_FILE = os.getenv("MQTT_CERT_FILE")  # Ruta al certificado cliente
MQTT_KEY_FILE = os.getenv("MQTT_KEY_FILE")  # Ruta a la clave privada

# Configuración de timeouts y reintentos MQTT
MQTT_KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", 60))  # segundos
MQTT_CONNECT_TIMEOUT = int(os.getenv("MQTT_CONNECT_TIMEOUT", 10))  # segundos
MQTT_MAX_RETRIES = int(os.getenv("MQTT_MAX_RETRIES", 3))

# Parámetros de monitoreo (mínimo 6 segundos para evitar sobrecarga del servidor)
PING_COUNT = int(os.getenv("PING_COUNT", 4))
MONITOR_INTERVAL = max(6, int(os.getenv("MONITOR_INTERVAL", 10)))  # mínimo 6 segundos

# Configuración de timeouts para comandos de red
PING_TIMEOUT = int(os.getenv("PING_TIMEOUT", 15))  # segundos
MAX_PING_RETRIES = int(os.getenv("MAX_PING_RETRIES", 2))

# Configuración de logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", 30))  # días
LOGS_DIRECTORY = os.getenv("LOGS_DIRECTORY", "logs")
ENABLE_DEBUG_LOGS = os.getenv("ENABLE_DEBUG_LOGS", "false").lower() == "true"
