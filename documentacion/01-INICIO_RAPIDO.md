# 🎓 Asistente de Documentación EPLA - Guía de Inicio Rápido

## 🚀 Comenzar en 3 Pasos

### 1️⃣ Ejecutar la Aplicación
Abre **Asistente de Documentación EPLA** desde el menú Inicio o el escritorio (en desarrollo: `python main.py`).

La ventana tiene tres pasos, de arriba abajo. La primera vez tras una actualización se abre antes la ventana **Novedades**.

### 2️⃣ Autenticarse
Paso 1 de la ventana:

1. Pulsa **«Iniciar sesión en SharePoint»**
2. En la ventana que se abre, pulsa **«Abrir navegador»**: Edge inicia sesión con la cuenta de secretaría
3. Completa MFA si aplica
4. Cuando llegue a OneDrive, pulsa **«Capturar sesión»**

### 3️⃣ Procesar Archivos
1. Paso 2: **«Seleccionar…»** junto a *Carpeta de destino* y junto a *Archivo de datos* (Excel o CSV con las respuestas del formulario)
2. Paso 3: **«Procesar archivos»**. La barra muestra el avance; **«Cancelar»** detiene el proceso al terminar el archivo en curso
3. Al acabar, un resumen dice cuántos alumnos, carpetas y descargas correctas y fallidas hay

---

## 📋 Formato del Archivo (Excel/CSV)

Tu archivo debe tener, como mínimo, estas columnas:

| Primer apellido del alumno/a | Segundo apellido del alumno/a | Nombre del alumno/a | Indique el ciclo al que pertenece | Campo de adjunto |
|-----------------------------|------------------------------|---------------------|-----------------------------------|------------------|
| García | Ejemplo | Ana | Gestión Administrativa | Modelo 046 Tasas Título |
| López | Prueba | Pablo | Carrocería | Justificante del pago de Tasas de título |

> **Nota**: El sistema detecta automáticamente las columnas aunque tengan nombres diferentes.

## 📁 Cómo se organiza en local

1. Carpeta principal por **ciclo/especialidad**.
2. Dentro, subcarpeta por alumno con nombre **APELLIDOS NOMBRE** en mayúsculas y sin guiones bajos.
3. Cada adjunto se guarda con el **nombre del campo** del formulario (manteniendo extensión cuando es posible).

---

## 🔐 Si tienes MFA (Autenticación de Dos Factores)

Completa el segundo factor normalmente durante el login del navegador.
No necesitas configurar Azure AD manualmente para usar la aplicación.

---

## 🔒 Auto-login seguro (recomendado en Windows)

La aplicación busca primero credenciales en Windows Credential Manager.

1. Guardar credencial genérica en Windows:
```powershell
cmdkey /generic:EPLA_AUTLOGIN /user:usuario@epla.es /pass:TU_PASSWORD
```
2. Reiniciar la aplicación.

Fallback opcional: variables de entorno `EPLA_AUTLOGIN_USER` y `EPLA_AUTLOGIN_PASSWORD`.

---

## 🧪 Modo simulación (solo desarrollo)

En producción, si faltan módulos críticos la aplicación falla al iniciar (fail-fast).
Para pruebas de desarrollo:

```powershell
$env:EPLA_ALLOW_SIMULATION="1"
python main.py
```

---

## ⚠️ Solución Rápida de Problemas

| Problema | Solución |
|----------|----------|
| **"No se pudo autenticar"** | Verifica correo y contraseña. Si tienes MFA, usa contraseña de aplicación |
| **"Error de conexión"** | Verifica tu internet. Intenta acceder a SharePoint desde el navegador |
| **"No se encontraron archivos"** | Verifica que el Excel/CSV tenga columnas de adjuntos con URLs válidas |

---

## 📚 Más Información

- **Guía de Usuario**: Ver `02-GUIA-USUARIO.md`
- **Autenticación**: Ver `03-AUTENTICACION-SIMPLE.md`
- **Resumen Técnico**: Ver `04-RESUMEN-TECNICO.md`
- **Solución de Problemas**: Ver `05-SOLUCION-PROBLEMAS.md`

---

## ✅ Checklist de Verificación

Antes de usar la aplicación, asegúrate de:

- [ ] Tener la aplicación instalada (o, en desarrollo, Python 3.13 y `pip install -r requirements.txt`)
- [ ] Tener configurada la credencial `EPLA_AUTLOGIN` de la cuenta de secretaría en el Administrador de credenciales
- [ ] Tener acceso a SharePoint de EPLA
- [ ] Tener un archivo Excel o CSV con los datos de estudiantes

---

**Versión**: 4.0.0 | **Fecha**: Octubre 2026  
**Sistema**: Autenticación por navegador + captura de sesión
