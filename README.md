# Media Flow Pro

Versión actual: `1.6.1`

Media Flow es una suite completa y local para Windows que convierte, recorta, comprime y procesa archivos de audio, video e imagen con aceleración por hardware mediante `ffmpeg`.

## Funciones Destacadas

- **Conversión de audio:** `MP3`, `M4A`, `WAV`, `FLAC`, `OGG`, `OPUS`, `AAC`, `ALAC`, `AIFF`.
- **Conversión de video:** `MP4`, `MOV`, `WEBM`, `MKV`, `GIF`, `AVI`, `AV1`, `H.265 (HEVC)`.
- **Conversión de imagen:** `PNG`, `JPG`, `WEBP`, `BMP`, `AVIF`, `ICO`, `TIFF`.
- **Modos Especiales:**
  - Extraer audio de videos a MP3.
  - Silenciar videos (eliminar pista de audio).
  - Extraer subtítulos en `.srt`.
  - Unir/Concatenar múltiples archivos de audio o video en uno solo.
- **Aceleración por Hardware (GPU):** Codificación acelerada automática con NVIDIA NVENC, AMD AMF o Intel QSV.
- **Procesamiento Multihilo por Lotes:** Procesar múltiples archivos en paralelo acelerando las conversiones en lotes masivos.
- **Recorte de Tiempo (Trim):** Especifica tiempo de inicio y fin (`hh:mm:ss`).
- **Compresión a Tamaño Objetivo:** Especifica un tamaño máximo en MB (ej. 25 MB para Discord) y ajusta bitrate automáticamente.
- **Preajustes Rápidos (Presets):** Configuración lista para usar (Optimizado para Web, WhatsApp/Redes, TikTok/Reels, Lossless).
- **Redimensión y FPS:** Escala resoluciones (4K, 1080p, 720p, 480p) y tasas de refresco (60fps, 30fps, 24fps).
- **Notificaciones Nativas de Windows:** Alertas globales al finalizar conversiones en segundo plano.
- **Historial de Conversiones:** Registro reciente con apertura rápida de archivo o carpeta en Explorer.
- **Tema Claro y Oscuro:** Interfaz moderna rediseñada con tarjetas pulidas y esquinas redondeadas.
- **Sincronización con Nube:** Salida directa a carpetas locales de OneDrive, Google Drive o iCloud Drive.

La app no descarga contenido de servicios de terceros. Convierte archivos locales que ya tengas derecho a usar.

## Instalacion

1. En Releases, descarga el instalador `.exe` si quieres una instalacion guiada.
2. Si prefieres una copia portable, descarga el ZIP.
3. Abre Media Flow y elige el archivo que quieres convertir.

## Requisitos

1. Windows 10 o Windows 11.
2. `ffmpeg` incluido en la version empaquetada o instalado en el sistema.

## Version Android

Hay una primera version nativa para Android en `android-app/`. No usa WebView:
selecciona archivos con el selector de Android, convierte localmente con
FFmpegKit y guarda los resultados en `Descargas/MediaFlow`.

Abre `android-app/` con Android Studio para compilarla.

## Uso

1. Abre Media Flow.
2. Elige `Audio`, `Video` o `Imagen`.
3. Selecciona uno o varios archivos locales.
4. Elige el formato y la calidad.
5. Elige la carpeta de salida o una carpeta sincronizada disponible.
6. Pulsa `Convertir`.

Puedes cambiar entre modo claro y oscuro desde el boton de la esquina superior derecha.

## Sincronizacion con nube

Media Flow no pide cuentas ni contrasenas. Si OneDrive, Google Drive o iCloud Drive estan instalados, detecta sus carpetas locales y guarda ahi el archivo convertido. El cliente oficial de cada servicio se encarga de la sincronizacion.

## Privacidad

Media Flow procesa los archivos localmente. No sube tus archivos a servidores propios y no requiere iniciar sesion.

Consulta `PRIVACY.md` para mas detalles.
