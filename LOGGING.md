# 📊 Sistema de Logging del Bot de Monitoreo

## 🎯 Descripción General

El bot incluye un sistema de logging completo que registra automáticamente todas las actividades, comandos, resultados de monitoreo y errores. Cada usuario tiene sesiones de logging independientes con archivos organizados por fechas.

## 📁 Estructura de Archivos de Log

### Tipos de Archivos Generados

1. **Logs Principales del Sistema**
   - `bot_main_YYYYMMDD.log` - Log principal del sistema por día
   - Contiene eventos del sistema, errores globales y estadísticas

2. **Logs de Sesión por Usuario**
   - Durante la sesión: `sesion_user_USERID_YYYYMMDD_HHMMSS.log`
   - Al finalizar: `user_USERID_FECHAINICIO-FECHAFIN.log`
   - Ejemplo: `user_123456789_20241201_143022-20241201_151205.log`

### Contenido de los Logs

#### Log Principal del Sistema
```
2024-12-01 14:30:22 - INFO - bot_main - Nueva sesión iniciada: {"event": "session_start", "user_id": 123456789, "username": "johndoe", "chat_id": -987654321, "session_start": "2024-12-01T14:30:22"}
2024-12-01 14:30:22 - INFO - bot_main - Comando ejecutado: {"event": "command_received", "command": "start", "args": [], "user_id": 123456789, "username": "johndoe"}
```

#### Log de Sesión de Usuario
```
2024-12-01 14:30:22 - INFO - === INICIO DE SESIÓN ===
2024-12-01 14:30:22 - INFO - Usuario: johndoe (ID: 123456789)
2024-12-01 14:30:22 - INFO - Chat ID: -987654321
2024-12-01 14:30:22 - INFO - Fecha inicio: 2024-12-01 14:30:22.123456
2024-12-01 14:30:22 - INFO - Archivo log: sesion_user_123456789_20241201_143022.log
2024-12-01 14:30:22 - INFO - ==================================================
2024-12-01 14:30:25 - INFO - COMANDO: /destino 8.8.8.8
2024-12-01 14:30:26 - INFO - PING OK: 8.8.8.8 - Latencia: 15ms, TTL: 64
2024-12-01 14:30:30 - INFO - COMANDO: /monitorear google.com
2024-12-01 14:30:30 - INFO - MONITOREO INICIADO: google.com
2024-12-01 14:30:35 - INFO - PING OK: google.com - Latencia: 12ms, TTL: 64
2024-12-01 14:30:35 - INFO - MQTT PUBLICADO: google.com - {'host': 'google.com', 'latencia': 12, 'saltos': 64, 'timestamp': 1733073035.123, 'ping_number': 1}
2024-12-01 14:30:40 - WARNING - PING FALLO: google.com - Host inalcanzable
2024-12-01 14:30:40 - WARNING - ALERTA ENVIADA: ALERTA: El host google.com está inalcanzable (fallo #1).
```

## 🚀 Comandos de Gestión de Logs

### `/logs` - Información de Sesión
Muestra información detallada de tu sesión actual:
- ID de sesión
- Hora de inicio y duración
- Contadores de comandos, pings y alertas
- Archivos de logs anteriores (últimos 3)

### `/estado_logs` - Estado del Sistema
Información general del sistema de logging:
- Directorio de logs y tamaño total
- Número total de archivos
- Fechas del log más antiguo y más reciente
- Sesiones activas

### `/limpiar_logs [días]` - Limpieza de Logs
Elimina logs antiguos:
- Sin parámetro: elimina logs de más de 30 días
- Con parámetro: `días` específicos
- Ejemplo: `/limpiar_logs 60` elimina logs de más de 60 días

## ⚙️ Configuración

### Variables de Entorno

```bash
# Directorio de logs (por defecto: "logs")
LOGS_DIRECTORY=logs

# Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# Días para retener logs automáticamente
LOG_RETENTION_DAYS=30

# Logs de debug detallados (true/false)
ENABLE_DEBUG_LOGS=false
```

