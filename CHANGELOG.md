# Changelog

Todas las versiones publicadas se documentan en este archivo.

## [1.0.0] - 2026-05-17

### Added

- Primera version publica del descargador YouTube a MP3.
- Interfaz grafica con carpeta de destino configurable.
- Soporte para cookies desde navegador o archivo `cookies.txt`.
- Deteccion local de `ffmpeg`.
- Soporte para runtime JavaScript de `yt-dlp` usando Node cuando esta disponible.
- Comprobacion de nuevas versiones desde GitHub Releases.

### Fixed

- Corregidos textos corruptos por codificacion.
- Evitado el uso automatico de un `cookies.txt` caducado.
- Mejorados los mensajes de error para `ffmpeg`, cookies y dependencias.

## [1.0.1] - 2026-05-17

### Added

- Hemos añadido la opción de MP4.
- Hemos configurado para que elijais la opción de calidad de audio MP3 (128, 192, 256 o 320 kbps).
