# Changelog

Todas las versiones publicadas se documentan en este archivo.

## [1.7.2] - 2026-08-24

### Fixed

- **Empaquetado de Microsoft Store**: El instalador incluye el runtime WinRT necesario para consultar y comprar el complemento PRO.

## [1.7.1] - 2026-08-24

### Fixed

- **Activación de complemento PRO en Microsoft Store**: La compra y la restauración de propiedad usan el add-on durable `9N6VZZ3HDFHJ`; se eliminó la activación de demo.

## [1.7.0] - 2026-08-21

### Added

- **Interfaz Moderna con Bordes Redondeados**: Migración completa a CustomTkinter con bordes redondeados en todas las tarjetas, botones, selectores segmentados, campos de entrada y barras de progreso.
- **Sistema de Complemento PRO (Gratis vs PRO)**: Niveles de acceso con funciones prémium para aceleración por GPU (NVENC/AMF/QSV), procesamiento masivo en lote multihilo (hasta 8 hilos), video 4K/60fps, codecs Hi-Fi/Lossless (FLAC, ALAC, AIFF, AV1, H.265), recorte milimétrico (Trim), compresión a tamaño objetivo (MB) y sincronización automática en la nube.
- **Soporte Híbrido de Monetización (Stripe & Microsoft Store)**: Modal interactivo de activación con integración para pagos online en Stripe y compra mediante Microsoft Store / IAP, además de validación de claves `MFPRO-XXXX-XXXX-XXXX`.

## [1.6.2] - 2026-08-20

### Fixed

- **Corrección de Contraste y Legibilidad de Botones**: Forzado del motor de renderizado `clam` en Windows y mapeo dinámico de color de texto (`foreground`) en `ttk.Button`, `ttk.Notebook.Tab` y selectores de modo para garantizar legibilidad perfecta del texto en blanco en modo claro y oscuro.

## [1.6.1] - 2026-08-20

### Changed

- **Rediseño Glassmorphism Premium**: Renovado completo del modo oscuro y claro con tarjetas de profundidad en tono *Obsidian Midnight*, bordes translúcidos de vidrio, resplandor en acentos *Electric Indigo*, barras de progreso frosted glass e indicadores pulsantes con aureola neon.

## [1.6.0] - 2026-08-20

### Added

- Rediseño completo de la interfaz de usuario estilo **Media Flow Pro** con pestañas de navegación (`Convertidor`, `Ajustes Avanzados`, `Historial`).
- Soporte para **Aceleración por Hardware (GPU)** detectando automáticamente encoders `NVENC` (NVIDIA), `AMF` (AMD) o `QSV` (Intel).
- **Extensión de formatos compatibles**:
  - Audio: OPUS, AAC, ALAC, AIFF.
  - Video: GIF animado, AVI, AV1, H.265 (HEVC).
  - Imagen: AVIF, ICO, TIFF.
- **Herramientas de Recorte de Tiempo (Trim)** indicando segundo o formato `hh:mm:ss` de inicio y fin.
- **Compresión a Tamaño Objetivo (Target MB)** para calcular bitrate exacto según límites de plataformas como Discord o Email.
- **Modos Especiales**: Extracción de audio independiente, silenciado de videos (remover audio) y extracción de subtítulos `.srt`.
- **Modo Concatenar (Unir)** para fusionar varios audios o videos en un archivo único.
- **Preajustes Rápidos (Presets)** para WhatsApp, Web, TikTok/Reels y Audio Hi-Fi.
- **Procesamiento Multihilo por Lotes**: Conversión paralela configurable hasta 8 hilos en CPU multinúcleo.
- **Notificaciones Nativas de Windows (Toast notifications)** al finalizar conversiones en segundo plano.
- **Historial de Conversiones Recientes** con opción para abrir la ubicación del archivo o carpeta creada en Windows Explorer.
- **Tabla / Lista de Cola Interactiva** con vista detallada de tamaño, nombre y estado individual por archivo.

## [1.5.0] - 2026-05-20

### Added

- Conversion por lotes seleccionando varios archivos a la vez.
- Guardado automatico de preferencias de tema, modo, formato, calidad y carpeta de salida.
- Vista de informacion del archivo con `ffprobe` cuando esta disponible.
- Esquinas de ventana redondeadas en Windows compatible y barra de progreso redondeada.

### Fixed

- Actualizador `.exe` mas robusto: ahora lanza un script independiente, espera a que la app se cierre, registra el resultado y vuelve a abrir Media Flow si la instalacion termina correctamente.

## [1.4.6] - 2026-05-19

### Changed

- Manifest MSIX alineado con la identidad asignada por Microsoft Partner Center.

## [1.4.5] - 2026-05-19

### Added

- Paquete MSIX generado automaticamente en el workflow de release.
- Archivo `.appinstaller` para instalaciones MSIX con actualizaciones gestionadas por Windows App Installer.

### Changed

- Las instalaciones MSIX omiten el actualizador por instalador `.exe` y delegan las actualizaciones en Windows.

## [1.4.4] - 2026-05-19

### Added

- Actualizacion automatica: la app descarga el instalador de la ultima release, lo lanza en modo silencioso y se cierra para completar la instalacion.

## [1.4.3] - 2026-05-18

### Changed

- Instalador de Windows pulido con icono propio, imagen de bienvenida y textos personalizados.
- Ejecutable de Windows empaquetado con el icono de Media Flow.

## [1.4.2] - 2026-05-18

### Added

- Instalador standalone de Windows para distribuir Media Flow como `.exe`.

### Changed

- Workflow de release actualizado para publicar el ZIP y el instalador.

## [1.4.1] - 2026-05-18

### Changed

- Actualizado el repositorio de actualizaciones y documentacion a `musicallyivan/mediaflow`.

## [1.4.0] - 2026-05-18

### Changed

- Renombrada la app a Media Flow.
- README simplificado para usuarios finales, sin instrucciones internas de publicacion.
- Nombres de ejecutable y ZIP de release alineados con la marca Media Flow.
- Textos de privacidad y ficha de Store actualizados con el nuevo nombre.

## [1.3.1] - 2026-05-18

### Added

- Politica de privacidad, borrador de ficha de Microsoft Store y avisos de terceros.

### Changed

- Release ZIP actualizado para incluir avisos de privacidad y licencias.

## [1.3.0] - 2026-05-18

### Added

- Modo claro y modo oscuro desde la interfaz.
- Barra de progreso animada durante la conversion.
- Indicador de estado animado y selector de tipo de conversion mas visual.

### Changed

- Interfaz redisenada con mejor jerarquia visual, botones mas claros y tarjetas mas limpias.

## [1.2.0] - 2026-05-18

### Added

- Nuevo enfoque de convertidor multimedia para audio, video e imagen.
- Salida a carpetas locales sincronizadas de OneDrive, Google Drive o iCloud Drive cuando estan disponibles.
- Interfaz renovada con selector de tipo de conversion, controles agrupados y estados mas claros.

## [1.1.0] - 2026-05-18

### Changed

- Convertida la app en un convertidor local MP3/MP4.
- Eliminadas las funciones de descarga desde servicios de terceros.
- Eliminado el uso de credenciales de navegador y dependencias de descarga externas.
- Actualizados los textos para un enfoque mas adecuado para Microsoft Store.
