#!/bin/bash
# Diagnostic sans accès réseau.
cd "$(dirname "$0")"
printf '\nDIAGNOSTIC SMALLVILLE — totalement local\n=====================================\n'
uname -srm
if command -v sw_vers >/dev/null 2>&1; then sw_vers; fi
if command -v sysctl >/dev/null 2>&1; then
  printf 'Mémoire physique (octets) : ';sysctl -n hw.memsize 2>/dev/null || true
fi
if command -v xcodebuild >/dev/null 2>&1; then xcodebuild -version 2>/dev/null || true; fi
if [ -x .venv/bin/python ]; then PY=.venv/bin/python; else PY=python3; fi
"$PY" - <<'PY'
import platform,sys
print('Python :',sys.version.split()[0])
print('Système :',platform.platform())
try:
 import apple_fm_sdk as fm
 model=fm.SystemLanguageModel()
 available,reason=model.is_available()
 print('SDK Apple FM : installé')
 print('Modèle Apple disponible :',available,'| motif :',reason)
except Exception as exc:
 print('Apple FM indisponible :',type(exc).__name__,str(exc)[:200])
PY
printf '\nAucune requête externe effectuée.\n'
read -r -p 'Entrée pour fermer… ' _unused
