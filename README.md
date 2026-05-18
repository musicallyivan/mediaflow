# Convertidor Multimedia

Version actual: `1.3.0`

Programa local para convertir archivos de audio, video e imagen usando `ffmpeg`.

## Funciones

- Conversion de audio a `MP3`, `M4A`, `WAV`, `FLAC` y `OGG`.
- Conversion de video a `MP4`, `MOV`, `WEBM` y `MKV`.
- Conversion de imagen a `PNG`, `JPG`, `WEBP` y `BMP`.
- Calidad configurable para audio, video e imagen.
- Salida a carpeta local o a carpetas sincronizadas de OneDrive, Google Drive o iCloud Drive cuando ya estan instaladas en el equipo.
- Interfaz moderna con modo claro/oscuro, selector segmentado y animaciones de estado durante la conversion.

La app no descarga contenido de servicios de terceros. Convierte archivos locales que ya tengas derecho a usar.

## Requisitos

1. Python 3.9 o superior.
2. ffmpeg instalado o copiado junto al programa.

Opcion sencilla:

1. Haz doble clic en `instalar_requisitos.bat`.
2. Cuando termine, cierra esa ventana.
3. Haz doble clic en `instalar_y_abrir.bat`.

Opcion manual:

1. Instala Python 3 desde <https://www.python.org/downloads/>.
2. Instala ffmpeg:
   ```powershell
   winget install -e --id Gyan.FFmpeg
   ```
   Tambien puedes copiar `ffmpeg.exe` dentro de esta carpeta.

## Uso

1. Haz doble clic en `instalar_y_abrir.bat`.
2. Elige `Audio`, `Video` o `Imagen`.
3. Elige un archivo local.
4. Elige el formato y la calidad.
5. Elige la carpeta de salida o una carpeta sincronizada disponible.
6. Pulsa `Convertir`.

Puedes cambiar entre modo claro y oscuro desde el boton de la esquina superior derecha.

## Sincronizacion con nube

La app no pide cuentas ni contrasenas. Si OneDrive, Google Drive o iCloud Drive estan instalados, detecta sus carpetas locales y guarda ahi el archivo convertido. El cliente oficial de cada servicio se encarga de la sincronizacion.

## Publicar en GitHub

El programa esta configurado para buscar actualizaciones en:

```python
GITHUB_REPO = os.environ.get("MEDIA_CONVERTER_GITHUB_REPO", "musicallyivan/media-converter")
```

Actualiza ese repositorio antes de publicar versiones reales.

No subas `ffmpeg.exe`, `ffprobe.exe`, `downloads/`, `dist/` ni `build/`. Ya estan ignorados en `.gitignore`.

## Crear una nueva version

1. Actualiza `APP_VERSION` en `app.py`.
2. Actualiza `VERSION`.
3. Anade los cambios en `CHANGELOG.md`.
4. Sube los cambios a GitHub.
5. Crea y sube un tag con el mismo numero:

```powershell
git tag v1.3.0
git push origin v1.3.0
```

Al subir un tag `vX.Y.Z`, GitHub Actions ejecutara `.github/workflows/release.yml`, generara un `.exe`, copiara `ffmpeg.exe` y `ffprobe.exe` dentro del ZIP, y publicara una release con el changelog.
