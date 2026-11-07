#!/usr/bin/env python3
"""Diagnostic TypeSafe : TLS certifié sans requête payante par défaut."""
from __future__ import annotations
import argparse
import socket
import ssl
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from smallville.settings import load,read_key
from smallville.jev import Jev, secure_tls_context
from smallville.store import Store

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe',action='store_true',help='Envoyer exactement 1 requête TypeSafe soumise au quota SQLite')
    args=parser.parse_args(argv)
    key=read_key()
    print('TypeSafe : clé', 'présente' if key else 'ABSENTE', '(valeur masquée)')
    print('Python :',sys.executable)
    try:
        context=secure_tls_context()
        assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname
        print('Validation TLS : activée et nom de domaine vérifié')
        print('Moteur TLS :',type(context).__module__)
    except Exception as error:
        print('TLS : configuration invalide :',type(error).__name__,str(error)[:160]);return 2
    try:
        with socket.create_connection(('api.typesafe.ai',443),timeout=7) as sock:
            with context.wrap_socket(sock,server_hostname='api.typesafe.ai') as tls:
                print('Connexion HTTPS TypeSafe : certificat VALIDÉ ; protocole',tls.version())
    except (OSError,ssl.SSLError) as error:
        print('Connexion HTTPS TypeSafe : ÉCHEC :',type(error).__name__,str(error)[:230])
        print('Vérifie le réseau et installe truststore dans le même environnement Python.')
        return 3
    if not args.probe:
        print('Aucune requête Jev facturée. Pour un essai : python scripts/diagnose_jev.py --probe')
        return 0
    if not key:
        print('Test annulé : clé absente de .env');return 4
    cfg=load();cfg['jev_enabled']=True
    store=Store()
    client=Jev(store,cfg)
    answers,error=client._request(
        0,
        {'phrase':'Le village de Salem possède une mairie.'},
        {'contains_mairie':{'type':'noul','instructions':'Does the phrase in `phrase` explicitly mention a town hall (mairie)?'}}
    )
    if error:
        print('Diagnostic Jev : ÉCHEC :',error)
        failures=store.all('SELECT error FROM jev_ledger ORDER BY id DESC LIMIT 1')
        if failures:print('Détail enregistré :',failures[0]['error'])
        return 5
    print('JEV CONFIRMÉ : réponse typée reçue :',answers.get('contains_mairie'))
    print('Budget restant de cette application (USD) :',store.budget(cfg)['remaining_usd'])
    return 0

if __name__=='__main__':raise SystemExit(main())
