import io
from pypdf import PdfReader as PyPdfReader, PdfWriter as PyPdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black
from modules.config import EFECTIVO_X_OFFSET, EFECTIVO_Y_OFFSET

class PdfWriter:
    def __init__(self, original_pdf_path):
        self.original_pdf_path = original_pdf_path

    def escribir_registros_ci(self, items_a_escribir, output_stream):
        """
        items_a_escribir: lista de dicts
        [
            {
                "pagina": 1,
                "x": 72.51,
                "y": 416.82,
                "registro": "CI-4587",
                "page_width": 612.0,
                "page_height": 792.0,
                "x_efectivo": 450.0 # opcional, si no se calcula con offset
            }, ...
        ]
        """
        reader = PyPdfReader(self.original_pdf_path)
        writer = PyPdfWriter()

        # Agrupar ítems por página
        items_por_pagina = {}
        for item in items_a_escribir:
            pag = item["pagina"]
            if pag not in items_por_pagina:
                items_por_pagina[pag] = []
            items_por_pagina[pag].append(item)

        for num_pag, page in enumerate(reader.pages, start=1):
            page_width = float(page.mediabox.width)
            page_height = float(page.mediabox.height)

            if num_pag in items_por_pagina:
                packet = io.BytesIO()
                can = canvas.Canvas(packet, pagesize=(page_width, page_height))
                can.setFont("Helvetica-Bold", 8)
                can.setFillColor(black)

                for item in items_por_pagina[num_pag]:
                    ci_texto = str(item["registro"])
                    
                    # Determinar posición X para columna EFECTIVO
                    if "x_efectivo" in item and item["x_efectivo"] is not None:
                        pos_x = item["x_efectivo"]
                    else:
                        pos_x = item["x"] + EFECTIVO_X_OFFSET

                    # Convertir Y de pdfplumber (top->down) a ReportLab (bottom->up)
                    pos_y = page_height - item["y"] + EFECTIVO_Y_OFFSET - 9

                    can.drawString(pos_x, pos_y, ci_texto)

                can.save()
                packet.seek(0)

                overlay_pdf = PyPdfReader(packet)
                page.merge_page(overlay_pdf.pages[0])

            writer.add_page(page)

        writer.write(output_stream)
