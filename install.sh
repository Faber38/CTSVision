#!/bin/bash

set -e

cd "$(dirname "$0")"

echo "========================================="
echo "        CTSVision Installation"
echo "========================================="
echo

if ! command -v python3 >/dev/null 2>&1; then
    echo "Fehler: Python3 wurde nicht gefunden."
    exit 1
fi

echo "Erstelle virtuelle Python-Umgebung..."
python3 -m venv venv

echo
echo "Aktiviere virtuelle Umgebung..."
source venv/bin/activate

echo
echo "Aktualisiere pip..."
python -m pip install --upgrade pip

echo
echo "Installiere benötigte Bibliotheken..."
pip install -r requirements.txt

echo
echo "========================================="
echo "Installation erfolgreich abgeschlossen."
echo
echo "CTSVision kann jetzt über"
echo
echo "    ./start.sh"
echo
echo "gestartet werden."
echo "========================================="