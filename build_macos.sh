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

for resource in \
    assets/logo.png \
    assets/app_icon.icns \
    infopol/materials/timber.json \
    ai/prompts/stabduebel_system.txt
do
    if [[ ! -f "$resource" ]]; then
        print -u2 "Fehlende Ressource: $resource"
        exit 1
    fi
done

"$BUILD_PYTHON" -m PyInstaller \
    --noconfirm \
    --clean \
    KI-Bemessungstool.spec

APP_PATH="$PROJECT_DIR/dist/KI-Bemessungstool.app"

print "App erstellt: $APP_PATH"
