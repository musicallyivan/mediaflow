# Preparacion para Microsoft Store

Este proyecto se presenta como convertidor multimedia local. La funcionalidad principal es convertir archivos locales de audio, video e imagen y guardar el resultado en una carpeta elegida por el usuario.

## Antes de enviar

1. Cambiar el nombre del repositorio y del producto a `media-converter` o un nombre comercial propio.
2. Crear iconos de Store en todos los tamaños requeridos.
3. Publicar una politica de privacidad publica. Puedes usar `PRIVACY.md` como base.
4. Revisar la licencia de `ffmpeg` y distribuir los avisos de licencia correspondientes junto al instalador. El proyecto incluye `THIRD_PARTY_NOTICES.md`.
5. Elegir empaquetado:
   - Recomendado: MSIX para que Microsoft Store gestione firma y actualizaciones.
   - Alternativa: instalador `.msi` o `.exe` firmado con instalacion silenciosa.
6. Si usas MSI/EXE, firmar el instalador con certificado Authenticode valido de una CA reconocida.
7. Preparar capturas de pantalla en modo claro, modo oscuro y conversion en progreso.
8. Usar una URL versionada para cada binario enviado a Partner Center.
9. Evitar en titulo, descripcion, capturas y keywords cualquier referencia a servicios de video, descarga de videos o extraccion de musica desde servicios de terceros.
10. Explicar que la sincronizacion con Google Drive, OneDrive e iCloud Drive se hace guardando archivos en carpetas locales ya sincronizadas por los clientes oficiales.

## Descripcion sugerida

Convertidor multimedia local para Windows. Permite elegir archivos del equipo y crear copias en formatos comunes de audio, video e imagen. Puede guardar resultados en carpetas locales o en carpetas sincronizadas por OneDrive, Google Drive o iCloud Drive.

## Notas de certificacion sugeridas

La app convierte archivos locales seleccionados por el usuario. No descarga contenido de servicios de terceros, no requiere inicio de sesion, no recoge credenciales y no sube archivos directamente a servidores externos. La sincronizacion en nube se realiza guardando el resultado en carpetas locales gestionadas por los clientes oficiales instalados por el usuario.
