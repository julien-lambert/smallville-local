#!/bin/bash
cd "$(dirname "$0")"
printf '\nSmallville Local — 100 %% local, hormis Jev si activé dans le navigateur.\n'
if [ -x .venv/bin/python ]; then PY=.venv/bin/python; else PY=python3; fi
( sleep 1.6; open 'http://127.0.0.1:8000/' 2>/dev/null || true ) &
"$PY" app.py
