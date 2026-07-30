import os
from datetime import datetime
from modules.config import PDFS_GENERADOS_DIR, DEFAULT_REPORT_NAME

class ReportGenerator:
    def __init__(self, output_dir=PDFS_GENERADOS_DIR):
        self.output_dir = output_dir
        self.ensure_output_dir()

    def ensure_output_dir(self):
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)

    def generar_ruta_salida(self, base_name=DEFAULT_REPORT_NAME):
        """
        Devuelve la ruta donde se guardará el PDF.
        Si Informe_Completado.pdf ya existe, genera Informe_Completado_YYYYMMDD_HHMMSS.pdf.
        """
        ruta_base = os.path.join(self.output_dir, base_name)
        if not os.path.exists(ruta_base):
            return ruta_base

        # Si el original ya existe, agregar marca de tiempo
        nombre_sin_ext, ext = os.path.splitext(base_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nuevo_nombre = f"{nombre_sin_ext}_{timestamp}{ext}"
        return os.path.join(self.output_dir, nuevo_nombre)

    def guardar_informe(self, pdf_writer_func, base_name=DEFAULT_REPORT_NAME):
        """
        Ejecuta pdf_writer_func pasando el stream de salida y guarda el archivo.
        Retorna la ruta absoluta del archivo generado.
        """
        ruta_salida = self.generar_ruta_salida(base_name)
        with open(ruta_salida, "wb") as f:
            pdf_writer_func(f)
        return ruta_salida
