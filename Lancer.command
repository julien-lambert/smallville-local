#!/bin/bash
set -e
cd "$(dirname "$0")"
printf '\nSalem-sur-Brume — monde local, 25 habitants, SurrealDB + Apple + Jev facultatif.\n'
if [ -x .venv/bin/python ]; then PY=.venv/bin/python; else PY=python3; fi
( sleep 2; open 'http://127.0.0.1:8000/' 2>/dev/null || true ) &
"$PY" scripts/launch.py
