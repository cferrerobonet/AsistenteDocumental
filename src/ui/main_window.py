"""
Ventana principal de la aplicación (PyQt6, aspecto de Partes de salida).

Tres pasos en tarjetas: 1 · iniciar sesión en SharePoint, 2 · elegir la carpeta
de destino y el archivo de datos, 3 · procesar (barra de progreso, Cancelar y
Procesar archivos). Arriba, la barra con «Novedades», «Buscar actualizaciones» y
el aviso dorado de versión nueva.

Hilos: el procesamiento (Excel, carpetas y descargas) va en un QThread y habla
con la interfaz solo por señales (`estado_cambiado`, `mensaje`); el navegador se
abre y se captura en hilos de `inicio_sesion.py`. La interfaz nunca se congela.
"""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QGuiApplication
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from config.app_config import UI_CONFIG
from src import NOMBRE_APP, __version__
from src.logger_config import get_logger
from src.ui import estilo
from src.ui.componentes import (
    AvisoFlotante,
    avisar,
    boton,
    error,
    etiqueta,
    informar,
    poner_propiedad,
    preguntar,
)

logger = get_logger(__name__)

ALLOW_SIMULATION = os.environ.get('EPLA_ALLOW_SIMULATION', '').strip().lower() in ('1', 'true', 'yes')
SHAREPOINT_URL = "https://epluisamigogodella-my.sharepoint.com"
TEXTO_BOTON_SESION = "Iniciar sesión en SharePoint"

# Importar los módulos de procesamiento
try:
    from src.excel_processor import create_excel_processor
    from src.file_downloader import FileDownloader
    from src.folder_manager import create_folder_manager
except ImportError as e:
    if ALLOW_SIMULATION:
        logger.warning("Dependencias no disponibles: %s", e)
        logger.warning("Modo simulación activado por EPLA_ALLOW_SIMULATION")
        FileDownloader = None
        create_excel_processor = None
        create_folder_manager = None
    else:
        logger.critical(
            "Faltan dependencias críticas (%s). "
            "Para desarrollo, puede activar simulación con EPLA_ALLOW_SIMULATION=1",
            e,
        )
        raise


class _HiloProceso(QThread):
    """Ejecuta `MainWindow.process_files` fuera de la interfaz."""

    def __init__(self, ventana: MainWindow):
        super().__init__()
        self._ventana = ventana

    def run(self):
        self._ventana.process_files()


