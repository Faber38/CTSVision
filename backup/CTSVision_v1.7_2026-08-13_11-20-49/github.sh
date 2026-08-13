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

echo
read -r -p "Neue Version taggen? [j/N]: " create_tag

case "$create_tag" in
    j|J|ja|JA|Ja)
        echo
        read -r -p "Versionsnummer (z.B. 1.7.1): " version

        if [ -z "$version" ]; then
            echo "Kein Tag erstellt: Keine Versionsnummer eingegeben."
            exit 0
        fi

        # Führendes "v" entfernen, falls der Benutzer es mit eingibt.
        version="${version#v}"
        tag="v${version}"

        if git rev-parse "$tag" >/dev/null 2>&1; then
            echo "Fehler: Der Tag $tag existiert bereits."
            exit 1
        fi

        echo
        echo "Erstelle Tag $tag ..."
        git tag -a "$tag" -m "CTSVision $tag"

        echo "Übertrage Tag zu GitHub ..."
        git push origin "$tag"

        echo
        echo "Tag $tag wurde erfolgreich erstellt und hochgeladen."
        ;;
    *)
        echo
        echo "Kein neuer Versions-Tag erstellt."
        ;;
esac
