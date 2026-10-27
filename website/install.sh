#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Media Flow — Instalador Universal para Linux (Debian/Ubuntu/Kali, Fedora/RHEL, Arch)
# Uso: curl -fsSL https://musicallyivan.github.io/mediaflow/install.sh | sudo bash
# ==============================================================================
REPO="musicallyivan/mediaflow"
API_URL="https://api.github.com/repos/${REPO}/releases/latest"

echo "=========================================================="
echo "  Media Flow Suite — Instalador Automático para Linux"
echo "=========================================================="

if [ "$(uname -m)" != "x86_64" ]; then
  echo "ERROR: Actualmente los paquetes precompilados son para arquitectura x86_64." >&2
  exit 1
fi

SUDO=""
if [ "$(id -u)" -ne 0 ]; then
  if command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
  else
    echo "ERROR: Ejecuta este script como root o instala sudo." >&2
    exit 1
  fi
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TMP_DIR}"' EXIT

echo "==> Consultando la última versión en GitHub (${REPO})..."
RELEASE_JSON="$(curl -fsSL "${API_URL}")"
TAG="$(printf '%s' "${RELEASE_JSON}" | grep -m1 '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')"
VERSION="${TAG#v}"

if [ -z "${VERSION}" ]; then
  echo "ERROR: No se pudo obtener la versión más reciente desde GitHub Releases." >&2
  exit 1
fi

echo "==> Versión detectada: v${VERSION}"

# Detectar gestor de paquetes de la distribución
if command -v apt-get >/dev/null 2>&1 && command -v dpkg >/dev/null 2>&1; then
  DEB_URL="https://github.com/${REPO}/releases/download/${TAG}/media-flow_${VERSION}_amd64.deb"
  DEB_FILE="${TMP_DIR}/media-flow_${VERSION}_amd64.deb"
  echo "==> Distribución basada en Debian/Ubuntu/Kali detectada (.deb)"
  if curl -fsSL "${DEB_URL}" -o "${DEB_FILE}"; then
    ${SUDO} apt-get update -qq || true
    ${SUDO} apt-get install -y "${DEB_FILE}"
    echo "==> ¡Media Flow v${VERSION} instalado con éxito! Ejecuta 'media-flow' o ábrelo desde tu menú de aplicaciones."
    exit 0
  fi
elif (command -v dnf >/dev/null 2>&1 || command -v yum >/dev/null 2>&1 || command -v zypper >/dev/null 2>&1) && command -v rpm >/dev/null 2>&1; then
  RPM_URL="https://github.com/${REPO}/releases/download/${TAG}/media-flow-${VERSION}-1.x86_64.rpm"
  RPM_FILE="${TMP_DIR}/media-flow-${VERSION}-1.x86_64.rpm"
  echo "==> Distribución basada en RPM (Fedora/RHEL/openSUSE) detectada (.rpm)"
  if curl -fsSL "${RPM_URL}" -o "${RPM_FILE}"; then
    if command -v dnf >/dev/null 2>&1; then
      ${SUDO} dnf install -y "${RPM_FILE}"
    elif command -v zypper >/dev/null 2>&1; then
      ${SUDO} zypper --non-interactive install --allow-unsigned-rpm "${RPM_FILE}"
    else
      ${SUDO} rpm -Uvh "${RPM_FILE}"
    fi
    echo "==> ¡Media Flow v${VERSION} instalado con éxito! Ejecuta 'media-flow' o ábrelo desde tu menú de aplicaciones."
    exit 0
  fi
fi

# Fallback universal mediante paquete .tar.gz
echo "==> Instalando desde paquete universal Linux (.tar.gz)..."
TAR_URL="https://github.com/${REPO}/releases/download/${TAG}/media-flow-${TAG}-linux-x86_64.tar.gz"
TAR_FILE="${TMP_DIR}/media-flow.tar.gz"
curl -fsSL "${TAR_URL}" -o "${TAR_FILE}"
tar -xzf "${TAR_FILE}" -C "${TMP_DIR}"

${SUDO} mkdir -p /opt/media-flow
${SUDO} cp -r "${TMP_DIR}/media-flow/"* /opt/media-flow/
${SUDO} chmod +x /opt/media-flow/media-flow
[ -f /opt/media-flow/ffmpeg ] && ${SUDO} chmod +x /opt/media-flow/ffmpeg
[ -f /opt/media-flow/ffprobe ] && ${SUDO} chmod +x /opt/media-flow/ffprobe
${SUDO} ln -sf /opt/media-flow/media-flow /usr/bin/media-flow

if [ -f /opt/media-flow/icon-300.png ]; then
  ${SUDO} mkdir -p /usr/share/pixmaps /usr/share/icons/hicolor/256x256/apps
  ${SUDO} cp /opt/media-flow/icon-300.png /usr/share/pixmaps/media-flow.png
  ${SUDO} cp /opt/media-flow/icon-300.png /usr/share/icons/hicolor/256x256/apps/media-flow.png
fi

${SUDO} tee /usr/share/applications/media-flow.desktop >/dev/null <<'EOF'
[Desktop Entry]
Type=Application
Name=Media Flow
Comment=Convierte, recorta y comprime archivos de audio, vídeo e imagen localmente
Exec=/usr/bin/media-flow %F
Icon=media-flow
Terminal=false
Categories=AudioVideo;AudioVideoEditing;GTK;
StartupWMClass=media-flow
EOF

echo "==> ¡Media Flow v${VERSION} instalado con éxito! Ejecuta 'media-flow' o ábrelo desde tu menú de aplicaciones."
