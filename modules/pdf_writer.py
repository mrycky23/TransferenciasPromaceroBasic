import io

from pypdf import (
    PdfReader as PyPdfReader,
    PdfWriter as PyPdfWriter
)

from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor

from modules.config import (
    EFECTIVO_X_OFFSET,
    CHDIA_X_OFFSET,
    EFECTIVO_Y_OFFSET
)


# ============================================================
# CONFIGURACIÓN
# ============================================================

COLOR_CI = HexColor("#1E88E5")


class PdfWriter:

    def __init__(self, original_pdf_path):
        self.original_pdf_path = original_pdf_path

    # ========================================================
    # ESCRIBIR REGISTROS CI EN EL PDF
    # ========================================================

    def escribir_registros_ci(
        self,
        items_a_escribir,
        output_stream
    ):
        """
        Escribe los registros CI sobre el PDF original.

        Corrige previamente la rotación de las páginas para
        evitar que los CI aparezcan verticalmente.
        """

        reader = PyPdfReader(
            self.original_pdf_path
        )

        writer = PyPdfWriter()

        # ====================================================
        # AGRUPAR REGISTROS POR PÁGINA
        # ====================================================

        items_por_pagina = {}

        for registro in items_a_escribir:

            pag = registro["pagina"]

            if pag not in items_por_pagina:
                items_por_pagina[pag] = []

            items_por_pagina[pag].append(
                registro
            )

        # ====================================================
        # INFORMACIÓN DE DEPURACIÓN
        # ====================================================

        print("=" * 60)
        print(
            "Cantidad items:",
            len(items_a_escribir)
        )
        print(
            "Páginas:",
            list(items_por_pagina.keys())
        )
        print("=" * 60)

        # ====================================================
        # RECORRER TODAS LAS PÁGINAS
        # ====================================================

        for num_pag, page in enumerate(
            reader.pages,
            start=1
        ):

            # =================================================
            # CORREGIR ROTACIÓN DEL PDF
            # =================================================
            #
            # El PDF original utiliza una rotación de página.
            # Convertimos esa rotación en contenido real para
            # que ReportLab utilice correctamente las
            # coordenadas X/Y.
            # =================================================

            try:

                page.transfer_rotation_to_content()

            except Exception as e:

                print(
                    f"[ADVERTENCIA] "
                    f"No se pudo corregir la rotación "
                    f"de la página {num_pag}: {e}"
                )

            # =================================================
            # OBTENER DIMENSIONES DE LA PÁGINA
            # =================================================

            page_width = float(
                page.mediabox.width
            )

            page_height = float(
                page.mediabox.height
            )

            print(
                f"[Página {num_pag}] "
                f"Width={page_width:.2f} "
                f"Height={page_height:.2f}"
            )

            # =================================================
            # VERIFICAR SI ESTA PÁGINA TIENE REGISTROS
            # =================================================

            if num_pag in items_por_pagina:

                packet = io.BytesIO()

                # =================================================
                # CREAR CANVAS
                # =================================================

                can = canvas.Canvas(
                    packet,
                    pagesize=(
                        page_width,
                        page_height
                    )
                )

                # =================================================
                # BANDERA: SE DIBUJÓ ALGO EN EL CANVAS
                # =================================================
                #
                # Si todos los registros de la página son filtrados
                # (sin CI válidos), el canvas queda vacío y pypdf
                # lanza "Sequence index out of range" al leer pages[0].
                # =================================================

                drew_something = False

                # =================================================
                # RECORRER REGISTROS DE LA PÁGINA
                # =================================================

                for registro in items_por_pagina[
                    num_pag
                ]:

                    # =============================================
                    # OBTENER TRANSFERENCIAS
                    # =============================================

                    transferencias = registro.get(
                        "transferencias",
                        []
                    )

                    # =============================================
                    # COMPATIBILIDAD CON REGISTROS ANTIGUOS
                    # =============================================

                    if (
                        not transferencias
                        and registro.get("registro")
                    ):

                        transferencias = [
                            {
                                "registro": registro.get(
                                    "registro",
                                    ""
                                ),
                                "valor": registro.get(
                                    "valor",
                                    0.0
                                )
                            }
                        ]

                    # =============================================
                    # ELIMINAR REGISTROS SIN CI
                    # =============================================

                    transferencias = [
                        t
                        for t in transferencias
                        if str(
                            t.get(
                                "registro",
                                ""
                            )
                        ).strip()
                    ]

                    # Si no existen CI, continuar
                    if not transferencias:
                        continue

                    # =============================================
                    # CANTIDAD DE TRANSFERENCIAS
                    # =============================================

                    num_transf = len(
                        transferencias
                    )

                    # =================================================
                    # CALCULAR POSICIÓN Y
                    # =================================================

                    row_top = registro["y"]

                    row_height = registro.get(
                        "height",
                        10.0
                    )

                    y_base = (
                        page_height
                        - row_top
                        - (
                            row_height * 0.75
                        )
                        + EFECTIVO_Y_OFFSET
                    )

                    # =================================================
                    # OBTENER POSICIÓN DE EFECTIVO
                    # =================================================

                    x_chdia = registro.get(
                        "x_chdia"
                    )

                    x_efectivo = registro.get(
                        "x_efectivo"
                    )

                    # =================================================
                    # CALCULAR POSICIÓN X INICIAL
                    # =================================================

                    if x_efectivo is not None:

                        x_inicio = (
                            x_efectivo + 8
                        )

                    else:

                        x_inicio = (
                            registro["x"] + 380
                        )

                    # =================================================
                    # CONFIGURAR TAMAÑO Y SEPARACIÓN
                    # =================================================

                    if num_transf == 1:

                        font_size = 7.5
                        separacion_x = 0

                    elif num_transf == 2:

                        font_size = 6.5
                        separacion_x = 52

                    else:

                        font_size = 5.5
                        separacion_x = 44

                    # =================================================
                    # ESCRIBIR CADA CI
                    # =================================================

                    for idx, transferencia in enumerate(
                        transferencias
                    ):

                        # =============================================
                        # OBTENER CI
                        # =============================================

                        ci_str = str(
                            transferencia.get(
                                "registro",
                                ""
                            )
                        ).strip()

                        # =============================================
                        # OBTENER VALOR
                        # =============================================

                        val = transferencia.get(
                            "valor",
                            0.0
                        )

                        # =============================================
                        # VALIDAR CI
                        # =============================================

                        if not ci_str:
                            continue

                        # =================================================
                        # CONSTRUIR TEXTO
                        # =================================================

                        if val and float(val) > 0:

                            try:

                                val_f = float(
                                    val
                                )

                                # Si es entero
                                if val_f == int(val_f):

                                    val_str = (
                                        f"{val_f:g}"
                                    )

                                # Si tiene decimales
                                else:

                                    val_str = (
                                        f"{val_f:.2f}"
                                    )

                                texto = (
                                    f"{ci_str} "
                                    f"${val_str}"
                                )

                            except (
                                ValueError,
                                TypeError
                            ):

                                texto = ci_str

                        else:

                            texto = ci_str

                        # =================================================
                        # CALCULAR POSICIÓN X
                        # =================================================

                        current_x = (
                            x_inicio
                            + (
                                idx
                                * separacion_x
                            )
                        )

                        # =================================================
                        # CONFIGURAR FUENTE
                        # =================================================

                        can.setFont(
                            "Helvetica-Bold",
                            font_size
                        )

                        # =================================================
                        # CONFIGURAR COLOR
                        # =================================================

                        can.setFillColor(
                            COLOR_CI
                        )

                        # =================================================
                        # ESCRIBIR TEXTO
                        # =================================================

                        can.drawString(
                            current_x,
                            y_base,
                            texto
                        )

                        drew_something = True

                        # =================================================
                        # DEBUG
                        # =================================================

                        print(
                            f"  [{num_pag}] "
                            f"'{texto}' "
                            f"X={current_x:.1f} "
                            f"Y={y_base:.1f}"
                        )

                # =================================================
                # FINALIZAR CANVAS Y FUSIONAR CON PDF ORIGINAL
                # =================================================
                #
                # Solo fusionar si realmente se dibujó algo.
                # Un canvas vacío genera un PDF sin páginas, lo
                # que causa IndexError en overlay_pdf.pages[0].
                # =================================================

                if drew_something:

                    can.save()

                    packet.seek(0)

                    # =============================================
                    # CREAR PDF DEL OVERLAY
                    # =============================================

                    overlay_pdf = PyPdfReader(
                        packet
                    )

                    # =============================================
                    # VALIDAR QUE EL OVERLAY TIENE PÁGINAS
                    # =============================================

                    if len(overlay_pdf.pages) > 0:

                        overlay_page = (
                            overlay_pdf.pages[0]
                        )

                        # =========================================
                        # UNIR OVERLAY CON PDF ORIGINAL
                        # =========================================

                        page.merge_page(
                            overlay_page
                        )

                    else:

                        print(
                            f"[ADVERTENCIA] "
                            f"Overlay vacío en página {num_pag}, "
                            f"se omite la fusión."
                        )

                # =================================================
                # ELIMINAR ROTACIÓN RESTANTE
                # =================================================

                try:

                    page.rotation = 0

                except Exception:

                    pass

                # =================================================
                # INFORMACIÓN DE DEPURACIÓN
                # =================================================

                print("=" * 60)

                print(
                    f"Página procesada: {num_pag}"
                )

                print(
                    "Registros encontrados:",
                    len(
                        items_por_pagina[
                            num_pag
                        ]
                    )
                )

                print(
                    f"Dimensiones: "
                    f"{page_width:.2f} x "
                    f"{page_height:.2f}"
                )

                print("=" * 60)

            # =================================================
            # AGREGAR PÁGINA AL PDF FINAL
            # =================================================

            writer.add_page(
                page
            )

        # ====================================================
        # GENERAR PDF FINAL
        # ====================================================

        writer.write(
            output_stream
        )