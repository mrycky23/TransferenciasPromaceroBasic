"""
wa_monitor.py
-------------
Monitor de WhatsApp Web usando Playwright con Chromium.
Detecta imágenes y archivos nuevos en el grupo de origen y los reenvía al grupo destino.

ESTRATEGIA DE REENVÍO:
  En lugar de usar el botón nativo "Reenviar" (frágil), el módulo:
  1. Detecta mensajes nuevos con media en el grupo origen.
  2. Hace clic en el mensaje para abrir el visor de medios.
  3. Descarga el archivo a una carpeta temporal local.
  4. Navega al grupo destino y sube el archivo descargado.
  Esto es más robusto y menos detectable como bot.
"""

import os
import time
import random
import threading
import tempfile
import shutil
import base64
from pathlib import Path
from typing import Callable, Optional

from modules.whatsapp_forwarder import forwarder_log as log
from modules.whatsapp_forwarder.config_manager import cargar_config

# Directorio de sesión persistente de Chromium (guarda el QR entre ejecuciones)
SESSION_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "wa_session")
SESSION_DIR = os.path.abspath(SESSION_DIR)

# Carpeta temporal para archivos descargados antes de reenviarlos
TEMP_MEDIA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "wa_temp_media")
TEMP_MEDIA_DIR = os.path.abspath(TEMP_MEDIA_DIR)

# Conjunto de IDs de mensajes ya procesados en esta sesión
_mensajes_procesados: set = set()


