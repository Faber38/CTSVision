#!/bin/bash

cd "$(dirname "$0")"

echo "========================================="
echo "          CTSVision starten"
echo "========================================="
echo

# Prüfen ob installiert
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

# Virtuelle Umgebung aktivieren
source venv/bin/activate

# Elite Dangerous prüfen
if ! pgrep -f "EliteDangerous64.exe" >/dev/null ; then
    echo "Elite Dangerous wurde nicht gefunden."
    echo
    echo "Bitte zuerst Elite Dangerous starten"
    echo "und danach CTSVision erneut starten."
    echo
    exit 1
fi

echo "Elite Dangerous gefunden."
echo "Starte CTSVision..."
echo

python automation.py

deactivate