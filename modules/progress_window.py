import customtkinter as ctk

class ProgressWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)

        self.title("Procesando Informe")
        self.geometry("380x280")
        self.resizable(False, False)
        self.attributes("-topmost", True)

        try:
            x = parent.winfo_rootx() + (parent.winfo_width() // 2) - 190
            y = parent.winfo_rooty() + (parent.winfo_height() // 2) - 140
            self.geometry(f"380x280+{x}+{y}")
        except Exception:
            pass

        self.protocol("WM_DELETE_WINDOW", lambda: None)

        self.frame = ctk.CTkFrame(self, corner_radius=12)
        self.frame.pack(fill="both", expand=True, padx=15, pady=15)

        self.lbl_titulo = ctk.CTkLabel(
            self.frame,
            text="══════════════════════\nProcesando Informe\n══════════════════════",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.lbl_titulo.pack(pady=(15, 10))

        self.progress_bar = ctk.CTkProgressBar(self.frame, width=280, height=14)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=10)

        self.lbl_pagina = ctk.CTkLabel(
            self.frame,
            text="Página\n0 / 0",
            font=ctk.CTkFont(size=13)
        )
        self.lbl_pagina.pack(pady=5)

        self.lbl_facturas = ctk.CTkLabel(
            self.frame,
            text="Facturas encontradas\n0",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#1E88E5"
        )
        self.lbl_facturas.pack(pady=5)

    def actualizar_progreso(self, pagina_actual, total_paginas, facturas_conteo):
        # ← Usar after() para ejecutar en el hilo principal de Tkinter
        self.after(0, self._actualizar_ui, pagina_actual, total_paginas, facturas_conteo)

    def _actualizar_ui(self, pagina_actual, total_paginas, facturas_conteo):
        # Este método siempre corre en el hilo principal
        try:
            if not self.winfo_exists():
                return
            if total_paginas > 0:
                porcentaje = pagina_actual / total_paginas
                self.progress_bar.set(porcentaje)
                self.lbl_pagina.configure(text=f"Página\n{pagina_actual} / {total_paginas}")
                self.lbl_facturas.configure(text=f"Facturas encontradas\n{facturas_conteo}")
        except Exception:
            pass