#!/bin/bash
# Configuration non destructive : jamais de suppression de .env, SQLite ou SurrealKV.
set -e
cd "$(dirname "$0")"
printf '\nSMALLVILLE — installation / mise à niveau macOS\n============================================\n'
command -v python3 >/dev/null || { echo 'Python 3.10+ requis.'; exit 1; }
python3 -c 'import sys; assert sys.version_info >= (3,10), "Python 3.10+ requis"'
if [ ! -x .venv/bin/python ]; then python3 -m venv .venv; fi
printf '\nClé Jev existante : conservée. Entrée vide = aucun changement.\n'
read -r -s -p 'Nouvelle clé TYPESAFE_API_KEY (facultatif) : ' NEW_JEV
printf '\n'
# Transfert sécurisé par stdin (jamais dans les arguments, ni dans le dépôt).
printf '%s' "$NEW_JEV" | .venv/bin/python -c '
import pathlib,os,secrets,sys
p=pathlib.Path(".env"); d={}
if p.exists():
 for row in p.read_text().splitlines():
  if "=" in row and not row.startswith("#"):
   k,v=row.split("=",1);d[k]=v
key=sys.stdin.read().strip()
if key: d["TYPESAFE_API_KEY"]=key
d.setdefault("SURREAL_USER","root")
d.setdefault("SURREAL_PASS",secrets.token_urlsafe(30))
os.umask(0o077)
p.write_text("".join(k+"="+v+"\n" for k,v in d.items()),encoding="utf8")
os.chmod(p,0o600)
print(".env préservé, identifiants SurrealDB initialisés localement.")
'
unset NEW_JEV
# Jev est le seul service cloud de la simulation. Le modèle macOS natif de
# confiance TLS corrige notamment CERTIFICATE_VERIFY_FAILED sur certains Python.
if ! .venv/bin/python -c 'import truststore,certifi' >/dev/null 2>&1; then
  printf '\nInstallation des certificats TLS pour Jev (une seule fois)...\n'
  .venv/bin/python -m pip install --disable-pip-version-check truststore certifi || \
    echo 'Le support des certificats Jev n’a pas pu être installé ; les autres fonctionnalités restent locales.'
fi
if ! command -v surreal >/dev/null 2>&1; then
  printf '\nSurrealDB permet de sauvegarder le graphe sur disque, indépendamment de SQLite.\n'
  read -r -p 'Installer SurrealDB via Homebrew [o/N] ? ' Y
  case "$Y" in
    o|O|oui|y|Y)
      if command -v brew >/dev/null 2>&1; then brew install surrealdb/tap/surreal
      else echo 'Homebrew absent. Installation SurrealDB : https://surrealdb.com/surrealdb/install';fi;;
    *) echo 'SurrealDB ignoré : le serveur sera utilisable en mode SQLite dégradé.';;
  esac
fi
printf '\nModèle Apple : macOS 26+, Apple Intelligence activé, Xcode 26+.\n'
read -r -p 'Installer / mettre à jour le SDK local Apple depuis PyPI [o/N] ? ' Y
case "$Y" in
  o|O|oui|y|Y) .venv/bin/python -m pip install --upgrade apple-fm-sdk || echo 'SDK Apple indisponible, mode scripté maintenu.';;
  *) echo 'SDK Apple conservé tel quel.';;
esac
printf '\nTerminé. Lance Lancer.command. Aucune donnée locale n’a été réinitialisée.\n'
read -r -p 'Entrée pour fermer… ' _
