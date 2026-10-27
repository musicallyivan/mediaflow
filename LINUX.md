# Media Flow en Linux

Media Flow comparte el mismo motor de conversión de la versión de escritorio de Windows y se distribuye en paquetes nativos **`.deb`**, **`.rpm`** y **`.tar.gz`** con **FFmpeg** y **FFprobe** ya integrados.

---

## 🚀 Instalación rápida en 1 comando (Cualquier distribución)

Detecta automáticamente si tu distribución usa `.deb` (Kali, Debian, Ubuntu, Mint), `.rpm` (Fedora, RHEL, openSUSE) o `.tar.gz`:

```bash
curl -fsSL https://musicallyivan.github.io/mediaflow/install.sh | sudo bash
```

---

## 📦 Instalar mediante paquete `.deb` (Kali Linux, Debian, Ubuntu, Linux Mint, Pop!_OS)

Descarga `media-flow_<version>_amd64.deb` desde [GitHub Releases](https://github.com/musicallyivan/mediaflow/releases/latest) e instálalo con `apt`:

```bash
sudo apt install ./media-flow_*_amd64.deb
```

Después podrás abrirlo desde tu menú de aplicaciones (**Media Flow**) o ejecutando `media-flow` en la terminal.

---

## 🎩 Instalar mediante paquete `.rpm` (Fedora, RHEL, CentOS Stream, Rocky, AlmaLinux, openSUSE)

Descarga `media-flow-<version>-1.x86_64.rpm` desde [GitHub Releases](https://github.com/musicallyivan/mediaflow/releases/latest) e instálalo:

```bash
# En Fedora / RHEL / Rocky / AlmaLinux:
sudo dnf install ./media-flow-*.x86_64.rpm

# En openSUSE:
sudo zypper install --allow-unsigned-rpm ./media-flow-*.x86_64.rpm
```

---

## 🏹 Arch Linux / Manjaro (AUR / PKGBUILD)

Puedes compilar e instalar el paquete nativo de Arch usando el `PKGBUILD` incluido en `packaging/linux/aur/`:

```bash
cd packaging/linux/aur
makepkg -si
```

---

## 🛠️ Desarrollo local / Ejecutar desde código fuente en Kali / Ubuntu / Debian

Si ejecutas `python3 linux_app.py` desde código fuente o entorno virtual (`venv`), asegúrate de instalar primero el soporte de Tkinter e ImageTk del sistema:

```bash
sudo apt update
sudo apt install -y python3-tk python3-pil python3-pil.imagetk ffmpeg
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python3 linux_app.py
```

---

## 🌐 Cómo publicar Media Flow en repositorios oficiales de Linux

El proyecto ya incluye los manifiestos listos en `packaging/linux/` para publicar en las principales tiendas y repositorios de Linux:

1. **Snap Store (Ubuntu / Canonical — `sudo snap install media-flow`)**:
   - Archivo: `packaging/linux/snap/snapcraft.yaml`
   - Crea una cuenta gratuita en [snapcraft.io](https://snapcraft.io/), registra el nombre `media-flow` y ejecuta:
     ```bash
     snapcraft login
     snapcraft upload --release=stable media-flow_*.snap
     ```
2. **Flathub (Flatpak universal para todas las distros)**:
   - Archivos: `packaging/linux/flatpak/io.github.musicallyivan.MediaFlow.yml` y `packaging/linux/io.github.musicallyivan.MediaFlow.metainfo.xml`
   - Envía un Pull Request al repositorio de [Flathub en GitHub](https://github.com/flathub/flathub) con estos dos archivos.
3. **AUR — Arch User Repository (`yay -S media-flow-bin`)**:
   - Archivo: `packaging/linux/aur/PKGBUILD`
   - Crea una cuenta en [aur.archlinux.org](https://aur.archlinux.org), añade tu clave SSH y sube el `PKGBUILD` junto con `.SRCINFO` (`makepkg --printsrcinfo > .SRCINFO`).
4. **OpenSUSE Build Service (OBS) — Repositorio APT y DNF/RPM firmado**:
   - En [build.opensuse.org](https://build.opensuse.org/) puedes subir el `.spec` y control de `packaging/linux/` para que OBS genere y aloje gratis un repositorio APT (`apt`) y RPM (`dnf`/`zypper`) firmado con GPG para Debian, Ubuntu, Kali, Fedora y openSUSE.
