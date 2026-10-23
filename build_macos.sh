#!/bin/zsh

set -euo pipefail

PROJECT_DIR="${0:A:h}"

if [[ -n "${PYTHON_BIN:-}" ]]; then
    BUILD_PYTHON="$PYTHON_BIN"
elif command -v python >/dev/null 2>&1 && python -c "import PyInstaller" 2>/dev/null; then
    BUILD_PYTHON="python"
elif command -v python3 >/dev/null 2>&1 && python3 -c "import PyInstaller" 2>/dev/null; then
    BUILD_PYTHON="python3"
else
    print -u2 "PyInstaller wurde in keinem verfügbaren Python-Interpreter gefunden."
    print -u2 "Installation: python -m pip install -r requirements-build.txt"
    exit 1
fi

cd "$PROJECT_DIR"

if ! command -v npm >/dev/null 2>&1; then
    print -u2 "npm wurde nicht gefunden. Für den Frontend-Build wird Node.js mit npm benötigt."
    exit 1
fi

print "Installiere Frontend-Abhängigkeiten reproduzierbar …"
if [[ -f frontend/package-lock.json ]]; then
    npm --prefix frontend ci
else
    npm --prefix frontend install
fi

print "Baue React-Frontend …"
npm --prefix frontend run build

if [[ ! -f frontend/dist/index.html ]]; then
    print -u2 "Frontend-Build fehlgeschlagen: frontend/dist/index.html wurde nicht erstellt."
    exit 1
fi

for resource in \
    assets/logo.png \
    assets/widget_1.png \
    assets/app_icon.icns \
    frontend/dist/index.html \
    infopol/materials/timber.json \
    ai/prompts/stabduebel_system.txt
do
    if [[ ! -f "$resource" ]]; then
        print -u2 "Fehlende Ressource: $resource"
        exit 1
    fi
done

# Finder-Metadaten und AppleDouble-Dateien können PyInstallers ad-hoc-
# Signierung blockieren. Es werden ausschließlich Metadaten entfernt.
find frontend/dist assets -name '._*' -type f -delete
if command -v xattr >/dev/null 2>&1; then
    xattr -cr frontend/dist assets
fi

"$BUILD_PYTHON" -m PyInstaller \
    --noconfirm \
    --clean \
    KI-Bemessungstool.spec

APP_PATH="$PROJECT_DIR/dist/KI-Bemessungstool.app"

if [[ ! -d "$APP_PATH" ]]; then
    print -u2 "PyInstaller hat die erwartete App nicht erstellt: $APP_PATH"
    exit 1
fi

# Auf synchronisierten Desktop-Ordnern kann macOS entfernte Finder-/FileProvider-
# Attribute unmittelbar wieder anlegen. Deshalb wird in einem neutralen
# temporären Verzeichnis bereinigt und signiert und erst danach zurückkopiert.
SIGN_STAGE_DIR="$(mktemp -d /tmp/ki-bemessung-sign.XXXXXX)"
SIGN_STAGE_APP="$SIGN_STAGE_DIR/KI-Bemessungstool.app"
trap 'rm -rf "$SIGN_STAGE_DIR"' EXIT

ditto --noextattr --noqtn "$APP_PATH" "$SIGN_STAGE_APP"
find "$SIGN_STAGE_APP" -name '._*' -type f -delete
if command -v xattr >/dev/null 2>&1; then
    find "$SIGN_STAGE_APP" -exec xattr -c {} \; 2>/dev/null || true
fi
if command -v codesign >/dev/null 2>&1; then
    codesign --force --deep --sign - "$SIGN_STAGE_APP"
    codesign --verify --deep --strict --verbose=2 "$SIGN_STAGE_APP"
fi

# Ein Kopieren in einen durch FileProvider verwalteten Desktop-Ordner kann
# FinderInfo erneut erzeugen. Ein atomarer Austausch per mv bewahrt dagegen
# das bereits signierte, saubere Bundle.
mv "$APP_PATH" "$SIGN_STAGE_DIR/unsigned.app"
mv "$SIGN_STAGE_APP" "$APP_PATH"
# Der signierte Stand wurde bereits im neutralen Verzeichnis streng geprüft.
# Im synchronisierten Desktop-Projekt hängt FileProvider am Ziel unmittelbar
# wieder FinderInfo an; eine zweite Prüfung dort wäre deshalb irreführend. Bei
# der Installation wird ohne erweiterte Attribute kopiert und erneut geprüft.

print "App erstellt: $APP_PATH"
