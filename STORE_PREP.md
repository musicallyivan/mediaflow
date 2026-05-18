# Preparacion para Microsoft Store

Este proyecto se presenta como convertidor multimedia local. La funcionalidad principal es convertir archivos locales de audio, video e imagen y guardar el resultado en una carpeta elegida por el usuario.

## Antes de enviar

1. Cambiar el nombre del repositorio y del producto a `media-converter` o un nombre comercial propio.
2. Crear iconos de Store en todos los tamaños requeridos.
3. Crear una politica de privacidad publica. Aunque la app no recoja datos personales, conviene declarar que los archivos se procesan localmente y no se suben a servidores.
4. Revisar la licencia de `ffmpeg` y distribuir los avisos de licencia correspondientes junto al instalador.
5. Firmar el binario o el instalador con certificado de firma de codigo valido.
6. Preparar un instalador `.msi` o `.exe` standalone con instalacion silenciosa, o empaquetar como MSIX.
7. Usar una URL versionada para cada binario enviado a Partner Center.
8. Evitar en titulo, descripcion, capturas y keywords cualquier referencia a servicios de video, descarga de videos o extraccion de musica desde servicios de terceros.
9. Explicar que la sincronizacion con Google Drive, OneDrive e iCloud Drive se hace guardando archivos en carpetas locales ya sincronizadas por los clientes oficiales.

## Descripcion sugerida

Convertidor multimedia local para Windows. Permite elegir archivos del equipo y crear copias en formatos comunes de audio, video e imagen. Puede guardar resultados en carpetas locales o en carpetas sincronizadas por OneDrive, Google Drive o iCloud Drive.

## Notas de certificacion sugeridas

La app convierte archivos locales seleccionados por el usuario. No descarga contenido de servicios de terceros, no requiere inicio de sesion, no recoge credenciales y no sube archivos directamente a servidores externos. La sincronizacion en nube se realiza guardando el resultado en carpetas locales gestionadas por los clientes oficiales instalados por el usuario.
