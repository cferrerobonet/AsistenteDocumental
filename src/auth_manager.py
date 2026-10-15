"""
Gestor de autenticación para Microsoft Graph API
Proporciona autenticación OAuth 2.0 usando MSAL
"""

import json
import os
import platform
import subprocess
import sys
import time
import webbrowser
import threading
from typing import Optional, Dict, Any
from urllib.parse import parse_qs, urlparse

import requests

try:
    from src.logger_config import get_logger
except ImportError:
    from logger_config import get_logger

logger = get_logger(__name__)

try:
    from msal import PublicClientApplication
    MSAL_AVAILABLE = True
except ImportError:
    MSAL_AVAILABLE = False
    logger.warning("MSAL no está disponible. Instale con: pip install msal")

class AuthenticationManager:
    """Clase para gestionar la autenticación con Microsoft Graph API"""
    
    def __init__(self, client_id: str, tenant: str = "organizations"):
        """
        Inicializar el gestor de autenticación con MSAL
        
        Args:
            client_id: ID de la aplicación Microsoft Graph
            tenant: Tenant ID o 'organizations' para cuentas corporativas
        
        Raises:
            ImportError: Si MSAL no está disponible
            ValueError: Si client_id no es válido
        """
        if not MSAL_AVAILABLE:
            raise ImportError("MSAL no está disponible. Instale con: pip install msal")
        
        if not client_id or not isinstance(client_id, str):
            raise ValueError("client_id debe ser una cadena válida")
        
        self.client_id = client_id
        self.tenant = tenant
        self.authority = f"https://login.microsoftonline.com/{tenant}"
        
        # Scopes básicos para Microsoft Graph API (evitar errores de consentimiento)
        self.scopes = [
            "https://graph.microsoft.com/User.Read"
        ]
        
        # Crear aplicación MSAL pública (no requiere client_secret)
        try:
            self.app = PublicClientApplication(
                client_id=self.client_id,
                authority=self.authority
            )
            logger.info("Cliente MSAL inicializado correctamente")
            logger.info("Client ID: %s", self.client_id)
            logger.info("Authority: %s", self.authority)
        except Exception as e:
            raise RuntimeError(f"Error inicializando cliente MSAL: {e}")
        
        # Estado de autenticación
        self.access_token = None
        self.user_info = None
        self._device_flow_state = None
        self._device_flow_lock = threading.Lock()
        
    def authenticate_device_flow(self, callback_func=None) -> bool:
        """
        Autenticación usando Device Flow - más compatible que el flujo interactivo
        
        Args:
            callback_func: Función opcional que se llama con información del dispositivo
            
        Returns:
            bool: True si la autenticación fue exitosa, False en caso contrario
        """
        try:
            logger.info("Iniciando autenticación con Device Flow")
            
            # Iniciar el flujo de autenticación de dispositivo
            flow = self.app.initiate_device_flow(scopes=self.scopes)
            
            if "user_code" not in flow:
                logger.error("No se pudo obtener el código de usuario")
                return False
            
            # Mostrar información del código de dispositivo
            device_info = {
                'user_code': flow['user_code'],
                'verification_uri': flow['verification_uri'],
                'message': flow['message']
            }
            
            logger.info("Código de usuario: %s", flow['user_code'])
            logger.info("URL de verificación: %s", flow['verification_uri'])
            logger.info("Mensaje Device Flow recibido")
            
            # Llamar al callback si se proporciona
            if callback_func:
                callback_func(device_info)
            
            # Intentar abrir el navegador automáticamente
            self._open_browser(flow['verification_uri'])
            
            # Esperar a que el usuario complete la autenticación
            logger.info("Esperando autenticación en navegador")
            result = self.app.acquire_token_by_device_flow(flow)
            
            if "access_token" in result:
                self.access_token = result["access_token"]
                logger.info("Autenticación exitosa")
                
                # Obtener información del usuario
                self._get_user_info()
                return True
            else:
                error = result.get("error_description", result.get("error", "Error desconocido"))
                logger.error("Error en la autenticación: %s", error)
                return False
                
        except Exception as e:
            logger.exception("Error durante la autenticación: %s", e)
            return False
    
    def authenticate_device_flow_async(self, callback_func=None, progress_callback=None):
        """
        Autenticación usando Device Flow de forma asíncrona con polling

        Args:
            callback_func: Función que se llama con información del dispositivo
            progress_callback: Función que se llama con actualizaciones de progreso

        Returns:
            dict: Información del flujo de dispositivo con 'flow' para polling
        """
        try:
            logger.info("Iniciando autenticación con Device Flow asíncrono")

            flow = self.app.initiate_device_flow(scopes=self.scopes)

            if "user_code" not in flow:
                logger.error("No se pudo obtener el código de usuario")
                return None

            device_info = {
                'user_code': flow['user_code'],
                'verification_uri': flow['verification_uri'],
                'message': flow['message'],
                'flow': flow
            }

            logger.info("Código de usuario: %s", flow['user_code'])
            logger.info("URL de verificación: %s", flow['verification_uri'])
            logger.info("Mensaje Device Flow recibido")

            if callback_func:
                callback_func(device_info)

            self._open_browser(flow['verification_uri'])

            initial_message = device_info.get('message') or "Introduce el código y completa la autenticación desde el navegador."
            with self._device_flow_lock:
                self._device_flow_state = {
                    "flow": flow,
                    "status": "pending",
                    "message": initial_message,
                    "completed": False
                }

            def _run_device_flow():
                try:
                    result = self.app.acquire_token_by_device_flow(flow)
                    if "access_token" in result:
                        self.access_token = result["access_token"]
                        logger.info("Autenticación exitosa en hilo de fondo")
                        self._get_user_info()
                        message = "Autenticación exitosa"
                        status = "success"
                    else:
                        error = result.get("error_description", result.get("error", "Error desconocido"))
                        logger.error("Error en la autenticación asíncrona: %s", error)
                        if "AADSTS65002" in error or "consent" in error.lower():
                            message = "Error: La aplicación necesita permisos adicionales. Contacte al administrador."
                            status = "consent_required"
                        else:
                            message = f"Error: {error}"
                            status = "error"
                    with self._device_flow_lock:
                        if self._device_flow_state and self._device_flow_state.get("flow") == flow:
                            self._device_flow_state.update({
                                "message": message,
                                "status": status,
                                "completed": True
                            })
                except Exception as ex:
                    logger.exception("Error durante la autenticación en hilo de fondo: %s", ex)
                    with self._device_flow_lock:
                        if self._device_flow_state and self._device_flow_state.get("flow") == flow:
                            self._device_flow_state.update({
                                "message": f"Error durante la autenticación: {ex}",
                                "status": "exception",
                                "completed": True
                            })

            threading.Thread(target=_run_device_flow, daemon=True).start()

            return device_info

        except Exception as e:
            logger.exception("Error durante la autenticación asíncrona: %s", e)
            return None

    def poll_for_token(self, flow):
        """
        Polling no bloqueante para verificar si el usuario completó la autenticación

        Args:
            flow: El flujo de autenticación retornado por authenticate_device_flow_async

        Returns:
            tuple: (success: bool, message: str, completed: bool)
                   completed indica si el proceso terminó (exitoso o no)
        """
        try:
            with self._device_flow_lock:
                state = self._device_flow_state

            if not state or state.get("flow") != flow:
                return False, "No hay un flujo de autenticación activo", True

            if not state.get("completed"):
                message = state.get("message") or "Esperando autenticación del usuario..."
                return False, message, False

            status = state.get("status")
            message = state.get("message") or "Autenticación completada"

            with self._device_flow_lock:
                self._device_flow_state = None

            if status == "success":
                return True, message, True

            return False, message, True

        except Exception as e:
            logger.exception("Error durante el polling: %s", e)
            return False, f"Error de conexión: {e}", True

    def _open_browser(self, url: str) -> bool:
        """
        Intenta abrir el navegador con diferentes métodos
        
        Args:
            url: URL a abrir
            
        Returns:
            bool: True si se pudo abrir el navegador, False en caso contrario
        """
        logger.info("Intentando abrir navegador: %s", url)
        
        methods_tried = []
        
        # Método 1: webbrowser.open (multiplataforma)
        try:
            if webbrowser.open(url):
                logger.info("Navegador abierto con webbrowser.open()")
                return True
            else:
                methods_tried.append("webbrowser.open() retornó False")
        except Exception as e:
            methods_tried.append(f"webbrowser.open() falló: {e}")
        
        # Método 2: Comando específico del sistema
        system = platform.system().lower()
        try:
            if system == "windows":
                # Método Windows específico
                subprocess.run(["start", url], shell=True, check=True)
                logger.info("Navegador abierto con 'start' (Windows)")
                return True
            elif system == "darwin":  # macOS
                subprocess.run(["open", url], check=True)
                logger.info("Navegador abierto con 'open' (macOS)")
                return True
            elif system == "linux":
                subprocess.run(["xdg-open", url], check=True)
                logger.info("Navegador abierto con 'xdg-open' (Linux)")
                return True
        except Exception as e:
            methods_tried.append(f"Comando del sistema falló: {e}")
        
        # Método 3: PowerShell en Windows
        if system == "windows":
            try:
                cmd = f'Start-Process "{url}"'
                subprocess.run(["powershell", "-Command", cmd], check=True)
                logger.info("Navegador abierto con PowerShell")
                return True
            except Exception as e:
                methods_tried.append(f"PowerShell falló: {e}")
        
        # Método 4: os.startfile en Windows
        if system == "windows":
            try:
                os.startfile(url)
                logger.info("Navegador abierto con os.startfile()")
                return True
            except Exception as e:
                methods_tried.append(f"os.startfile() falló: {e}")
        
        # Si llegamos aquí, ningún método funcionó
        logger.warning("No se pudo abrir automáticamente el navegador")
        logger.warning("Métodos intentados:")
        for i, method in enumerate(methods_tried, 1):
            logger.warning("%s. %s", i, method)
        logger.warning("Abrir manualmente: %s", url)
        
        return False
    
    def _get_user_info(self) -> None:
        """Obtiene información del usuario autenticado"""
        if not self.access_token:
            return
        
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers)
            
            if response.status_code == 200:
                self.user_info = response.json()
                logger.info("Usuario autenticado: %s", self.user_info.get('displayName', 'Usuario'))
                logger.info("Email: %s", self.user_info.get('mail', self.user_info.get('userPrincipalName', 'N/A')))
            else:
                logger.warning("No se pudo obtener información del usuario: %s", response.status_code)
                
        except Exception as e:
            logger.exception("Error obteniendo información del usuario: %s", e)
    
    def is_authenticated(self) -> bool:
        """Verifica si el usuario está autenticado"""
        return self.access_token is not None
    
    def get_access_token(self) -> Optional[str]:
        """Obtiene el token de acceso actual"""
        return self.access_token
    
    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """Obtiene la información del usuario"""
        return self.user_info
    
    def logout(self) -> None:
        """Cierra la sesión del usuario"""
        self.access_token = None
        self.user_info = None
        logger.info("Sesión cerrada")

