import os
from datetime import datetime
from modules.config import LOGS_DIR

class Logger:
    def __init__(self, logs_dir=LOGS_DIR):
        self.logs_dir = logs_dir
        self.ensure_logs_dir()

    def ensure_logs_dir(self):
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir, exist_ok=True)

    def get_log_filepath(self):
        fecha_str = datetime.now().strftime("%Y%m%d")
        return os.path.join(self.logs_dir, f"{fecha_str}.log")

    def log_factura_agregada(self, factura, ci):
        filepath = self.get_log_filepath()
        contenido = (
            f"Factura\n"
            f"{factura}\n"
            f"CI agregado\n"
            f"{ci}\n"
            f"--------------------\n"
        )
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(contenido)

    def log_factura_no_encontrada(self, factura):
        filepath = self.get_log_filepath()
        contenido = (
            f"Factura\n"
            f"{factura}\n"
            f"No encontrada\n"
            f"--------------------\n"
        )
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(contenido)
