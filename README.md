# Descargar YouTube a MP3/MP4

Version actual: `1.0.0`

Programa local para pegar un enlace de YouTube y descargarlo como MP3 o MP4.

## Requisitos

1. Python 3.9 o superior.
2. ffmpeg instalado.

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
2. Pega el enlace de YouTube.
3. Elige la carpeta de destino.
4. Elige `MP3` o `MP4`.
5. Elige la calidad de audio: `128 kbps`, `192 kbps`, `256 kbps` o `320 kbps`.
6. Pulsa `Descargar MP3` o `Descargar MP4`.

## Si YouTube pide iniciar sesion o comprobar que no eres un robot

YouTube a veces bloquea descargas anonimas. En ese caso:

1. Inicia sesion en YouTube desde Chrome, Edge o Firefox.
2. En el programa, elige ese navegador en `Cookies de YouTube`.
3. Vuelve a pulsar `Descargar MP3`.

Si eso falla, cierra el navegador y prueba otra vez. Como alternativa, exporta tus cookies de YouTube a un archivo `cookies.txt` en formato Netscape y seleccionalo con el boton `cookies.txt...`.

Deja el navegador en `Ninguno` para usar el archivo `cookies.txt` seleccionado. Si eliges Chrome, Edge o Firefox, el programa usara el navegador seleccionado y no el archivo.

Si aparece un error diciendo que no se han podido copiar las cookies del navegador, cierra todas las ventanas del navegador y termina sus procesos desde el Administrador de tareas. Si aun asi falla, usa un archivo `cookies.txt`.

Usa esta herramienta solo con contenido propio, con permiso, o que tengas derecho a descargar.

## Publicar en GitHub

El programa esta configurado para buscar actualizaciones en:

```python
GITHUB_REPO = os.environ.get("YTMP3_GITHUB_REPO", "musicallyivan/youtube-mp3-downloader")
```

No subas `ffmpeg.exe`, `ffprobe.exe`, `cookies.txt`, `downloads/`, `dist/` ni `build/`. Ya estan ignorados en `.gitignore`.

## Crear una nueva version

1. Actualiza `APP_VERSION` en `app.py`.
2. Actualiza `VERSION`.
3. Añade los cambios en `CHANGELOG.md`.
4. Sube los cambios a GitHub.
5. Crea y sube un tag con el mismo numero:

```powershell
git tag v1.0.0
git push origin v1.0.0
```

Al subir un tag `vX.Y.Z`, GitHub Actions ejecutara `.github/workflows/release.yml`, generara un `.exe`, copiara `ffmpeg.exe` y `ffprobe.exe` dentro del ZIP, y publicara una release con el changelog.

## Actualizaciones automaticas

Al abrir el programa, se consulta la ultima release publicada en GitHub. Si hay una version mas nueva que `APP_VERSION`, el programa pregunta si quieres abrir la pagina de descarga.

Tambien puedes comprobarlo manualmente con el boton `Buscar actualizaciones`.
