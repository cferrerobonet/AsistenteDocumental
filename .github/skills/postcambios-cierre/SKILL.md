---
name: postcambios-cierre
description: 'Cierre postcambios con estandar del proyecto. Use when: finalizar tareas, preparar entrega, hacer commit, push, bump de version y actualizar documentacion.'
argument-hint: 'Describe brevemente el cambio para generar cierre completo (commit/push/version/docs).'
user-invocable: true
---

# Cierre Postcambios

Skill para ejecutar el flujo de cierre obligatorio del proyecto con trazabilidad completa.

## Cuando usar

- Al terminar cualquier cambio funcional o tecnico.
- Antes de dar una tarea por cerrada.
- Cuando se necesite asegurar commit + push + version + documentacion.

## Procedimiento

1. Revisar cambios
- Ejecutar estado git y confirmar que solo se incluyen archivos esperados.
- Revisar diffs para evitar cambios accidentales.

2. Validar calidad minima
- Revisar errores del workspace en archivos modificados.
- Ejecutar comprobaciones rapidas de funcionamiento si aplica.

3. Bump de version
- Actualizar `src/__init__.py` (`__version__`, la fuente).
- Actualizar `README.md` (version visible).
- Actualizar `installer_setup.iss` (`MyAppVersion`).
- Anadir la entrada en `CHANGELOG.md` y las novedades en `src/recursos/novedades.md` (tests/test_proyecto.py comprueba que coinciden).
- Regla recomendada:
  - funcionalidad nueva: bump menor
  - fix/documentacion: bump parche

4. Documentar si procede
- Actualizar docs afectadas por cambios de comportamiento:
  - `README.md`
  - `documentacion/01-INICIO_RAPIDO.md`
  - `documentacion/04-RESUMEN-TECNICO.md`
  - `documentacion/00-INDICE.md` si hay archivos nuevos

5. Commit
- Mensaje claro con convencion (`feat`, `fix`, `docs`, `chore`).
- Confirmar que el commit agrupa cambios coherentes.

6. Push
- Hacer push a `origin/main`.
- En repos sincronizado con OneDrive, preferir:
  - `git -c gc.auto=0 push origin main`

7. Verificacion final
- Confirmar sincronizacion:
  - `git status -sb`
  - `git rev-list --left-right --count origin/main...HEAD`
- Resultado esperado: sin ahead/behind.

## Salida esperada

- Commit creado y subido a remoto.
- Version actualizada.
- Documentacion alineada.
- Resumen final con hash de commit y estado de sincronizacion.
