import os

# Configuración de archivos y directorios
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EXCEL_PATH = os.path.join(BASE_DIR, "MODELO.xlsx")
PDFS_GENERADOS_DIR = os.path.join(BASE_DIR, "pdfs_generados")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

# Prefijo predeterminado de facturas
PREFIJO_FACTURA_DEFAULT = "001002000"

# Desplazamientos X / Y para escribir en las columnas del PDF
# EFECTIVO_X_OFFSET: Distancia desde X de la factura hasta la columna EFECTIVO
EFECTIVO_X_OFFSET = 320.0

# CHDIA_X_OFFSET: Distancia desde X de la factura hasta la columna CH.DIA
CHDIA_X_OFFSET = 390.0

EFECTIVO_Y_OFFSET = 0.0

# Rango X estimado para detectar si la columna EFECTIVO del PDF contiene un valor
EFECTIVO_COL_MIN_X = 300.0
EFECTIVO_COL_MAX_X = 370.0

# Nombre por defecto del informe final
DEFAULT_REPORT_NAME = "Informe_Completado.pdf"
