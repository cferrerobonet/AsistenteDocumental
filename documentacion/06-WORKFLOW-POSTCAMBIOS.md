# Workflow Postcambios

Este documento define el flujo obligatorio tras cualquier cambio funcional o técnico en el proyecto.

## Objetivo

Garantizar trazabilidad, versionado consistente y documentación mínima en cada entrega.

## Flujo Obligatorio

1. Validar cambios locales
- Ejecutar `python -m pytest` con `QT_QPA_PLATFORM=offscreen` y, si cambia la interfaz, revisar las ventanas.
- Verificar que no hay cambios inesperados.

2. Bump de versión
- Incrementar versión del proyecto antes del commit final.
- Referencias mínimas (un test comprueba que coinciden):
  - `src/__init__.py` (`__version__`: la fuente; la usan la app, el actualizador y la compilación).
  - `README.md` («Versión actual»).
  - `installer_setup.iss` (`MyAppVersion` por defecto).
  - `CHANGELOG.md` (entrada `## [X.Y.Z] - AAAA-MM-DD`).
  - `src/recursos/novedades.md` (lo que se cuenta a la persona usuaria, sin jerga).
- Regla recomendada:
  - Cambios funcionales: subir versión menor (ej. 3.0 -> 3.1).
  - Ajustes menores/fixes: subir parche (ej. 3.1.0 -> 3.1.1).

3. Documentar si procede
- Actualizar documentación cuando cambie comportamiento, formato de entrada o estructura de salida.
- Documentos típicos a revisar:
  - `README.md`
  - `documentacion/01-INICIO_RAPIDO.md`
  - `documentacion/04-RESUMEN-TECNICO.md`
  - `documentacion/00-INDICE.md` (si se añade un documento nuevo)

4. Commit
- Hacer commit con mensaje claro y orientado a cambio real.
- Formato recomendado:
  - `feat: ...` para funcionalidad nueva
  - `fix: ...` para correcciones
  - `docs: ...` para cambios solo documentales
  - `chore: ...` para mantenimiento

5. Push
- Subir a remoto inmediatamente tras commit:
  - `git push origin main`

6. Verificación final
- Confirmar sincronización local/remoto:
  - `git status -sb`
  - Resultado esperado: `main...origin/main` sin `ahead`/`behind`.

## Checklist Rápido

- [ ] Cambios validados localmente
- [ ] Versión incrementada
- [ ] Documentación actualizada (si aplica)
- [ ] Commit realizado
- [ ] Push realizado
- [ ] Repositorio sincronizado con remoto

## Nota Operativa

Este workflow se considera estándar del proyecto y debe seguirse en cada entrega para evitar cambios sin traza o versiones inconsistentes.

## Skills recomendadas para automatizar el flujo

- `postcambios-cierre`: ejecuta y verifica el cierre completo (commit, push, bump de version y documentacion).
- `python-quality-gate`: valida calidad minima y regresiones antes del cierre.

Ubicacion de skills del proyecto:

- `.github/skills/postcambios-cierre/SKILL.md`
- `.github/skills/python-quality-gate/SKILL.md`

Uso recomendado:

1. Ejecutar quality gate (`/python-quality-gate`) durante o al final del desarrollo.
2. Ejecutar cierre (`/postcambios-cierre`) para finalizar entrega de forma estandarizada.