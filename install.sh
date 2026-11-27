#!/bin/bash

set -e

cd "$(dirname "$0")"

echo "========================================="
echo "        CTSVision Installation"
echo "========================================="
echo

source ./python_runtime.sh

if [ -e venv ] || [ -L venv ]; then
    ctsvision_existing_venv
    echo "Verwende vorhandene kompatible venv (CTSVISION_PYTHON gilt nur für neue Umgebungen)."
else
    if [ -e .venv ] || [ -L .venv ]; then
        echo 'Eine .venv wurde gefunden. CTSVision verwendet ausschließlich venv; .venv bleibt unverändert.'
    fi
    ctsvision_select_python
    echo "Erstelle virtuelle Umgebung mit $CTSVISION_SELECTED ..."
    if ! "$CTSVISION_SELECTED" -I -B -m venv "$PWD/venv"; then
        echo 'Die Projektumgebung konnte nicht angelegt werden. Eventuell angelegte Dateien bleiben erhalten.' >&2
        echo 'venv/ensurepip und Schreibrechte prüfen; eine unvollständige venv vor einem neuen Versuch sichern/umbenennen.' >&2
        ctsvision_platform_help
        exit 1
    fi
    ctsvision_existing_venv
fi
ctsvision_use_venv

echo "Aktualisiere pip in der Projektumgebung..."
"$VIRTUAL_ENV/bin/python" -I -m pip --isolated install --upgrade pip

echo "Installiere benötigte Bibliotheken..."
"$VIRTUAL_ENV/bin/python" -I -m pip --isolated install -r requirements.txt

cat <<'CTSVISION_INSTALL_COMPLETE'

=========================================
Installation erfolgreich abgeschlossen.

CTSVision wurde erfolgreich eingerichtet.

Starten:

    ./start.sh

Beim ersten Start sollten mit dem
Vision Wizard Referenzbilder für
die eigene Bildschirmauflösung erstellt werden.

Viel Spaß!

=========================================
CTSVISION_INSTALL_COMPLETE