class MainWindow(QMainWindow):
    """Ventana principal de la aplicación"""

    #: (texto, porcentaje) desde el hilo de proceso
    estado_cambiado = pyqtSignal(str, float)
    #: (tipo «info»/«error», título, texto) desde el hilo de proceso
    mensaje = pyqtSignal(str, str, str)

    def __init__(self):
        super().__init__()
        self.destination_folder = ""
        self.excel_file = ""
        self.is_authenticated = False

        # Inicializar componentes
        self.auth_manager = None
        self.excel_processor = None
        self.file_downloader = None
        self.folder_manager = None

        # Control de procesamiento
        self.processing_thread: _HiloProceso | None = None
        self.cancel_processing_flag = False
        self.processing_result = 'idle'
        self._cerrar_al_terminar = False
        self._actualizacion: tuple[str, str, str] | None = None

        self.setup_window()
        self.create_widgets()
        self.estado_cambiado.connect(self._aplicar_estado)
        self.mensaje.connect(self._mostrar_mensaje)

    # ------------------------------------------------------------------
    # Construcción
    # ------------------------------------------------------------------
    def setup_window(self):
        """Configuración inicial de la ventana"""
        self.setWindowTitle(UI_CONFIG.get("window_title") or NOMBRE_APP)
        self.setWindowIcon(estilo.icono_app())
        self.resize(780, 720)
        self.setMinimumSize(700, 660)
        self.center_window()

    def center_window(self):
        """Centrar la ventana en la pantalla"""
        pantalla = QGuiApplication.primaryScreen()
        if pantalla is not None:
            centro = pantalla.availableGeometry().center()
            self.move(centro.x() - self.width() // 2, centro.y() - self.height() // 2)

    def create_widgets(self):
        """Crear todos los widgets de la interfaz"""
        raiz = QWidget()
        raiz.setObjectName("raiz")
        self.setCentralWidget(raiz)
        vertical = QVBoxLayout(raiz)
        vertical.setContentsMargins(0, 0, 0, 0)
        vertical.setSpacing(0)
        vertical.addWidget(self.create_header())

        cuerpo = QVBoxLayout()
        cuerpo.setContentsMargins(24, 18, 24, 20)
        cuerpo.setSpacing(14)
        titulo = QLabel("Documentación de las solicitudes de título")
        titulo.setFont(estilo.fuente(26, QFont.Weight.Bold, estilo.TITULAR))
        cuerpo.addWidget(titulo)
        cuerpo.addWidget(etiqueta(
            "Descarga los archivos de cada solicitud y los ordena en carpetas por ciclo y alumno.",
            "muted", envolver=True))
        cuerpo.addSpacing(2)
        cuerpo.addWidget(self.create_auth_section())
        cuerpo.addWidget(self.create_file_selection_section())
        cuerpo.addWidget(self.create_progress_section(), 1)
        vertical.addLayout(cuerpo, 1)
        self.aviso = AvisoFlotante(raiz, arriba=64)

    def create_header(self) -> QWidget:
        """Barra superior: escudo, nombre, novedades y actualizaciones."""
        barra = QWidget()
        barra.setObjectName("barra")
        barra.setStyleSheet(
            f"#barra {{ background: {estilo.T['surface2']}; border-bottom: 1px solid {estilo.T['line']}; }}"
        )
        fila = QHBoxLayout(barra)
        fila.setContentsMargins(16, 9, 12, 9)
        fila.setSpacing(10)
        logo = QLabel()
        logo.setPixmap(estilo.escudo(34))
        fila.addWidget(logo)
        titulo = QLabel("Asistente de Documentación")
        titulo.setFont(estilo.fuente(19, QFont.Weight.Bold, estilo.TITULAR))
        titulo.setMinimumWidth(titulo.sizeHint().width())
        fila.addWidget(titulo)
        self.subtitulo = etiqueta(f"v{__version__}", "muted")
        self.subtitulo.setMinimumWidth(10)
        fila.addWidget(self.subtitulo, 1)
        # Aviso de versión nueva: dorado y bien visible; abre el diálogo de actualizar.
        self.boton_actualizar = boton("", pequeno=True, dorado=True)
        self.boton_actualizar.hide()
        self.boton_actualizar.clicked.connect(self._ofrecer_actualizacion)
        fila.addWidget(self.boton_actualizar)
        self.boton_novedades = boton("Novedades", pequeno=True)
        self.boton_novedades.setToolTip("Qué ha cambiado en esta versión")
        self.boton_novedades.clicked.connect(lambda: self.mostrar_novedades())
        fila.addWidget(self.boton_novedades)
        self.boton_buscar_actualizaciones = boton("Buscar actualizaciones", pequeno=True)
        self.boton_buscar_actualizaciones.setToolTip("Comprobar ahora si hay una versión nueva")
        self.boton_buscar_actualizaciones.clicked.connect(lambda: self.buscar_actualizaciones(manual=True))
        fila.addWidget(self.boton_buscar_actualizaciones)
        return barra

    def _tarjeta(self, numero: int, titulo: str, explicacion: str) -> tuple[QFrame, QVBoxLayout, QLabel]:
        caja = QFrame()
        caja.setProperty("rol", "caja")
        capa = QVBoxLayout(caja)
        capa.setContentsMargins(18, 14, 18, 16)
        capa.setSpacing(10)
        cabecera = QHBoxLayout()
        cabecera.setSpacing(12)
        paso = QLabel(str(numero))
        paso.setProperty("rol", "paso")
        paso.setFixedSize(28, 28)
        paso.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cabecera.addWidget(paso, 0, Qt.AlignmentFlag.AlignTop)
        textos = QVBoxLayout()
        textos.setSpacing(1)
        t = QLabel(titulo)
        t.setFont(estilo.fuente(19, QFont.Weight.Bold, estilo.TITULAR))
        textos.addWidget(t)
        textos.addWidget(etiqueta(explicacion, "muted", envolver=True))
        cabecera.addLayout(textos, 1)
        capa.addLayout(cabecera)
        return caja, capa, paso

    def create_auth_section(self) -> QFrame:
        """Paso 1: autenticación con navegador"""
        caja, capa, self.paso_sesion = self._tarjeta(
            1, "Iniciar sesión", "Se abre Edge y se entra en SharePoint con la cuenta de secretaría.")
        fila = QHBoxLayout()
        fila.setContentsMargins(40, 0, 0, 0)
        self.auth_status = etiqueta("Estado: No autenticado", "estado", envolver=True)
        fila.addWidget(self.auth_status, 1)
        self.auth_button = boton(TEXTO_BOTON_SESION, primario=True)
        self.auth_button.clicked.connect(self.authenticate_browser)
        fila.addWidget(self.auth_button)
        capa.addLayout(fila)
        return caja

    def _fila_archivo(self, rotulo: str, accion) -> tuple[QVBoxLayout, QLineEdit, QWidget]:
        bloque = QVBoxLayout()
        bloque.setSpacing(5)
        bloque.addWidget(etiqueta(rotulo, "etiqueta"))
        fila = QHBoxLayout()
        campo = QLineEdit()
        campo.setReadOnly(True)
        campo.setPlaceholderText("Sin elegir")
        fila.addWidget(campo, 1)
        elegir = boton("Seleccionar…")
        elegir.clicked.connect(accion)
        fila.addWidget(elegir)
        bloque.addLayout(fila)
        return bloque, campo, elegir

    def create_file_selection_section(self) -> QFrame:
        """Paso 2: selección de archivos"""
        caja, capa, self.paso_archivos = self._tarjeta(
            2, "Elegir los archivos", "Dónde se guardan las carpetas y la exportación de Microsoft Forms.")
        cuerpo = QVBoxLayout()
        cuerpo.setContentsMargins(40, 0, 0, 0)
        cuerpo.setSpacing(10)
        bloque, self.dest_entry, self.dest_button = self._fila_archivo(
            "Carpeta de destino", self.select_destination_folder)
        cuerpo.addLayout(bloque)
        bloque, self.excel_entry, self.excel_button = self._fila_archivo(
            "Archivo de datos · Excel o CSV", self.select_excel_file)
        cuerpo.addLayout(bloque)
        capa.addLayout(cuerpo)
        return caja

    def create_progress_section(self) -> QFrame:
        """Paso 3: progreso y botones de acción"""
        caja, capa, self.paso_proceso = self._tarjeta(
            3, "Procesar", "Crea las carpetas y descarga los archivos de cada alumno.")
        cuerpo = QVBoxLayout()
        cuerpo.setContentsMargins(40, 0, 0, 0)
        cuerpo.setSpacing(8)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        cuerpo.addWidget(self.progress_bar)
        self.status_label = etiqueta("Listo para procesar...", "estado", envolver=True)
        cuerpo.addWidget(self.status_label)
        capa.addLayout(cuerpo)
        capa.addStretch(1)
        self.create_action_buttons(capa)
        return caja

    def create_action_buttons(self, capa: QVBoxLayout):
        """Botones principales: Cancelar y Procesar archivos"""
        fila = QHBoxLayout()
        fila.addStretch(1)
        self.cancel_button = boton("Cancelar")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_processing)
        fila.addWidget(self.cancel_button)
        self.process_button = boton("Procesar archivos", primario=True, grande=True)
        self.process_button.setEnabled(False)
        self.process_button.clicked.connect(self.start_processing)
        fila.addWidget(self.process_button)
        capa.addLayout(fila)

    # ------------------------------------------------------------------
    # Autenticación
    # ------------------------------------------------------------------
    def _estado_sesion(self, texto: str, tipo: str = "") -> None:
        self.auth_status.setText(texto)
        poner_propiedad(self.auth_status, "estado", tipo)

    def authenticate_browser(self):
        """Autenticación usando navegador automatizado (Selenium)"""
        self._estado_sesion("Estado: Iniciando autenticación...", "curso")
        self.auth_button.setEnabled(False)
        self.auth_button.setText("Iniciando...")

        try:
            # Importar el sistema de autenticación con Selenium
            try:
                from src.auth_selenium import SeleniumBrowserAuth
                logger.info("Sistema de autenticación Selenium cargado")
            except ImportError as e:
                error(self, "Error de Configuración", "No se pudo cargar Selenium.",
                      f"{e}\n\nInstala con: pip install selenium")
                self._restaurar_boton_sesion()
                self._estado_sesion("Estado: Error de configuración", "error")
                return

            # Crear gestor de autenticación y abrir la ventana de inicio de sesión
            self.auth_manager = SeleniumBrowserAuth(SHAREPOINT_URL)
            self.auth_manager.authenticate(callback=self._handle_browser_auth_completion, padre=self)

        except Exception as e:
            self._estado_sesion("Estado: Error de autenticación", "error")
            error(self, "Error", "Error durante la autenticación.", str(e))
            logger.exception("Error de autenticación en navegador: %s", e)
            self._restaurar_boton_sesion()

    def _restaurar_boton_sesion(self) -> None:
        self.auth_button.setEnabled(True)
        self.auth_button.setText(TEXTO_BOTON_SESION)

    def _nombre_usuario(self) -> str:
        am = self.auth_manager
        if am is None:
            return ""
        if hasattr(am, 'get_user_info'):
            info = am.get_user_info() or {}
            return info.get('displayName', '')
        info = getattr(am, 'user_info', None) or {}
        return info.get('displayName', '') if isinstance(info, dict) else ''

    def _handle_browser_auth_completion(self, success: bool, message: str):
        """Manejar la finalización de la autenticación con navegador"""
        if success:
            self.is_authenticated = True
            nombre = self._nombre_usuario()
            texto = f"Estado: Autenticado como {nombre}" if nombre and nombre != "Usuario" else \
                "Estado: Autenticado correctamente"
            self._estado_sesion(texto, "ok")
            self.auth_button.setText("Sesión iniciada")
            self.auth_button.setEnabled(False)
            poner_propiedad(self.paso_sesion, "hecho", True)
            self.aviso.mostrar(
                "Sesión iniciada. Elige la carpeta de destino y el archivo de datos y pulsa «Procesar archivos».")
            self.check_ready_to_process()
            return

        cancelada = "cancelada" in (message or "").lower()
        self._estado_sesion("Estado: Autenticación cancelada" if cancelada else "Estado: Error de autenticación",
                            "" if cancelada else "error")
        self._restaurar_boton_sesion()
        # La falta de credenciales ya se ha contado al intentarlo; cancelar no es un error.
        if not cancelada and "credenciales" not in (message or "").lower():
            error(
                self,
                "Error de Autenticación",
                "No se pudo completar la autenticación.",
                f"Detalles: {message}\n\n"
                "Asegúrate de:\n"
                "• Haber iniciado sesión en SharePoint\n"
                "• Esperar a llegar a OneDrive antes de capturar la sesión\n"
                "• Estar usando el mismo navegador\n\n"
                "Intenta de nuevo si es necesario.",
            )

    # ------------------------------------------------------------------
    # Archivos
    # ------------------------------------------------------------------
    def select_destination_folder(self):
        """Seleccionar carpeta de destino"""
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de destino", self.destination_folder)
        if folder:
            self.destination_folder = folder
            self.dest_entry.setText(folder)
            self.check_ready_to_process()

    def select_excel_file(self):
        """Seleccionar archivo Excel"""
        file, _filtro = QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo de datos",
            os.path.dirname(self.excel_file) if self.excel_file else "",
            "Archivos de datos (*.xlsx *.xls *.csv);;Todos los archivos (*)",
        )
        if file:
            self.excel_file = file
            self.excel_entry.setText(file)
            self.check_ready_to_process()

    def check_ready_to_process(self):
        """Verificar si está listo para procesar"""
        poner_propiedad(self.paso_archivos, "hecho", bool(self.destination_folder and self.excel_file))
        listo = bool(self.is_authenticated and self.destination_folder and self.excel_file)
        self.process_button.setEnabled(listo and not self._procesando())

    # ------------------------------------------------------------------
    # Procesamiento
    # ------------------------------------------------------------------
    def _procesando(self) -> bool:
        return self.processing_thread is not None and self.processing_thread.isRunning()

    def _bloquear_entradas(self, bloquear: bool) -> None:
        for b in (self.dest_button, self.excel_button):
            b.setEnabled(not bloquear)

    def start_processing(self):
        """Iniciar el procesamiento"""
        if self._procesando():
            avisar(self, "Procesamiento en curso", "Ya hay un procesamiento en marcha")
            return

        self.process_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self._bloquear_entradas(True)
        self.progress_bar.setValue(0)
        self._aplicar_estado("Iniciando procesamiento...", 0)
        poner_propiedad(self.paso_proceso, "hecho", False)
        self.cancel_processing_flag = False
        self.processing_result = 'running'

        # Iniciar procesamiento en hilo separado
        self.processing_thread = _HiloProceso(self)
        self.processing_thread.finished.connect(self.processing_complete)
        self.processing_thread.start()

    def process_files(self):
        """Procesar archivos de forma completa (se ejecuta en el hilo de proceso)"""
        outcome = 'error'
        try:
            # Paso 1: Cargar y procesar Excel
            self.update_status("Analizando archivo Excel...", 10)

            if not self.excel_processor:
                try:
                    self.excel_processor = create_excel_processor()
                except Exception:
                    self.excel_processor = None
                    logger.warning("Excel processor no disponible, usando modo simulación")

            if self.excel_processor:
                # Cargar archivo Excel
                success = self.excel_processor.load_excel(self.excel_file)
                if not success:
                    raise Exception("No se pudo cargar el archivo Excel")

                # Detectar columnas automáticamente
                self.excel_processor.detect_columns()

                # Validar datos
                validation_warnings = self.excel_processor.validate_data()
                if validation_warnings:
                    logger.warning("Advertencias en los datos: %s", validation_warnings)

                # Obtener datos procesados
                students_data = self.excel_processor.get_processed_data()

            else:
                # Datos simulados para pruebas
                students_data = self.create_sample_data()

            if self.cancel_processing_flag:
                self.update_status("Procesamiento cancelado", 0)
                outcome = 'cancelled'
                return

            self.update_status(f"Excel procesado: {len(students_data)} estudiantes encontrados", 20)

            # Paso 2: Crear estructura de carpetas
            self.update_status("Creando estructura de carpetas...", 30)

            # Si se ha cambiado de carpeta de destino, gestor nuevo (antes se
            # reutilizaba el primero y se seguía escribiendo en la carpeta anterior).
            if not self.folder_manager or self.folder_manager.base_path != os.path.abspath(self.destination_folder):
                self.folder_manager = create_folder_manager(self.destination_folder)

            structure_info = self.folder_manager.create_folder_structure(students_data)

            if structure_info['errors']:
                logger.warning("Errores creando carpetas: %s", structure_info['errors'])

            if self.cancel_processing_flag:
                self.update_status("Procesamiento cancelado", 0)
                outcome = 'cancelled'
                return

            self.update_status(f"Carpetas creadas: {structure_info['student_folders_created']} estudiantes, "
                               f"{structure_info['stages_created']} etapas", 50)

            # Paso 3: Preparar descargas
            downloads_to_process = []
            for student in students_data:
                student_folder = self.folder_manager.get_student_folder_path(student)

                for url_info in student.get('urls', []):
                    downloads_to_process.append({
                        'url': url_info['url'],
                        'destination_path': student_folder,
                        'filename': url_info.get('filename'),
                        'student': student
                    })

            if not downloads_to_process:
                raise Exception("No se encontraron URLs para descargar en el archivo Excel")

            self.update_status(f"Preparando {len(downloads_to_process)} descargas...", 60)

            # Paso 4: Descargar archivos
            if not self.file_downloader:
                try:
                    if FileDownloader:
                        self.file_downloader = FileDownloader(self.auth_manager, self.download_progress_callback)
                        logger.info("FileDownloader creado correctamente")
                    else:
                        logger.warning("Clase FileDownloader no disponible")
                        self.file_downloader = None
                except Exception as e:
                    self.file_downloader = None
                    logger.exception("Error creando FileDownloader: %s", e)

            if self.file_downloader:
                # Descargas reales
                download_results = []
                for i, download_info in enumerate(downloads_to_process):
                    if self.cancel_processing_flag:
                        break

                    progress = 60 + ((i / len(downloads_to_process)) * 35)
                    self.update_status(f"Descargando archivo {i+1}/{len(downloads_to_process)}...", progress)

                    result = self.file_downloader.download_file(
                        download_info['url'],
                        download_info['destination_path'],
                        download_info['filename']
                    )
                    download_results.append(result)

            else:
                # Simular descargas
                download_results = self.simulate_downloads(downloads_to_process)

            if self.cancel_processing_flag:
                self.update_status("Procesamiento cancelado", 0)
                outcome = 'cancelled'
                return

            # Resumen final
            successful_downloads = sum(1 for r in download_results if r.get('success', False))
            failed_downloads = len(download_results) - successful_downloads

            self.update_status("Procesamiento completado exitosamente", 100)

            summary_message = (
                f"Estudiantes procesados: {len(students_data)}\n"
                f"Carpetas creadas: {structure_info['student_folders_created']}\n"
                f"Descargas correctas: {successful_downloads}\n"
                f"Descargas fallidas: {failed_downloads}\n\n"
                f"Archivos organizados en: {self.destination_folder}"
            )
            self.mensaje.emit("info", "¡Procesamiento completado!", summary_message)
            outcome = 'success'

        except Exception as e:
            error_msg = f"Error durante el procesamiento: {str(e)}"
            logger.exception(error_msg)
            self.update_status(f"Error: {str(e)}", 0)
            self.mensaje.emit("error", "Error", error_msg)
            outcome = 'error'

        finally:
            self.processing_result = outcome

    def create_sample_data(self):
        """Crear datos de ejemplo para pruebas (ficticios)"""
        return [
            {
                'index': 1,
                'primer_apellido': 'GARCÍA',
                'segundo_apellido': 'EJEMPLO',
                'nombre': 'ANA',
                'etapa': 'GESTION ADMINISTRATIVA',
                'curso': '2º',
                'urls': [
                    {'url': 'https://example.com/file1.pdf', 'filename': 'documento1.pdf'},
                    {'url': 'https://example.com/file2.docx', 'filename': 'tarea1.docx'}
                ]
            },
            {
                'index': 2,
                'primer_apellido': 'LÓPEZ',
                'segundo_apellido': 'PRUEBA',
                'nombre': 'PABLO',
                'etapa': 'CARROCERIA',
                'curso': '2º',
                'urls': [
                    {'url': 'https://example.com/file3.pdf', 'filename': 'proyecto.pdf'}
                ]
            },
        ]

    def simulate_downloads(self, downloads_to_process):
        """Simular descargas para pruebas"""
        import random
        import time

        results = []
        for i, download_info in enumerate(downloads_to_process):
            if self.cancel_processing_flag:
                break

            # Simular tiempo de descarga
            time.sleep(0.5)

            # Simular éxito/fallo (90% éxito)
            success = random.random() > 0.1  # nosec B311 - solo simulación

            result = {
                'success': success,
                'url': download_info['url'],
                'destination_path': download_info['destination_path'],
                'filename': download_info.get('filename') or f'archivo_{i}.bin',
                'file_size': random.randint(1000, 1000000) if success else 0,  # nosec B311
                'error': None if success else "Simulación de error"
            }

            # Crear archivo vacío para la simulación
            if success:
                try:
                    os.makedirs(download_info['destination_path'], exist_ok=True)
                    file_path = os.path.join(download_info['destination_path'], result['filename'])
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(f"Archivo simulado: {result['filename']}")
                    result['file_path'] = file_path
                except OSError:
                    result['success'] = False
                    result['error'] = "Error creando archivo simulado"

            results.append(result)

            progress = 60 + ((i / len(downloads_to_process)) * 35)
            self.update_status(f"Simulando descarga {i+1}/{len(downloads_to_process)}...", progress)

        return results

    def download_progress_callback(self, progress, current, total, message=""):
        """Callback para progreso de descarga individual (sin uso por ahora)"""
        pass

    def update_status(self, message, progress):
        """Actualizar estado y progreso de forma segura desde cualquier hilo"""
        self.estado_cambiado.emit(str(message), float(progress))

    def _aplicar_estado(self, message: str, progress: float) -> None:
        self.status_label.setText(message)
        self.progress_bar.setValue(int(round(progress)))
        tipo = "curso"
        if message.startswith("Error"):
            tipo = "error"
        elif progress >= 100:
            tipo = "ok"
        poner_propiedad(self.status_label, "estado", tipo)

    def _mostrar_mensaje(self, tipo: str, titulo: str, texto: str) -> None:
        if tipo == "error":
            error(self, titulo, texto)
        else:
            informar(self, titulo, titulo, texto)

    def processing_complete(self):
        """Completar el procesamiento (en el hilo de la interfaz)"""
        self.cancel_button.setEnabled(False)
        self._bloquear_entradas(False)
        self.check_ready_to_process()

        if self.processing_result == 'success':
            self.progress_bar.setValue(100)
            self.status_label.setText("Procesamiento completado exitosamente")
            poner_propiedad(self.status_label, "estado", "ok")
            poner_propiedad(self.paso_proceso, "hecho", True)
        elif self.processing_result == 'cancelled':
            self.status_label.setText("Procesamiento cancelado")
            poner_propiedad(self.status_label, "estado", "")
        else:
            self.status_label.setText("Procesamiento finalizado con errores")
            poner_propiedad(self.status_label, "estado", "error")

        if self._cerrar_al_terminar:
            self.close()

    def cancel_processing(self):
        """Cancelar el procesamiento: se detiene en el siguiente punto de verificación"""
        self.cancel_processing_flag = True
        self.cancel_button.setEnabled(False)
        self.status_label.setText("Cancelando procesamiento...")
        poner_propiedad(self.status_label, "estado", "curso")

    # ------------------------------------------------------------------
    # Novedades y actualizaciones
    # ------------------------------------------------------------------
    def mostrar_novedades(self, versiones=None) -> None:
        """Abre la ventana de novedades (por defecto, las de la versión instalada)."""
        from src import novedades
        from src.ui.novedades import VentanaNovedades

        if versiones is None:
            propia = novedades.de_la_version(__version__)
            versiones = [propia] if propia else novedades.cargar()[:1]
        VentanaNovedades(versiones, self).exec()
        novedades.marcar_vistas(__version__)

    def mostrar_novedades_si_toca(self) -> bool:
        """La primera vez que se abre una versión nueva, sus novedades. Devuelve si las ha enseñado."""
        from src import novedades

        pendientes = novedades.pendientes(__version__)
        if not pendientes:
            novedades.marcar_vistas(__version__)
            return False
        self.mostrar_novedades(pendientes)
        return True

    def buscar_actualizaciones(self, manual: bool = False) -> None:
        from src.ui.dialogos import buscar_actualizaciones

        buscar_actualizaciones(self, avisar_si_al_dia=manual, al_encontrar=self.actualizacion_disponible)

    def actualizacion_disponible(self, version: str, url: str, notas: str) -> None:
        """Hay versión nueva: botón dorado fijo y, la primera vez, el diálogo."""
        nueva = self._actualizacion is None or self._actualizacion[0] != version
        self._actualizacion = (version, url, notas)
        self.boton_actualizar.setText(f"↑  Actualizar a {version}")
        self.boton_actualizar.setToolTip("Hay una versión nueva de la aplicación")
        self.boton_actualizar.show()
        if nueva and self.isVisible():
            self._ofrecer_actualizacion()

    def _ofrecer_actualizacion(self) -> None:
        from src.ui import dialogos

        if self._actualizacion:
            dialogos.ofrecer(self, *self._actualizacion)

    # ------------------------------------------------------------------
    # Ventana
    # ------------------------------------------------------------------
    def closeEvent(self, evento):  # noqa: N802
        if self._procesando():
            if self._cerrar_al_terminar or not preguntar(
                self,
                "Proceso en marcha",
                "Hay un proceso en marcha. ¿Cancelarlo y cerrar el asistente?",
                "Cancelar y cerrar",
                "Seguir procesando",
                "Se detiene al terminar el archivo que se está descargando.",
            ):
                evento.ignore()
                return
            self._cerrar_al_terminar = True
            self.cancel_processing()
            self.status_label.setText("Cancelando… el asistente se cerrará al terminar el archivo en curso.")
            evento.ignore()
            return
        # El navegador automatizado no se queda abierto huérfano.
        cerrar = getattr(self.auth_manager, "cerrar_navegador", None)
        if callable(cerrar) and getattr(self.auth_manager, "driver", None):
            try:
                cerrar()
            except Exception as e:  # noqa: BLE001
                logger.debug("No se pudo cerrar el navegador al salir: %s", e)
        evento.accept()

    def acerca_de(self) -> str:
        return f"{NOMBRE_APP} {__version__}"

    def run(self):
        """Ejecutar la aplicación (compatibilidad con la 3.x)"""
        self.show()
        return QApplication.instance().exec()
