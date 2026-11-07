#!/bin/bash
set -e
cd "$(dirname "$0")"
if [ -x .venv/bin/python ]; then PY=.venv/bin/python; else PY=python3; fi
"$PY" scripts/diagnose_jev.py || true
printf '\nEnvoyer une UNIQUE requête Jev de test (dans le budget) ? [o/N] : '
read -r yes
case "$yes" in o|O|oui|OUI|y|Y) "$PY" scripts/diagnose_jev.py --probe;; esac
read -r -p 'Entrée pour quitter...' _