### Configuración en config.py

```python
# Configuración de logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", 30))
LOGS_DIRECTORY = os.getenv("LOGS_DIRECTORY", "logs")
ENABLE_DEBUG_LOGS = os.getenv("ENABLE_DEBUG_LOGS", "false").lower() == "true"
```

## 📋 Eventos Registrados

### Comandos de Usuario
- `/start`, `/destino`, `/monitorear`, `/detener`
- `/logs`, `/estado_logs`, `/limpiar_logs`
- Argumentos pasados a cada comando
- Errores en comandos mal formados

### Monitoreo de Red
- Resultados de ping (latencia, TTL, alcanzabilidad)
- Inicio y detención de monitoreo
- Fallos consecutivos y recuperación
- Publicaciones MQTT exitosas y fallidas

### Alertas y Notificaciones
- Alertas enviadas por hosts inalcanzables
- Número de fallos consecutivos
- Recuperación de conectividad

### Eventos del Sistema
- Inicio y cierre del bot
- Configuración de handlers
- Inicio y detención de hilos de monitoreo
- Limpieza automática de logs

## 🔒 Seguridad y Privacidad

### Thread Safety
- Uso de locks para operaciones concurrentes
- Manejo seguro de múltiples usuarios simultáneos

### Gestión de Sesiones
- Sesiones independientes por usuario
- Limpieza automática al cerrar el bot
- Renombrado automático con fechas de inicio/fin

### Rotación de Logs
- Archivos organizados por fecha
- Limpieza automática de logs antiguos
- Configuración flexible de retención

## 📊 Métricas y Estadísticas

### Por Sesión de Usuario
- Número de comandos ejecutados
- Cantidad de pings realizados
- Total de alertas enviadas
- Duración de la sesión

### Sistema Global
- Total de archivos de log
- Tamaño ocupado en disco
- Sesiones activas concurrentes
- Archivos eliminados en limpieza

## 🛠️ Implementación Técnica

### Clase Principal: `BotLogger`
```python
from logger_service import bot_logger

# Registro automático de comandos
bot_logger.log_command(user_id, "destino", ["8.8.8.8"], username="johndoe")

# Registro de resultados de ping
bot_logger.log_ping_result(user_id, "8.8.8.8", 15, 64, True)

# Registro de alertas
bot_logger.log_alert(user_id, "google.com", "Host inalcanzable")
```

### Integración con Módulos
- **bot.py**: Comandos de usuario y manejo de errores
- **monitoring_service.py**: Resultados de monitoreo y MQTT
- **logger_service.py**: Lógica central de logging

## 🎯 Mejores Prácticas

### Para Usuarios
1. Usar `/logs` para verificar actividad de sesión
2. Ejecutar `/limpiar_logs` periódicamente para ahorrar espacio
3. Revisar `/estado_logs` para monitorear el sistema

### Para Administradores
1. Configurar `LOG_RETENTION_DAYS` según espacio disponible
2. Monitorear el tamaño del directorio de logs
3. Configurar `LOG_LEVEL` apropiado para el entorno
4. Realizar backups periódicos de logs importantes

## 🔧 Resolución de Problemas

### Logs No Se Generan
- Verificar permisos de escritura en directorio de logs
- Revisar configuración de `LOGS_DIRECTORY`
- Comprobar espacio en disco disponible

### Archivos de Log Grandes
- Reducir `LOG_RETENTION_DAYS`
- Ejecutar `/limpiar_logs` más frecuentemente
- Considerar configurar `LOG_LEVEL` a `WARNING` o `ERROR`

### Errores de Logging
- Los errores del sistema de logging se registran en el log principal
- Verificar permisos de archivos y directorios
- Revisar configuración de variables de entorno

---

*Sistema de logging implementado para el Bot de Monitoreo de Red - v1.0* 