"""
Acceso a secretos para auto-login.
Prioriza Windows Credential Manager y usa variables de entorno como fallback.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
from typing import Optional, Tuple

try:
    from src.logger_config import get_logger
except ImportError:
    from logger_config import get_logger

logger = get_logger(__name__)

_CRED_TYPE_GENERIC = 1
_CRED_PERSIST_LOCAL_MACHINE = 2


class _CREDENTIALW(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", ctypes.c_byte * 8),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_byte)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


_PCREDENTIALW = ctypes.POINTER(_CREDENTIALW)


def _is_windows() -> bool:
    return os.name == "nt"


def _decode_blob(cred: _CREDENTIALW) -> str:
    size = int(cred.CredentialBlobSize)
    if size <= 0 or not cred.CredentialBlob:
        return ""

    raw = ctypes.string_at(cred.CredentialBlob, size)

    # cmdkey suele guardar en UTF-16LE en Windows.
    for encoding in ("utf-16-le", "utf-8", "latin-1"):
        try:
            return raw.decode(encoding).rstrip("\x00")
        except UnicodeDecodeError:
            continue

    return ""


def get_windows_credential(target_name: str) -> Optional[Tuple[str, str]]:
    """
    Leer credencial genérica de Windows Credential Manager.

    Devuelve (username, password) si existe, o None en caso contrario.
    """
    if not _is_windows():
        return None

    advapi32 = ctypes.WinDLL("Advapi32.dll")

    cred_ptr = _PCREDENTIALW()
    CredReadW = advapi32.CredReadW
    CredReadW.argtypes = [wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(_PCREDENTIALW)]
    CredReadW.restype = wintypes.BOOL

    CredFree = advapi32.CredFree
    CredFree.argtypes = [ctypes.c_void_p]
    CredFree.restype = None

    ok = CredReadW(target_name, _CRED_TYPE_GENERIC, 0, ctypes.byref(cred_ptr))
    if not ok:
        return None

    try:
        cred = cred_ptr.contents
        username = cred.UserName or ""
        password = _decode_blob(cred)
        if username and password:
            return username, password
        return None
    finally:
        CredFree(cred_ptr)


def load_auto_login_credentials() -> Optional[dict]:
    """
    Cargar credenciales para auto-login.

    Orden de prioridad:
    1) Credential Manager: target EPLA_AUTLOGIN
    2) Variables de entorno EPLA_AUTLOGIN_USER / EPLA_AUTLOGIN_PASSWORD
    """
    cred = get_windows_credential("EPLA_AUTLOGIN")
    if cred:
        username, password = cred
        logger.info("Credenciales de auto-login cargadas desde Credential Manager")
        return {"username": username.strip(), "password": password.strip()}

    username = os.environ.get("EPLA_AUTLOGIN_USER", "").strip()
    password = os.environ.get("EPLA_AUTLOGIN_PASSWORD", "").strip()
    if username and password:
        logger.info("Credenciales de auto-login cargadas desde variables de entorno")
        return {"username": username, "password": password}

    return None
