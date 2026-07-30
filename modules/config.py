import os

# Configuración de archivos y directorios
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EXCEL_PATH = os.path.join(BASE_DIR, "MODELO.xlsx")
PDFS_GENERADOS_DIR = os.path.join(BASE_DIR, "pdfs_generados")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

# Prefijo predeterminado de facturas
PREFIJO_FACTURA_DEFAULT = "001002000"

# Desplazamiento X / Y para escribir en la columna EFECTIVO
# X_OFFSET: Distancia desde la coordenada X de la factura encontrada hasta la columna EFECTIVO.
# Ajustable según el diseño exacto del PDF original.
EFECTIVO_X_OFFSET = 380.0
EFECTIVO_Y_OFFSET = 3.0

# Nombre por defecto del informe final
DEFAULT_REPORT_NAME = "Informe_Completado.pdf"
