import subprocess
import platform
import re

def ping_host(host, count=4):
    """
    Ejecuta el comando ping al host especificado y retorna la salida.
    """
    param = "-n" if platform.system().lower() == "windows" else "-c"
    try:
        result = subprocess.run(
            ["ping", param, str(count), host],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout
    except Exception as e:
        return str(e)

def parse_ping_output(output):
    """
    Analiza la salida del ping y extrae la latencia promedio y el TTL.
    Retorna (latencia_promedio_ms, ttl, host_alcanzable)
    """
    # Latencia promedio (Windows español)
    match_lat = re.search(r"Media = (\d+)ms", output)
    # Latencia promedio (Windows inglés)
    if not match_lat:
        match_lat = re.search(r"Average = (\d+)ms", output)
    # Latencia promedio (Linux)
    if not match_lat:
        match_lat = re.search(r"= [\d\.]+/([\d\.]+)/", output)
    latency = round(float(match_lat.group(1))) if match_lat else None

    # TTL: busca el primer TTL en la salida
    match_ttl = re.search(r"TTL=(\d+)", output, re.IGNORECASE)
    ttl = int(match_ttl.group(1)) if match_ttl else None

    # Considera alcanzable si hay latencia y TTL
    reachable = latency is not None and ttl is not None
    return latency, ttl, reachable

# Nota: El número de saltos (TTL) requiere análisis adicional y puede variar según el sistema.
