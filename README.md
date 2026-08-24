# Media Flow Suite

Versión actual: `1.7.1`

Media Flow es una suite multimedia moderna para Windows con diseño contemporáneo de tarjetas y esquinas redondeadas, que convierte, recorta, comprime y procesa archivos de audio, video e imagen con aceleración por hardware mediante `ffmpeg`.

## 💎 Versión Gratuita vs Complemento PRO

Media Flow incluye un sistema de niveles con un **Complemento PRO** para usuarios avanzados:

| Característica | Versión Gratuita | Complemento PRO |
| :--- | :--- | :--- |
| **Formatos Estándar** | MP3, M4A, WAV, OGG, AAC, MP4, MOV, WEBM, AVI, GIF, PNG, JPG... | Todos los estándar + Hi-Fi |
| **Formatos Hi-Fi & Lossless** | ❌ Básico | ✔ FLAC, OPUS, ALAC, AIFF, AV1, H.265 (HEVC) |
| **Aceleración Hardware GPU** | Solo codificación por CPU | ✔ NVIDIA NVENC / AMD AMF / Intel QSV (10x más rápido) |
| **Multihilo en Lote** | 1 archivo a la vez | ✔ Hasta 8 conversiones en paralelo |
| **Resolución & FPS** | Hasta 1080p / 30 fps | ✔ 4K Ultra HD (2160p) y 60 FPS |
| **Herramientas de Edición** | ❌ Bloqueado | ✔ Recorte milimétrico (Trim) y Compresión a Tamaño Objetivo (MB) |
| **Modos Especiales** | ❌ Básico | ✔ Extracción de audio/subtítulos SRT y Unión/Concatenación |
| **Sincronización en la Nube** | Guardado local | ✔ Exportación automática a OneDrive, Google Drive, iCloud |
| **Interfaz Moderna** | ✔ Bordes redondeados y Dark/Light Mode | ✔ Bordes redondeados, Temas e insignia VIP |

La app no descarga contenido de servicios de terceros. Convierte archivos locales que ya tengas derecho a usar. PRO es opcional y se puede activar con una clave o mediante los canales de compra disponibles.

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

Las funciones gratuitas de Media Flow no piden cuentas ni contrasenas. Si OneDrive, Google Drive o iCloud Drive estan instalados, detecta sus carpetas locales y guarda ahi el archivo convertido. El cliente oficial de cada servicio se encarga de la sincronizacion. El complemento PRO opcional ofrece exportación automática a estas carpetas compatibles.

## Privacidad

Media Flow procesa los archivos localmente y no sube tus archivos a servidores propios. Las funciones gratuitas no requieren iniciar sesión; los pagos opcionales de PRO se gestionan por el proveedor de compra seleccionado.

Consulta `PRIVACY.md` para mas detalles.
