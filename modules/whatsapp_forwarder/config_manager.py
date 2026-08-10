"""
config_manager.py
-----------------
Gestión de configuración del módulo WhatsApp Forwarder.
Guarda y carga ajustes en wa_forwarder_config.json.
"""

import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "wa_forwarder_config.json")
CONFIG_PATH = os.path.abspath(CONFIG_PATH)

DEFAULT_CONFIG = {
    "grupo_origen": "",
    "grupo_destino": "",
    "delay_min_segundos": 2,
    "delay_max_segundos": 5,
    "tipos_permitidos": ["imagen", "archivo"],
    "activo": False
}


def cargar_config() -> dict:
    """Carga la configuración desde disco. Si no existe, devuelve la configuración por defecto."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Fusionar con defaults por si faltan claves nuevas
            config = {**DEFAULT_CONFIG, **data}
            return config
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def guardar_config(config: dict) -> None:
    """Guarda la configuración en disco."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def actualizar_campo(clave: str, valor) -> None:
    """Actualiza un campo específico de la configuración."""
    config = cargar_config()
    config[clave] = valor
    guardar_config(config)