def create_auth_manager(client_id: str = None, tenant: str = "organizations") -> AuthenticationManager:
    """
    Función helper para crear un gestor de autenticación
    
    Args:
        client_id: ID del cliente de Microsoft Graph (opcional)
        tenant: Tenant ID o 'organizations' para cuentas corporativas
        
    Returns:
        AuthenticationManager: Instancia del gestor de autenticación
        
    Raises:
        ImportError: Si MSAL no está disponible
        ValueError: Si hay problemas con la configuración
        RuntimeError: Si no se puede crear el gestor
    """
    
    # Validar y usar client_id predeterminado si es necesario
    if not client_id or client_id == "your_client_id_here":
        # Azure CLI - Client ID público que soporta Device Flow
        client_id = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"  # Azure CLI
        logger.info("Usando Azure CLI Client ID")
        logger.info("Client ID público que soporta Device Flow")
        logger.info("Funciona directamente con cualquier cuenta corporativa")
    
    # Validar formato del client_id
    if not isinstance(client_id, str) or len(client_id) < 8:
        raise ValueError(f"Client ID inválido: {client_id}")
    
    # Crear y retornar el gestor de autenticación
    try:
        return AuthenticationManager(client_id=client_id, tenant=tenant)
    except Exception as e:
        raise RuntimeError(f"No se pudo crear el gestor de autenticación: {e}")

# Cliente ID predeterminado - Azure CLI (público)
DEFAULT_CLIENT_ID = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"  # Azure CLI client ID

