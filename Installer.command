#!/bin/bash
# Installation macOS sans service cloud pour Smallville (sauf Jev explicitement activé).
set -e
cd "$(dirname "$0")"
printf '\n  SMALLVILLE LOCAL  — installation sur ton Mac\n  ===========================================\n\n'
if [ "$(uname -s)" != 'Darwin' ]; then
  printf 'Cette installation est prévue pour macOS. Le serveur fonctionne aussi sous Python ailleurs.\n'
fi
if ! command -v python3 >/dev/null 2>&1; then
  printf 'Python 3 absent. Installe Python 3.10+ puis relance Installer.command.\n'; exit 1
fi
python3 - <<'PY'
import sys
if sys.version_info < (3,10):
    raise SystemExit('Python 3.10 ou ultérieur requis. Version détectée : '+sys.version)
print('Python détecté :',sys.version.split()[0])
PY
if [ ! -d .venv ]; then python3 -m venv .venv; fi
printf '\nClé Jev : elle sera stockée UNIQUEMENT sur ce Mac dans .env (mode 600).\n'
printf 'Colle ta clé TypeSafe, puis appuie sur Entrée (saisie masquée).\n'
read -r -s -p 'TYPESAFE_API_KEY (vide pour conserver la clé existante ou désactiver) : ' API_KEY
printf '\n'
if [ -n "$API_KEY" ]; then
  umask 077
  printf '%s\n' "$API_KEY" | .venv/bin/python -c 'import os,pathlib,sys;p=pathlib.Path(".env");p.write_text("TYPESAFE_API_KEY="+sys.stdin.read().rstrip("\n")+"\n",encoding="utf8");os.chmod(p,0o600)'
  unset API_KEY
  printf 'Clé enregistrée. Elle ne sera jamais incluse dans les exports.\n'
else
  printf 'Clé conservée si présente ; sinon Jev restera désactivé.\n'
fi
printf '\nMode IA Apple : macOS 26+, Apple Intelligence activé et Xcode 26+ sont nécessaires.\n'
printf 'Installer maintenant apple-fm-sdk depuis PyPI ? Cette étape télécharge des paquets,\n'
printf 'mais l application ne contacte ensuite aucun service cloud hors Jev.\n'
read -r -p 'Installer le SDK Apple [o/N] ? ' ANSWER
case "$ANSWER" in
  o|O|oui|OUI|y|Y|yes|YES)
    if .venv/bin/python -m pip install apple-fm-sdk; then
      printf 'SDK installé. La disponibilité réelle du modèle sera testée au lancement.\n'
    else
      printf 'Installation SDK impossible. Smallville reste exécutable en mode scripté.\n'
    fi;;
  *) printf 'SDK non installé. Tu pourras l ajouter plus tard via .venv/bin/pip install apple-fm-sdk.\n';;
esac
printf '\nInstallation terminée. Lance Lancer.command.\n'
printf 'Sécurité : appels Jev désactivés à chaque démarrage ; plafond local par défaut 0,75 USD.\n\n'
read -r -p 'Entrée pour fermer… ' _unused
