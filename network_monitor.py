import subprocess
import platform
import re
import socket
import logging
import time
from config import PING_TIMEOUT, MAX_PING_RETRIES

class NetworkError(Exception):
    """Excepción personalizada para errores de red."""
    pass

class NetworkMonitor:
    """
    Monitor de red robusto con manejo de errores y validación de hosts.
    """
    
    def __init__(self):
        self.logger = logging.getLogger('network_monitor')
        self.logger.setLevel(logging.INFO)
        self.system = platform.system().lower()
        
        # Configurar parámetros según el sistema operativo
        if self.system == "windows":
            self.ping_param = "-n"
            self.ping_timeout_param = "-w"
            self.ping_timeout_value = str(PING_TIMEOUT * 1000)  # Windows usa milisegundos
        else:  # Linux/Unix
            self.ping_param = "-c"
            self.ping_timeout_param = "-W"
            self.ping_timeout_value = str(PING_TIMEOUT)  # Linux usa segundos
    
    def validate_host(self, host):
        """
        Valida si el host es válido antes de hacer ping.
        
        Args:
            host (str): Dirección IP o nombre de dominio
            
        Returns:
            tuple: (es_valido, mensaje_error)
        """
        if not host or not isinstance(host, str):
            return False, "Host no puede estar vacío"
        
        host = host.strip()
        
        # Verificar longitud
        if len(host) > 255:
            return False, "Nombre del host demasiado largo"
        
        # Verificar caracteres inválidos
        if not re.match(r'^[a-zA-Z0-9.-]+$', host):
            return False, "Host contiene caracteres inválidos"
        
        # Verificar formato de IP si es una dirección IP
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', host):
            try:
                socket.inet_aton(host)
            except socket.error:
                return False, "Dirección IP inválida"
        
        # Verificar que no sea una dirección privada peligrosa
        dangerous_hosts = [
            "127.0.0.1", "localhost", "0.0.0.0", 
            "::1", "169.254.1.1"
        ]
        if host.lower() in dangerous_hosts:
            return False, f"Host '{host}' no permitido por seguridad"
        
        return True, "Host válido"
    
    def resolve_host(self, host):
        """
        Resuelve el nombre del host a dirección IP.
        
        Args:
            host (str): Nombre del host o IP
            
        Returns:
            tuple: (ip_resuelta, error)
        """
        try:
            # Si ya es una IP, la devolvemos
            socket.inet_aton(host)
            return host, None
        except socket.error:
            pass
        
        # Intentar resolver DNS
        try:
            ip = socket.gethostbyname(host)
            self.logger.debug(f"Host {host} resuelto a {ip}")
            return ip, None
        except socket.gaierror as e:
            error_msg = f"No se pudo resolver el host '{host}': {e}"
            self.logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"Error inesperado resolviendo '{host}': {e}"
            self.logger.error(error_msg)
            return None, error_msg

def ping_host(host, count=4, timeout=None):
    """
    Ejecuta el comando ping al host especificado con manejo robusto de errores.
    
    Args:
        host (str): Dirección IP o nombre de dominio
        count (int): Número de pings a enviar
        timeout (int): Timeout en segundos (opcional)
        
    Returns:
        str: Salida del comando ping o mensaje de error
    """
    monitor = NetworkMonitor()
    timeout = timeout or PING_TIMEOUT
    
    # Validar el host
    is_valid, validation_msg = monitor.validate_host(host)
    if not is_valid:
        error_msg = f"Host inválido: {validation_msg}"
        monitor.logger.error(error_msg)
        raise NetworkError(error_msg)
    
    # Resolver el host si es necesario
    resolved_ip, resolve_error = monitor.resolve_host(host)
    if resolve_error:
        raise NetworkError(resolve_error)
    
    # Construir comando ping
    cmd = [
        "ping",
        monitor.ping_param, str(count),
        monitor.ping_timeout_param, monitor.ping_timeout_value,
        resolved_ip
    ]
    
    # Intentar ping con reintentos
    last_error = None
    for attempt in range(MAX_PING_RETRIES + 1):
        try:
            monitor.logger.debug(f"Ejecutando ping (intento {attempt + 1}): {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True, 
                text=True, 
                timeout=timeout + 5,  # Timeout adicional para el proceso
                check=False  # No lanzar excepción por códigos de salida no-cero
            )
            
            # El ping puede devolver código != 0 si el host no responde, pero eso es normal
            output = result.stdout or result.stderr
            
            if output:
                monitor.logger.debug(f"Ping exitoso, salida recibida para {host}")
                return output
            else:
                raise NetworkError("No se recibió salida del comando ping")
                
        except subprocess.TimeoutExpired:
            last_error = f"Timeout ejecutando ping a {host} (intento {attempt + 1})"
            monitor.logger.warning(last_error)
            time.sleep(1)  # Esperar antes del siguiente intento
            
        except subprocess.CalledProcessError as e:
            last_error = f"Error en comando ping: código {e.returncode}, stderr: {e.stderr}"
            monitor.logger.warning(last_error)
            time.sleep(1)
            
        except Exception as e:
            last_error = f"Error inesperado ejecutando ping: {e}"
            monitor.logger.error(last_error)
            time.sleep(1)
    
    # Si llegamos aquí, todos los intentos fallaron
    final_error = f"Ping falló después de {MAX_PING_RETRIES + 1} intentos. Último error: {last_error}"
    monitor.logger.error(final_error)
    raise NetworkError(final_error)

