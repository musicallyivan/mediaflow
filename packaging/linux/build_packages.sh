#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Media Flow — Generador de paquetes Linux (.deb, .rpm y .tar.gz)
# ==============================================================================
RAW_VERSION="${1:-$(cat VERSION 2>/dev/null || echo "1.7.7")}"
VERSION="${RAW_VERSION#v}"
ARCH_DEB="amd64"
ARCH_RPM="x86_64"

echo "==> Construyendo paquetes Linux para Media Flow v${VERSION}..."

if [ ! -f "dist/media-flow" ]; then
  echo "ERROR: No se encontró dist/media-flow. Ejecuta PyInstaller primero." >&2
  exit 1
fi

# ------------------------------------------------------------------------------
# 1. Preparar directorio base portable (tar.gz)
# ------------------------------------------------------------------------------
PORTABLE_ROOT="release/media-flow"
rm -rf release build/linux-pkg
mkdir -p "${PORTABLE_ROOT}/assets/icons"

cp dist/media-flow "${PORTABLE_ROOT}/"
chmod +x "${PORTABLE_ROOT}/media-flow"

if [ -f "ffmpeg" ] && [ -f "ffprobe" ]; then
  cp ffmpeg ffprobe "${PORTABLE_ROOT}/"
  chmod +x "${PORTABLE_ROOT}/ffmpeg" "${PORTABLE_ROOT}/ffprobe"
fi

