#!/bin/bash

set -e

VERSION="1.0.0"
RELEASE="CTSVision_v${VERSION}"
RELEASE_DIR="release/${RELEASE}"
ARCHIVE="release/${RELEASE}.zip"

echo "========================================="
echo "       Erstelle CTSVision Release"
echo "========================================="
echo
echo "Version : ${VERSION}"
echo "Release : ${RELEASE}"
echo

# Altes Release entfernen
rm -rf release
mkdir -p "${RELEASE_DIR}"

echo "Kopiere Python-Dateien..."
find . -maxdepth 1 -name "*.py" -exec cp {} "${RELEASE_DIR}/" \;

echo "Kopiere Shell-Skripte..."
cp install.sh "${RELEASE_DIR}/"
cp start.sh "${RELEASE_DIR}/"

echo "Kopiere Dokumentation..."
cp README.md "${RELEASE_DIR}/"

# Optionale Dokumentationsdateien übernehmen
cp LICENSE "${RELEASE_DIR}/" 2>/dev/null || true
cp CHANGELOG.md "${RELEASE_DIR}/" 2>/dev/null || true
cp CONTRIBUTING.md "${RELEASE_DIR}/" 2>/dev/null || true

echo "Kopiere Konfiguration und Projektdaten..."
cp requirements.txt "${RELEASE_DIR}/"
cp -r assets "${RELEASE_DIR}/"
cp -r config "${RELEASE_DIR}/"
cp -r navigation "${RELEASE_DIR}/"

# Dokumentationsbilder übernehmen, falls vorhanden
if [ -d docs ]; then
    cp -r docs "${RELEASE_DIR}/"
fi

echo "Erstelle benötigte Verzeichnisse..."
mkdir -p "${RELEASE_DIR}/references"
mkdir -p "${RELEASE_DIR}/debug"

echo "Entferne Entwicklungsreste..."
find "${RELEASE_DIR}" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "${RELEASE_DIR}" -name "*.pyc" -delete
find "${RELEASE_DIR}" -name "*.pyo" -delete

echo "Erstelle ZIP..."
(
    cd release
    zip -r "${RELEASE}.zip" "${RELEASE}"
)

echo
echo "========================================="
echo "Release erfolgreich erstellt!"
echo
echo "Version : ${VERSION}"
echo "Release : ${RELEASE}"
echo
echo "Archiv:"
echo "${ARCHIVE}"
echo "========================================="