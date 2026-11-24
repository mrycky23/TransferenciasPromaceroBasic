import os
import sys


# ============================================================
# DIRECTORIO BASE DE LA APLICACIÓN
# ============================================================

def obtener_base_dir():
    """
    Obtiene correctamente la carpeta de la aplicación.

    En ejecución normal con Python:
        utiliza la carpeta raíz del proyecto.

    En ejecución como EXE de PyInstaller:
        utiliza la carpeta donde se encuentra el EXE.

    Esto evita utilizar la carpeta temporal MEIPASS.
    """

    # --------------------------------------------------------
    # Aplicación compilada con PyInstaller
    # --------------------------------------------------------

    if getattr(sys, "frozen", False):

        return os.path.dirname(
            os.path.abspath(
                sys.executable
            )
        )

    # --------------------------------------------------------
    # Ejecución normal con Python
    # --------------------------------------------------------

    return os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )


# ============================================================
# DIRECTORIO BASE
# ============================================================

BASE_DIR = obtener_base_dir()


# ============================================================
# ARCHIVO EXCEL
# ============================================================

EXCEL_PATH = os.path.join(
    BASE_DIR,
    "MODELO.xlsx"
)


# ============================================================
# DIRECTORIO DE PDF GENERADOS
# ============================================================

PDFS_GENERADOS_DIR = os.path.join(
    BASE_DIR,
    "pdfs_generados"
)


# ============================================================
# DIRECTORIO DE LOGS
# ============================================================

LOGS_DIR = os.path.join(
    BASE_DIR,
    "logs"
)


# ============================================================
# PREFIJO PREDETERMINADO DE FACTURAS
# ============================================================

PREFIJO_FACTURA_DEFAULT = "001002000"


# ============================================================
# DESPLAZAMIENTOS X / Y PARA EL PDF
# ============================================================

# Distancia desde X de la factura hasta la columna EFECTIVO
EFECTIVO_X_OFFSET = 320.0


# Distancia desde X de la factura hasta la columna CH.DIA
CHDIA_X_OFFSET = 390.0


# Desplazamiento vertical para EFECTIVO
EFECTIVO_Y_OFFSET = 0.0


# ============================================================
# RANGO X PARA DETECTAR COLUMNA EFECTIVO
# ============================================================

EFECTIVO_COL_MIN_X = 300.0

EFECTIVO_COL_MAX_X = 370.0


# ============================================================
# NOMBRE POR DEFECTO DEL INFORME FINAL
# ============================================================

DEFAULT_REPORT_NAME = "Informe_Completado.pdf"


# ============================================================
# DIAGNÓSTICO
# ============================================================

print("=" * 60)
print("[CONFIG] BASE_DIR:")
print(BASE_DIR)
print()
print("[CONFIG] EXCEL_PATH:")
print(EXCEL_PATH)
print("=" * 60)