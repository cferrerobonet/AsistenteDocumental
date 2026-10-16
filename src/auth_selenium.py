"""
Autenticacion con SharePoint usando Selenium
Navegador automatizado que captura cookies de forma confiable
"""

import sys
import os

# Configurar encoding solo si hay stdout disponible (no en ejecutables --windowed).
# Se reconfigura el mismo objeto en vez de envolverlo en otro TextIOWrapper: el
# envoltorio nuevo cerraba la salida al recogerse el viejo (y rompía pytest).
if sys.stdout is not None and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError, OSError):
        pass  # Ignorar si falla

# Si no hay stdout (ejecutable --windowed), redirigir a null
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w', encoding='utf-8')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w', encoding='utf-8')

import time
import threading
from typing import Optional, Callable
import requests
from selenium import webdriver
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service

try:
    from src.logger_config import get_logger
except ImportError:
    from logger_config import get_logger

try:
    from src.secret_store import load_auto_login_credentials
except ImportError:
    from secret_store import load_auto_login_credentials

logger = get_logger(__name__)


class SeleniumBrowserAuth:
    """
    Sistema de autenticación usando Selenium:
    1. Abre navegador Edge automatizado
    2. Usuario inicia sesión
    3. Captura cookies automáticamente
    """
    
    def __init__(self, sharepoint_url: str):
        self.sharepoint_url = sharepoint_url.rstrip('/')
        self.session = requests.Session()
        self.cookies = None
        self.auth_complete = False
        self.user_info = None
        self.driver = None
        self._keep_alive_active = False
        self._dialogo = None
        self.auto_login_credentials = self._load_auto_login_credentials()

    def _load_auto_login_credentials(self):
        """
        Cargar credenciales de auto-login desde almacén seguro o entorno.
        """
        credentials = load_auto_login_credentials()
        if not credentials:
            return None

        username = (credentials.get('username') or '').strip()
        if 'secretaria' not in username.lower():
            logger.error("La cuenta configurada no corresponde al usuario 'secretaria': %s", username)
            return None

        return credentials
    
    # ------------------------------------------------------------------
    # Inicio de sesión. La ventana (src/ui/inicio_sesion.py) llama a
    # abrir_navegador() y capturar_sesion() en un hilo aparte; aquí solo
    # queda la lógica, sin interfaz (antes eran funciones de tkinter dentro
    # de authenticate()). Los pasos y los mensajes son los mismos.
    # ------------------------------------------------------------------

    MENSAJE_SIN_CREDENCIALES = (
        "No hay credenciales válidas para la cuenta 'secretaria'.\n\n"
        + ("Guarda en el llavero de macOS el servicio EPLA_AUTLOGIN\n"
           "(Terminal: security add-generic-password -s EPLA_AUTLOGIN -a <usuario> -w)\n"
           if sys.platform == "darwin" else
           "Configura en Credential Manager el target EPLA_AUTLOGIN\n")
        + "con usuario que contenga 'secretaria' y su contraseña."
    )

    def authenticate(self, callback: Optional[Callable] = None, padre=None):
        """
        Abre la ventana de inicio de sesión (navegador automatizado).

        El resultado llega por ``callback(exito, mensaje)`` en el hilo de la
        interfaz. Devuelve False si no se puede ni empezar.
        """
        # Forzar autenticación automática exclusivamente con la cuenta secretaria
        if not self.auto_login_credentials:
            from src.ui.componentes import error

            error(padre, "Auto-login obligatorio no configurado", self.MENSAJE_SIN_CREDENCIALES)
            if callback:
                callback(False, "Credenciales de secretaria no configuradas")
            return False

        from src.ui.inicio_sesion import DialogoInicioSesion

        self._dialogo = DialogoInicioSesion(self, callback, padre)
        self._dialogo.open()
        return True

    def _keep_driver_alive(self):
        """Hilo que mantiene la sesión de Selenium activa"""
        while self._keep_alive_active and self.driver:
            try:
                # Ping suave al driver para mantener sesión activa
                _ = self.driver.current_window_handle
                logger.debug("Keep-alive: sesión de Selenium activa")
                time.sleep(5)  # Ping cada 5 segundos
            except Exception as e:
                logger.debug("Keep-alive detectó desconexión: %s", e)
                break

    def abrir_navegador(self, avisar: Optional[Callable[[str], None]] = None) -> str:
        """
        Abre Edge automatizado en SharePoint e inicia sesión con la cuenta de
        secretaría. Lanza la excepción si no se puede abrir el navegador.
        Devuelve el texto de estado final.
        """
        avisar = avisar or (lambda _texto: None)
        auth_type = 'auto'
        avisar("Abriendo navegador...")

        # Configurar Edge
        options = EdgeOptions()
        options.add_argument('--start-maximized')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_argument('--log-level=3')  # Suprimir logs

        # Si es autenticación automática, abrir en modo InPrivate para evitar cuenta de Windows
        if auth_type == 'auto':
            options.add_argument('--inprivate')
            logger.info("Abriendo navegador en modo InPrivate para auto-login")

        # --- Inicialización del WebDriver --------------------------
        # get_driver_path() es la fuente única de verdad
        # (comprueba %APPDATA% primero, luego el empaquetado).
        # Si no hay driver local, Selenium Manager lo resolverá.
        try:
            from src.driver_updater import get_driver_path
        except ImportError:
            from driver_updater import get_driver_path

        driver_path = get_driver_path()
        logger.info("Driver path resuelto: %s", driver_path)

        try:
            if driver_path and os.path.isfile(driver_path):
                logger.info("Usando driver local: %s", driver_path)
                service = Service(executable_path=driver_path)
                self.driver = webdriver.Edge(service=service, options=options)
            else:
                logger.info("Sin driver local, usando Selenium Manager")
                self.driver = webdriver.Edge(options=options)
            logger.info("Edge WebDriver iniciado correctamente")
        except Exception as e:
            # Si el driver local falla, último intento con Selenium Manager
            logger.warning("Driver local falló (%s), reintentando con Selenium Manager", e)
            try:
                self.driver = webdriver.Edge(options=options)
                logger.info("Edge iniciado vía Selenium Manager")
            except Exception as e2:
                logger.exception("Error definitivo iniciando Edge WebDriver: %s", e2)
                raise

        logger.info("Edge abierto correctamente")

        # Abrir SharePoint
        logger.info("Navegando a %s", self.sharepoint_url)
        self.driver.get(self.sharepoint_url)
        logger.info("SharePoint cargado")

        # Si se seleccionó inicio automático, completar el login
        if auth_type == 'auto' and self.auto_login_credentials:
            avisar("Iniciando sesión automáticamente...")
            self._auto_login()

        # Iniciar hilo keep-alive para mantener sesión de Selenium activa
        self._keep_alive_active = True
        threading.Thread(target=self._keep_driver_alive, daemon=True).start()
        logger.info("Thread keep-alive iniciado para mantener sesión activa")
        logger.info("Listo para capturar sesión")
        return "Sesión iniciada: compruébala en el navegador y pulsa «Capturar sesión»"

    def capturar_sesion(self, avisar: Optional[Callable[[str], None]] = None):
        """
        Captura las cookies del navegador y comprueba la sesión de SharePoint.

        Devuelve ``(exito, mensaje)``. Si va bien, cierra el navegador.
        """
        avisar = avisar or (lambda _texto: None)
        if not self.driver:
            return False, "Driver no disponible"

        try:
            avisar("Capturando cookies...")

            # Obtener cookies de Selenium (con reintentos si hay error de sesión)
            retry_count = 0
            max_retries = 2
            selenium_cookies = None

            while retry_count <= max_retries and selenium_cookies is None:
                try:
                    selenium_cookies = self.driver.get_cookies()
                    break
                except Exception as e:
                    error_str = str(e)
                    if 'invalid session id' in error_str.lower() or 'session deleted' in error_str.lower():
                        retry_count += 1
                        if retry_count <= max_retries:
                            logger.warning("Sesión inválida, reintentando... (%d/%d)", retry_count, max_retries)
                            time.sleep(2)
                            # Reintentar acceso al driver para recuperar la sesión
                            try:
                                _ = self.driver.current_window_handle
                            except Exception:
                                pass
                        else:
                            raise Exception(f"No se pudo recuperar la sesión de Selenium tras {max_retries} intentos")
                    else:
                        raise

            if not selenium_cookies:
                return False, "No se encontraron cookies"

            logger.info("Cookies capturadas: %s", len(selenium_cookies))

            # Transferir cookies a requests
            for cookie in selenium_cookies:
                self.session.cookies.set(
                    cookie['name'],
                    cookie['value'],
                    domain=cookie.get('domain', ''),
                    path=cookie.get('path', '/')
                )

            # Verificar sesión
            if self._verify_session():
                # Detener keep-alive y cerrar navegador
                self.cerrar_navegador()
                return True, "¡Autenticación exitosa!"
            return False, "Sesión no válida. ¿Iniciaste sesión?"

        except Exception as e:
            logger.exception("Error capturando sesión: %s", e)
            return False, f"Error: {str(e)[:80]}"

    def cerrar_navegador(self):
        """Detiene el keep-alive y cierra el navegador automatizado."""
        self._keep_alive_active = False
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    def _verify_session(self) -> bool:
        """Verifica que la sesión de SharePoint es válida"""
        try:
            response = self.session.get(
                f"{self.sharepoint_url}/_api/web",
                headers={'Accept': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Sesión de SharePoint verificada correctamente")
                self._extract_user_info()
                self.cookies = self.session.cookies
                self.auth_complete = True
                return True
            else:
                logger.warning("Sesión no válida; código de respuesta: %s", response.status_code)
            
            return False
            
        except Exception as e:
            logger.exception("Error verificando sesión: %s", e)
            return False
    
    def _extract_user_info(self):
        """Extraer información del usuario"""
        try:
            response = self.session.get(
                f"{self.sharepoint_url}/_api/web/currentuser",
                headers={'Accept': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.user_info = {
                    'displayName': data.get('Title', 'Usuario'),
                    'email': data.get('Email', data.get('LoginName', ''))
                }
                logger.info("Usuario autenticado: %s", self.user_info['displayName'])
            
        except Exception as e:
            logger.warning("Error extrayendo información de usuario: %s", e)
            self.user_info = {'displayName': 'Usuario', 'email': ''}
    
    def _auto_login(self):
        """
        Realizar inicio de sesión automático con credenciales predefinidas
        """
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            import time
            
            logger.info("Iniciando sesión automática")

            # Forzar limpieza de sesión Microsoft para evitar cuentas previas.
            self._force_microsoft_logout()

            # Volver a la URL objetivo y esperar carga inicial.
            self.driver.get(self.sharepoint_url)
            time.sleep(3)

            # Si aparece selector de cuentas, forzar "Usar otra cuenta".
            self._choose_use_another_account_if_needed()
            
            try:
                # Intentar encontrar el campo de email
                email_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "loginfmt"))
                )
                
                logger.info("Ingresando usuario en login automático")
                email_input.clear()
                email_input.send_keys(self.auto_login_credentials['username'])
                
                # Click en "Siguiente"
                next_button = self.driver.find_element(By.ID, "idSIButton9")
                next_button.click()
                
                time.sleep(2)
                
                # Esperar campo de contraseña
                password_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "passwd"))
                )
                
                logger.info("Ingresando contraseña en login automático")
                password_input.clear()
                password_input.send_keys(self.auto_login_credentials['password'])
                
                # Click en "Iniciar sesión"
                signin_button = self.driver.find_element(By.ID, "idSIButton9")
                signin_button.click()
                
                time.sleep(3)
                
                # Manejar "¿Mantener sesión iniciada?"
                try:
                    stay_signed_in = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.ID, "idSIButton9"))
                    )
                    logger.info("Aceptando diálogo 'mantener sesión iniciada'")
                    stay_signed_in.click()
                except Exception:
                    logger.info("No se mostró diálogo 'mantener sesión iniciada'")
                
                # Esperar a que cargue SharePoint
                time.sleep(5)
                
                logger.info("Inicio de sesión automático completado")
                
            except Exception as e:
                logger.warning("Error durante login automático: %s", e)
                logger.info("Posible sesión previa iniciada o cambios en la página de login")
                
        except Exception as e:
            logger.exception("Error en _auto_login: %s", e)
            import traceback
            logger.debug(traceback.format_exc())

    def _force_microsoft_logout(self):
        """Cerrar cualquier sesión Microsoft activa antes del login automático."""
        logout_urls = [
            "https://login.microsoftonline.com/common/oauth2/v2.0/logout",
            "https://login.live.com/logout.srf"
        ]

        for url in logout_urls:
            try:
                self.driver.get(url)
                time.sleep(2)
            except Exception as e:
                logger.debug("No se pudo abrir URL de logout %s: %s", url, e)

        try:
            self.driver.delete_all_cookies()
        except Exception as e:
            logger.debug("No se pudieron borrar cookies del navegador: %s", e)

    def _choose_use_another_account_if_needed(self):
        """Si Microsoft muestra cuentas previas, seleccionar 'Usar otra cuenta'."""
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            # Intento por id habitual del enlace/botón.
            try:
                other_account = WebDriverWait(self.driver, 4).until(
                    EC.element_to_be_clickable((By.ID, "otherTileText"))
                )
                other_account.click()
                time.sleep(1)
                return
            except Exception:
                pass

            # Fallback por textos en español/inglés.
            xpath_candidates = [
                "//*[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚ', 'abcdefghijklmnopqrstuvwxyzáéíóú'), 'usar otra cuenta')]",
                "//*[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'use another account')]"
            ]

            for xpath in xpath_candidates:
                try:
                    elem = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    elem.click()
                    time.sleep(1)
                    return
                except Exception:
                    continue

        except Exception as e:
            logger.debug("No fue necesario seleccionar 'Usar otra cuenta': %s", e)
    
    def get_session(self) -> requests.Session:
        """Obtiene la sesión autenticada"""
        return self.session
    
    def is_authenticated(self) -> bool:
        """Verifica si está autenticado"""
        return self.auth_complete
    
    def get_user_display_name(self) -> str:
        """Obtiene el nombre del usuario"""
        if self.user_info:
            return self.user_info.get('displayName', 'Usuario')
        return 'Usuario'
