#!/bin/bash

set -e

cd "$(dirname "$0")" || exit 1
source ./python_runtime.sh

echo "========================================="
echo "       CTSVision 1.9.6"
echo "========================================="
echo

if [ ! -e "venv" ] && [ ! -L "venv" ]; then
    echo "CTSVision wurde noch nicht installiert."
    echo
    echo "Bitte zuerst"
    echo
    echo "    ./install.sh"
    echo
    echo "ausführen."
    echo
    exit 1
fi

ctsvision_existing_venv
ctsvision_use_venv

echo "Starte CTSVision..."
echo

exec "$VIRTUAL_ENV/bin/python" automation_gui.py
