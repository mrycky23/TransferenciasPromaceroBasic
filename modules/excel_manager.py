import openpyxl
import os
from modules.config import EXCEL_PATH

class ExcelManager:
    def __init__(self, excel_path=EXCEL_PATH):
        self.excel_path = excel_path
        self.facturas_index = {}
        self.cargado = False

    def cargar_excel(self):
        """
        Lee MODELO.xlsx únicamente una vez y crea un índice en memoria.
        Estructura del índice:
        facturas = {
            "001002000458741": {
                "registro": "CI-4587",
                "valor": 125.30
            }
        }
        """
        if self.cargado:
            return self.facturas_index

        if not os.path.exists(self.excel_path):
            raise FileNotFoundError(f"No se encontró el archivo de Excel: {self.excel_path}")

        wb = openpyxl.load_workbook(self.excel_path, data_only=True)
        ws = wb.active

        index = {}

        def procesar_fila(fila):
            val_b = ws[f"H{fila}"].value # Registro / Transferencia
            val_e = ws[f"E{fila}"].value # Factura
            val_f = ws[f"F{fila}"].value # Valor

            if val_e is not None and str(val_e).strip():
                factura_str = str(val_e).strip()
                registro_str = str(val_b).strip() if val_b is not None else ""
                
                try:
                    valor_num = float(val_f) if val_f is not None else 0.0
                except (ValueError, TypeError):
                    valor_num = 0.0

                index[factura_str] = {
                    "registro": registro_str,
                    "valor": valor_num
                }

        # Sección 1: filas 4 a 44
        for fila in range(4, 45):
            if ws[f"H{fila}"].value is None and ws[f"E{fila}"].value is None:
                continue
            procesar_fila(fila)

        # Sección 2: filas 56 hasta el final del contenido
        fila = 56
        max_row = ws.max_row
        while fila <= max_row:
            if ws[f"H{fila}"].value is not None or ws[f"E{fila}"].value is not None:
                procesar_fila(fila)
            fila += 1

        wb.close()
        self.facturas_index = index
        self.cargado = True
        return self.facturas_index

    def buscar_factura(self, numero_factura):
        """
        Busca instantáneamente una factura en el índice en memoria.
        Retorna dict con 'registro' y 'valor' o None si no existe.
        """
        if not self.cargado:
            self.cargar_excel()

        key = str(numero_factura).strip()
        return self.facturas_index.get(key)
