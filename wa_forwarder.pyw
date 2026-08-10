"""
wa_forwarder.pyw
----------------
Script lanzador del WhatsApp Forwarder.

Extensión .pyw → Windows lo ejecuta con pythonw.exe (sin ventana de consola).
Doble clic para iniciar el forwarder en la bandeja del sistema.

Para arrancar con el sistema:
  Crear un acceso directo a este archivo en la carpeta Inicio de Windows:
  %APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup
"""

import os
import sys

# Agregar el directorio raíz del proyecto al path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from modules.whatsapp_forwarder.tray_app import WhatsAppTrayApp
from modules.whatsapp_forwarder import forwarder_log as log


def main():
    log.log_info("=" * 60)
    log.log_info("WhatsApp Forwarder iniciado.")
    log.log_info(f"Directorio base: {BASE_DIR}")
    log.log_info("=" * 60)

    app = WhatsAppTrayApp()
    try:
        app.run()
    except KeyboardInterrupt:
        log.log_info("Forwarder detenido por el usuario (Ctrl+C).")
    except Exception as e:
        log.log_error(f"Error fatal: {e}")
        import traceback
        log.log_error(traceback.format_exc())


if __name__ == "__main__":
    main()
