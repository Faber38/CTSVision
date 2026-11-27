#!/usr/bin/env bash

set -euo pipefail

cd -- "$(dirname -- "$0")/.."

PROJECT_NAME="CTSVision"

show_header() {
    clear || true
    echo "================================="
    echo " $PROJECT_NAME – GitHub-Werkzeug"
    echo "================================="
    echo
}

pause() {
    echo
    read -r -p "Weiter mit Enter ..."
}

check_repository() {
    if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        echo "Fehler: Dieses Verzeichnis ist kein Git-Repository."
        exit 1
    fi
}

show_status() {
    echo "Aktueller Git-Status:"
    echo
    git status
}

show_short_status() {
    echo "Geänderte Dateien:"
    echo
    git status --short
}

commit_and_push() {
    show_short_status
    echo

    if git diff --quiet \
        && git diff --cached --quiet \
        && [ -z "$(git ls-files --others --exclude-standard)" ]; then
        echo "Keine Änderungen vorhanden."
        return
    fi

    read -r -p "Commit-Nachricht: " commit_message

    if [ -z "$commit_message" ]; then
        echo "Abgebrochen: Keine Commit-Nachricht eingegeben."
        return
    fi

    echo
    echo "Dateien werden hinzugefügt ..."
    # Explizite NUL-getrennte Dateiliste; private Pfade auch dann ausschließen,
    # wenn sie bereits versioniert sind. Dieselben Regeln wie beim Paketbau.
    local staging_paths
    staging_paths=$(mktemp)
    if ! python3 -B - > "$staging_paths" <<'PY_PATHS'
import os
import runpy
import subprocess
import sys
check = runpy.run_path('tools/build_release.py')['validate_paths']
paths = subprocess.check_output([
    'git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'
]).split(b'\0')
for raw in sorted(set(paths) - {b''}):
    path = os.fsdecode(raw)
    try:
        check([path])
    except ValueError:
        continue
    sys.stdout.buffer.write(b':(literal)' + raw + b'\0')
PY_PATHS
    then
        rm -f -- "$staging_paths"
        return 1
    fi
    if ! git add -A --pathspec-from-file="$staging_paths" --pathspec-file-nul; then
        rm -f -- "$staging_paths"
        return 1
    fi
    rm -f -- "$staging_paths"

    # Bereits vorgemerkte persönliche Daten ebenfalls abweisen.
    # Löschungen aus dem Index sind erlaubt; lokale Dateien bleiben erhalten.
    if ! python3 -B - <<'PY_CHECK'
import runpy
import subprocess
check = runpy.run_path('tools/build_release.py')['validate_paths']
paths = subprocess.check_output([
    'git', 'diff', '--cached', '--name-only', '--diff-filter=ACMRT', '-z'
]).decode().split('\0')
check([path for path in paths if path])
PY_CHECK
    then
        echo 'Abbruch: Persönliche oder unzulässige Dateien sind vorgemerkt.' >&2
        return 1
    fi
    git diff --cached --stat

    echo
    echo "Commit wird erstellt ..."
    if ! git commit -m "$commit_message"; then
        echo
        echo "Der Commit konnte nicht erstellt werden."
        return
    fi

    echo
    echo "Änderungen werden zu GitHub übertragen ..."
    if ! git push; then
        echo
        echo "Der Push ist fehlgeschlagen."
        return
    fi

    echo
    echo "Erfolgreich zu GitHub übertragen."
    echo
    git log -1 --oneline
}

show_last_commit() {
    echo "Letzter Commit:"
    echo
    git log -1 --stat
}

show_history() {
    echo "Commit-Verlauf:"
    echo
    git log --oneline --graph --decorate --all -20
}

show_remote() {
    echo "Eingetragene Git-Remotes:"
    echo
    git remote -v
}

pull_changes() {
    echo "Änderungen von GitHub werden abgerufen ..."
    echo

    if git pull --ff-only; then
        echo
        echo "Repository ist aktuell."
    else
        echo
        echo "Git pull konnte nicht automatisch abgeschlossen werden."
        echo "Möglicherweise gibt es lokale Änderungen oder unterschiedliche Verläufe."
    fi
}

show_tags() {
    echo "Vorhandene Tags:"
    echo

    if [ -z "$(git tag)" ]; then
        echo "Noch keine Tags vorhanden."
    else
        git tag --sort=-version:refname
    fi
}

create_tag() {
    echo "Neuen Versions-Tag erstellen"
    echo

    read -r -p "Tag, zum Beispiel v0.1.0: " tag_name

    if [ -z "$tag_name" ]; then
        echo "Abgebrochen: Kein Tag eingegeben."
        return
    fi

    if git rev-parse "$tag_name" >/dev/null 2>&1; then
        echo "Der Tag '$tag_name' existiert bereits."
        return
    fi

    read -r -p "Beschreibung: " tag_message

    if [ -z "$tag_message" ]; then
        tag_message="CTSVision $tag_name"
    fi

    git tag -a "$tag_name" -m "$tag_message"

    echo
    read -r -p "Tag jetzt zu GitHub übertragen? [j/N]: " answer

    case "$answer" in
        j|J|y|Y)
            git push origin "$tag_name"
            echo
            echo "Tag '$tag_name' wurde übertragen."
            ;;
        *)
            echo
            echo "Tag wurde nur lokal erstellt."
            ;;
    esac
}

check_repository

while true; do
    show_header

    echo "1) Git-Status anzeigen"
    echo "2) Änderungen committen und pushen"
    echo "3) Änderungen von GitHub holen"
    echo "4) Letzten Commit anzeigen"
    echo "5) Commit-Verlauf anzeigen"
    echo "6) GitHub-Remote anzeigen"
    echo "7) Tags anzeigen"
    echo "8) Neuen Versions-Tag erstellen"
    echo "9) Beenden"
    echo

    read -r -p "Auswahl: " choice

    show_header

    case "$choice" in
        1)
            show_status
            pause
            ;;
        2)
            commit_and_push
            pause
            ;;
        3)
            pull_changes
            pause
            ;;
        4)
            show_last_commit
            pause
            ;;
        5)
            show_history
            pause
            ;;
        6)
            show_remote
            pause
            ;;
        7)
            show_tags
            pause
            ;;
        8)
            create_tag
            pause
            ;;
        9)
            echo "Programm beendet."
            exit 0
            ;;
        *)
            echo "Ungültige Auswahl."
            pause
            ;;
    esac
done