def parse_ping_output(output):
    """
    Analiza la salida del ping y extrae la latencia promedio y el TTL con manejo robusto de errores.
    
    Args:
        output (str): Salida del comando ping
        
    Returns:
        tuple: (latencia_promedio_ms, ttl, host_alcanzable, estadisticas_adicionales)
    """
    logger = logging.getLogger('ping_parser')
    
    if not output or not isinstance(output, str):
        logger.error("Salida de ping vacía o inválida")
        return None, None, False, {"error": "Salida inválida"}
    
    # Estadísticas adicionales
    stats = {
        "packets_sent": None,
        "packets_received": None, 
        "packet_loss": None,
        "min_latency": None,
        "max_latency": None,
        "avg_latency": None,
        "system": platform.system().lower()
    }
    
    try:
        # Buscar estadísticas de paquetes (Windows y Linux)
        packet_stats = re.search(r'(\d+) (?:packets )?(?:paquetes )?.*?(\d+) (?:received|recibidos).*?(\d+)% (?:packet )?loss', output, re.IGNORECASE)
        if packet_stats:
            stats["packets_sent"] = int(packet_stats.group(1))
            stats["packets_received"] = int(packet_stats.group(2))
            stats["packet_loss"] = int(packet_stats.group(3))
        
        # Latencia promedio (múltiples formatos)
        latency = None
        
        # Windows español
        match_lat = re.search(r"Media = (\d+)ms", output)
        if match_lat:
            latency = float(match_lat.group(1))
            
        # Windows inglés
        if not match_lat:
            match_lat = re.search(r"Average = (\d+)ms", output)
            if match_lat:
                latency = float(match_lat.group(1))
        
        # Linux formato estándar (min/avg/max/mdev)
        if not match_lat:
            match_lat = re.search(r"= [\d\.]+/([\d\.]+)/[\d\.]+/[\d\.]+ ms", output)
            if match_lat:
                latency = float(match_lat.group(1))
        
        # Linux formato alternativo
        if not match_lat:
            match_lat = re.search(r"avg = ([\d\.]+)", output)
            if match_lat:
                latency = float(match_lat.group(1))
        
        # Buscar estadísticas min/max en Linux
        linux_stats = re.search(r"= ([\d\.]+)/([\d\.]+)/([\d\.]+)/([\d\.]+) ms", output)
        if linux_stats:
            stats["min_latency"] = float(linux_stats.group(1))
            stats["avg_latency"] = float(linux_stats.group(2))
            stats["max_latency"] = float(linux_stats.group(3))
        
        # TTL: busca el primer TTL en la salida
        ttl = None
        match_ttl = re.search(r"TTL[=\s]+(\d+)", output, re.IGNORECASE)
        if match_ttl:
            ttl = int(match_ttl.group(1))
        
        # En Linux, el TTL puede aparecer como "ttl=64"
        if not match_ttl:
            match_ttl = re.search(r"ttl=(\d+)", output, re.IGNORECASE)
            if match_ttl:
                ttl = int(match_ttl.group(1))
        
        # Determinar si el host es alcanzable
        reachable = False
        
        # Criterios para considerar alcanzable:
        # 1. Tiene latencia válida
        # 2. No hay 100% de pérdida de paquetes
        # 3. No hay mensajes de error evidentes
        
        if latency is not None and latency > 0:
            reachable = True
            
        # Verificar pérdida de paquetes
        if stats["packet_loss"] is not None and stats["packet_loss"] >= 100:
            reachable = False
            
        # Verificar mensajes de error comunes
        error_patterns = [
            r"unreachable|inalcanzable",
            r"timeout|tiempo agotado", 
            r"unknown host|host desconocido",
            r"network unreachable|red inalcanzable",
            r"destination host unreachable"
        ]
        
        for pattern in error_patterns:
            if re.search(pattern, output, re.IGNORECASE):
                reachable = False
                break
        
        # Redondear latencia si existe
        if latency is not None:
            latency = round(latency, 2)
            stats["avg_latency"] = latency
        
        logger.debug(f"Ping parseado - Latencia: {latency}ms, TTL: {ttl}, Alcanzable: {reachable}")
        
        return latency, ttl, reachable, stats
        
    except Exception as e:
        logger.error(f"Error parseando salida de ping: {e}")
        return None, None, False, {"error": str(e), "raw_output": output[:200]}

# Funciones de compatibilidad hacia atrás
def ping_host_simple(host, count=4):
    """Función simple de ping para compatibilidad hacia atrás."""
    try:
        return ping_host(host, count)
    except NetworkError as e:
        return f"Error: {e}"

# Crear instancia global del monitor
network_monitor = NetworkMonitor()
