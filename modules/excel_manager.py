import openpyxl
import os
from modules.config import EXCEL_PATH


def normalizar_factura(valor):
    """
    Normaliza el número de factura eliminando guiones y espacios.
    '001-002-000159582' → '001002000159582'
    '001002000159582'   → '001002000159582'
    """
    if valor is None:
        return ""
    return str(valor).strip().replace("-", "").replace(" ", "")


class ExcelManager:
    def __init__(self, excel_path=EXCEL_PATH):
        self.excel_path = excel_path
        self.facturas_index = {}
        self.cargado = False

    def cargar_excel(self):
        """
        Lee MODELO.xlsx únicamente una vez y crea un índice en memoria.
        Estructura del índice:
        {
            "001002000159582": {
                "registro": "CI-14444",       ← Col H (# TRANSFERENCIA)
                "comprobante_h": "CI-14444",
                "valor": 120.0,
                "transferencias": [
                    {"registro": "CI-14444", "comprobante_h": "CI-14444",
                     "comprobante_bancario": "12658818", "valor": 120.0}
                ]
            }
        }
        """
        if self.cargado:
            return self.facturas_index

        if not os.path.exists(self.excel_path):
            raise FileNotFoundError(f"No se encontró el archivo Excel: {self.excel_path}")

        wb = openpyxl.load_workbook(self.excel_path, data_only=True)
        ws = wb.active

        index = {}

        def procesar_fila(fila):
            val_b = ws[f"B{fila}"].value  # #COMPROBANTE (número bancario)
            val_e = ws[f"E{fila}"].value  # FACTURA
            val_f = ws[f"F{fila}"].value  # VALOR
            val_h = ws[f"H{fila}"].value  # # TRANSFERENCIA → CI que va al PDF

            if val_e is None or not str(val_e).strip():
                return

            # Normalizar factura: quitar guiones para comparar con lo que
            # extrae el PDF reader (que también normaliza)
            factura_str = normalizar_factura(val_e)

            comprobante_bancario = str(val_b).strip() if val_b is not None else ""
            registro_ci = str(val_h).strip() if val_h is not None else ""

            try:
                valor_num = float(val_f) if val_f is not None else 0.0
            except (ValueError, TypeError):
                valor_num = 0.0

            transf = {
                "registro": registro_ci,           # CI-14444 → se escribe en PDF
                "comprobante_h": registro_ci,
                "comprobante_bancario": comprobante_bancario,
                "valor": valor_num
            }

            if factura_str not in index:
                index[factura_str] = {
                    "registro": registro_ci,
                    "comprobante_h": registro_ci,
                    "valor": valor_num,
                    "transferencias": [transf]
                }
            else:
                index[factura_str]["transferencias"].append(transf)
                index[factura_str]["valor"] += valor_num

        # Sección 1: filas 4 a 44
        for fila in range(4, 45):
            if ws[f"B{fila}"].value is None and ws[f"E{fila}"].value is None:
                continue
            procesar_fila(fila)

        # Sección 2: filas 56 hasta el final
        fila = 56
        max_row = ws.max_row or 200
        while fila <= max_row:
            if ws[f"B{fila}"].value is not None or ws[f"E{fila}"].value is not None:
                procesar_fila(fila)
            fila += 1

        wb.close()
        self.facturas_index = index
        self.cargado = True

        # Diagnóstico — quitar en producción
        print(f"[ExcelManager] {len(index)} facturas cargadas:")
        for k, v in list(index.items())[:5]:
            cis = [t['registro'] for t in v['transferencias']]
            print(f"  {k} - {cis}")

        return self.facturas_index

    def buscar_factura(self, numero_factura):
        """
        Busca una factura normalizando el número para que coincidan
        tanto '001-002-000159582' como '001002000159582'.
        """
        if not self.cargado:
            self.cargar_excel()

        key = normalizar_factura(numero_factura)

        resultado = self.facturas_index.get(key)

        # Diagnóstico — quitar en producción
        if resultado:
            cis = [t['registro'] for t in resultado.get('transferencias', [])]
            print(f"[ExcelManager] ENCONTRADA '{key}'  CIs: {cis}")
        else:
            print(f"[ExcelManager] NO ENCONTRADA '{key}'")

        return resultado