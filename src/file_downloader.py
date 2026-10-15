"""
Sistema de descarga de archivos desde Microsoft SharePoint/OneDrive
"""

import os
import requests
from typing import List, Dict, Optional, Callable, Any
import urllib.parse
from urllib.parse import urlparse
import time
import hashlib

try:
    from src.logger_config import get_logger
except ImportError:
    from logger_config import get_logger

logger = get_logger(__name__)

class FileDownloader:
    """Clase para descargar archivos desde SharePoint/OneDrive usando Microsoft Graph API"""
    
    def __init__(self, auth_manager, progress_callback: Optional[Callable] = None):
        """
        Inicializar el descargador de archivos
        
        Args:
            auth_manager: Instancia del gestor de autenticación
            progress_callback: Función callback para reportar progreso
        """
        self.auth_manager = auth_manager
        self.progress_callback = progress_callback
        self.download_session = requests.Session()
        self.max_retries = 3
        self.retry_delay_seconds = 1.0

        # Configurar cookies de autenticación si existen
        if hasattr(self.auth_manager, 'cookies') and self.auth_manager.cookies:
            try:
                # Las cookies pueden venir de diferentes fuentes
                cookies_count = 0

                # Si es un CookieJar o RequestsCookieJar (de requests.Session)
                if hasattr(self.auth_manager.cookies, '__iter__'):
                    for cookie in self.auth_manager.cookies:
                        # Si es un objeto Cookie (de requests)
                        if hasattr(cookie, 'name'):
                            self.download_session.cookies.set(
                                cookie.name,
                                cookie.value,
                                domain=cookie.domain if hasattr(cookie, 'domain') else '',
                                path=cookie.path if hasattr(cookie, 'path') else '/'
                            )
                            cookies_count += 1
                        # Si es un diccionario (de Selenium)
                        elif isinstance(cookie, dict):
                            self.download_session.cookies.set(
                                cookie.get('name', ''),
                                cookie.get('value', ''),
                                domain=cookie.get('domain', ''),
                                path=cookie.get('path', '/')
                            )
                            cookies_count += 1

                if cookies_count > 0:
                    logger.info("Cookies transferidas a sesión de descarga: %s", cookies_count)
                else:
                    logger.warning("No se pudieron transferir cookies")

            except Exception as e:
                logger.exception("Error transfiriendo cookies: %s", e)
                import traceback
                logger.debug(traceback.format_exc())

        # Configurar headers predeterminados
        self.download_session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
            'Accept': '*/*',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        })

        # Si hay token de acceso (solo para autenticación MSAL), agregarlo
        if hasattr(self.auth_manager, 'get_access_token'):
            try:
                token = self.auth_manager.get_access_token()
                if token:
                    self.download_session.headers.update({
                        'Authorization': f'Bearer {token}'
                    })
                    logger.info("Token de acceso agregado a la sesión")
            except Exception:
                pass  # No pasa nada si no hay token, usamos solo cookies

    def _sleep_for_retry(self, attempt: int) -> None:
        time.sleep(self.retry_delay_seconds * attempt)

    def _request_with_retries(self, method: str, url: str, **kwargs):
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info("Solicitud %s intento %s/%s: %s", method.upper(), attempt, self.max_retries, url)
                response = self.download_session.request(method=method, url=url, **kwargs)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                last_error = e
                logger.warning(
                    "Fallo de red en %s (intento %s/%s): %s",
                    method.upper(),
                    attempt,
                    self.max_retries,
                    e,
                )
                if attempt < self.max_retries:
                    self._sleep_for_retry(attempt)

        if last_error:
            raise last_error
        raise RuntimeError("Error inesperado en _request_with_retries")

    def _resolve_direct_download_url_with_retries(self, share_url: str) -> str:
        encoded_url = urllib.parse.quote(share_url, safe='')

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.auth_manager.make_graph_request(f"/shares/{encoded_url}/driveItem")
                if response and '@microsoft.graph.downloadUrl' in response:
                    return response['@microsoft.graph.downloadUrl']
                return share_url
            except Exception as e:
                logger.warning(
                    "Error resolviendo URL directa (intento %s/%s): %s",
                    attempt,
                    self.max_retries,
                    e,
                )
                if attempt < self.max_retries:
                    self._sleep_for_retry(attempt)

        return share_url

    def _validate_destination_path(self, destination_path: str) -> None:
        if not destination_path or not isinstance(destination_path, str):
            raise ValueError("Ruta de destino inválida")

        normalized = os.path.normpath(destination_path)
        os.makedirs(normalized, exist_ok=True)

        if not os.path.isdir(normalized):
            raise ValueError(f"Ruta de destino no válida: {destination_path}")
    
    def download_file(self, url: str, destination_path: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Descargar un archivo desde una URL de SharePoint/OneDrive
        
        Args:
            url: URL del archivo a descargar
            destination_path: Ruta de destino donde guardar el archivo
            filename: Nombre personalizado para el archivo (opcional)
            
        Returns:
            Diccionario con información del resultado de la descarga
        """
        result = {
            'success': False,
            'url': url,
            'destination_path': destination_path,
            'filename': filename,
            'file_path': '',
            'file_size': 0,
            'error': None
        }
        
        try:
            # Validar URL y destino antes de iniciar operaciones de red
            validation = self.validate_url(url)
            if not validation['valid']:
                result['error'] = validation['error']
                return result

            self._validate_destination_path(destination_path)
            
            # Procesar la URL para obtener el enlace de descarga directo
            download_url = self._process_sharepoint_url(url)
            
            # Obtener información del archivo
            file_info = self._get_file_info(download_url)
            
            # Determinar el nombre del archivo
            if not filename:
                filename = file_info.get('filename', self._extract_filename_from_url(url))
            
            # Limpiar el nombre del archivo
            filename = self._sanitize_filename(filename)
            file_path = os.path.join(destination_path, filename)
            
            # Descargar el archivo
            download_success = self._download_file_stream(download_url, file_path)
            
            if download_success:
                file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                result.update({
                    'success': True,
                    'filename': filename,
                    'file_path': file_path,
                    'file_size': file_size
                })
            else:
                result['error'] = "Error durante la descarga del archivo"
                
        except Exception as e:
            result['error'] = f"Error al descargar archivo: {str(e)}"
            logger.exception("Error en download_file para %s: %s", url, e)
        
        return result
    
    def _process_sharepoint_url(self, url: str) -> str:
        """
        Procesar URL de SharePoint/OneDrive para obtener enlace de descarga directo
        
        Args:
            url: URL original del archivo
            
        Returns:
            URL procesada para descarga directa
        """
        try:
            parsed_url = urlparse(url)
            
            # Si es una URL de compartir de OneDrive/SharePoint
            if 'sharepoint.com' in parsed_url.netloc or '1drv.ms' in parsed_url.netloc:
                # Intentar obtener el enlace directo usando Graph API
                return self._get_direct_download_url(url)
            
            # Si parece ser una URL directa, usarla tal como está
            return url
            
        except Exception as e:
            logger.exception("Error al procesar URL de SharePoint: %s", e)
            return url
    
    def _get_direct_download_url(self, share_url: str) -> str:
        """
        Obtener URL de descarga directa usando Microsoft Graph API
        
        Args:
            share_url: URL de compartir
            
        Returns:
            URL de descarga directa
        """
        try:
            if not hasattr(self.auth_manager, 'make_graph_request'):
                return share_url

            return self._resolve_direct_download_url_with_retries(share_url)
            
            # Si no se puede obtener la URL directa, usar la original
            return share_url
            
        except Exception as e:
            logger.exception("Error al obtener URL directa: %s", e)
            return share_url
    
    def _get_file_info(self, url: str) -> Dict[str, Any]:
        """
        Obtener información del archivo antes de descargarlo
        
        Args:
            url: URL del archivo
            
        Returns:
            Diccionario con información del archivo
        """
        try:
            # Hacer una petición HEAD para obtener información sin descargar
            response = self._request_with_retries(
                method='head',
                url=url,
                allow_redirects=True,
                timeout=10,
            )
            
            info = {
                'filename': '',
                'size': 0,
                'content_type': response.headers.get('content-type', ''),
                'url': response.url
            }
            
            # Intentar extraer el nombre del archivo del header Content-Disposition
            content_disposition = response.headers.get('content-disposition', '')
            if 'filename=' in content_disposition:
                filename = content_disposition.split('filename=')[1].strip('"\'')
                info['filename'] = filename
            
            # Obtener tamaño del archivo
            content_length = response.headers.get('content-length')
            if content_length:
                info['size'] = int(content_length)
            
            return info
            
        except Exception as e:
            logger.exception("Error al obtener información del archivo: %s", e)
            return {'filename': '', 'size': 0, 'content_type': '', 'url': url}
    
    def _download_file_stream(self, url: str, file_path: str, chunk_size: int = 8192) -> bool:
        """
        Descargar archivo usando streaming para archivos grandes
        
        Args:
            url: URL del archivo
            file_path: Ruta donde guardar el archivo
            chunk_size: Tamaño de chunk para la descarga
            
        Returns:
            True si la descarga fue exitosa
        """
        try:
            logger.info("Descargando archivo: %s", url)
            response = self._request_with_retries(
                method='get',
                url=url,
                stream=True,
                timeout=30,
                allow_redirects=True,
            )

            # Verificar que no sea una página HTML de error
            content_type = response.headers.get('content-type', '').lower()
            logger.info("Content-Type: %s", content_type)

            # Si es HTML, probablemente es una página de error o login
            if 'text/html' in content_type:
                logger.warning("Recibiendo HTML en lugar de archivo. Puede ser error de autenticación")
                logger.warning("URL final después de redirecciones: %s", response.url)
                content_preview = response.content[:500].decode('utf-8', errors='ignore')
                logger.debug("Vista previa del contenido: %s", content_preview[:200])

            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0

            logger.info("Tamaño esperado: %s bytes", total_size)

            with open(file_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        file.write(chunk)
                        downloaded_size += len(chunk)

                        # Reportar progreso si hay callback
                        if self.progress_callback and total_size > 0:
                            progress = (downloaded_size / total_size) * 100
                            self.progress_callback(progress, downloaded_size, total_size)

            actual_size = os.path.getsize(file_path)
            logger.info("Descargado: %s bytes", actual_size)

            # Verificar si el tamaño es sospechosamente pequeño
            if actual_size < 500 and 'text/html' in content_type:
                logger.warning(
                    "Archivo muy pequeño (%s bytes) y tipo HTML; probablemente corrupto",
                    actual_size,
                )
                return False

            return True

        except Exception as e:
            logger.exception("Error inesperado al descargar archivo: %s", e)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass
            return False
    
    def _extract_filename_from_url(self, url: str) -> str:
        """
        Extraer nombre de archivo de la URL
        
        Args:
            url: URL del archivo
            
        Returns:
            Nombre del archivo extraído
        """
        try:
            parsed = urlparse(url)
            path = parsed.path
            
            if path:
                filename = os.path.basename(path)
                if filename and '.' in filename:
                    return filename
            
            # Si no se puede extraer, generar nombre basado en hash de URL
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            return f"archivo_{url_hash}.bin"
            
        except Exception:
            # Fallback: generar nombre aleatorio
            import random
            return f"archivo_{random.randint(1000, 9999)}.bin"
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Limpiar nombre de archivo para el sistema de archivos
        
        Args:
            filename: Nombre original del archivo
            
        Returns:
            Nombre de archivo limpio
        """
        # Caracteres no permitidos en nombres de archivo
        invalid_chars = '<>:"/\\|?*'
        
        # Reemplazar caracteres inválidos
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Limitar longitud
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:255-len(ext)] + ext
        
        # Asegurar que no esté vacío
        if not filename.strip():
            filename = "archivo_sin_nombre.bin"
        
        return filename.strip()
    
    def download_multiple_files(self, downloads: List[Dict[str, str]], 
                               base_destination: str,
                               progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """
        Descargar múltiples archivos
        
        Args:
            downloads: Lista de diccionarios con información de descarga
                      Cada diccionario debe tener: {'url': str, 'destination_subdir': str, 'filename': str}
            base_destination: Directorio base de destino
            progress_callback: Callback para progreso global
            
        Returns:
            Lista con resultados de cada descarga
        """
        results = []
        total_files = len(downloads)
        
        for i, download_info in enumerate(downloads):
            url = download_info['url']
            subdir = download_info.get('destination_subdir', '')
            filename = download_info.get('filename', None)
            
            # Crear ruta de destino completa
            destination_path = os.path.join(base_destination, subdir)
            
            # Callback de progreso individual
            def file_progress(progress, downloaded, total):
                if progress_callback:
                    overall_progress = ((i / total_files) + (progress / 100 / total_files)) * 100
                    progress_callback(overall_progress, i + 1, total_files, 
                                    f"Descargando {filename or 'archivo'}...")
            
            # Descargar archivo
            result = self.download_file(url, destination_path, filename)
            result['file_index'] = i + 1
            result['total_files'] = total_files
            results.append(result)
            
            # Reportar progreso global
            if progress_callback:
                overall_progress = ((i + 1) / total_files) * 100
                progress_callback(overall_progress, i + 1, total_files, 
                                f"Completado {i + 1}/{total_files}")
            
            # Pequeña pausa entre descargas para no sobrecargar el servidor
            time.sleep(0.1)
        
        return results
    
    def validate_url(self, url: str) -> Dict[str, Any]:
        """
        Validar si una URL es accesible
        
        Args:
            url: URL a validar
            
        Returns:
            Diccionario con información de validación
        """
        validation = {
            'valid': False,
            'accessible': False,
            'url': url,
            'status_code': None,
            'error': None
        }
        
        try:
            # Validar formato de URL
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                validation['error'] = "Formato de URL inválido"
                return validation
            
            validation['valid'] = True
            
            # Verificar accesibilidad
            response = self._request_with_retries(
                method='head',
                url=url,
                timeout=10,
                allow_redirects=True,
            )
            validation['status_code'] = response.status_code
            
            if response.status_code == 200:
                validation['accessible'] = True
            else:
                validation['error'] = f"Código de estado HTTP: {response.status_code}"
            
        except Exception as e:
            validation['error'] = str(e)
        
        return validation

def create_file_downloader(auth_manager, progress_callback: Optional[Callable] = None) -> FileDownloader:
    """
    Crear una instancia del descargador de archivos
    
    Args:
        auth_manager: Gestor de autenticación
        progress_callback: Callback para progreso
        
    Returns:
        Instancia de FileDownloader
    """
    return FileDownloader(auth_manager, progress_callback)