#!/bin/bash

cd "$(dirname "$0")" || exit 1

echo "========================================="
echo "       CTSVision 1.6"
echo "========================================="
echo

if [ ! -d "venv" ]; then
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

source venv/bin/activate

echo "Starte CTSVision..."
echo

python automation_gui.py
