#!/bin/bash

set -e

VERSION="0.1.0"
RELEASE="CTSVision_Test_v${VERSION}"

echo "========================================="
echo "       Erstelle CTSVision Release"
echo "========================================="

# Altes Release entfernen
rm -rf release
mkdir -p release/$RELEASE

echo "Kopiere Python-Dateien..."

find . -maxdepth 1 -name "*.py" -exec cp {} release/$RELEASE/ \;

echo "Kopiere Shell-Skripte..."

cp install.sh release/$RELEASE/
cp start.sh release/$RELEASE/

echo "Kopiere Dokumentation..."

cp README.md release/$RELEASE/

echo "Kopiere Konfiguration..."

cp requirements.txt release/$RELEASE/
cp -r assets release/$RELEASE/
cp -r config release/$RELEASE/
cp -r navigation release/$RELEASE/

echo "Erstelle benötigte Verzeichnisse..."

mkdir -p release/$RELEASE/references
mkdir -p release/$RELEASE/debug

echo "Entferne Entwicklungsreste..."

find release/$RELEASE -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find release/$RELEASE -name "*.pyc" -delete
find release/$RELEASE -name "*.pyo" -delete

echo "Erstelle ZIP..."

(
    cd release
    zip -r "${RELEASE}.zip" "${RELEASE}"
)

echo
echo "========================================="
echo "Release erfolgreich erstellt!"
echo
echo "Datei:"
echo
echo "release/${RELEASE}.zip"
echo
echo "========================================="