class WhatsAppMonitor:
    """
    Monitor de WhatsApp Web.
    Usa Playwright (Chromium) con contexto persistente para no requerir
    escaneo del QR en cada arranque (solo la primera vez).
    """

    def __init__(self, callback_estado: Optional[Callable[[str], None]] = None):
        """
        Args:
            callback_estado: Función llamada con mensajes de estado ("Activo", "Pausado", "Error", etc.)
                             para actualizar el ícono de la bandeja del sistema.
        """
        self._playwright = None
        self._context = None
        self._page = None
        self._corriendo = False
        self._pausado = False
        self._hilo: Optional[threading.Thread] = None
        self._callback_estado = callback_estado or (lambda msg: None)

        os.makedirs(SESSION_DIR, exist_ok=True)
        os.makedirs(TEMP_MEDIA_DIR, exist_ok=True)

    # ------------------------------------------------------------------
    # CONTROL PÚBLICO
    # ------------------------------------------------------------------

    def iniciar(self) -> None:
        """Lanza el monitor en un hilo daemon."""
        if self._corriendo:
            log.log_advertencia("Monitor ya está corriendo; ignorando llamada a iniciar().")
            return
        self._corriendo = True
        self._pausado = False
        self._hilo = threading.Thread(target=self._run, daemon=True, name="WAMonitorThread")
        self._hilo.start()
        log.log_info("Monitor iniciado en hilo separado.")

    def pausar(self) -> None:
        """Pausa el loop de monitoreo sin cerrar el navegador."""
        self._pausado = True
        self._callback_estado("Pausado")
        log.log_info("Monitor pausado.")

    def reanudar(self) -> None:
        """Reanuda el loop después de una pausa."""
        self._pausado = False
        self._callback_estado("Activo")
        log.log_info("Monitor reanudado.")

    def detener(self) -> None:
        """Detiene el monitor y cierra el navegador."""
        self._corriendo = False
        self._pausado = False
        self._cerrar_navegador()
        log.log_info("Monitor detenido.")

    def esta_corriendo(self) -> bool:
        return self._corriendo and not self._pausado

    # ------------------------------------------------------------------
    # HILO PRINCIPAL
    # ------------------------------------------------------------------

    def _run(self) -> None:
        """Lógica principal ejecutada en el hilo del monitor."""
        try:
            self._abrir_navegador()
            self._esperar_login()

            config = cargar_config()
            grupo_origen = config.get("grupo_origen", "").strip()
            grupo_destino = config.get("grupo_destino", "").strip()

            if not grupo_origen or not grupo_destino:
                log.log_error("Grupos no configurados. Abre la configuración desde la bandeja.")
                self._callback_estado("Sin configurar")
                return

            log.log_info(f"Navegando al grupo origen: '{grupo_origen}'")
            if not self._navegar_a_grupo(grupo_origen):
                log.log_error(f"No se encontró el grupo origen: '{grupo_origen}'")
                self._callback_estado("Error: grupo no encontrado")
                return

            self._callback_estado("Activo")
            log.log_info("Iniciando loop de monitoreo...")
            self._loop_monitoreo(grupo_origen, grupo_destino)

        except Exception as e:
            log.log_error(f"Error crítico en el monitor: {e}")
            self._callback_estado(f"Error: {str(e)[:40]}")
        finally:
            self._corriendo = False

    # ------------------------------------------------------------------
    # PLAYWRIGHT: INICIALIZACIÓN
    # ------------------------------------------------------------------

    def _abrir_navegador(self) -> None:
        """Lanza Chromium con contexto persistente para mantener la sesión de WhatsApp."""
        from playwright.sync_api import sync_playwright

        log.log_info(f"Abriendo Chromium con perfil en: {SESSION_DIR}")
        self._playwright = sync_playwright().start()
        self._context = self._playwright.chromium.launch_persistent_context(
            user_data_dir=SESSION_DIR,
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--start-maximized",
            ],
            no_viewport=True,
            accept_downloads=True,
        )
        # Usar la primera página si ya existe, o crear una nueva
        pages = self._context.pages
        self._page = pages[0] if pages else self._context.new_page()

        # Configurar carpeta de descargas en el contexto
        self._context.set_default_timeout(30_000)  # 30 segundos

    def _esperar_login(self) -> None:
        """
        Navega a WhatsApp Web y espera hasta que el usuario esté logueado.
        En la primera ejecución muestra el QR; en ejecuciones posteriores la sesión
        se carga automáticamente desde el perfil guardado.
        """
        log.log_info("Navegando a WhatsApp Web...")
        self._page.goto("https://web.whatsapp.com/", wait_until="domcontentloaded")

        log.log_info("Esperando que WhatsApp cargue (puede requerir escanear QR la primera vez)...")
        self._callback_estado("Esperando login...")

        # Esperar hasta que aparezca el panel lateral (señal de que ya estamos logueados)
        # Timeout extendido a 3 minutos para dar tiempo al escaneo del QR
        try:
            self._page.wait_for_selector(
                'div[data-testid="chat-list"]',
                timeout=180_000  # 3 minutos
            )
            log.log_info("Login detectado. WhatsApp Web listo.")
            self._callback_estado("Conectado")
        except Exception:
            # Intentar selector alternativo (WhatsApp cambia la UI periódicamente)
            try:
                self._page.wait_for_selector(
                    '#pane-side',
                    timeout=30_000
                )
                log.log_info("Login detectado (selector alternativo). WhatsApp Web listo.")
                self._callback_estado("Conectado")
            except Exception as e:
                raise RuntimeError(f"No se pudo detectar login en WhatsApp Web: {e}")

    def _cerrar_navegador(self) -> None:
        """Cierra el contexto y el playwright de forma segura."""
        try:
            if self._context:
                self._context.close()
        except Exception:
            pass
        try:
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass
        self._context = None
        self._page = None
        self._playwright = None

    # ------------------------------------------------------------------
    # PLAYWRIGHT: NAVEGACIÓN
    # ------------------------------------------------------------------

    def _navegar_a_grupo(self, nombre_grupo: str) -> bool:
        """
        Busca el grupo por nombre en la barra de búsqueda y abre la conversación.
        Devuelve True si tuvo éxito.
        """
        try:
            # Abrir buscador
            search_box = self._page.query_selector('div[data-testid="search-container"] div[contenteditable="true"]')
            if not search_box:
                # Selector alternativo
                search_box = self._page.query_selector('div[role="textbox"][title="Buscar"]')
            if not search_box:
                search_box = self._page.query_selector('div[role="textbox"]')

            if not search_box:
                log.log_error("No se encontró el cuadro de búsqueda de WhatsApp.")
                return False

            search_box.click()
            self._delay_humano(0.3, 0.6)
            search_box.fill("")
            self._escribir_como_humano(nombre_grupo)
            self._delay_humano(1.5, 2.5)

            # Esperar resultados y hacer clic en el grupo con nombre exacto
            resultado = self._page.query_selector(f'span[title="{nombre_grupo}"]')
            if not resultado:
                # Intentar clic en el primer resultado
                resultado = self._page.query_selector('div[data-testid="cell-frame-container"]')

            if resultado:
                resultado.click()
                self._delay_humano(1.0, 1.5)
                log.log_info(f"Grupo '{nombre_grupo}' abierto.")
                return True

            log.log_advertencia(f"No se encontró el grupo '{nombre_grupo}' en los resultados.")
            return False

        except Exception as e:
            log.log_error(f"Error navegando al grupo '{nombre_grupo}': {e}")
            return False

    # ------------------------------------------------------------------
    # LOOP PRINCIPAL DE MONITOREO
    # ------------------------------------------------------------------

    def _loop_monitoreo(self, grupo_origen: str, grupo_destino: str) -> None:
        """
        Loop continuo que detecta mensajes nuevos con media y los reenvía.
        Usa delays aleatorios para simular comportamiento humano.
        """
        log.log_info(f"Loop activo: '{grupo_origen}' → '{grupo_destino}'")

        while self._corriendo:
            # Respetar estado de pausa
            if self._pausado:
                time.sleep(1)
                continue

            # Recargar config por si el usuario la cambió
            config = cargar_config()
            if not config.get("activo", False):
                self._pausado = True
                self._callback_estado("Pausado (configuración)")
                time.sleep(2)
                continue

            try:
                mensajes_media = self._obtener_mensajes_media_nuevos()
                for msg_info in mensajes_media:
                    if not self._corriendo:
                        break
                    self._procesar_mensaje(msg_info, grupo_destino, grupo_origen)
                    self._delay_humano(2, 4)

            except Exception as e:
                log.log_error(f"Error en loop de monitoreo: {e}")
                self._callback_estado(f"Error temporal: {str(e)[:30]}")
                time.sleep(5)  # Esperar antes de reintentar
                # Intentar re-navegar al grupo origen
                try:
                    self._navegar_a_grupo(grupo_origen)
                    self._callback_estado("Activo")
                except Exception:
                    pass

            # Delay entre ciclos de verificación
            config = cargar_config()
            delay_min = config.get("delay_min_segundos", 2)
            delay_max = config.get("delay_max_segundos", 5)
            time.sleep(random.uniform(delay_min, delay_max))

    # ------------------------------------------------------------------
    # DETECCIÓN DE MENSAJES
    # ------------------------------------------------------------------

    def _obtener_mensajes_media_nuevos(self) -> list:
        """
        Escanea el DOM del grupo actual en busca de mensajes con imágenes o archivos
        que aún no hayan sido procesados.

        Devuelve una lista de dicts con información del mensaje:
          { "id": str, "tipo": "imagen"|"archivo", "element": Locator }
        """
        mensajes_media = []
        config = cargar_config()
        tipos_permitidos = config.get("tipos_permitidos", ["imagen", "archivo"])

        try:
            # Obtener todos los mensajes entrantes (recibidos, no enviados)
            # data-testid="msg-container" marca mensajes; los enviados tienen "message-out"
            contenedor_chat = self._page.query_selector('div[data-testid="conversation-panel-messages"]')
            if not contenedor_chat:
                contenedor_chat = self._page.query_selector('#main div[role="application"]')

            if not contenedor_chat:
                return []

            # --- IMÁGENES ---
            if "imagen" in tipos_permitidos:
                # Mensajes de imagen recibidos
                img_mensajes = self._page.query_selector_all(
                    'div.message-in img[src*="blob:"], div.message-in div[data-testid="media-url-provider"] img'
                )
                for el in img_mensajes:
                    try:
                        msg_id = el.get_attribute("src") or el.get_attribute("data-id") or str(id(el))
                        if msg_id not in _mensajes_procesados:
                            mensajes_media.append({
                                "id": msg_id,
                                "tipo": "imagen",
                                "element": el
                            })
                    except Exception:
                        continue

            # --- ARCHIVOS / DOCUMENTOS ---
            if "archivo" in tipos_permitidos:
                # Mensajes de documento/archivo recibidos
                doc_mensajes = self._page.query_selector_all(
                    'div.message-in div[data-testid="document-thumb"], '
                    'div.message-in span[data-testid="document-media-title"]'
                )
                for el in doc_mensajes:
                    try:
                        msg_id = el.inner_text() or str(id(el))
                        if msg_id not in _mensajes_procesados:
                            mensajes_media.append({
                                "id": msg_id,
                                "tipo": "archivo",
                                "element": el
                            })
                    except Exception:
                        continue

        except Exception as e:
            log.log_debug(f"Error obteniendo mensajes: {e}")

        return mensajes_media

    # ------------------------------------------------------------------
    # PROCESAMIENTO Y REENVÍO
    # ------------------------------------------------------------------

    def _procesar_mensaje(self, msg_info: dict, grupo_destino: str, grupo_origen: str) -> None:
        """
        Descarga el media del mensaje y lo envía al grupo destino.
        """
        msg_id = msg_info["id"]
        tipo = msg_info["tipo"]
        element = msg_info["element"]

        log.log_debug(f"Procesando mensaje id={msg_id[:40]} tipo={tipo}")

        # Marcar como procesado ANTES de descargarlo para evitar doble reenvío
        _mensajes_procesados.add(msg_id)

        ruta_descargada = None
        try:
            if tipo == "imagen":
                ruta_descargada = self._descargar_imagen_blob(element)
            elif tipo == "archivo":
                ruta_descargada = self._descargar_documento(element)

            if not ruta_descargada or not os.path.exists(ruta_descargada):
                log.log_advertencia(f"No se pudo obtener el archivo del mensaje {msg_id[:20]}")
                return

            nombre_archivo = os.path.basename(ruta_descargada)
            exito = self._enviar_archivo_a_grupo(ruta_descargada, grupo_destino)

            if exito:
                log.log_reenvio_exitoso(tipo, nombre_archivo, grupo_origen, grupo_destino)
            else:
                log.log_reenvio_error(tipo, nombre_archivo, "Fallo al enviar al grupo destino")
                # Re-navegar al grupo origen para el próximo ciclo
                self._navegar_a_grupo(grupo_origen)

        except Exception as e:
            log.log_reenvio_error(tipo, msg_id[:30], str(e))
        finally:
            # Limpiar archivo temporal
            if ruta_descargada and os.path.exists(ruta_descargada):
                try:
                    os.remove(ruta_descargada)
                except Exception:
                    pass
            # Regresar al grupo origen
            try:
                self._navegar_a_grupo(grupo_origen)
            except Exception:
                pass

    def _descargar_imagen_blob(self, img_element) -> Optional[str]:
        """
        Descarga una imagen con src blob: usando JavaScript canvas.
        Devuelve la ruta al archivo PNG temporal.
        """
        try:
            src = img_element.get_attribute("src")
            if not src:
                return None

            # Usar JS para convertir la imagen blob a base64
            b64 = self._page.evaluate("""
                async (src) => {
                    const response = await fetch(src);
                    const blob = await response.blob();
                    return new Promise((resolve) => {
                        const reader = new FileReader();
                        reader.onloadend = () => resolve(reader.result);
                        reader.readAsDataURL(blob);
                    });
                }
            """, src)

            if not b64 or "," not in b64:
                return None

            # Decodificar base64
            header, data = b64.split(",", 1)
            ext = "png"
            if "jpeg" in header or "jpg" in header:
                ext = "jpg"
            elif "webp" in header:
                ext = "webp"

            nombre = f"wa_img_{int(time.time())}_{random.randint(1000,9999)}.{ext}"
            ruta = os.path.join(TEMP_MEDIA_DIR, nombre)
            with open(ruta, "wb") as f:
                f.write(base64.b64decode(data))

            log.log_debug(f"Imagen descargada: {ruta} ({os.path.getsize(ruta)} bytes)")
            return ruta

        except Exception as e:
            log.log_debug(f"Error descargando imagen blob: {e}")
            return None

    def _descargar_documento(self, doc_element) -> Optional[str]:
        """
        Descarga un documento/archivo haciendo clic en él y capturando la descarga.
        Devuelve la ruta al archivo temporal.
        """
        try:
            # Buscar el botón de descarga del documento (subir desde el elemento)
            # Playwright permite capturar el evento download antes de hacer clic
            with self._page.expect_download(timeout=15_000) as download_info:
                # Intentar hacer clic en el botón de descarga del documento
                parent = doc_element
                for _ in range(5):
                    try:
                        dl_btn = parent.query_selector('[data-testid="download"]')
                        if dl_btn:
                            dl_btn.click()
                            break
                    except Exception:
                        pass
                    parent = parent.evaluate_handle("el => el.parentElement")
                else:
                    # Hacer clic en el propio elemento del documento
                    doc_element.click()

            download = download_info.value
            nombre_original = download.suggested_filename or f"archivo_{int(time.time())}"
            ruta = os.path.join(TEMP_MEDIA_DIR, nombre_original)
            download.save_as(ruta)
            log.log_debug(f"Documento descargado: {ruta}")
            return ruta

        except Exception as e:
            log.log_debug(f"Error descargando documento: {e}")
            return None

    # ------------------------------------------------------------------
    # ENVÍO AL GRUPO DESTINO
    # ------------------------------------------------------------------

    def _enviar_archivo_a_grupo(self, ruta_archivo: str, nombre_grupo: str) -> bool:
        """
        Navega al grupo destino y sube el archivo usando el input de adjuntos de WhatsApp Web.
        Devuelve True si el envío tuvo éxito.
        """
        try:
            if not self._navegar_a_grupo(nombre_grupo):
                return False

            self._delay_humano(1.0, 2.0)

            # Buscar el botón de adjuntar archivo (clip)
            attach_btn = self._page.query_selector('div[data-testid="clip"]')
            if not attach_btn:
                attach_btn = self._page.query_selector('span[data-testid="clip"]')

            if not attach_btn:
                log.log_error("No se encontró el botón de adjuntar en WhatsApp Web.")
                return False

            attach_btn.click()
            self._delay_humano(0.5, 1.0)

            # Seleccionar el input de archivo "Photos & Videos" o "Document"
            ext = Path(ruta_archivo).suffix.lower()
            es_imagen = ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")

            if es_imagen:
                # Input para imágenes
                file_input = self._page.query_selector('input[accept*="image"]')
            else:
                # Input para documentos
                file_input = self._page.query_selector('input[accept*="pdf"], input[type="file"]')

            if not file_input:
                # Intentar con el input genérico de archivo
                file_input = self._page.query_selector('input[type="file"]')

            if not file_input:
                log.log_error("No se encontró el input de archivo en WhatsApp Web.")
                return False

            file_input.set_input_files(ruta_archivo)
            self._delay_humano(1.5, 2.5)

            # Presionar Enter o hacer clic en el botón Enviar
            send_btn = self._page.query_selector('div[data-testid="send"]')
            if not send_btn:
                send_btn = self._page.query_selector('span[data-testid="send"]')

            if send_btn:
                send_btn.click()
            else:
                self._page.keyboard.press("Enter")

            self._delay_humano(2.0, 3.0)
            log.log_debug(f"Archivo '{os.path.basename(ruta_archivo)}' enviado al grupo '{nombre_grupo}'.")
            return True

        except Exception as e:
            log.log_error(f"Error enviando archivo al grupo '{nombre_grupo}': {e}")
            return False

    # ------------------------------------------------------------------
    # UTILIDADES
    # ------------------------------------------------------------------

    def _delay_humano(self, min_seg: float = 0.5, max_seg: float = 1.5) -> None:
        """Espera un tiempo aleatorio para simular comportamiento humano."""
        time.sleep(random.uniform(min_seg, max_seg))

    def _escribir_como_humano(self, texto: str) -> None:
        """Escribe texto carácter por carácter con delays variables para evadir detección."""
        for char in texto:
            self._page.keyboard.type(char)
            time.sleep(random.uniform(0.05, 0.15))