cp icon-300.png "${PORTABLE_ROOT}/" 2>/dev/null || true
cp -r assets/icons/* "${PORTABLE_ROOT}/assets/icons/" 2>/dev/null || true
cp README.md CHANGELOG.md PRIVACY.md THIRD_PARTY_NOTICES.md LICENSE "${PORTABLE_ROOT}/" 2>/dev/null || true
if [ -d "ffmpeg-licenses" ]; then
  cp -r ffmpeg-licenses "${PORTABLE_ROOT}/"
fi

cat > "${PORTABLE_ROOT}/install.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Instalando Media Flow en /opt/media-flow..."
sudo mkdir -p /opt/media-flow
sudo cp -r "${SCRIPT_DIR}/"* /opt/media-flow/
sudo chmod +x /opt/media-flow/media-flow
[ -f /opt/media-flow/ffmpeg ] && sudo chmod +x /opt/media-flow/ffmpeg
[ -f /opt/media-flow/ffprobe ] && sudo chmod +x /opt/media-flow/ffprobe
sudo ln -sf /opt/media-flow/media-flow /usr/bin/media-flow
if [ -f /opt/media-flow/icon-300.png ]; then
  sudo mkdir -p /usr/share/pixmaps /usr/share/icons/hicolor/256x256/apps
  sudo cp /opt/media-flow/icon-300.png /usr/share/pixmaps/media-flow.png
  sudo cp /opt/media-flow/icon-300.png /usr/share/icons/hicolor/256x256/apps/media-flow.png
fi
sudo tee /usr/share/applications/media-flow.desktop >/dev/null <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=Media Flow
Comment=Convierte, recorta y comprime archivos de audio, vídeo e imagen localmente
Exec=/usr/bin/media-flow %F
Icon=media-flow
Terminal=false
Categories=AudioVideo;AudioVideoEditing;GTK;
StartupWMClass=media-flow
DESKTOP
echo "¡Media Flow se ha instalado correctamente! Ejecuta 'media-flow' o ábrelo desde tu menú de aplicaciones."
EOF
chmod +x "${PORTABLE_ROOT}/install.sh"

cat > "${PORTABLE_ROOT}/README-LINUX.md" <<'EOF'
# Media Flow para Linux

Media Flow convierte audio, vídeo e imágenes de forma 100% local mediante FFmpeg.

## Ejecutar en modo portable

```bash
chmod +x media-flow
./media-flow
```

## Instalar en el sistema

```bash
./install.sh
```
EOF

TAR_NAME="media-flow-v${VERSION}-linux-x86_64.tar.gz"
tar -C release -czf "${TAR_NAME}" media-flow
echo "==> Creado paquete portable: ${TAR_NAME}"

# ------------------------------------------------------------------------------
# 2. Construir paquete .deb (Debian, Ubuntu, Kali Linux, Mint, Pop!_OS)
# ------------------------------------------------------------------------------
DEB_ROOT="build/linux-pkg/deb/media-flow_${VERSION}_${ARCH_DEB}"
mkdir -p "${DEB_ROOT}/DEBIAN"
mkdir -p "${DEB_ROOT}/opt/media-flow"
mkdir -p "${DEB_ROOT}/usr/bin"
mkdir -p "${DEB_ROOT}/usr/share/applications"
mkdir -p "${DEB_ROOT}/usr/share/pixmaps"
mkdir -p "${DEB_ROOT}/usr/share/icons/hicolor/256x256/apps"
mkdir -p "${DEB_ROOT}/usr/share/metainfo"
mkdir -p "${DEB_ROOT}/usr/share/doc/media-flow"

cp -r "${PORTABLE_ROOT}/"* "${DEB_ROOT}/opt/media-flow/"
ln -sf /opt/media-flow/media-flow "${DEB_ROOT}/usr/bin/media-flow"

cp packaging/linux/media-flow.desktop "${DEB_ROOT}/usr/share/applications/media-flow.desktop"
cp packaging/linux/io.github.musicallyivan.MediaFlow.metainfo.xml "${DEB_ROOT}/usr/share/metainfo/"

if [ -f "icon-300.png" ]; then
  cp icon-300.png "${DEB_ROOT}/usr/share/pixmaps/media-flow.png"
  cp icon-300.png "${DEB_ROOT}/usr/share/icons/hicolor/256x256/apps/media-flow.png"
fi

cp LICENSE README.md CHANGELOG.md "${DEB_ROOT}/usr/share/doc/media-flow/" 2>/dev/null || true

INSTALLED_SIZE="$(du -sk "${DEB_ROOT}/opt" "${DEB_ROOT}/usr" | awk '{s+=$1} END {print s}')"

cat > "${DEB_ROOT}/DEBIAN/control" <<EOF
Package: media-flow
Version: ${VERSION}
Section: video
Priority: optional
Architecture: ${ARCH_DEB}
Installed-Size: ${INSTALLED_SIZE}
Depends: libc6, libx11-6, libxext6, libxrender1, libxft2, libfontconfig1, libfreetype6
Recommends: libnotify-bin, xdg-utils
Maintainer: MusicallyIvan <https://github.com/musicallyivan/mediaflow>
Homepage: https://musicallyivan.github.io/mediaflow/
Description: Suite de conversion y procesamiento multimedia con aceleracion GPU
 Media Flow es una aplicacion de escritorio para convertir, recortar,
 comprimir y unir archivos de audio, video e imagen localmente con FFmpeg.
 Incluye soporte para MP4, MKV, AV1, H.265, FLAC, MP3, OPUS, WebP y AVIF.
EOF

cat > "${DEB_ROOT}/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
chmod +x /opt/media-flow/media-flow 2>/dev/null || true
[ -f /opt/media-flow/ffmpeg ] && chmod +x /opt/media-flow/ffmpeg || true
[ -f /opt/media-flow/ffprobe ] && chmod +x /opt/media-flow/ffprobe || true
ln -sf /opt/media-flow/media-flow /usr/bin/media-flow
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
fi
exit 0
EOF
chmod 0755 "${DEB_ROOT}/DEBIAN/postinst"

cat > "${DEB_ROOT}/DEBIAN/postrm" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = "remove" ] || [ "$1" = "purge" ]; then
  rm -f /usr/bin/media-flow
fi
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database -q /usr/share/applications || true
fi
exit 0
EOF
chmod 0755 "${DEB_ROOT}/DEBIAN/postrm"

DEB_NAME="media-flow_${VERSION}_${ARCH_DEB}.deb"
dpkg-deb --build --root-owner-group "${DEB_ROOT}" "${DEB_NAME}"
echo "==> Creado paquete Debian/Ubuntu/Kali: ${DEB_NAME}"

# ------------------------------------------------------------------------------
# 3. Construir paquete .rpm (Fedora, RHEL, CentOS, openSUSE, Rocky, AlmaLinux)
# ------------------------------------------------------------------------------
if command -v rpmbuild >/dev/null 2>&1; then
  RPM_TOPDIR="$(pwd)/build/linux-pkg/rpm"
  mkdir -p "${RPM_TOPDIR}"/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

  RPM_SPEC="${RPM_TOPDIR}/SPECS/media-flow.spec"
  cat > "${RPM_SPEC}" <<EOF
%global debug_package %{nil}
%define _build_id_links none
%define __strip /bin/true

Name:           media-flow
Version:        ${VERSION}
Release:        1
Summary:        Suite de conversion y procesamiento multimedia con aceleracion GPU
License:        MIT
URL:            https://musicallyivan.github.io/mediaflow/
BuildArch:      ${ARCH_RPM}
AutoReqProv:    no
Requires:       glibc, libX11, libXext, libXrender, libXft, fontconfig, freetype

%description
Media Flow es una suite multimedia moderna para convertir, recortar,
comprimir y unir archivos de audio, video e imagen de forma 100% local
mediante FFmpeg, con soporte para aceleracion por hardware GPU.

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}/opt/media-flow
mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}/usr/share/applications
mkdir -p %{buildroot}/usr/share/pixmaps
mkdir -p %{buildroot}/usr/share/icons/hicolor/256x256/apps
mkdir -p %{buildroot}/usr/share/metainfo

cp -a "$(pwd)/${PORTABLE_ROOT}/"* %{buildroot}/opt/media-flow/
ln -sf /opt/media-flow/media-flow %{buildroot}/usr/bin/media-flow
cp -a "$(pwd)/packaging/linux/media-flow.desktop" %{buildroot}/usr/share/applications/media-flow.desktop
cp -a "$(pwd)/packaging/linux/io.github.musicallyivan.MediaFlow.metainfo.xml" %{buildroot}/usr/share/metainfo/
if [ -f "$(pwd)/icon-300.png" ]; then
  cp -a "$(pwd)/icon-300.png" %{buildroot}/usr/share/pixmaps/media-flow.png
  cp -a "$(pwd)/icon-300.png" %{buildroot}/usr/share/icons/hicolor/256x256/apps/media-flow.png
fi

%post
chmod +x /opt/media-flow/media-flow 2>/dev/null || true
[ -f /opt/media-flow/ffmpeg ] && chmod +x /opt/media-flow/ffmpeg || true
[ -f /opt/media-flow/ffprobe ] && chmod +x /opt/media-flow/ffprobe || true
ln -sf /opt/media-flow/media-flow /usr/bin/media-flow
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database -q /usr/share/applications || true
fi

%postun
if [ \$1 -eq 0 ]; then
  rm -f /usr/bin/media-flow
fi

%files
/opt/media-flow
/usr/bin/media-flow
/usr/share/applications/media-flow.desktop
/usr/share/metainfo/io.github.musicallyivan.MediaFlow.metainfo.xml
/usr/share/pixmaps/media-flow.png
/usr/share/icons/hicolor/256x256/apps/media-flow.png
EOF

  rpmbuild --define "_topdir ${RPM_TOPDIR}" -bb "${RPM_SPEC}"
  RPM_BUILT="$(find "${RPM_TOPDIR}/RPMS" -name '*.rpm' | head -n 1)"
  RPM_NAME="media-flow-${VERSION}-1.${ARCH_RPM}.rpm"
  cp "${RPM_BUILT}" "${RPM_NAME}"
  echo "==> Creado paquete Fedora/RHEL/openSUSE: ${RPM_NAME}"
else
  echo "AVISO: rpmbuild no está instalado; se omite la creación de .rpm"
fi

echo "==> ¡Todos los paquetes de Linux se han generado con éxito!"
