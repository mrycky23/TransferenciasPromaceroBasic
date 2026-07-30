import pdfplumber
import re

class PdfReader:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path

    def extraer_facturas(self, progress_callback=None):
        """
        Lee todo el PDF utilizando pdfplumber.
        Devuelve una lista de diccionarios con:
        [
            {
                "factura": "001002000458741",
                "x": 72.51,
                "y": 416.82,
                "pagina": 1
            }, ...
        ]
        """
        hallazgos = []
        # Patrones para identificar números de factura (ej. 15 dígitos o prefijo 001002000...)
        patron_factura = re.compile(r"\b(001002000\d{6}|\d{15}|\d{3}-\d{3}-\d{9})\b")

        with pdfplumber.open(self.pdf_path) as pdf:
            total_paginas = len(pdf.pages)

            for num_pag, page in enumerate(pdf.pages, start=1):
                words = page.extract_words()
                
                for word in words:
                    texto = word["text"].strip()
                    coincidencias = patron_factura.findall(texto)
                    for factura in coincidencias:
                        # Limpiar guiones si los hubiera
                        factura_limpia = factura.replace("-", "")
                        hallazgos.append({
                            "factura": factura_limpia,
                            "x": float(word["x0"]),
                            "y": float(word["top"]), # Coordenada Y desde la parte superior
                            "pagina": num_pag,
                            "page_height": float(page.height),
                            "page_width": float(page.width)
                        })

                if progress_callback:
                    progress_callback(num_pag, total_paginas, len(hallazgos))

        return hallazgos
