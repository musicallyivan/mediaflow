# Media Flow para iOS

Versión nativa de Media Flow para dispositivos iOS (iPhone y iPad) desarrollada en **SwiftUI** y con procesamiento multimedia local mediante **FFmpegKit**.

---

## 📱 Características

- **100% Nativo y Privado**: Todo el procesamiento se realiza localmente en el procesador del iPhone sin subir tus archivos a internet.
- **Soporte de Formatos**:
  - **Audio**: MP3, M4A, WAV, FLAC, OGG, OPUS, AAC.
  - **Video**: MP4, WEBM, MOV, MKV, GIF, AVI.
  - **Imagen**: PNG, JPG, WEBP, BMP, TIFF.
- **Selector de Archivos e iCloud**: Integrado directamente con la app Archivos de iOS y almacenamiento en la nube.
- **Hoja de Compartir (Share Sheet)**: Guarda el resultado en Archivos, envíalo por AirDrop o compártelo directamente en WhatsApp, Telegram u otras apps.

---

## 🛠️ ¿Cómo se compila sin tener Mac?

No necesitas comprar un Mac ni tener Xcode en tu PC. El repositorio incluye un flujo de integración continua en **GitHub Actions** (`.github/workflows/ios-build.yml`):

1. Cada vez que subes cambios a la carpeta `ios-app/` o creas una versión (tag), GitHub compila automáticamente la aplicación en un servidor macOS virtual.
2. Puedes descargar el archivo **`MediaFlow.ipa`** directamente desde la pestaña **Actions** o en la sección **Releases** de tu repositorio en GitHub.

---

## 📲 ¿Cómo instalar en tu iPhone desde Windows?

Consulta la guía detallada paso a paso en [GUIA_INSTALACION_IOS.md](GUIA_INSTALACION_IOS.md) para instalar el `.ipa` en tu iPhone usando **Sideloadly** o **AltStore** de forma 100% gratuita.
