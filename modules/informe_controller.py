import os
import win32api
from tkinter import messagebox
from modules.excel_manager import ExcelManager
from modules.pdf_reader import PdfReader
from modules.pdf_writer import PdfWriter
from modules.report_generator import ReportGenerator
from modules.logger import Logger
from modules.progress_window import ProgressWindow

class InformeController:
    def __init__(self, excel_path=None):
        self.excel_manager = ExcelManager(excel_path) if excel_path else ExcelManager()
        self.logger = Logger()
        self.report_generator = ReportGenerator()

    def procesar_informe(self, pdf_path, parent_window=None):
        """
        Orquesta el proceso completo:
        Abrir Excel -> Crear Diccionario -> Abrir PDF -> Leer Facturas -> Buscar Factura -> Si existe: Escribir CI -> Guardar PDF -> Mostrar Resultado -> Abrir PDF
        """
        if not pdf_path or not os.path.exists(pdf_path):
            messagebox.showerror("Error", "El archivo PDF seleccionado no existe.")
            return None

        progress_win = None
        if parent_window:
            progress_win = ProgressWindow(parent_window)

        try:
            # 1. Abrir Excel y crear diccionario en memoria
            self.excel_manager.cargar_excel()

            # 2. Abrir PDF y leer facturas con coordenadas
            reader = PdfReader(pdf_path)
            
            def callback_progreso(pag_actual, total_pags, total_facturas):
                if progress_win and progress_win.winfo_exists():
                    progress_win.actualizar_progreso(pag_actual, total_pags, total_facturas)

            facturas_halladas = reader.extraer_facturas(progress_callback=callback_progreso)

            # 3. Buscar cada factura en el diccionario de Excel e integrar con Logger
            items_a_escribir = []
            encontradas_cnt = 0
            no_encontradas_cnt = 0

            for item in facturas_halladas:
                num_factura = item["factura"]
                datos_excel = self.excel_manager.buscar_factura(num_factura)

                if datos_excel and datos_excel.get("registro"):
                    ci = datos_excel["registro"]
                    item_escritura = dict(item)
                    item_escritura["registro"] = ci
                    items_a_escribir.append(item_escritura)
                    self.logger.log_factura_agregada(num_factura, ci)
                    encontradas_cnt += 1
                else:
                    self.logger.log_factura_no_encontrada(num_factura)
                    no_encontradas_cnt += 1

            # 4. Escribir CIs en el PDF y Guardar en pdfs_generados/
            writer = PdfWriter(pdf_path)

            def writer_callback(stream):
                writer.escribir_registros_ci(items_a_escribir, stream)

            ruta_pdf_generado = self.report_generator.guardar_informe(writer_callback)

            if progress_win and progress_win.winfo_exists():
                progress_win.destroy()

            # 5. Mostrar resultado y abrir PDF
            msg_exito = (
                f"✅ Informe generado correctamente.\n\n"
                f"📄 Facturas procesadas: {len(facturas_halladas)}\n"
                f"✔️ CIs agregados: {encontradas_cnt}\n"
                f"⚠️ Facturas no encontradas: {no_encontradas_cnt}\n\n"
                f"Ubicación:\n{ruta_pdf_generado}"
            )
            messagebox.showinfo("Proceso Completado", msg_exito)

            # Abrir el PDF generado automáticamente
            try:
                if os.name == 'nt':
                    win32api.ShellExecute(0, "open", ruta_pdf_generado, None, ".", 1)
                else:
                    os.system(f'xdg-open "{ruta_pdf_generado}"')
            except Exception as e:
                print("No se pudo abrir el PDF automáticamente:", e)

            return ruta_pdf_generado

        except Exception as e:
            if progress_win and progress_win.winfo_exists():
                progress_win.destroy()
            messagebox.showerror("Error al procesar informe", f"Ocurrió un error inesperado:\n{str(e)}")
            return None
