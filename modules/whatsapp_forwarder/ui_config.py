"""
ui_config.py
------------
Ventana de configuración del módulo WhatsApp Forwarder.
Construida con tkinter para no requerir dependencias extra.
Se abre desde el menú del tray icon.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading

from modules.whatsapp_forwarder.config_manager import cargar_config, guardar_config
from modules.whatsapp_forwarder import forwarder_log as log


class VentanaConfiguracion:
    """
    Ventana de configuración del forwarder de WhatsApp.
    Se puede abrir múltiples veces; cada llamada a mostrar() crea una nueva instancia.
    """

    _instancia_activa: tk.Toplevel = None

    @classmethod
    def mostrar(cls, raiz: tk.Tk = None, callback_guardado=None) -> None:
        """
        Muestra la ventana de configuración.
        Si ya hay una instancia activa, la trae al frente.

        Args:
            raiz: Ventana raíz de tkinter (puede ser None para crear una temporal)
            callback_guardado: Función llamada con el config dict al guardar cambios.
        """
        # Si ya hay una ventana abierta, traerla al frente
        if cls._instancia_activa is not None:
            try:
                cls._instancia_activa.lift()
                cls._instancia_activa.focus_force()
                return
            except tk.TclError:
                cls._instancia_activa = None

        # Crear ventana raíz temporal si no se provee una
        _raiz_propia = False
        if raiz is None:
            raiz = tk.Tk()
            raiz.withdraw()  # Ocultar la raíz, solo mostrar el Toplevel
            _raiz_propia = True

        ventana = tk.Toplevel(raiz)
        cls._instancia_activa = ventana
        ventana.title("⚙️ Configuración – WhatsApp Forwarder")
        ventana.geometry("520x580")
        ventana.resizable(False, False)
        ventana.configure(bg="#1a1a2e")
        ventana.attributes("-topmost", True)

        config = cargar_config()

        # ------------------------------------------------------------------
        # ESTILOS
        # ------------------------------------------------------------------
        COLOR_BG = "#1a1a2e"
        COLOR_PANEL = "#16213e"
        COLOR_ACCENT = "#0f3460"
        COLOR_GREEN = "#00b894"
        COLOR_TEXT = "#e8e8e8"
        COLOR_SUBTEXT = "#a0a0b0"
        FONT_TITULO = ("Segoe UI", 16, "bold")
        FONT_LABEL = ("Segoe UI", 10)
        FONT_SMALL = ("Segoe UI", 9)

        # ------------------------------------------------------------------
        # HEADER
        # ------------------------------------------------------------------
        frame_header = tk.Frame(ventana, bg=COLOR_ACCENT, pady=14)
        frame_header.pack(fill="x")
        tk.Label(
            frame_header,
            text="🔀  WhatsApp Forwarder",
            font=FONT_TITULO,
            fg=COLOR_GREEN,
            bg=COLOR_ACCENT
        ).pack()
        tk.Label(
            frame_header,
            text="Reenvío automático de imágenes y archivos entre grupos",
            font=FONT_SMALL,
            fg=COLOR_SUBTEXT,
            bg=COLOR_ACCENT
        ).pack(pady=(2, 0))

        # ------------------------------------------------------------------
        # CUERPO
        # ------------------------------------------------------------------
        frame_body = tk.Frame(ventana, bg=COLOR_BG, pady=20, padx=30)
        frame_body.pack(fill="both", expand=True)

        def crear_campo(parent, label_text, valor_inicial="", altura=1):
            tk.Label(parent, text=label_text, font=FONT_LABEL, fg=COLOR_TEXT, bg=COLOR_BG, anchor="w").pack(fill="x", pady=(10, 2))
            if altura == 1:
                entry = tk.Entry(
                    parent,
                    font=("Segoe UI", 11),
                    bg=COLOR_PANEL,
                    fg=COLOR_TEXT,
                    insertbackground=COLOR_GREEN,
                    relief="flat",
                    bd=6
                )
                entry.insert(0, valor_inicial)
                entry.pack(fill="x", ipady=6)
            else:
                entry = tk.Text(
                    parent,
                    font=("Segoe UI", 10),
                    bg=COLOR_PANEL,
                    fg=COLOR_TEXT,
                    insertbackground=COLOR_GREEN,
                    relief="flat",
                    bd=6,
                    height=altura,
                    wrap="word"
                )
                entry.insert("1.0", valor_inicial)
                entry.pack(fill="x")
            return entry

        # Campo: Grupo Origen
        entry_origen = crear_campo(frame_body, "📥  Nombre exacto del grupo ORIGEN:", config.get("grupo_origen", ""))

        # Campo: Grupo Destino
        entry_destino = crear_campo(frame_body, "📤  Nombre exacto del grupo DESTINO:", config.get("grupo_destino", ""))

        # Separador
        tk.Frame(frame_body, bg=COLOR_ACCENT, height=1).pack(fill="x", pady=15)

        # Tipos permitidos
        tk.Label(frame_body, text="📎  Tipos de contenido a reenviar:", font=FONT_LABEL, fg=COLOR_TEXT, bg=COLOR_BG, anchor="w").pack(fill="x")

        frame_tipos = tk.Frame(frame_body, bg=COLOR_BG)
        frame_tipos.pack(fill="x", pady=5)

        var_imagenes = tk.BooleanVar(value="imagen" in config.get("tipos_permitidos", ["imagen", "archivo"]))
        var_archivos = tk.BooleanVar(value="archivo" in config.get("tipos_permitidos", ["imagen", "archivo"]))

        chk_style = {"font": FONT_LABEL, "fg": COLOR_TEXT, "bg": COLOR_BG, "activebackground": COLOR_BG,
                     "activeforeground": COLOR_GREEN, "selectcolor": COLOR_PANEL, "pady": 3}

        tk.Checkbutton(frame_tipos, text="🖼  Imágenes (JPG, PNG, GIF, WebP)", variable=var_imagenes, **chk_style).pack(anchor="w")
        tk.Checkbutton(frame_tipos, text="📄  Archivos (PDF, DOCX, XLSX, ZIP...)", variable=var_archivos, **chk_style).pack(anchor="w")

        # Separador
        tk.Frame(frame_body, bg=COLOR_ACCENT, height=1).pack(fill="x", pady=15)

        # Delay entre verificaciones
        tk.Label(frame_body, text="⏱  Delay entre verificaciones (segundos):", font=FONT_LABEL, fg=COLOR_TEXT, bg=COLOR_BG, anchor="w").pack(fill="x")

        frame_delay = tk.Frame(frame_body, bg=COLOR_BG)
        frame_delay.pack(fill="x", pady=5)

        tk.Label(frame_delay, text="Mín:", font=FONT_SMALL, fg=COLOR_SUBTEXT, bg=COLOR_BG).pack(side="left")
        spin_min = tk.Spinbox(frame_delay, from_=1, to=30, width=5, font=FONT_LABEL, bg=COLOR_PANEL, fg=COLOR_TEXT, insertbackground=COLOR_GREEN, buttonbackground=COLOR_PANEL, relief="flat")
        spin_min.delete(0, "end")
        spin_min.insert(0, str(config.get("delay_min_segundos", 2)))
        spin_min.pack(side="left", padx=(4, 16))

        tk.Label(frame_delay, text="Máx:", font=FONT_SMALL, fg=COLOR_SUBTEXT, bg=COLOR_BG).pack(side="left")
        spin_max = tk.Spinbox(frame_delay, from_=1, to=60, width=5, font=FONT_LABEL, bg=COLOR_PANEL, fg=COLOR_TEXT, insertbackground=COLOR_GREEN, buttonbackground=COLOR_PANEL, relief="flat")
        spin_max.delete(0, "end")
        spin_max.insert(0, str(config.get("delay_max_segundos", 5)))
        spin_max.pack(side="left", padx=4)

        # ------------------------------------------------------------------
        # BOTONES
        # ------------------------------------------------------------------
        frame_btns = tk.Frame(ventana, bg=COLOR_BG, pady=16, padx=30)
        frame_btns.pack(fill="x")

        def guardar():
            origen = entry_origen.get().strip()
            destino = entry_destino.get().strip()

            if not origen or not destino:
                messagebox.showerror("Error", "Debes ingresar el nombre del grupo origen y destino.", parent=ventana)
                return

            try:
                d_min = int(spin_min.get())
                d_max = int(spin_max.get())
                if d_min > d_max:
                    messagebox.showerror("Error", "El delay mínimo no puede ser mayor que el máximo.", parent=ventana)
                    return
            except ValueError:
                messagebox.showerror("Error", "Los valores de delay deben ser números enteros.", parent=ventana)
                return

            tipos = []
            if var_imagenes.get():
                tipos.append("imagen")
            if var_archivos.get():
                tipos.append("archivo")

            if not tipos:
                messagebox.showerror("Error", "Debes seleccionar al menos un tipo de contenido.", parent=ventana)
                return

            nuevo_config = {
                "grupo_origen": origen,
                "grupo_destino": destino,
                "delay_min_segundos": d_min,
                "delay_max_segundos": d_max,
                "tipos_permitidos": tipos,
                "activo": config.get("activo", False)
            }
            guardar_config(nuevo_config)
            log.log_info(f"Configuración guardada: origen='{origen}', destino='{destino}'")
            messagebox.showinfo(
                "✅ Guardado",
                f"Configuración guardada correctamente.\n\n"
                f"Origen: {origen}\n"
                f"Destino: {destino}\n\n"
                f"Reinicia el monitor desde la bandeja para aplicar los cambios.",
                parent=ventana
            )
            if callback_guardado:
                callback_guardado(nuevo_config)
            ventana.destroy()

        btn_guardar = tk.Button(
            frame_btns,
            text="  💾  Guardar Configuración  ",
            font=("Segoe UI", 11, "bold"),
            bg=COLOR_GREEN,
            fg="#1a1a2e",
            activebackground="#00a381",
            activeforeground="#1a1a2e",
            relief="flat",
            bd=0,
            padx=10,
            pady=8,
            cursor="hand2",
            command=guardar
        )
        btn_guardar.pack(side="left", expand=True, fill="x", padx=(0, 8))

        btn_cancelar = tk.Button(
            frame_btns,
            text="  Cancelar  ",
            font=("Segoe UI", 10),
            bg=COLOR_PANEL,
            fg=COLOR_SUBTEXT,
            activebackground=COLOR_ACCENT,
            activeforeground=COLOR_TEXT,
            relief="flat",
            bd=0,
            padx=10,
            pady=8,
            cursor="hand2",
            command=ventana.destroy
        )
        btn_cancelar.pack(side="left")

        # Limpiar referencia al cerrar
        def _on_cerrar():
            cls._instancia_activa = None
            ventana.destroy()
            if _raiz_propia:
                try:
                    raiz.destroy()
                except Exception:
                    pass

        ventana.protocol("WM_DELETE_WINDOW", _on_cerrar)

        # Centrar ventana en pantalla
        ventana.update_idletasks()
        w = ventana.winfo_width()
        h = ventana.winfo_height()
        sw = ventana.winfo_screenwidth()
        sh = ventana.winfo_screenheight()
        ventana.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

        if _raiz_propia:
            raiz.mainloop()
