#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./build_release_locked.sh [owner_github] [release_signature]
# Example:
#   ./build_release_locked.sh darkex REL-20260403-darkex

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

OWNER_GITHUB="${1:-darkex}"
RELEASE_SIGNATURE="${2:-REL-$(date +%Y%m%d)-${OWNER_GITHUB}}"
APP_NAME="JARVIS-release-locked"
OUT_DIR="release_locked"

printf "[BUILD] Root: %s\n" "$ROOT_DIR"
printf "[BUILD] Owner GitHub: %s\n" "$OWNER_GITHUB"
printf "[BUILD] Signature: %s\n" "$RELEASE_SIGNATURE"

# Preferred path: use cross-platform Python builder (more robust on locked environments).
if [[ -f "$ROOT_DIR/build_release_locked.py" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    exec python3 "$ROOT_DIR/build_release_locked.py" "$OWNER_GITHUB" "$RELEASE_SIGNATURE"
  elif command -v python >/dev/null 2>&1; then
    exec python "$ROOT_DIR/build_release_locked.py" "$OWNER_GITHUB" "$RELEASE_SIGNATURE"
  fi
fi

BUILD_VENV="${ROOT_DIR}/.jarvis_release_venv"
if [[ ! -x "$BUILD_VENV/bin/python" ]]; then
  python3 -m venv "$BUILD_VENV"
fi

"$BUILD_VENV/bin/python" -m pip install --upgrade pip setuptools wheel pyinstaller

rm -rf build dist "$OUT_DIR"
mkdir -p "$OUT_DIR"

export JARVIS_RELEASE_MODE=1
export JARVIS_RELEASE_OWNER="$OWNER_GITHUB"
export JARVIS_RELEASE_SIGNATURE="$RELEASE_SIGNATURE"

# Linux/macOS --add-data uses ':' as separator.
"$BUILD_VENV/bin/python" -m PyInstaller \
  --noconfirm \
  --clean \
  --onefile \
  --windowed \
  --name "$APP_NAME" \
  --add-data "resources:resources" \
  --add-data "jarvis_modules:jarvis_modules" \
  JARVIS.py

cp "dist/$APP_NAME" "$OUT_DIR/"
chmod +x "$OUT_DIR/$APP_NAME"

cat > "$OUT_DIR/RELEASE_INFO.txt" <<EOF
App: $APP_NAME
Release mode: ON
Owner GitHub: $OWNER_GITHUB
Release signature: $RELEASE_SIGNATURE
Built at: $(date -Is)

Distribution notes:
- Share only this folder ($OUT_DIR).
- Do not share JARVIS.py or source tree.
- In release mode, dev/code-edit/plugin features are locked.
EOF

printf "[OK] Build complete: %s/%s\n" "$OUT_DIR" "$APP_NAME"
printf "[OK] Release info: %s/RELEASE_INFO.txt\n" "$OUT_DIR"
