"""
tray_app.py
-----------
Aplicación de bandeja del sistema (system tray) para el WhatsApp Forwarder.

Muestra un ícono verde en la bandeja de Windows con menú contextual para:
  - Ver el estado del monitor (Activo / Pausado / Error)
  - Iniciar / Pausar el monitor
  - Abrir la configuración de grupos
  - Ver el log de reenvíos
  - Salir del proceso

Usa pystray + Pillow para el ícono, y llama a WhatsAppMonitor para la lógica.
"""

import threading
import tkinter as tk
from tkinter import scrolledtext
import os
import sys

import pystray
from PIL import Image, ImageDraw, ImageFont

from modules.whatsapp_forwarder.config_manager import cargar_config, actualizar_campo
from modules.whatsapp_forwarder import forwarder_log as log
from modules.whatsapp_forwarder.ui_config import VentanaConfiguracion
from modules.whatsapp_forwarder.wa_monitor import WhatsAppMonitor


# ------------------------------------------------------------------
# GENERACIÓN DEL ÍCONO (dibujado con Pillow — no requiere archivo externo)
# ------------------------------------------------------------------

def _crear_icono_imagen(estado: str = "activo") -> Image.Image:
    """
    Dibuja un ícono circular de WhatsApp (W verde) en un canvas de 64x64.
    El color cambia según el estado:
      - activo   → verde WhatsApp (#25D366)
      - pausado  → amarillo (#f39c12)
      - error    → rojo (#e74c3c)
      - esperando → azul (#3498db)
    """
    COLORES = {
        "activo":    "#25D366",
        "pausado":   "#f39c12",
        "error":     "#e74c3c",
        "esperando": "#3498db",
        "default":   "#95a5a6",
    }
    color = COLORES.get(estado, COLORES["default"])

    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Fondo circular
    draw.ellipse([2, 2, size - 2, size - 2], fill=color, outline="white", width=2)

    # Letra "W" centrada
    try:
        font = ImageFont.truetype("arialbd.ttf", 30)
    except Exception:
        font = ImageFont.load_default()

    text = "W"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (size - tw) // 2
    ty = (size - th) // 2 - 2
    draw.text((tx, ty), text, fill="white", font=font)

    return img


# ------------------------------------------------------------------
# CLASE PRINCIPAL DEL TRAY
# ------------------------------------------------------------------

