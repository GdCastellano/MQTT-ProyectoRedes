# MQTT-ProyectoRedes
Proyecto de Redes de Comunicación de  Datos usando MQTT


A continuación se detalla un texto completo que explica, paso a paso, lo que hay que hacer para desarrollar el proyecto, integrando tanto las instrucciones del documento PDF como la explicación de la figura de la Arquitectura Referencial. Este texto servirá de contexto para otra IA que te asista en la programación.

---

## 1. Descripción General del Proyecto

El objetivo principal es desarrollar un sistema de monitoreo de red y telemetría utilizando un bot de Telegram, donde el usuario envía comandos para realizar pruebas (por ejemplo, mediante el comando `ping`) a un nodo objetivo. Los resultados obtenidos (como la latencia promedio y la cantidad de saltos) se enviarán tanto al bot para mostrarlos en la interfaz de Telegram como a un broker MQTT, donde posteriormente se visualizarán en forma de gráficos de serie de tiempo a través de una herramienta como MQTT Explorer. Además, se incorpora una funcionalidad adicional para el monitoreo recurrente: el sistema debe ejecutar de forma periódica pruebas a un nodo específico y, en caso de inalcanzabilidad, enviar una alerta de inmediato al bot. Esto permite una doble vía de monitoreo y validación en tiempo real. 

---

## 2. Objetivos Específicos

El documento define claramente los siguientes objetivos:

1. **Desarrollar un Bot de Telegram:**  
   - Permitir que el usuario envíe instrucciones para ejecutar comandos de red.
   - Mostrar las respuestas y alertas a través del bot.

2. **Capturar y Procesar Comandos de Red:**  
   - Crear un script en Python que reciba el destino (dirección IP o nombre de host) y ejecute al menos 4 solicitudes utilizando `ping` para medir la latencia.
   - Analizar la salida de estos comandos para extraer los datos relevantes: latencia promedio y número de saltos hasta alcanzar el nodo.

3. **Integrar MQTT para la Telemetría:**  
   - **Paso 1:** Instala la librería `paho-mqtt` en tu entorno de Python usando el comando `pip install paho-mqtt`.
   - **Paso 2:** Crea un módulo en Python (por ejemplo, `mqtt_client.py`) que gestione la conexión y publicación de mensajes a un broker MQTT.
   - **Paso 3:** En tu archivo `.env`, define las variables necesarias para la conexión: dirección del broker, puerto y tópico.
   - **Paso 4:** En el módulo MQTT, utiliza estas variables para conectar el cliente MQTT al broker.
   - **Paso 5:** Implementa una función que reciba los datos procesados (latencia, saltos, etc.) y los publique en el tópico MQTT configurado.
   - **Paso 6:** Desde el módulo principal o desde donde proceses los resultados del ping, llama a esta función para enviar los datos cada vez que se obtengan resultados nuevos.
   - **Paso 7:** Verifica que los datos publicados sean visibles en el broker usando una herramienta como MQTT Explorer, conectándote al mismo tópico.

4. **Implementar el Mecanismo de Monitoreo Recurrente y Alertas:**  
   - Diseñar una instrucción especial en el bot que inicie un proceso de monitoreo continuo a un nodo objetivo.
   - El sistema debe comprobar periódicamente (con un retardo mínimo de 5 segundos entre solicitudes) si el host está accesible; en caso negativo, se debe enviar un mensaje de alerta al bot.
   - Incluir una instrucción que permita detener este monitoreo recurrente desde la propia interfaz del bot. 

---

## 3. Arquitectura del Sistema y Explicación de la Figura Referencial

La figura de Arquitectura Referencial que acompaña al documento ilustra la estructura modular y la interconexión de todos los componentes del sistema. Esta arquitectura se organiza de la siguiente manera:

- **Bot de Telegram:**  
  La aplicación de Telegram en un dispositivo móvil (o cualquier otro) se comunica con la API de Telegram. A través de esta conexión, el usuario envía comandos (como iniciar el monitoreo o establecer el destino) y recibe respuestas o alertas del sistema.

- **Infraestructura de Red del Laboratorio:**  
  La comunicación se extiende desde el dispositivo móvil, a través del Internet y un ISP, hasta el entorno local (LAN). En la red local se encuentran dispositivos clave:
  
  - **Router y Switch:**  
    Se utiliza un router que permite la salida y la entrada a la LAN, y un switch para la interconexión de dispositivos. Esto garantiza que el servidor y otros equipos del laboratorio estén conectados de forma estable.
  
  - **Servidor Local:**  
    Este servidor ejecuta el script principal en Python. Aquí se integra la lógica completa para gestionar las instrucciones recibidas del bot, ejecutar los comandos de red y procesar la salida para extraer latencia y saltos.

