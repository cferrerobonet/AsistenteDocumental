"""Baja a drivers/ el msedgedriver estable de este sistema para empaquetarlo.

Lo usa .github/workflows/compilar.yml antes de PyInstaller: el driver ya no se
versiona (ASD-SEC-001), pero va dentro del instalador y del .app para que la app
funcione sin red la primera vez. Usa la misma dirección y el mismo paquete que el
actualizador de la app (src/driver_updater.py): si Microsoft los cambia, falla la
compilación y no el equipo de Secretaría.

    python scripts/descargar_driver.py            # LATEST_STABLE
    python scripts/descargar_driver.py 141.0.3537.99
"""

from __future__ import annotations

import io
import os
import subprocess  # nosec B404 - ejecuta el driver recién bajado para ver su versión
import sys
import urllib.request
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src import driver_updater as du  # noqa: E402
from src.actualizaciones import contexto_ssl  # noqa: E402


def main(argv: list[str]) -> int:
    version = argv[1] if len(argv) > 1 else du.version_remota("LATEST_STABLE")
    if not version:
        print("[ERROR] No se pudo saber la versión estable del driver")
        return 1
    url = f"{du._MS_DRIVER_BASE}/{version}/{du.paquete_driver()}"
    print(f"Descargando {url}")
    with urllib.request.urlopen(url, timeout=120, context=contexto_ssl()) as r:  # nosec B310 - URL fija de Microsoft
        datos = r.read()
    with zipfile.ZipFile(io.BytesIO(datos)) as zf:
        contenido = zf.read(du._DRIVER_EXE)
    destino = RAIZ / "drivers" / du._DRIVER_EXE
    destino.parent.mkdir(exist_ok=True)
    destino.write_bytes(contenido)
    os.chmod(destino, 0o755)
    salida = subprocess.run([str(destino), "--version"], capture_output=True, text=True, timeout=30)  # nosec B603
    print(salida.stdout.strip())
    if version not in salida.stdout:
        print(f"[ERROR] El driver no dice ser la {version}")
        return 1
    print(f"[OK] {destino.relative_to(RAIZ)}: {len(contenido) / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