class WhatsAppTrayApp:
    """
    Gestiona el ícono de la bandeja del sistema y coordina el WhatsAppMonitor.
    """

    def __init__(self):
        self._monitor = WhatsAppMonitor(callback_estado=self._on_estado_monitor)
        self._estado = "inactivo"
        self._icon: pystray.Icon = None
        self._raiz_tk: tk.Tk = None  # Raíz oculta de tkinter para los Toplevel
        self._config = cargar_config()

    # ------------------------------------------------------------------
    # ARRANQUE
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Punto de entrada: inicia la raíz de tkinter y el ícono de la bandeja."""
        # Raíz Tkinter oculta (necesaria para abrir Toplevel desde el tray)
        self._raiz_tk = tk.Tk()
        self._raiz_tk.withdraw()
        self._raiz_tk.title("WA Forwarder")

        # Lanzar el tray icon en un hilo separado
        hilo_tray = threading.Thread(target=self._iniciar_tray, daemon=True, name="TrayIconThread")
        hilo_tray.start()

        # Si hay configuración completa y estaba activo, auto-iniciar el monitor
        config = cargar_config()
        if config.get("grupo_origen") and config.get("grupo_destino") and config.get("activo", False):
            self._iniciar_monitor()

        # El mainloop de tkinter mantiene vivo el proceso
        self._raiz_tk.mainloop()

    # ------------------------------------------------------------------
    # TRAY ICON
    # ------------------------------------------------------------------

    def _iniciar_tray(self) -> None:
        """Crea y ejecuta el ícono de la bandeja en su propio hilo."""
        menu = pystray.Menu(
            pystray.MenuItem(
                lambda item: f"Estado: {self._estado.upper()}",
                None,
                enabled=False
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("▶  Iniciar Monitor",  self._cmd_iniciar,  visible=self._es_parado),
            pystray.MenuItem("⏸  Pausar Monitor",   self._cmd_pausar,   visible=self._es_activo),
            pystray.MenuItem("▶  Reanudar Monitor", self._cmd_reanudar, visible=self._es_pausado),
            pystray.MenuItem("⟳  Reiniciar Monitor", self._cmd_reiniciar),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("⚙️  Configurar grupos...", self._cmd_configurar),
            pystray.MenuItem("📋  Ver log de reenvíos",  self._cmd_ver_log),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌  Salir", self._cmd_salir),
        )

        self._icon = pystray.Icon(
            name="WAForwarder",
            icon=_crear_icono_imagen("default"),
            title="WhatsApp Forwarder – Inactivo",
            menu=menu
        )
        self._icon.run()

    def _actualizar_icono(self) -> None:
        """Actualiza la imagen y tooltip del ícono según el estado actual."""
        if self._icon is None:
            return

        mapa_estado = {
            "activo":    ("activo",    "WhatsApp Forwarder – 🟢 Activo"),
            "pausado":   ("pausado",   "WhatsApp Forwarder – ⏸ Pausado"),
            "error":     ("error",     f"WhatsApp Forwarder – ❌ Error"),
            "inactivo":  ("default",   "WhatsApp Forwarder – Inactivo"),
            "esperando": ("esperando", "WhatsApp Forwarder – ⏳ Esperando login..."),
        }

        estado_key = "default"
        titulo = "WhatsApp Forwarder"
        for key in mapa_estado:
            if key in self._estado.lower():
                estado_key, titulo = mapa_estado[key][0], mapa_estado[key][1]
                break

        self._icon.icon = _crear_icono_imagen(estado_key)
        self._icon.title = titulo

    # ------------------------------------------------------------------
    # PREDICADOS PARA VISIBILIDAD DE MENÚ
    # ------------------------------------------------------------------

    def _es_activo(self, item) -> bool:
        return self._estado == "activo"

    def _es_pausado(self, item) -> bool:
        return self._estado == "pausado"

    def _es_parado(self, item) -> bool:
        return self._estado in ("inactivo", "error", "sin configurar")

    # ------------------------------------------------------------------
    # COMANDOS DEL MENÚ
    # ------------------------------------------------------------------

    def _cmd_iniciar(self, icon=None, item=None) -> None:
        self._iniciar_monitor()

    def _cmd_pausar(self, icon=None, item=None) -> None:
        self._monitor.pausar()
        actualizar_campo("activo", False)

    def _cmd_reanudar(self, icon=None, item=None) -> None:
        self._monitor.reanudar()
        actualizar_campo("activo", True)

    def _cmd_reiniciar(self, icon=None, item=None) -> None:
        log.log_info("Reiniciando monitor por solicitud del usuario.")
        self._monitor.detener()
        import time; time.sleep(2)
        self._iniciar_monitor()

    def _cmd_configurar(self, icon=None, item=None) -> None:
        """Abre la ventana de configuración en el hilo de tkinter."""
        self._raiz_tk.after(0, lambda: VentanaConfiguracion.mostrar(
            raiz=self._raiz_tk,
            callback_guardado=self._on_config_guardada
        ))

    def _cmd_ver_log(self, icon=None, item=None) -> None:
        """Abre una ventana con las últimas líneas del log."""
        self._raiz_tk.after(0, self._mostrar_ventana_log)

    def _cmd_salir(self, icon=None, item=None) -> None:
        log.log_info("Saliendo del WhatsApp Forwarder.")
        self._monitor.detener()
        if self._icon:
            self._icon.stop()
        if self._raiz_tk:
            self._raiz_tk.after(0, self._raiz_tk.destroy)

    # ------------------------------------------------------------------
    # LÓGICA INTERNA
    # ------------------------------------------------------------------

    def _iniciar_monitor(self) -> None:
        """Verifica configuración y arranca el monitor."""
        config = cargar_config()
        if not config.get("grupo_origen") or not config.get("grupo_destino"):
            self._raiz_tk.after(0, lambda: self._mostrar_alerta(
                "Sin configurar",
                "Primero debes configurar los grupos origen y destino.\n"
                "Haz clic derecho en el ícono → ⚙️ Configurar grupos..."
            ))
            return

        actualizar_campo("activo", True)
        self._monitor.iniciar()
        log.log_info("Monitor iniciado desde el tray.")

    def _on_estado_monitor(self, estado: str) -> None:
        """Callback invocado por WhatsAppMonitor cuando cambia su estado."""
        self._estado = estado.lower()
        log.log_debug(f"Estado del monitor: {estado}")
        self._actualizar_icono()

    def _on_config_guardada(self, nueva_config: dict) -> None:
        """Callback cuando el usuario guarda la configuración."""
        self._config = nueva_config
        log.log_info("Configuración actualizada desde la UI.")

    def _mostrar_ventana_log(self) -> None:
        """Crea una ventana Toplevel que muestra el contenido del log."""
        from modules.whatsapp_forwarder.forwarder_log import obtener_ultimas_lineas

        win = tk.Toplevel(self._raiz_tk)
        win.title("📋 Log de Reenvíos – WhatsApp Forwarder")
        win.geometry("780x480")
        win.configure(bg="#1a1a2e")
        win.attributes("-topmost", True)

        # Header
        tk.Label(
            win,
            text="📋  Últimas actividades del forwarder",
            font=("Segoe UI", 13, "bold"),
            fg="#00b894",
            bg="#0f3460",
            pady=10
        ).pack(fill="x")

        # Texto del log
        txt = scrolledtext.ScrolledText(
            win,
            font=("Consolas", 9),
            bg="#0d1117",
            fg="#e6edf3",
            insertbackground="#00b894",
            relief="flat",
            padx=10,
            pady=10
        )
        txt.pack(fill="both", expand=True, padx=10, pady=10)
        txt.insert("1.0", obtener_ultimas_lineas(100))
        txt.configure(state="disabled")

        # Botones
        frame_btns = tk.Frame(win, bg="#1a1a2e", pady=10)
        frame_btns.pack()

        def refrescar():
            txt.configure(state="normal")
            txt.delete("1.0", "end")
            txt.insert("1.0", obtener_ultimas_lineas(100))
            txt.configure(state="disabled")
            txt.see("end")

        tk.Button(
            frame_btns, text="🔄 Actualizar", font=("Segoe UI", 10),
            bg="#0f3460", fg="#e8e8e8", relief="flat", padx=12, pady=6,
            cursor="hand2", command=refrescar
        ).pack(side="left", padx=5)

        tk.Button(
            frame_btns, text="Cerrar", font=("Segoe UI", 10),
            bg="#2d2d2d", fg="#a0a0b0", relief="flat", padx=12, pady=6,
            cursor="hand2", command=win.destroy
        ).pack(side="left", padx=5)

        txt.see("end")  # Scroll al final

    def _mostrar_alerta(self, titulo: str, mensaje: str) -> None:
        from tkinter import messagebox
        messagebox.showwarning(titulo, mensaje)
