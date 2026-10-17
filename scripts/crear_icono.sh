#!/bin/bash
# Crea los iconos de la aplicación a partir de imagenes/icono.png (1024×1024 con
# transparencia; la fuente vectorial es imagenes/icono.svg):
#   • imagenes/icono.ico  (Windows: exe e instalador), con Pillow, 16 a 256 px.
#   • imagenes/icono.icns (macOS: el .app), con sips e iconutil.
# Procedimiento copiado de Partes de salida (scripts/build/crear_icono.sh). Sólo en
# macOS; los dos iconos van en el repositorio y la compilación de GitHub los usa tal cual.
# Uso: PYTHON=~/.venvs/asistente-documental/bin/python scripts/crear_icono.sh
set -e
cd "$(dirname "$0")/.."
[ -f imagenes/icono.png ] || { echo "Falta imagenes/icono.png"; exit 1; }
"${PYTHON:-python3}" - <<'PY'
from PIL import Image

im = Image.open("imagenes/icono.png").convert("RGBA")
tamanos = [(t, t) for t in (16, 24, 32, 48, 64, 128, 256)]
im.save("imagenes/icono.ico", format="ICO", sizes=tamanos)
PY
echo "Icono creado: imagenes/icono.ico"
SET="imagenes/icono.iconset"
rm -rf "$SET" && mkdir -p "$SET"
for t in 16 32 128 256 512; do
    sips -z $t $t imagenes/icono.png --out "$SET/icon_${t}x${t}.png" >/dev/null
    d=$((t * 2))
    sips -z $d $d imagenes/icono.png --out "$SET/icon_${t}x${t}@2x.png" >/dev/null
done
iconutil -c icns "$SET" -o imagenes/icono.icns
rm -rf "$SET"
echo "Icono creado: imagenes/icono.icns"
