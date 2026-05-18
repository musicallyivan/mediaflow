# Publicar en GitHub

## 1. Crear el repositorio

Crea un repositorio en GitHub con un nombre neutral, por ejemplo:

```text
mediaflow
```

El programa esta configurado para usar:

```python
GITHUB_REPO = os.environ.get("MEDIA_FLOW_GITHUB_REPO", "musicallyivan/mediaflow")
```

Si eliges otro nombre, actualiza ese valor en `app.py`.

## 2. Subir el codigo

No subas `ffmpeg.exe`, `ffprobe.exe`, `downloads/`, `dist/` ni `build/`.
Ya estan excluidos por `.gitignore`.

Comandos:

```powershell
git init
git add .
git commit -m "Initial release"
git branch -M main
git remote add origin https://github.com/musicallyivan/mediaflow.git
git push -u origin main
```

## 3. Publicar una release

Para publicar la version `1.4.1`:

```powershell
git tag v1.4.1
git push origin v1.4.1
```

GitHub Actions ejecutara `.github/workflows/release.yml` y publicara un ZIP en Releases.

## 4. Nueva version

Para cada version nueva:

1. Cambia `APP_VERSION` en `app.py`.
2. Cambia `VERSION`.
3. Añade la seccion correspondiente en `CHANGELOG.md`.
4. Haz commit.
5. Crea un tag `vX.Y.Z`.
6. Sube el tag.

La app detectara la nueva version al consultar la ultima release publicada.
