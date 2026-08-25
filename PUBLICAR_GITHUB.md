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

Para publicar la version `1.7.6`:

```powershell
git tag -a v1.7.6 -m "Media Flow 1.7.6"
git push origin v1.7.6
```

GitHub Actions ejecutara `.github/workflows/release.yml` y publicara estos archivos en Releases:

- ZIP portable de Windows.
- Instalador `.exe`.
- Paquete `.msix`.
- Archivo `.appinstaller`.
- iOS .ipa `.zip/.ipa`.

Para que el MSIX sea instalable directamente fuera de Microsoft Store, configura estos valores en GitHub:

- Secret `MSIX_PFX_BASE64`: certificado `.pfx` codificado en base64.
- Secret `MSIX_PFX_PASSWORD`: contrasena del certificado.
- Variable `MSIX_PUBLISHER`: publisher de Partner Center, por ejemplo `CN=33EC4121-53F8-4312-9812-C8687536BF5A`.

Si no configuras el certificado, el workflow genera el MSIX sin firmar. Ese paquete sirve como base para Microsoft Store o para firmarlo despues, pero Windows no lo instalara directamente con doble clic.

Para Microsoft Store, el manifest debe coincidir con los valores de Partner Center:

- `Package/Identity/Name`: `MusicallyIvan.MediaFlow`
- `Package/Identity/Publisher`: `CN=33EC4121-53F8-4312-9812-C8687536BF5A`
- `Package/Properties/PublisherDisplayName`: `Musically Ivan`

No copies el PFN, Package SID ni Store ID en `AppxManifest.xml`; Microsoft los deriva o los usa en Partner Center.

## 4. Nueva version

Para cada version nueva:

1. Cambia `APP_VERSION` en `app.py`.
2. Cambia `VERSION`.
3. Anade la seccion correspondiente en `CHANGELOG.md`.
4. Haz commit.
5. Crea un tag `vX.Y.Z`.
6. Sube el tag.

La app detectara la nueva version al consultar la ultima release publicada.
