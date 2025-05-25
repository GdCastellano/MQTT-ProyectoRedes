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
    Analiza la salida del ping y extrae la latencia promedio.
    Retorna (latencia_promedio_ms, host_alcanzable)
    """
    # Buscar latencia promedio según el sistema operativo
    if "Average" in output:  # Windows
        match = re.search(r"Average = (\d+)ms", output)
        if match:
            return float(match.group(1)), True
    elif "avg" in output:  # Linux
        match = re.search(r"= [\d\.]+/([\d\.]+)/", output)
        if match:
            return float(match.group(1)), True
    # Si no se encuentra latencia, se asume inalcanzable
    return None, False

# Nota: El número de saltos (TTL) requiere análisis adicional y puede variar según el sistema.
