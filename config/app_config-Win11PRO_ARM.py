"""
Configuración de la aplicación
"""

# ============================================
# CONFIGURACIÓN DE AUTENTICACIÓN
# ============================================

# Modo de autenticación: 'simple' o 'msal'
# 'simple': Autenticación directa con credenciales (NO requiere Azure AD)
# 'msal': Autenticación OAuth con MSAL (requiere Azure AD y permisos)
AUTH_MODE = "simple"  # Cambia a 'msal' si tienes acceso a Azure AD

# Configuración para autenticación simple (sin Azure AD)
SIMPLE_AUTH_CONFIG = {
    "enabled": True,
    "default_sharepoint_url": "https://epluisamigogodella-my.sharepoint.com",
    "description": "Autenticación directa sin Azure AD - Solo usuario y contraseña"
}

# Configuración de Microsoft Graph API (para modo MSAL)
CLIENT_ID = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"  # Azure CLI

GRAPH_CONFIG = {
    "client_id": CLIENT_ID,
    "client_secret": None,  # No se requiere para aplicaciones públicas
    "authority": "https://login.microsoftonline.com/organizations",
    "scope": [
        "https://graph.microsoft.com/User.Read",
        "https://graph.microsoft.com/Files.Read.All",
        "https://graph.microsoft.com/Sites.Read.All"
    ]
}

# Configuración alternativa para evitar problemas de permisos
MINIMAL_CONFIG = {
    "client_id": CLIENT_ID,
    "client_secret": None,
    "authority": "https://login.microsoftonline.com/organizations", 
    "scope": [
        "https://graph.microsoft.com/User.Read"
    ]
}

# Configuración de la interfaz
UI_CONFIG = {
    "window_title": "Asistente de Documentación",
    "window_size": "700x650",  # Ventana más compacta
    "theme": "superhero",  # Tema moderno oscuro
    "logo_path": "imágenes/logo.png",
    "colors": {
        "primary": "#0078d4",
        "secondary": "#106ebe",
        "success": "#107c10",
        "warning": "#ff8c00",
        "danger": "#d83b01",
        "light": "#f3f2f1",
        "dark": "#201f1e"
    }
}

# Configuración de archivos
FILE_CONFIG = {
    "supported_excel_formats": [".xlsx", ".xls"],
    "max_file_size_mb": 500,
    "download_timeout": 30,
    "chunk_size": 1024 * 1024  # 1MB chunks para descarga
}

# Patrones para identificar columnas dinámicamente
COLUMN_PATTERNS = {
    "primer_apellido": ["primer apellido", "apellido 1", "first surname"],
    "segundo_apellido": ["segundo apellido", "apellido 2", "second surname"],
    "nombre": ["nombre del alumno", "nombre alumno", "first name student"],
    "etapa": ["etapa", "stage", "nivel educativo"],
    "curso": ["curso", "course", "grado", "grade"],
    "urls": ["url", "link", "enlace", "archivo", "file", "descarga", "download"]
}

# Configuración de carpetas
FOLDER_CONFIG = {
    "create_timestamp_folders": False,  # Crear carpetas con timestamp
    "normalize_names": True,  # Normalizar nombres de carpetas (mayúsculas, sin caracteres especiales)
    "max_folder_name_length": 100
}
