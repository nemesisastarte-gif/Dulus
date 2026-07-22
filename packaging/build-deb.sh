#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:-$(python - <<'PY'
import tomllib
with open('pyproject.toml','rb') as f: print(tomllib.load(f)['project']['version'])
PY
)}"
ARCH="${DEB_ARCH:-amd64}"
PKG="${ROOT}/build/deb/nemesis_${VERSION}_${ARCH}"
rm -rf "${PKG}"
mkdir -p "${PKG}/DEBIAN" "${PKG}/opt/nemesis" "${PKG}/usr/bin" "${PKG}/usr/share/applications" "${PKG}/usr/share/icons/hicolor/256x256/apps"

# PyInstaller executable contains Python and all Python packages.
install -m 0755 "${ROOT}/dist/nemesis" "${PKG}/opt/nemesis/nemesis"

# Playwright's browser is not a Python module, so copy it explicitly into the
# package. The launcher points Playwright at this private directory.
BROWSER_CACHE="${PLAYWRIGHT_BROWSERS_PATH:-${HOME}/.cache/ms-playwright}"
if [[ ! -d "${BROWSER_CACHE}" ]]; then
  echo "Playwright browser cache not found: ${BROWSER_CACHE}" >&2
  exit 1
fi
mkdir -p "${PKG}/opt/nemesis/playwright-browsers"
# Only Chromium is needed by the harvesters; omit Playwright's FFmpeg and
# headless-shell downloads to keep the Debian artifact smaller.
for browser_dir in "${BROWSER_CACHE}"/chromium-*; do
  [[ -e "${browser_dir}" ]] && cp -a "${browser_dir}" "${PKG}/opt/nemesis/playwright-browsers/"
done

# Native assets used by the GUI and DeepSeek PoW fallback.
[[ -d "${ROOT}/brand-assets" ]] && cp -a "${ROOT}/brand-assets" "${PKG}/opt/nemesis/"
[[ -f "${ROOT}/sha3_wasm_bg.wasm" ]] && install -m 0644 "${ROOT}/sha3_wasm_bg.wasm" "${PKG}/opt/nemesis/"

cat > "${PKG}/usr/bin/nemesis" <<'SH'
#!/bin/sh
set -eu
export NEMESIS_BUNDLE_HOME=/opt/nemesis
export PLAYWRIGHT_BROWSERS_PATH=/opt/nemesis/playwright-browsers
exec /opt/nemesis/nemesis "$@"
SH
chmod 0755 "${PKG}/usr/bin/nemesis"

cat > "${PKG}/usr/share/applications/nemesis.desktop" <<'DESKTOP'
[Desktop Entry]
Name=NEMESIS
Comment=NEMESIS — L'aigle de la justice
Exec=nemesis --gui
Icon=nemesis
Terminal=false
Type=Application
Categories=Development;Utility;
DESKTOP
if [[ -f "${ROOT}/brand-assets/cigua-icon-256.png" ]]; then
  install -m 0644 "${ROOT}/brand-assets/cigua-icon-256.png" "${PKG}/usr/share/icons/hicolor/256x256/apps/nemesis.png"
fi

cat > "${PKG}/DEBIAN/control" <<CONTROL
Package: nemesis
Version: ${VERSION}
Section: devel
Priority: optional
Architecture: ${ARCH}
Maintainer: NEMESIS Project
Depends: libc6, libstdc++6
Description: NEMESIS — L'aigle de la justice
 Self-contained AI coding agent with CLI, GUI, local tools and multi-provider support.
 Python and Playwright browser runtime are bundled in /opt/nemesis.
CONTROL

cat > "${PKG}/DEBIAN/postinst" <<'POSTINST'
#!/bin/sh
set -eu
chmod 0755 /opt/nemesis/nemesis /usr/bin/nemesis
exit 0
POSTINST
chmod 0755 "${PKG}/DEBIAN/postinst"

mkdir -p "${ROOT}/dist"
dpkg-deb --build --root-owner-group "${PKG}" "${ROOT}/dist/nemesis_${VERSION}_${ARCH}.deb"
echo "Created ${ROOT}/dist/nemesis_${VERSION}_${ARCH}.deb"
