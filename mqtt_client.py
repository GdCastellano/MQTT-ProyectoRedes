import paho.mqtt.client as mqtt
from config import MQTT_BROKER, MQTT_PORT, MQTT_TOPIC

class MQTTClient:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.connect(MQTT_BROKER, MQTT_PORT)

    def publish(self, data):
        """
        Publica un mensaje en el tópico MQTT configurado.
        """
        self.client.publish(MQTT_TOPIC, data)

# Uso:
# mqtt_client = MQTTClient()
# mqtt_client.publish("mensaje")
