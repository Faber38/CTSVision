#!/usr/bin/env bash

set -e

echo
echo "CTSVision – GitHub Upload"
echo "========================="
echo

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "Fehler: Dieses Verzeichnis ist kein Git-Repository."
    exit 1
fi

echo "Aktueller Status:"
git status --short
echo

if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
    echo "Keine Änderungen vorhanden."
    exit 0
fi

read -r -p "Commit-Nachricht: " commit_message

if [ -z "$commit_message" ]; then
    echo "Abgebrochen: Keine Commit-Nachricht eingegeben."
    exit 1
fi

echo
echo "Dateien werden hinzugefügt ..."
git add .

echo "Commit wird erstellt ..."
git commit -m "$commit_message"

echo "Änderungen werden zu GitHub übertragen ..."
git push

echo
echo "Erfolgreich hochgeladen."
echo

git log -1 --oneline
