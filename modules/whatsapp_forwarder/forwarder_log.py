"""
forwarder_log.py
----------------
Logger de reenvíos de WhatsApp.
Escribe eventos en logs/wa_forwarder.log con timestamp, tipo y estado.
"""

import os
import logging
from datetime import datetime

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
LOG_DIR = os.path.abspath(LOG_DIR)
LOG_FILE = os.path.join(LOG_DIR, "wa_forwarder.log")

# Asegurar que el directorio de logs existe
os.makedirs(LOG_DIR, exist_ok=True)

# Configurar logger
_logger = logging.getLogger("WAForwarder")
_logger.setLevel(logging.DEBUG)

if not _logger.handlers:
    _fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    _fh.setLevel(logging.DEBUG)
    _fmt = logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    _fh.setFormatter(_fmt)
    _logger.addHandler(_fh)

    _ch = logging.StreamHandler()
    _ch.setLevel(logging.INFO)
    _ch.setFormatter(_fmt)
    _logger.addHandler(_ch)


def log_reenvio_exitoso(tipo: str, nombre_archivo: str, grupo_origen: str, grupo_destino: str) -> None:
    _logger.info(f"REENVIO OK | tipo={tipo} | archivo={nombre_archivo} | {grupo_origen} → {grupo_destino}")


def log_reenvio_error(tipo: str, nombre_archivo: str, error: str) -> None:
    _logger.error(f"REENVIO ERROR | tipo={tipo} | archivo={nombre_archivo} | error={error}")


def log_info(mensaje: str) -> None:
    _logger.info(mensaje)


def log_error(mensaje: str) -> None:
    _logger.error(mensaje)


def log_debug(mensaje: str) -> None:
    _logger.debug(mensaje)


def log_advertencia(mensaje: str) -> None:
    _logger.warning(mensaje)


def obtener_ultimas_lineas(n: int = 50) -> str:
    """Devuelve las últimas n líneas del log para mostrar en la UI."""
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lineas = f.readlines()
        return "".join(lineas[-n:])
    except Exception:
        return "(Sin registros aún)"
