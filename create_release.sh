#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "$0")"
VERSION="1.9.4"

# Explizite Dateiliste; vorhandene Versionen werden niemals gelöscht.
# Ein vorhandenes v1.9.4-Paket führt zum Abbruch statt zum Überschreiben.
python3 tools/build_release.py --version "${VERSION}"