- **Cliente MQTT y Broker MQTT:**  
  El mismo servidor (o un módulo independiente) actúa como cliente MQTT. Una vez procesados los resultados de las pruebas de red, éste se conecta a un broker MQTT (inicialmente un broker público, pero en la fase final se utiliza un broker local) y publica dichos datos en el tópico “mensaje grupo”.
  
- **Visualización y Monitoreo:**  
  Utilizando herramientas como MQTT Explorer, se conectan al broker y se visualizan los datos en tiempo real en gráficos de series de tiempo. Así, se consigue una representación visual de la latencia y los saltos a lo largo del tiempo, permitiendo un monitoreo detallado de la red.

Esta arquitectura modular permite que cada componente – el bot, la ejecución y análisis de los comandos de red, la comunicación por MQTT y la visualización – sea desarrollado, probado y eventualmente escalado de forma independiente. Además, se mejora la trazabilidad del sistema, ya que cada acción y mensaje pueden ser registrados, monitoreados y depurados en caso de errores o incidencias. 

---

## 4. Tecnologías a Utilizar

Para implementar este proyecto se requiere el uso de diversas herramientas y librerías:

1. **Python:**  
   Es el lenguaje de programación principal para escribir los scripts que gestionarán la lógica del bot, la ejecución de comandos de red, la conexión al broker MQTT y el manejo de alertas.

2. **Librerías de Telegram para Python:**  
   Se recomienda utilizar librerías como `python-telegram-bot` para facilitar la comunicación con la API de Telegram y gestionar de forma sencilla los mensajes y comandos.

3. **Librería Paho-MQTT:**  
   Esta librería permite configurar y gestionar la comunicación con el broker MQTT. Se usará para publicar los resultados en el tópico “mensaje grupo”.

4. **Broker MQTT:**  
   Inicialmente se puede utilizar un broker público (por ejemplo, `broker.hivemq.com` o `test.mosquitto.org`) para las pruebas, pero el desarrollo final debe emplear un broker local que ofrezca mayor control y seguridad.

5. **Sistema Operativo:**  
   El proyecto puede ejecutarse tanto en sistemas Linux como Windows, dependiendo de las preferencias y requisitos del entorno de desarrollo. 

---

## 5. Plan de Desarrollo Paso a Paso

### 5.1 Desarrollo del Bot de Telegram

