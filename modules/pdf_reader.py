import pdfplumber
import re


class PdfReader:

    PATRON_FACTURA = re.compile(r"(001-002-\d{9}|001002\d{9})")
    PATRON_FECHA = re.compile(r"\d{2}/\d{2}/\d{4}")
    PATRON_NUMERO = re.compile(r"^\d{1,3}(?:,\d{3})*(?:\.\d+)?$|^\d+(?:\.\d+)?$")

    HEADER_KEYWORDS = {
        "factura": ["SECUENCIAL", "FACTURA", "COMPROBANTE", "NUMERO"],
        "cliente": ["CLIENTE", "RAZON SOCIAL", "NOMBRE"],
        "fecha": ["EMISION", "EMISIÓN", "FECHA"],
        "total": ["TOTAL", "VALOR TOTAL"],
        "efectivo": ["EFECTIVO", "EFEC."],
        "chdia": ["CH.DIA", "CH/DIA", "CHEQUE", "DIFERIDO"],
    }

    def __init__(self, pdf_path):
        self.pdf_path = pdf_path

    # -----------------------------------------------------

    def _detectar_columnas_cabecera(self, lineas):
        """
        Inspecciona las líneas extraídas con extract_text_lines()
        para ubicar los límites horizontales (x0, x1) y centros X
        de cada columna del reporte (SECUENCIAL, CLIENTE, FECHA, TOTAL, EFECTIVO, CH.DIA).
        """
        columnas = {}

        for line in lineas:
            texto_linea = line.get("text", "").upper()

            # Verificar si la línea contiene suficientes palabras clave para ser cabecera
            coincidencias = sum(
                1 for clave, palabras in self.HEADER_KEYWORDS.items()
                if any(p in texto_linea for p in palabras)
            )

            if coincidencias >= 2:
                chars = line.get("chars", [])
                if not chars:
                    continue

                # Agrupar caracteres contiguos en palabras de la cabecera
                palabras_linea = self._obtener_palabras_de_linea(chars)

                for p in palabras_linea:
                    txt = p["text"].upper()
                    for col_name, palabras_clave in self.HEADER_KEYWORDS.items():
                        if col_name not in columnas:
                            if any(pk in txt for pk in palabras_clave):
                                columnas[col_name] = {
                                    "x0": p["x0"],
                                    "x1": p["x1"],
                                    "center": (p["x0"] + p["x1"]) / 2.0
                                }

        return columnas

    # -----------------------------------------------------

    def _obtener_palabras_de_linea(self, chars):
        """
        Agrupa una lista de caracteres en palabras manteniendo coordenadas x0, x1.
        """
        palabras = []
        if not chars:
            return palabras

        palabra_actual = []

        for c in sorted(chars, key=lambda x: x["x0"]):
            if not palabra_actual:
                palabra_actual.append(c)
            else:
                # Distancia entre el final del último caracter y el inicio del actual
                prev_c = palabra_actual[-1]
                gap = c["x0"] - prev_c["x1"]
                if gap < 3.5 and c.get("top", 0) - prev_c.get("top", 0) < 3.0:
                    palabra_actual.append(c)
                else:
                    txt = "".join(ch["text"] for ch in palabra_actual).strip()
                    if txt:
                        palabras.append({
                            "text": txt,
                            "x0": palabra_actual[0]["x0"],
                            "x1": palabra_actual[-1]["x1"],
                            "top": palabra_actual[0]["top"],
                            "bottom": palabra_actual[0]["bottom"]
                        })
                    palabra_actual = [c]

        if palabra_actual:
            txt = "".join(ch["text"] for ch in palabra_actual).strip()
            if txt:
                palabras.append({
                    "text": txt,
                    "x0": palabra_actual[0]["x0"],
                    "x1": palabra_actual[-1]["x1"],
                    "top": palabra_actual[0]["top"],
                    "bottom": palabra_actual[0]["bottom"]
                })

        return palabras

    # -----------------------------------------------------

    def _extraer_datos_fila(self, line, columnas_detected):
        """
        Procesa una línea de texto de extract_text_lines() que contiene una factura.
        Asigna el texto a cada columna por su posición X lógica.
        """
        chars = line.get("chars", [])
        palabras = self._obtener_palabras_de_linea(chars)

        registro = {
            "factura": None,
            "fecha": None,
            "total": 0.0,
            "efectivo": 0.0,
            "x_factura": line.get("x0", 0),
            "x_efectivo": None,
            "x_chdia": None,
        }

        # Buscar factura en las palabras de la línea
        word_factura = None
        for p in palabras:
            m = self.PATRON_FACTURA.fullmatch(p["text"])
            if m:
                registro["factura"] = m.group(1).replace("-", "")
                word_factura = p
                registro["x_factura"] = p["x0"]
                break

        if not registro["factura"]:
            # Intento secundario por regex en el texto entero de la línea
            m = self.PATRON_FACTURA.search(line.get("text", ""))
            if m:
                registro["factura"] = m.group(1).replace("-", "")

        if not registro["factura"]:
            return None

        # Posiciones estimadas de columnas
        x_efectivo_col = columnas_detected.get("efectivo", {}).get("center")
        x_total_col = columnas_detected.get("total", {}).get("center")
        x_chdia_col = columnas_detected.get("chdia", {}).get("center")

        registro["x_efectivo"] = x_efectivo_col
        registro["x_chdia"] = x_chdia_col

        # Clasificar números por cercanía horizontal a las columnas detectadas
        for p in palabras:
            txt = p["text"].replace(",", "")
            if self.PATRON_NUMERO.fullmatch(txt):
                try:
                    val = float(txt)
                except ValueError:
                    continue

                center_p = (p["x0"] + p["x1"]) / 2.0

                if x_efectivo_col is not None:
                    # Si el número está cerca de la columna EFECTIVO
                    if abs(center_p - x_efectivo_col) <= 35:
                        registro["efectivo"] = val
                        continue

                if x_total_col is not None:
                    # Si el número está cerca de la columna TOTAL
                    if abs(center_p - x_total_col) <= 35:
                        registro["total"] = val
                        continue

                # Si no se detectaron cabeceras explícitas, fallback por orden numérico
                # (Normalmente el primer float relevante es total y el segundo es efectivo si x0 > total_x)

        return registro

    # -----------------------------------------------------

    def _ocr_extraer_lineas(self, numero_pagina):
        import fitz
        import pytesseract
        from PIL import Image

        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.ex'
        lineas = []
        try:
            doc = fitz.open(self.pdf_path)
            page = doc[numero_pagina - 1]
            # render at 300 DPI
            zoom = 300 / 72
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            
            lineas_dict = {}
            for i in range(len(data['level'])):
                text = data['text'][i].strip()
                if not text:
                    continue
                line_key = (data['block_num'][i], data['par_num'][i], data['line_num'][i])
                
                # Scale coordinates back to PDF points
                x0 = data['left'][i] / zoom
                top = data['top'][i] / zoom
                x1 = (data['left'][i] + data['width'][i]) / zoom
                bottom = (data['top'][i] + data['height'][i]) / zoom
                
                char_simulado = {
                    "text": text,
                    "x0": x0,
                    "x1": x1,
                    "top": top,
                    "bottom": bottom
                }
                
                if line_key not in lineas_dict:
                    lineas_dict[line_key] = {
                        "text": text,
                        "chars": [char_simulado],
                        "x0": x0,
                        "x1": x1,
                        "top": top,
                        "bottom": bottom
                    }
                else:
                    lineas_dict[line_key]["text"] += " " + text
                    lineas_dict[line_key]["chars"].append(char_simulado)
                    lineas_dict[line_key]["x0"] = min(lineas_dict[line_key]["x0"], x0)
                    lineas_dict[line_key]["x1"] = max(lineas_dict[line_key]["x1"], x1)
                    lineas_dict[line_key]["top"] = min(lineas_dict[line_key]["top"], top)
                    lineas_dict[line_key]["bottom"] = max(lineas_dict[line_key]["bottom"], bottom)
                    
            lineas = list(lineas_dict.values())
            # Ordenar de arriba hacia abajo
            lineas.sort(key=lambda x: x["top"])
            doc.close()
        except Exception as e:
            print(f"[PdfReader] Error en OCR para pág {numero_pagina}: {e}")
        return lineas

    # -----------------------------------------------------

    def extraer_facturas(self, progress_callback=None):
        resultado = []

        with pdfplumber.open(self.pdf_path) as pdf:
            total_paginas = len(pdf.pages)
            columnas_globales = {}

            for numero_pagina, page in enumerate(pdf.pages, start=1):
                # Usar page.extract_text_lines() para reconstruir la estructura lógica
                lineas = page.extract_text_lines(
                    layout=True,
                    strip=True
                )

                # Fallback a OCR si la página no tiene texto (ej. documento escaneado)
                if not lineas:
                    print(f"[PdfReader] Página {numero_pagina} sin texto, ejecutando OCR...")
                    lineas = self._ocr_extraer_lineas(numero_pagina)

                # Intentar detectar cabeceras en esta página
                cols_pag = self._detectar_columnas_cabecera(lineas)
                if cols_pag:
                    columnas_globales.update(cols_pag)

                # Usar columnas detectadas en la página o las acumuladas globales
                columnas_actuales = columnas_globales

                for line in lineas:
                    texto = line.get("text", "")

                    if self.PATRON_FACTURA.search(texto):
                        datos = self._extraer_datos_fila(line, columnas_actuales)

                        if datos and datos.get("factura"):
                            # Coordenadas por defecto si no hubo detección de cabecera
                            x_efec = datos["x_efectivo"]
                            if x_efec is None:
                                x_efec = datos["x_factura"] + 320.0

                            x_ch = datos["x_chdia"]
                            if x_ch is None:
                                x_ch = datos["x_factura"] + 390.0

                            valor_efectivo = datos["efectivo"]
                            tiene_efectivo = valor_efectivo > 0.001

                            resultado.append({
                                "factura": datos["factura"],
                                "pagina": numero_pagina,
                                "x": datos["x_factura"],
                                "y": line["top"],
                                "height": line["bottom"] - line["top"],
                                "x_efectivo": x_efec,
                                "x_chdia": x_ch,
                                "page_width": page.width,
                                "page_height": page.height,
                                "valor_total": datos["total"],
                                "valor_efectivo": valor_efectivo,
                                "tiene_efectivo": tiene_efectivo,
                            })

                if progress_callback:
                    progress_callback(
                        numero_pagina,
                        total_paginas,
                        len(resultado)
                    )

        return resultado