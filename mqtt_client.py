import json
import ssl
import time
import threading
import logging
import paho.mqtt.client as mqtt
from config import (
    MQTT_BROKER, MQTT_PORT, MQTT_TOPIC, 
    MQTT_USERNAME, MQTT_PASSWORD, MQTT_USE_SSL,
    MQTT_CA_CERT, MQTT_CERT_FILE, MQTT_KEY_FILE,
    MQTT_KEEPALIVE, MQTT_CONNECT_TIMEOUT, MQTT_MAX_RETRIES
)

# Detectar la versión de paho-mqtt para compatibilidad
try:
    # paho-mqtt 2.x
    from paho.mqtt.client import CallbackAPIVersion
    MQTT_V2_AVAILABLE = True
except ImportError:
    # paho-mqtt 1.x
    MQTT_V2_AVAILABLE = False

class SecureMQTTClient:
    """
    Cliente MQTT seguro con autenticación, SSL/TLS, manejo de errores y reconexión automática.
    
    Compatible con paho-mqtt 1.x y 2.x:
    - Para paho-mqtt 2.x: usa callback_api_version=VERSION1 para mantener compatibilidad
    - Para paho-mqtt 1.x: usa la sintaxis original
    
    Esto resuelve el error "Unsupported callback API version 2.0" en versiones recientes.
    """
    
    def __init__(self, client_id=None):
        self.client_id = client_id or f"network_monitor_{int(time.time())}"
        self.client = None
        self.connected = False
        self.connection_attempts = 0
        self.max_retries = MQTT_MAX_RETRIES
        self.lock = threading.Lock()
        
        # Configurar logger
        self.logger = logging.getLogger(f'mqtt_client_{self.client_id}')
        self.logger.setLevel(logging.INFO)
        
        # Configurar cliente
        self._setup_client()
    
    def _setup_client(self):
        """Configura el cliente MQTT con todas las opciones de seguridad."""
        try:
            # Crear cliente con compatibilidad para ambas versiones de paho-mqtt
            if MQTT_V2_AVAILABLE:
                # paho-mqtt 2.x - usar callback API version 1 para compatibilidad
                self.client = mqtt.Client(
                    client_id=self.client_id, 
                    callback_api_version=CallbackAPIVersion.VERSION1
                )
                self.logger.info("Cliente MQTT creado con paho-mqtt 2.x (callback API v1)")
            else:
                # paho-mqtt 1.x - usar sintaxis original
                self.client = mqtt.Client(self.client_id)
                self.logger.info("Cliente MQTT creado con paho-mqtt 1.x")
            
            # Configurar callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            self.client.on_publish = self._on_publish
            self.client.on_log = self._on_log
            
            # Configurar autenticación si está disponible
            if MQTT_USERNAME and MQTT_PASSWORD:
                self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
                self.logger.info("Autenticación MQTT configurada")
            
            # Configurar SSL/TLS si está habilitado
            if MQTT_USE_SSL:
                self._configure_ssl()
            
            # Configurar opciones de conexión
            self.client.reconnect_delay_set(min_delay=1, max_delay=120)
            
        except Exception as e:
            self.logger.error(f"Error configurando cliente MQTT: {e}")
            raise
    
    def _configure_ssl(self):
        """Configura SSL/TLS para conexiones seguras."""
        try:
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            
            # Configurar certificado CA si está disponible
            if MQTT_CA_CERT:
                context.load_verify_locations(MQTT_CA_CERT)
            
            # Configurar certificados de cliente si están disponibles
            if MQTT_CERT_FILE and MQTT_KEY_FILE:
                context.load_cert_chain(MQTT_CERT_FILE, MQTT_KEY_FILE)
            
            # Aplicar contexto SSL al cliente
            self.client.tls_set_context(context)
            self.logger.info("SSL/TLS configurado correctamente")
            
        except Exception as e:
            self.logger.error(f"Error configurando SSL/TLS: {e}")
            raise
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback ejecutado al conectar con el broker."""
        if rc == 0:
            self.connected = True
            self.connection_attempts = 0
            self.logger.info(f"Conectado al broker MQTT: {MQTT_BROKER}:{MQTT_PORT}")
        else:
            self.connected = False
            error_messages = {
                1: "Protocolo incorrecto",
                2: "ID de cliente inválido", 
                3: "Servidor no disponible",
                4: "Usuario o contraseña incorrectos",
                5: "No autorizado"
            }
            error_msg = error_messages.get(rc, f"Error desconocido: {rc}")
            self.logger.error(f"Error de conexión MQTT: {error_msg}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback ejecutado al desconectar del broker."""
        self.connected = False
        if rc != 0:
            self.logger.warning(f"Desconexión inesperada del broker MQTT. Código: {rc}")
        else:
            self.logger.info("Desconectado del broker MQTT")
    
    def _on_message(self, client, userdata, msg):
        """Callback para mensajes recibidos."""
        try:
            payload = json.loads(msg.payload.decode())
            self.logger.debug(f"Mensaje recibido en {msg.topic}: {payload}")
        except Exception as e:
            self.logger.error(f"Error procesando mensaje: {e}")
    
    def _on_publish(self, client, userdata, mid):
        """Callback ejecutado cuando se publica un mensaje."""
        self.logger.debug(f"Mensaje publicado exitosamente. MID: {mid}")
    
    def _on_log(self, client, userdata, level, buf):
        """Callback para logs del cliente MQTT."""
        if level <= mqtt.MQTT_LOG_WARNING:
            self.logger.warning(f"MQTT Log: {buf}")
        else:
            self.logger.debug(f"MQTT Log: {buf}")
    
    def connect(self):
        """Establece conexión con el broker MQTT con reintentos."""
        if not MQTT_BROKER:
            self.logger.error("MQTT_BROKER no configurado")
            return False
        
        with self.lock:
            self.connection_attempts += 1
            
            if self.connection_attempts > self.max_retries:
                self.logger.error(f"Máximo número de intentos de conexión alcanzado: {self.max_retries}")
                return False
            
            try:
                self.logger.info(f"Intentando conectar a {MQTT_BROKER}:{MQTT_PORT} (intento {self.connection_attempts})")
                
                # Intentar conexión
                result = self.client.connect(
                    MQTT_BROKER, 
                    MQTT_PORT, 
                    MQTT_KEEPALIVE
                )
                
                if result == mqtt.MQTT_ERR_SUCCESS:
                    # Iniciar loop en background
                    self.client.loop_start()
                    
                    # Esperar confirmación de conexión
                    timeout = MQTT_CONNECT_TIMEOUT
                    while not self.connected and timeout > 0:
                        time.sleep(0.1)
                        timeout -= 0.1
                    
                    if self.connected:
                        self.logger.info("Conexión MQTT establecida exitosamente")
                        return True
                    else:
                        self.logger.error("Timeout esperando confirmación de conexión")
                        return False
                else:
                    self.logger.error(f"Error iniciando conexión MQTT: {mqtt.error_string(result)}")
                    return False
                    
            except Exception as e:
                self.logger.error(f"Excepción durante conexión MQTT: {e}")
                return False
    
    def disconnect(self):
        """Desconecta del broker MQTT."""
        try:
            if self.client and self.connected:
                self.client.loop_stop()
                self.client.disconnect()
                self.connected = False
                self.logger.info("Desconectado del broker MQTT")
        except Exception as e:
            self.logger.error(f"Error durante desconexión: {e}")
    
    def publish(self, data, topic=None, qos=1, retain=False):
        """
        Publica un mensaje en el tópico MQTT configurado.
        
        Args:
            data (dict): Datos a publicar
            topic (str): Tópico personalizado (opcional)
            qos (int): Quality of Service (0, 1, 2)
            retain (bool): Mensaje retenido
            
        Returns:
            bool: True si la publicación fue exitosa, False en caso contrario
        """
        if not data:
            self.logger.warning("Datos vacíos, no se publicará")
            return False
        
        topic_to_use = topic or MQTT_TOPIC
        if not topic_to_use:
            self.logger.error("Tópico MQTT no configurado")
            return False
        
        # Verificar conexión y reconectar si es necesario
        if not self.connected:
            if not self.connect():
                self.logger.error("No se pudo establecer conexión MQTT para publicar")
                return False
        
        try:
            # Preparar datos
            if isinstance(data, dict):
                # Agregar timestamp si no existe
                if 'timestamp' not in data:
                    data['timestamp'] = time.time()
                
                # Agregar ID de cliente
                data['client_id'] = self.client_id
                
                payload = json.dumps(data, ensure_ascii=False)
            else:
                payload = str(data)
            
            # Publicar mensaje
            result = self.client.publish(topic_to_use, payload, qos=qos, retain=retain)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.logger.debug(f"Mensaje encolado para publicación en {topic_to_use}")
                
                # Esperar confirmación si QoS > 0
                if qos > 0:
                    result.wait_for_publish(timeout=5.0)
                    if result.is_published():
                        self.logger.info(f"Mensaje publicado exitosamente en {topic_to_use}")
                        return True
                    else:
                        self.logger.warning(f"Timeout esperando confirmación de publicación")
                        return False
                else:
                    self.logger.info(f"Mensaje enviado (QoS 0) a {topic_to_use}")
                    return True
            else:
                self.logger.error(f"Error publicando mensaje: {mqtt.error_string(result.rc)}")
                return False
                
        except Exception as e:
            self.logger.error(f"Excepción durante publicación: {e}")
            return False
    
    def is_connected(self):
        """Verifica si el cliente está conectado."""
        return self.connected
    
    def get_connection_status(self):
        """Obtiene el estado detallado de la conexión."""
        return {
            'connected': self.connected,
            'client_id': self.client_id,
            'broker': MQTT_BROKER,
            'port': MQTT_PORT,
            'connection_attempts': self.connection_attempts,
            'ssl_enabled': MQTT_USE_SSL,
            'authenticated': bool(MQTT_USERNAME)
        }

# Alias para compatibilidad hacia atrás
MQTTClient = SecureMQTTClient
