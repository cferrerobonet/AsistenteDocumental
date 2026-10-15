---
name: python-quality-gate
description: 'Quality gate para cambios Python. Use when: antes de commit, validar regresiones, comprobar parsing CSV/Excel, clasificacion por ciclo y nomenclatura de carpetas/adjuntos.'
argument-hint: 'Indica alcance: rapido | completo y archivos tocados.'
user-invocable: true
---

# Python Quality Gate

Skill para aplicar una puerta de calidad estandar antes de commitear cambios en el proyecto.

## Cuando usar

- Antes de cada commit en `src/`.
- Tras cambios en parsing de datos (Excel/CSV).
- Tras cambios en reglas de clasificacion y nombres de archivos/carpetas.

## Checklist

1. Errores estaticos
- Ejecutar revision de errores en archivos modificados.
- Corregir errores nuevos antes de continuar.

2. Regresiones funcionales clave
- Verificar soporte de entrada `.xlsx`, `.xls`, `.csv`.
- Verificar deteccion de columna de ciclo/especialidad (ej. "Indique el ciclo al que pertenece").
- Verificar que la carpeta principal se crea por ciclo/especialidad.
- Verificar subcarpeta de alumno en formato `APELLIDOS NOMBRE` (mayusculas, sin `_`).
- Verificar que adjuntos se nombran por nombre de campo (manteniendo extension cuando sea posible).

3. Consistencia de UI
- Confirmar texto y selector de archivos en UI para Excel/CSV.
- Confirmar que el flujo principal no cambia fuera del objetivo del cambio.

4. Documentacion minima
- Si cambia comportamiento, actualizar:
  - `README.md`
  - `documentacion/01-INICIO_RAPIDO.md`
  - `documentacion/04-RESUMEN-TECNICO.md` (si aplica)

5. Preparacion de entrega
- Si todo pasa, recomendar `postcambios-cierre` para finalizar con commit/push/versionado.

## Criterio de aprobacion

- Sin errores nuevos.
- Reglas de negocio clave validadas.
- Documentacion coherente con el comportamiento real.
- Cambios listos para cierre de entrega.
