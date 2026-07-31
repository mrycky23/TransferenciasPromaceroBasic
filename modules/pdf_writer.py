import io
from pypdf import PdfReader as PyPdfReader, PdfWriter as PyPdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from modules.config import EFECTIVO_X_OFFSET, CHDIA_X_OFFSET, EFECTIVO_Y_OFFSET

COLOR_CI = HexColor("#1E88E5")


class PdfWriter:
    def __init__(self, original_pdf_path):
        self.original_pdf_path = original_pdf_path

    def escribir_registros_ci(self, items_a_escribir, output_stream):
        reader = PyPdfReader(self.original_pdf_path)
        writer = PyPdfWriter()

        items_por_pagina = {}
        for registro in items_a_escribir:
            pag = registro["pagina"]
            if pag not in items_por_pagina:
                items_por_pagina[pag] = []
            items_por_pagina[pag].append(registro)

        print("=" * 60)
        print("Cantidad items:", len(items_a_escribir))
        print("Páginas:", list(items_por_pagina.keys()))
        print("=" * 60)

        for num_pag, page in enumerate(reader.pages, start=1):
            page_width  = float(page.mediabox.width)
            page_height = float(page.mediabox.height)

            if num_pag in items_por_pagina:
                packet = io.BytesIO()
                can = canvas.Canvas(packet, pagesize=(page_width, page_height))

                for registro in items_por_pagina[num_pag]:

                    transferencias = registro.get("transferencias", [])

                    if not transferencias and registro.get("registro"):
                        transferencias = [{
                            "registro": registro.get("registro", ""),
                            "valor": registro.get("valor", 0.0)
                        }]

                    transferencias = [
                        t for t in transferencias
                        if str(t.get("registro", "")).strip()
                    ]

                    if not transferencias:
                        continue

                    num_transf = len(transferencias)

                    row_top    = registro["y"]
                    row_height = registro.get("height", 10.0)
                    y_base = page_height - row_top - (row_height * 0.75) + EFECTIVO_Y_OFFSET

                    x_chdia    = registro.get("x_chdia")
                    x_efectivo = registro.get("x_efectivo")

                    if x_efectivo is not None:
                        x_inicio = x_efectivo + 8

                    else:
                        x_inicio = registro["x"] + 380

                    if num_transf == 1:
                        font_size    = 7.5
                        separacion_x = 0
                    elif num_transf == 2:
                        font_size    = 6.5
                        separacion_x = 52
                    else:
                        font_size    = 5.5
                        separacion_x = 44

                    for idx, t in enumerate(transferencias):
                        ci_str = str(t.get("registro", "")).strip()
                        val    = t.get("valor", 0.0)

                        if not ci_str:
                            continue

                        if val and float(val) > 0:
                            try:
                                val_f   = float(val)
                                val_str = f"{val_f:g}" if val_f == int(val_f) else f"{val_f:.2f}"
                                texto   = f"{ci_str} ${val_str}"
                            except:
                                texto = ci_str
                        else:
                            texto = ci_str

                        current_x = x_inicio + (idx * separacion_x)

                        # Color y fuente justo antes de cada drawString
                        can.setFont("Helvetica-Bold", font_size)
                        can.setFillColor(COLOR_CI)
                        can.drawString(current_x, y_base, texto)

                        print(f"  [{num_pag}] '{texto}'   ({current_x:.1f}, {y_base:.1f})")
                print("="*50)
                print("Transferencias encontradas:", len(transferencias))
                print("Texto:", texto)
                print("X:", current_x)
                print("Y:", y_base)
                print("="*50)
                can.save()
                packet.seek(0)

                overlay_pdf = PyPdfReader(packet)
                page.merge_page(overlay_pdf.pages[0])

            writer.add_page(page)

        writer.write(output_stream)
