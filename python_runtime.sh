# Shared by install.sh and start.sh; sourced after changing to the project root.
CTSVISION_ROOT="$PWD"
unset PYTHONHOME PYTHONPATH

ctsvision_platform_help() {
    local ID='' ID_LIKE='' PRETTY_NAME='Linux'
    if [ -r /etc/os-release ]; then
        . /etc/os-release
    fi
    echo "Distribution: $PRETTY_NAME" >&2
    case " $ID $ID_LIKE " in
        *fedora*)
            echo 'Fedora (auch 44): Python 3.12 bei Bedarf zusätzlich mit sudo dnf install python3.12 installieren.' >&2 ;;
        *ubuntu*|*debian*)
            echo 'Debian/Ubuntu/Pop!_OS: Eine verfügbare Python-Version 3.11–3.13 samt passendem python3.X-venv-Paket zusätzlich installieren.' >&2 ;;
        *suse*)
            echo 'openSUSE: Eine zusätzliche Python-Version 3.11–3.13 mit venv/ensurepip aus den Repositories verwenden.' >&2 ;;
        *arch*|*manjaro*)
            echo 'Arch/Manjaro: Einen zusätzlichen Python-3.12-Interpreter verwenden; das Rolling-Release-System-Python kann zu neu sein.' >&2 ;;
        *)
            echo 'Eine zusätzliche Python-Version 3.11–3.13 mit venv/ensurepip für Ihre Distribution bereitstellen.' >&2 ;;
    esac
    echo 'Manuelle Auswahl: CTSVISION_PYTHON=/pfad/zu/python3.12 ./install.sh' >&2
    echo 'CTSVision verändert das System-Python nicht und installiert keine Systempakete.' >&2
}

ctsvision_probe() {
    "$1" -I -B "$CTSVISION_ROOT/python_runtime.py" "$2" "$CTSVISION_ROOT"
}

ctsvision_existing_venv() {
    if [ ! -x "$CTSVISION_ROOT/venv/bin/python" ] ||
       ! ctsvision_probe "$CTSVISION_ROOT/venv/bin/python" venv ||
       ! "$CTSVISION_ROOT/venv/bin/python" -I -B -m pip --version; then
        echo 'Die vorhandene venv ist inkompatibel oder beschädigt. Sie wurde nicht gelöscht.' >&2
        echo 'CTSVision beenden, venv zur Sicherung unter einem freien Namen umbenennen' >&2
        echo 'und ./install.sh erneut ausführen. Keine Python-Symlinks in venv austauschen.' >&2
        ctsvision_platform_help
        return 1
    fi
}

ctsvision_select_python() {
    local candidate resolved
    if [ -n "${CTSVISION_PYTHON:-}" ]; then
        resolved=$(command -v -- "$CTSVISION_PYTHON") || {
            echo "CTSVISION_PYTHON wurde nicht gefunden: $CTSVISION_PYTHON" >&2
            ctsvision_platform_help
            return 1
        }
        ctsvision_probe "$resolved" base || { ctsvision_platform_help; return 1; }
        CTSVISION_SELECTED="$resolved"
        return 0
    fi
    local version wanted directory
    local -a candidates=() versions=() search_dirs=()
    IFS=: read -r -a search_dirs <<< "$PATH"
    for candidate in python3.12 python3.13 python3.11 python3 python; do
        for directory in "${search_dirs[@]}"; do
            resolved="${directory:-.}/$candidate"
            [ -x "$resolved" ] || continue
            if version=$(ctsvision_probe "$resolved" base); then
                candidates+=("$resolved")
                versions+=("$version")
            fi
        done
    done
    for wanted in 3.12 3.13 3.11; do
        for candidate in "${!candidates[@]}"; do
            if [[ "${versions[$candidate]}" == "$wanted".* ]]; then
                CTSVISION_SELECTED="${candidates[$candidate]}"
                return 0
            fi
        done
    done
    echo 'Kein kompatibler Python-Interpreter mit geeigneter Plattform und venv/ensurepip gefunden.' >&2
    ctsvision_platform_help
    return 1
}

ctsvision_use_venv() {
    export VIRTUAL_ENV="$CTSVISION_ROOT/venv"
    export PATH="$VIRTUAL_ENV/bin:$PATH"
    unset PIP_TARGET PIP_PREFIX PIP_USER
}
