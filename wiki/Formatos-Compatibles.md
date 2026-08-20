# 🎥 Formatos y Códecs Compatibles

Media Flow Pro utiliza el motor multimedia **FFmpeg** integrado para ofrecer compatibilidad masiva con formatos de entrada y salida.

---

## 🎵 Formatos de Audio

| Formato | Extensión | Códec Utilizado | Descripción / Uso Recomendado |
| :--- | :--- | :--- | :--- |
| **MP3** | `.mp3` | `libmp3lame` | Estándar universal compatible con cualquier reproductor. |
| **M4A** | `.m4a` | `aac` | Formato eficiente ideal para dispositivos Apple y móviles. |
| **WAV** | `.wav` | `pcm_s16le` | Audio sin compresión (PCM 16-bit). Ideal para edición profesional. |
| **FLAC** | `.flac` | `flac` | Compresión sin pérdida de calidad (Lossless). Fidelidad Hi-Fi. |
| **OGG** | `.ogg` | `libvorbis` | Formato abierto de alta calidad y compresión. |
| **OPUS** | `.opus` | `libopus` | Códec ultra moderno con la mejor relación calidad/bitrate. |
| **AAC** | `.aac` | `aac` | Códec de audio estándar para streaming y video. |
| **ALAC** | `.alac` | `alac` | Audio Lossless de Apple. |
| **AIFF** | `.aiff` | `pcm_s16be` | Formato sin compresión utilizado en entornos Mac/Estudio. |

---

## 🎬 Formatos de Video

| Formato | Extensión | Códec por Defecto | Aceleración GPU | Uso Recomendado |
| :--- | :--- | :--- | :--- | :--- |
| **MP4** | `.mp4` | H.264 (`libx264`) | `h264_nvenc`, `h264_amf`, `h264_qsv` | Estándar web, redes sociales y dispositivos. |
| **H.265 (HEVC)**| `.mp4` | H.265 (`libx265`) | `hevc_nvenc`, `hevc_amf`, `hevc_qsv` | Máxima compresión 4K con 50% menos peso. |
| **WEBM** | `.webm` | VP9 (`libvpx-vp9`) | N/A (CPU) | Optimizado para páginas web y navegadores. |
| **MKV** | `.mkv` | H.264 / H.265 | `h264_nvenc` / `hevc_nvenc` | Contenedor flexible con múltiples subtítulos y audios. |
| **GIF Animado** | `.gif` | PaletteGen / Lanczos | N/A | Animación sin sonido para chats y foros. |
| **AVI** | `.avi` | MPEG-4 / H.264 | `h264_nvenc` | Compatibilidad con televisores y reproductores antiguos. |
| **AV1** | `.mp4` | `libsvtav1` | N/A | Códec de video de nueva generación ultra ligero. |

---

## 🖼️ Formatos de Imagen

| Formato | Extensión | Características |
| :--- | :--- | :--- |
| **PNG** | `.png` | Soporta transparencia de canal alfa. Compresión sin pérdida. |
| **JPG** | `.jpg` / `.jpeg` | Fotografía estándar con compresión ajustable. |
| **WEBP** | `.webp` | Formato de imagen ultraligero para sitios web modernos. |
| **BMP** | `.bmp` | Mapa de bits sin compresión nativo de Windows. |
| **AVIF** | `.avif` | Formato de imagen de última generación basado en AV1. |
| **ICO** | `.ico` | Iconos de aplicación e iconos de escritorio de Windows. |
| **TIFF** | `.tiff` | Formato de alta resolución para impresión y escaneo profesional. |
