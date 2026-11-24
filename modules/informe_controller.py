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
        Orquesta el proceso completo en un hilo secundario para no bloquear Tkinter:
        Abrir Excel -> Crear Diccionario -> Abrir PDF -> Leer Facturas -> Buscar Factura ->
        Si existe y tiene valor en EFECTIVO -> Escribir comprobante H en CH.DIA del PDF
        Si no -> Escribir registro en EFECTIVO del PDF -> Guardar PDF -> Mostrar Resultado -> Abrir PDF
        """
        if not pdf_path or not os.path.exists(pdf_path):
            messagebox.showerror("Error", "El archivo PDF seleccionado no existe.")
            return None

        # ProgressWindow se crea en el hilo principal ANTES de lanzar el hilo
        progress_win = None
        if parent_window:
            progress_win = ProgressWindow(parent_window)

        # ── Helpers para mostrar mensajes desde el hilo secundario ──────────
        def mostrar_exito(msg):
            if parent_window:
                parent_window.after(0, lambda: messagebox.showinfo("Proceso Completado", msg))
            else:
                messagebox.showinfo("Proceso Completado", msg)

        def mostrar_error(msg):
            if parent_window:
                parent_window.after(0, lambda: messagebox.showerror("Error al procesar informe", msg))
            else:
                messagebox.showerror("Error al procesar informe", msg)

        def cerrar_progress():
            if progress_win:
                if parent_window:
                    parent_window.after(0, lambda: progress_win.destroy() if progress_win.winfo_exists() else None)
                else:
                    if progress_win.winfo_exists():
                        progress_win.destroy()

        # ── Lógica principal que corre en el hilo secundario ────────────────
        def _worker():
            try:
                # 1. Abrir Excel y crear diccionario en memoria
                self.excel_manager.cargar_excel()

                # 2. Abrir PDF y leer facturas con coordenadas y detección de columna EFECTIVO
                reader = PdfReader(pdf_path)

                def callback_progreso(pag_actual, total_pags, total_facturas):
                    # progress_win.actualizar_progreso ya usa after() internamente
                    if progress_win and progress_win.winfo_exists():
                        progress_win.actualizar_progreso(pag_actual, total_pags, total_facturas)

                facturas_halladas = reader.extraer_facturas(progress_callback=callback_progreso)

                # 3. Buscar cada factura en el diccionario de Excel e integrar con Logger
                items_a_escribir = []
                encontradas_cnt = 0
                no_encontradas_cnt = 0

                for factura_hallada in facturas_halladas:
                    num_factura = factura_hallada["factura"]
                    datos_excel = self.excel_manager.buscar_factura(num_factura)

                    if datos_excel and (datos_excel.get("registro") or datos_excel.get("transferencias")):
                        ci = datos_excel.get("registro", "")
                        comp_h = datos_excel.get("comprobante_h", ci)
                        transferencias = datos_excel.get("transferencias", [])

                        item_escritura = dict(factura_hallada)
                        item_escritura["registro"] = ci
                        item_escritura["comprobante_h"] = comp_h
                        item_escritura["transferencias"] = transferencias
                        items_a_escribir.append(item_escritura)

                        if factura_hallada.get("tiene_efectivo"):
                            self.logger.log_factura_agregada(
                                num_factura,
                                "OMITIDA_EFECTIVO_EXISTENTE (Ya tiene EFECTIVO > 0)"
                            )
                        else:
                            ci_summary = ", ".join(
                                t.get("registro", "") for t in transferencias if t.get("registro")
                            )
                            self.logger.log_factura_agregada(num_factura, f"{ci_summary} (Columna EFECTIVO)")

                        encontradas_cnt += 1
                    else:
                        self.logger.log_factura_no_encontrada(num_factura)
                        no_encontradas_cnt += 1

                # 4. Escribir CIs / Comprobantes en el PDF y guardar
                writer = PdfWriter(pdf_path)

                def writer_callback(stream):
                    writer.escribir_registros_ci(items_a_escribir, stream)

                ruta_pdf_generado = self.report_generator.guardar_informe(writer_callback)

                # Cerrar ventana de progreso desde el hilo principal
                cerrar_progress()

                # 5. Mostrar resultado desde el hilo principal
                msg_exito = (
                    f"✅ Informe generado correctamente.\n\n"
                    f"📄 Facturas procesadas: {len(facturas_halladas)}\n"
                    f"✔️ CIs / Comprobantes agregados: {encontradas_cnt}\n"
                    f"⚠️ Facturas no encontradas: {no_encontradas_cnt}\n\n"
                    f"Ubicación:\n{ruta_pdf_generado}"
                )
                mostrar_exito(msg_exito)

                # Abrir el PDF generado automáticamente
                def abrir_pdf():
                    try:
                        os.startfile(ruta_pdf_generado)
                    except Exception as e:
                        print("No se pudo abrir el PDF automáticamente:", e)

                if parent_window:
                    parent_window.after(800, abrir_pdf)
                else:
                    abrir_pdf()

            except Exception as e:
                import traceback
                import os
                tb_str = traceback.format_exc()
                # Guardar log completo para diagnóstico en EXE
                try:
                    log_path = os.path.join(
                        os.path.dirname(os.path.abspath(
                            getattr(__import__('sys'), 'executable', __file__)
                        )),
                        "error_informe.txt"
                    )
                    with open(log_path, "w", encoding="utf-8") as _f:
                        _f.write(tb_str)
                except Exception:
                    pass
                cerrar_progress()
                mostrar_error(
                    f"Ocurrió un error inesperado:\n{str(e)}\n\n"
                    f"Detalles guardados en: error_informe.txt\n\n"
                    f"{tb_str}"
                )

        # ── Lanzar el worker en hilo secundario ─────────────────────────────
        import threading
        hilo = threading.Thread(target=_worker, daemon=True)
        hilo.start()