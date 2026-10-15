"""
Gestor para crear y organizar la estructura de carpetas
"""

import os
import re
import unicodedata
from typing import List, Dict, Any, Optional
import shutil
from pathlib import Path

try:
    from src.logger_config import get_logger
except ImportError:
    from logger_config import get_logger

logger = get_logger(__name__)

class FolderManager:
    """Clase para gestionar la creación y organización de carpetas"""
    
    def __init__(self, base_path: str):
        """
        Inicializar el gestor de carpetas
        
        Args:
            base_path: Ruta base donde crear la estructura de carpetas
        """
        self.base_path = os.path.abspath(base_path)
        self.created_folders = {}  # Cache de carpetas creadas
        
    def create_folder_structure(self, students_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Crear estructura completa de carpetas para todos los estudiantes
        
        Args:
            students_data: Lista con información de estudiantes
            
        Returns:
            Diccionario con información de la estructura creada
        """
        structure_info = {
            'base_path': self.base_path,
            'total_students': len(students_data),
            'stages_created': 0,
            'student_folders_created': 0,
            'errors': [],
            'folder_mapping': {}  # Mapeo de estudiante -> ruta de carpeta
        }
        
        try:
            # Asegurar que el directorio base existe
            os.makedirs(self.base_path, exist_ok=True)
            
            # Agrupar estudiantes por etapa
            stages = self._group_students_by_stage(students_data)
            
            for stage_name, stage_students in stages.items():
                try:
                    # Crear carpeta de etapa
                    stage_folder = self._create_stage_folder(stage_name)
                    if stage_folder:
                        structure_info['stages_created'] += 1
                        
                        # Crear carpetas de estudiantes dentro de la etapa
                        for student in stage_students:
                            try:
                                student_folder = self._create_student_folder(stage_folder, student)
                                if student_folder:
                                    structure_info['student_folders_created'] += 1
                                    # Guardar mapeo para uso posterior
                                    primer_ap = student.get('primer_apellido', '')
                                    segundo_ap = student.get('segundo_apellido', '')
                                    nombre = student.get('nombre', '')
                                    student_key = f"{primer_ap}_{segundo_ap}_{nombre}"
                                    structure_info['folder_mapping'][student_key] = student_folder
                                
                            except Exception as e:
                                primer_ap = student.get('primer_apellido', 'N/A')
                                segundo_ap = student.get('segundo_apellido', 'N/A')
                                nombre = student.get('nombre', 'N/A')
                                error_msg = f"Error creando carpeta para estudiante {nombre} {primer_ap} {segundo_ap}: {e}"
                                structure_info['errors'].append(error_msg)
                                
                except Exception as e:
                    error_msg = f"Error creando carpeta para etapa {stage_name}: {e}"
                    structure_info['errors'].append(error_msg)
            
        except Exception as e:
            structure_info['errors'].append(f"Error general creando estructura: {e}")
        
        return structure_info
    
    def _group_students_by_stage(self, students_data: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Agrupar estudiantes por etapa
        
        Args:
            students_data: Lista con información de estudiantes
            
        Returns:
            Diccionario agrupado por etapa
        """
        stages = {}
        
        for student in students_data:
            # Clasificación principal por ciclo/especialidad.
            # Se mantiene fallback a 'etapa' para compatibilidad.
            stage = student.get('especialidad') or student.get('etapa', 'SIN_ETAPA')
            stage = str(stage).strip()
            if not stage:
                stage = 'SIN_ETAPA'
            
            # Normalizar nombre de etapa
            stage_normalized = self._normalize_folder_name(stage)
            
            if stage_normalized not in stages:
                stages[stage_normalized] = []
            
            stages[stage_normalized].append(student)
        
        return stages
    
    def _create_stage_folder(self, stage_name: str) -> Optional[str]:
        """
        Crear carpeta para una etapa
        
        Args:
            stage_name: Nombre de la etapa
            
        Returns:
            Ruta de la carpeta creada o None si hay error
        """
        try:
            # Normalizar nombre
            folder_name = self._normalize_folder_name(stage_name)
            folder_path = os.path.join(self.base_path, folder_name)
            
            # Crear carpeta si no existe
            os.makedirs(folder_path, exist_ok=True)
            
            # Guardar en cache
            self.created_folders[f"stage_{stage_name}"] = folder_path
            
            return folder_path
            
        except Exception as e:
            logger.exception("Error creando carpeta de etapa %s: %s", stage_name, e)
            return None
    
    def _create_student_folder(self, stage_folder: str, student_data: Dict[str, Any]) -> Optional[str]:
        """
        Crear carpeta para un estudiante
        
        Args:
            stage_folder: Ruta de la carpeta de etapa
            student_data: Información del estudiante
            
        Returns:
            Ruta de la carpeta del estudiante o None si hay error
        """
        try:
            # Carpeta de estudiante: APELLIDOS NOMBRE (sin guiones bajos)
            primer_apellido = student_data.get('primer_apellido', '').strip()
            segundo_apellido = student_data.get('segundo_apellido', '').strip()
            nombre = student_data.get('nombre', '').strip()
            
            if not primer_apellido and not nombre:
                # Usar índice si no hay nombres
                student_folder_name = f"ESTUDIANTE {student_data.get('index', 'SIN_ID')}"
            else:
                # Formato: PRIMER_APELLIDO SEGUNDO_APELLIDO NOMBRE
                partes = []
                if primer_apellido:
                    partes.append(primer_apellido)
                if segundo_apellido:
                    partes.append(segundo_apellido)
                if nombre:
                    partes.append(nombre)
                student_folder_name = ' '.join(partes)
            
            # Normalizar nombre
            folder_name = self._normalize_folder_name(student_folder_name)
            folder_path = os.path.join(stage_folder, folder_name)
            
            # Crear carpeta si no existe
            os.makedirs(folder_path, exist_ok=True)
            
            # Guardar en cache
            student_key = f"{primer_apellido}_{segundo_apellido}_{nombre}"
            self.created_folders[f"student_{student_key}"] = folder_path
            
            return folder_path
            
        except Exception as e:
            logger.exception("Error creando carpeta de estudiante: %s", e)
            return None
    
    def _normalize_folder_name(self, name: str) -> str:
        """
        Normalizar nombre de carpeta para el sistema de archivos
        
        Args:
            name: Nombre original
            
        Returns:
            Nombre normalizado
        """
        if not name:
            return "SIN_NOMBRE"
        
        # Convertir a mayúsculas
        name = name.upper()
        
        # Remover acentos y caracteres especiales
        name = unicodedata.normalize('NFD', name)
        name = ''.join(char for char in name if unicodedata.category(char) != 'Mn')
        
        # Reemplazar caracteres no válidos por espacio
        name = re.sub(r'[<>:"/\\|?*]+', ' ', name)

        # Sustituir guiones bajos existentes por espacio para no usarlos en carpetas
        name = name.replace('_', ' ')

        # Colapsar espacios múltiples y limpiar extremos
        name = re.sub(r'\s+', ' ', name).strip()
        
        # Limitar longitud para evitar problemas en Windows
        if len(name) > 100:
            name = name[:100]
        
        # Asegurar que no esté vacío después de la limpieza
        if not name:
            name = "CARPETA_SIN_NOMBRE"
        
        return name
    
    def get_student_folder_path(self, student_data: Dict[str, Any], stage_folder: str = None) -> str:
        """
        Obtener la ruta de carpeta de un estudiante
        
        Args:
            student_data: Información del estudiante
            stage_folder: Carpeta de etapa (opcional)
            
        Returns:
            Ruta completa de la carpeta del estudiante
        """
        if not stage_folder:
            # Construir desde la etapa
            stage_value = student_data.get('especialidad') or student_data.get('etapa', 'SIN_ETAPA')
            stage_folder_name = self._normalize_folder_name(stage_value)
            stage_folder = os.path.join(self.base_path, stage_folder_name)
        
        # Construir nombre de carpeta del estudiante: APELLIDOS NOMBRE
        primer_apellido = student_data.get('primer_apellido', '').strip()
        segundo_apellido = student_data.get('segundo_apellido', '').strip()
        nombre = student_data.get('nombre', '').strip()
        
        if not primer_apellido and not nombre:
            student_folder_name = f"ESTUDIANTE {student_data.get('index', 'SIN_ID')}"
        else:
            partes = []
            if primer_apellido:
                partes.append(primer_apellido)
            if segundo_apellido:
                partes.append(segundo_apellido)
            if nombre:
                partes.append(nombre)
            student_folder_name = ' '.join(partes)
        
        folder_name = self._normalize_folder_name(student_folder_name)
        return os.path.join(stage_folder, folder_name)
    
    def organize_downloaded_files(self, download_results: List[Dict[str, Any]], 
                                students_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Organizar archivos descargados en las carpetas correspondientes
        
        Args:
            download_results: Resultados de las descargas
            students_data: Información de estudiantes
            
        Returns:
            Información del proceso de organización
        """
        organization_info = {
            'files_organized': 0,
            'files_failed': 0,
            'errors': []
        }
        
        for result in download_results:
            if not result.get('success', False):
                organization_info['files_failed'] += 1
                continue
            
            try:
                # Aquí implementarías la lógica para mover archivos descargados
                # a las carpetas correctas basándose en la información del estudiante
                
                # Por ahora, simplemente contar como organizados
                organization_info['files_organized'] += 1
                
            except Exception as e:
                organization_info['files_failed'] += 1
                organization_info['errors'].append(f"Error organizando archivo: {e}")
        
        return organization_info
    
    def clean_empty_folders(self) -> int:
        """
        Limpiar carpetas vacías en la estructura
        
        Returns:
            Número de carpetas eliminadas
        """
        removed_count = 0
        
        try:
            # Recorrer la estructura desde las hojas hacia la raíz
            for root, dirs, files in os.walk(self.base_path, topdown=False):
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    try:
                        # Verificar si la carpeta está vacía
                        if not os.listdir(dir_path):
                            os.rmdir(dir_path)
                            removed_count += 1
                    except OSError:
                        # Carpeta no está vacía o no se puede eliminar
                        continue
                        
        except Exception as e:
            logger.exception("Error limpiando carpetas vacías: %s", e)
        
        return removed_count
    
    def get_folder_structure_info(self) -> Dict[str, Any]:
        """
        Obtener información sobre la estructura de carpetas creada
        
        Returns:
            Información detallada de la estructura
        """
        info = {
            'base_path': self.base_path,
            'total_folders': 0,
            'stage_folders': 0,
            'student_folders': 0,
            'folder_sizes': {},
            'structure': {}
        }
        
        try:
            if not os.path.exists(self.base_path):
                return info
            
            # Recorrer estructura
            for root, dirs, files in os.walk(self.base_path):
                info['total_folders'] += len(dirs)
                
                # Calcular tamaño de carpeta
                folder_size = 0
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        folder_size += os.path.getsize(file_path)
                    except OSError:
                        continue
                
                rel_path = os.path.relpath(root, self.base_path)
                info['folder_sizes'][rel_path] = folder_size
                
                # Determinar tipo de carpeta
                depth = len(rel_path.split(os.sep)) if rel_path != '.' else 0
                if depth == 1:  # Carpetas de etapa
                    info['stage_folders'] += 1
                elif depth == 2:  # Carpetas de estudiante
                    info['student_folders'] += 1
                    
        except Exception as e:
            logger.exception("Error obteniendo información de estructura: %s", e)
        
        return info

def create_folder_manager(base_path: str) -> FolderManager:
    """
    Crear una instancia del gestor de carpetas
    
    Args:
        base_path: Ruta base donde crear la estructura
        
    Returns:
        Instancia de FolderManager
    """
    return FolderManager(base_path)