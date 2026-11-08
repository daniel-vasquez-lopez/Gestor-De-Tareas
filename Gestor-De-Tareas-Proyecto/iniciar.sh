#!/bin/sh
# Inicia el gestor desde esta carpeta.
APP_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)" || exit 1
cd "$APP_DIR" || exit 1
exec python3 "$APP_DIR/app.py"