1. **Creación e Inicialización del Bot:**
   - Registra un nuevo bot en Telegram a través de [@BotFather](https://telegram.me/BotFather) y obtén su token de acceso.
   - Configura un entorno en Python para usar la librería `python-telegram-bot` y realiza la conexión con la API de Telegram usando el token.

2. **Implementación de Comandos Básicos:**
   - Define un comando, por ejemplo `/destino`, que permita al usuario ingresar la dirección IP o el nombre del host del nodo objetivo.
   - Programa la recepción y el procesamiento de otros comandos básicos, como iniciar el servicio de monitoreo y detenerlo.

### 5.2 Captura y Ejecución de Comandos de Red

1. **Desarrollo del Script en Python:**
   - Crea un script que, al recibir la dirección del nodo objetivo, ejecute el comando `ping` utilizando la librería `subprocess`. Se deben realizar al menos 4 solicitudes consecutivas.
   - Implementa un retardo (por ejemplo, 5 segundos) entre ciclos para evitar sobrecargar el servidor.

2. **Procesamiento de la Salida del Comando:**
   - Analiza la salida del `ping` para extraer la latencia promedio y la cantidad de saltos necesarios para alcanzar el nodo.
   - Organiza estos datos para que puedan ser enviados al bot de Telegram y publicados por el cliente MQTT.

### 5.3 Integración con el Broker MQTT

1. **Configuración del Cliente MQTT:**
   - Utiliza la librería `paho-mqtt` para configurar en Python un cliente que se conecte al broker MQTT.
   - Define la conexión al broker (por ahora público, y luego local) y asegúrate de gestionar los eventos de conexión y desconexión.

2. **Publicación de Resultados:**
   - Implementa una función que, tras procesar los resultados del comando `ping`, publique los datos (latencia y saltos) en el tópico “mensaje grupo”.
   - Verifica que los resultados se muestren correctamente en el explorador MQTT, permitiendo su análisis en gráficos de serie de tiempo.

### 5.4 Implementación del Módulo de Monitoreo y Alertas

1. **Monitoreo Recurrente:**
   - Añade una funcionalidad en el bot que permita iniciar un proceso de monitoreo continuo de un nodo objetivo.  
   - Este proceso debe ejecutar periódicamente el comando de red y revisar la conectividad.

2. **Gestión de Alertas:**
   - Establece una condición que, en caso de que el nodo esté inalcanzable (por ejemplo, si no se recibe respuesta del `ping`), envíe automáticamente un mensaje de alerta al bot de Telegram.
   - Asegúrate de que este proceso pueda detenerse mediante un comando específico del bot (como `/detener`).

### 5.5 Pruebas y Ajustes

1. **Validación Integral del Sistema:**
   - Realiza pruebas exhaustivas por cada módulo: el bot de Telegram, la ejecución y procesamiento del `ping`, la publicación en MQTT y la visualización en el explorador.
   - Ajusta parámetros, retardo entre recorridos y captura de errores según los resultados de las pruebas.

2. **Entorno de Pruebas Adicional:**
   - Evalúa la posibilidad de desplegar una máquina virtual para simular el host objetivo, o realiza las pruebas sobre la computadora designada en el laboratorio.
   
3. **Implementación de Logs y Manejo de Errores:**
   - Agrega mecanismos de captura de errores y logs para detectar problemas en la conexión, en la ejecución de comandos o en la interacción con el broker MQTT.
   - Considera implementar autenticación en el broker MQTT para reforzar la seguridad. 

---

## 6. Consideraciones de Seguridad y Captura de Errores

- **Protección del Broker MQTT:**  
  Ten en cuenta las implicaciones de seguridad en la configuración del broker, considerando la autenticación mediante usuario y contraseña para evitar accesos no autorizados.

- **Manejo de Errores en la Ejecución de Comandos:**  
  Debido a que se estarán ejecutando comandos de red de forma recurrente en el servidor, es imprescindible capturar y gestionar posibles fallos en la ejecución que puedan generar bloqueos o excesos en la carga del sistema.

- **Pruebas de Robustez:**  
  Se debe verificar que, ante fallas en la conexión o respuestas inesperadas del nodo, el sistema continúe operando de forma segura enviando los logs y las alertas correspondientes. 

---

## 7. Presentación de Resultados y Evaluación

La entrega final del proyecto debe ser valorada considerando los siguientes escenarios:

1. **Inicio del Servicio desde el Bot:**  
   El usuario debe poder iniciar la captura de datos de latencia y saltos mediante el bot de Telegram. (20%)

2. **Monitoreo a través de Telegram:**  
   Se verificará que se reciban correctamente los datos de latencia promedio, saltos y alertas ante hosts inalcanzables. (30%)

3. **Visualización en Tiempo Real:**  
   Los datos publicados en MQTT deberán ser representados en un gráfico de serie de tiempo utilizando herramientas como MQTT Explorer. (30%)

4. **Detención del Servicio:**  
   Se debe implementar un comando en el bot para detener tanto el proceso de captura como el de alerta. (20%)

---

## Conclusión y Siguientes Pasos

Este proyecto se basa en una arquitectura modular que integra un bot de Telegram, la ejecución de comandos de red y la comunicación a través de MQTT. Cada módulo se desarrolla y prueba de manera independiente para luego integrar todo el sistema, asegurando robustez, monitoreo en tiempo real y control de alertas. Esta explicación detallada proporciona el contexto y la guía necesaria para que otra IA o asistente de programación pueda ayudarte a implementar el proyecto en Python, utilizando las librerías mencionadas y siguiendo las pautas de seguridad y robustez recomendadas.

Si deseas profundizar en alguno de los aspectos, por ejemplo, ejemplos de código para la integración del cliente MQTT o el manejo asíncrono en Python para el bot, podemos abordar esos detalles de forma más específica. También podemos explorar estrategias para mejorar la escalabilidad o la gestión de logs y errores en ambientes de producción.

---

## Configuración del archivo `.env`

Crea un archivo llamado `.env` en la raíz del proyecto y agrega las siguientes variables de entorno:

```
TELEGRAM_TOKEN=tu_token_de_telegram
MQTT_BROKER=localhost
MQTT_PORT=1883
MQTT_TOPIC=mensaje_grupo
PING_COUNT=4
MONITOR_INTERVAL=5
```

Asegúrate de reemplazar `tu_token_de_telegram` con tu token real de Telegram.