"""
Procesador de archivos tabulares (Excel/CSV) con detección automática de columnas.
"""

import pandas as pd
import numpy as np
import re
from typing import Dict, List, Optional, Tuple, Any
import os
from urllib.parse import urlparse
import openpyxl

try:
    from src.logger_config import get_logger
except ImportError:
    from logger_config import get_logger

logger = get_logger(__name__)

class ExcelProcessor:
    """Clase para procesar archivos Excel/CSV y detectar automáticamente columnas relevantes."""
    
    def __init__(self):
        self.df = None
        self.file_path = ""
        self.detected_columns = {}
        
        # Patrones para detectar columnas automáticamente
        self.column_patterns = {
            'primer_apellido': [
                r'primer[_\s]?apellido',
                r'apellido[_\s]?1',
                r'first[_\s]?surname'
            ],
            'segundo_apellido': [
                r'segundo[_\s]?apellido',
                r'apellido[_\s]?2',
                r'second[_\s]?surname'
            ],
            'nombre': [
                r'nombre[_\s]?(?:del|de\sla)?[_\s]*alumn(?:o|a)(?:[/_]a)?',
                r'first[_\s]?name[_\s]?(?:student|alumno)',
                r'given[_\s]?name'
            ],
            'especialidad': [
                r'indique[_\s]+el[_\s]+ciclo[_\s]+al[_\s]+que[_\s]+pertene(?:ce|cen)',
                r'indique[_\s]+el[_\s]+ciclo[_\s]+al[_\s]+que[_\s]+petene(?:ce|cen)',
                r'ciclo',
                r'especialidad',
                r'familia[_\s]?profesional'
            ],
            'etapa': [
                r'etapa',
                r'stage',
                r'nivel[_\s]?educativo'
            ],
            'curso': [
                r'curso',
                r'course',
                r'grado',
                r'grade'
            ],
            'urls': [
                r'url[s]?',
                r'link[s]?',
                r'enlace[s]?',
                r'archivo[s]?',
                r'file[s]?',
                r'descarga[s]?',
                r'download[s]?',
                r'documento[s]?',
                r'document[s]?',
                r'anexo[s]?',
                r'attachment[s]?'
            ]
        }
    
    def load_excel(self, file_path: str, sheet_name: Optional[str] = None) -> bool:
        """
        Cargar archivo Excel o CSV
        
        Args:
            file_path: Ruta al archivo Excel/CSV
            sheet_name: Nombre de la hoja (solo para Excel, None para primera hoja)
            
        Returns:
            True si se cargó correctamente, False en caso contrario
        """
        try:
            self.file_path = file_path
            
            extension = os.path.splitext(file_path)[1].lower()

            # Cargar el archivo según extensión
            if extension == '.csv':
                # Los CSV de Microsoft Forms suelen venir con ';' en entornos ES.
                self.df = pd.read_csv(file_path, sep=None, engine='python', encoding='utf-8-sig')
            else:
                if sheet_name:
                    self.df = pd.read_excel(file_path, sheet_name=sheet_name)
                else:
                    self.df = pd.read_excel(file_path)
            
            # Limpiar nombres de columnas
            self.df.columns = self.df.columns.str.strip()
            
            logger.info(
                "Archivo cargado: %s filas, %s columnas",
                len(self.df),
                len(self.df.columns),
            )
            logger.info("Columnas encontradas: %s", list(self.df.columns))
            
            return True
            
        except Exception as e:
            logger.exception("Error al cargar archivo tabular: %s", e)
            return False
    
    def get_sheet_names(self, file_path: str) -> List[str]:
        """
        Obtener los nombres de todas las hojas del archivo Excel
        
        Args:
            file_path: Ruta al archivo Excel
            
        Returns:
            Lista con los nombres de las hojas
        """
        try:
            workbook = openpyxl.load_workbook(file_path, read_only=True)
            return workbook.sheetnames
        except Exception as e:
            logger.exception("Error al leer hojas del Excel: %s", e)
            return []
    
    def detect_columns(self) -> Dict[str, List[str]]:
        """
        Detectar automáticamente las columnas relevantes
        
        Returns:
            Diccionario con las columnas detectadas para cada tipo
        """
        if self.df is None:
            return {}
        
        detected = {
            'primer_apellido': [],
            'segundo_apellido': [],
            'nombre': [],
            'especialidad': [],
            'etapa': [],
            'curso': [],
            'urls': []
        }
        
        # Analizar cada columna
        for column in self.df.columns:
            column_lower = column.lower()
            
            # Verificar patrones para cada tipo
            for column_type, patterns in self.column_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, column_lower, re.IGNORECASE):
                        detected[column_type].append(column)
                        break
        
        # Detectar URLs analizando el contenido de las columnas
        for column in self.df.columns:
            if column not in detected['urls']:
                # Verificar si la columna contiene URLs
                if self._column_contains_urls(column):
                    detected['urls'].append(column)
        
        self.detected_columns = detected
        
        logger.info("Columnas detectadas automáticamente")
        for column_type, columns in detected.items():
            logger.info("  %s: %s", column_type.capitalize(), columns)
        
        return detected
    
    def _column_contains_urls(self, column: str, sample_size: int = 10) -> bool:
        """
        Verificar si una columna contiene URLs analizando una muestra
        
        Args:
            column: Nombre de la columna
            sample_size: Número de filas a analizar
            
        Returns:
            True si la columna parece contener URLs
        """
        if column not in self.df.columns:
            return False
        
        # Tomar una muestra de la columna
        sample_data = self.df[column].dropna().head(sample_size)
        url_count = 0
        
        for value in sample_data:
            if isinstance(value, str) and self._is_url(value):
                url_count += 1
        
        # Considerar que contiene URLs si más del 30% son URLs válidas
        return url_count > len(sample_data) * 0.3
    
    def _is_url(self, text: str) -> bool:
        """
        Verificar si un texto es una URL válida
        
        Args:
            text: Texto a verificar
            
        Returns:
            True si es una URL válida
        """
        try:
            result = urlparse(text.strip())
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def get_suggested_columns(self, column_type: str) -> List[str]:
        """
        Obtener sugerencias de columnas para un tipo específico
        
        Args:
            column_type: Tipo de columna ('primer_apellido', 'segundo_apellido', 'nombre', 'etapa', 'curso', 'urls')
            
        Returns:
            Lista de columnas sugeridas
        """
        if column_type in self.detected_columns:
            return self.detected_columns[column_type]
        return []
    
    def set_column_mapping(self, mapping: Dict[str, str]):
        """
        Establecer manualmente el mapeo de columnas
        
        Args:
            mapping: Diccionario con el mapeo {tipo: nombre_columna}
        """
        self.column_mapping = mapping
        logger.info("Mapeo de columnas establecido: %s", mapping)
    
    def get_processed_data(self, column_mapping: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """
        Obtener los datos procesados usando el mapeo de columnas
        
        Args:
            column_mapping: Mapeo personalizado de columnas
            
        Returns:
            Lista de diccionarios con los datos procesados
        """
        if self.df is None:
            return []
        
        # Usar mapeo proporcionado o detectado automáticamente
        if column_mapping:
            mapping = column_mapping
        else:
            # Usar la primera columna detectada para cada tipo
            mapping = {}
            for column_type, columns in self.detected_columns.items():
                if columns:
                    mapping[column_type] = columns[0]
        
        processed_data = []
        
        for index, row in self.df.iterrows():
            student_data = {
                'index': index,
                'primer_apellido': '',
                'segundo_apellido': '',
                'nombre': '',
                'especialidad': '',
                'etapa': '',
                'curso': '',
                'urls': []
            }
            
            # Extraer primer apellido
            if 'primer_apellido' in mapping and mapping['primer_apellido'] in self.df.columns:
                primer_apellido = row[mapping['primer_apellido']]
                if pd.notna(primer_apellido):
                    student_data['primer_apellido'] = str(primer_apellido).strip().upper()
            
            # Extraer segundo apellido
            if 'segundo_apellido' in mapping and mapping['segundo_apellido'] in self.df.columns:
                segundo_apellido = row[mapping['segundo_apellido']]
                if pd.notna(segundo_apellido):
                    student_data['segundo_apellido'] = str(segundo_apellido).strip().upper()
            
            # Extraer nombre
            if 'nombre' in mapping and mapping['nombre'] in self.df.columns:
                nombre = row[mapping['nombre']]
                if pd.notna(nombre):
                    student_data['nombre'] = str(nombre).strip().upper()
            
            # Extraer especialidad/ciclo (agrupación principal de carpetas)
            if 'especialidad' in mapping and mapping['especialidad'] in self.df.columns:
                especialidad = row[mapping['especialidad']]
                if pd.notna(especialidad):
                    special_value = str(especialidad).strip().upper()
                    student_data['especialidad'] = special_value
                    student_data['etapa'] = special_value

            # Compatibilidad: extraer etapa si no se detectó especialidad
            if 'etapa' in mapping and mapping['etapa'] in self.df.columns:
                etapa = row[mapping['etapa']]
                if pd.notna(etapa) and not student_data['etapa']:
                    student_data['etapa'] = str(etapa).strip().upper()
            
            # Extraer curso (solo informativo, no para agrupación)
            if 'curso' in mapping and mapping['curso'] in self.df.columns:
                curso = row[mapping['curso']]
                if pd.notna(curso):
                    student_data['curso'] = str(curso).strip().upper()
            
            # Extraer URLs de todas las columnas que las contengan
            urls = []
            if 'urls' in self.detected_columns:
                for url_column in self.detected_columns['urls']:
                    if url_column in self.df.columns:
                        url_value = row[url_column]
                        if pd.notna(url_value) and isinstance(url_value, str):
                            url_value = url_value.strip()
                            if self._is_url(url_value):
                                urls.append({
                                    'url': url_value,
                                    'column': url_column,
                                    'filename': self._build_filename_from_field(url_column, url_value)
                                })
            
            student_data['urls'] = urls
            
            # Solo agregar si tiene datos mínimos
            if student_data['primer_apellido'] or student_data['nombre']:
                processed_data.append(student_data)
        
        logger.info("Datos procesados: %s estudiantes", len(processed_data))
        return processed_data

    def _build_filename_from_field(self, field_name: str, url: str) -> str:
        """
        Construir nombre de archivo a partir del nombre del campo de formulario.
        Conserva la extensión del archivo original cuando es posible.
        """
        base_name = str(field_name).strip()
        if not base_name:
            base_name = "DOCUMENTO"

        original_name = self._extract_filename_from_url(url)
        _, ext = os.path.splitext(original_name)
        ext = ext.lower()

        if ext:
            return f"{base_name}{ext}"
        return base_name
    
    def _extract_filename_from_url(self, url: str) -> str:
        """
        Extraer el nombre del archivo de una URL
        
        Args:
            url: URL del archivo
            
        Returns:
            Nombre del archivo o nombre generado
        """
        try:
            parsed = urlparse(url)
            path = parsed.path
            
            if path:
                filename = os.path.basename(path)
                if filename and '.' in filename:
                    return filename
            
            # Si no se puede extraer, generar un nombre basado en la URL
            return f"archivo_{hash(url) % 10000}.bin"
            
        except:
            return f"archivo_{hash(url) % 10000}.bin"
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Obtener un resumen del archivo Excel procesado
        
        Returns:
            Diccionario con información resumen
        """
        if self.df is None:
            return {}
        
        summary = {
            'file_path': self.file_path,
            'total_rows': len(self.df),
            'total_columns': len(self.df.columns),
            'columns': list(self.df.columns),
            'detected_columns': self.detected_columns,
            'empty_rows': self.df.isnull().all(axis=1).sum(),
            'students_with_data': 0,
            'total_urls': 0
        }
        
        # Contar estudiantes con datos y URLs
        processed_data = self.get_processed_data()
        summary['students_with_data'] = len(processed_data)
        summary['total_urls'] = sum(len(student['urls']) for student in processed_data)
        
        return summary
    
    def validate_data(self) -> List[str]:
        """
        Validar los datos y retornar lista de advertencias/errores
        
        Returns:
            Lista de mensajes de validación
        """
        warnings = []
        
        if self.df is None:
            warnings.append("No hay datos cargados")
            return warnings
        
        # Verificar columnas detectadas
        if not any(self.detected_columns.values()):
            warnings.append("No se detectaron columnas automáticamente. Revisa los nombres de las columnas.")
        
        if not self.detected_columns.get('primer_apellido') and not self.detected_columns.get('nombre'):
            warnings.append("No se detectaron columnas de nombres o apellidos")
        
        if not self.detected_columns.get('urls'):
            warnings.append("No se detectaron columnas con URLs para descargar")
        
        if not self.detected_columns.get('especialidad') and not self.detected_columns.get('etapa'):
            warnings.append("No se detectó la columna de ciclo/especialidad para clasificar")
        
        # Verificar datos vacíos
        processed_data = self.get_processed_data()
        students_without_names = sum(1 for student in processed_data 
                                   if not student['primer_apellido'] and not student['nombre'])
        
        if students_without_names > 0:
            warnings.append(f"{students_without_names} estudiantes sin nombres/apellidos")
        
        students_without_urls = sum(1 for student in processed_data if not student['urls'])
        if students_without_urls > 0:
            warnings.append(f"{students_without_urls} estudiantes sin URLs para descargar")
        
        return warnings

def create_excel_processor() -> ExcelProcessor:
    """
    Crear una instancia del procesador de Excel
    
    Returns:
        Instancia de ExcelProcessor
    """
    return ExcelProcessor()