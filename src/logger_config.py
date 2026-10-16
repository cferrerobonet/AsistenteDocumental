"""
Configuracion central de logging para la aplicacion.
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

try:
    from src.rutas import CARPETA, base_del_sistema
except ImportError:
    from rutas import CARPETA, base_del_sistema

_LOGGER_INITIALIZED = False


def setup_logging() -> None:
    """Inicializa logging una sola vez para toda la aplicacion."""
    global _LOGGER_INITIALIZED
    if _LOGGER_INITIALIZED:
        return

    log_dir = os.path.join(base_del_sistema(), CARPETA, "logs")
    os.makedirs(log_dir, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # Solo agregar stream si hay salida de consola disponible.
    try:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        root_logger.addHandler(stream_handler)
    except Exception:
        pass

    _LOGGER_INITIALIZED = True


def get_logger(name: str) -> logging.Logger:
    """Devuelve un logger con configuracion centralizada."""
    setup_logging()
    return logging.getLogger(name)
