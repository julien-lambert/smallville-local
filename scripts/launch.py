#!/usr/bin/env python3
"""Démarre SurrealDB LOCAL si présent, puis Smallville, sans service public."""
import os
import pathlib
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from smallville.settings import read_var


def alive():
    try:
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open('http://127.0.0.1:8001/health',timeout=.5) as resp:
            return resp.status==200
    except Exception:return False


def spawn_database():
    if alive():
        print('SurrealDB déjà présent sur 127.0.0.1:8001.')
        return None
    surreal=shutil.which('surreal')
    password=read_var('SURREAL_PASS')
    if not surreal:
        print('SurrealDB non installé : données SQLite conservées, graphe en attente. Exécute Installer.command.')
        return None
    if not password:
        print('Mot de passe SurrealDB absent : lance Installer.command pour le créer.')
        return None
    env=os.environ.copy();env['SURREAL_USER']=read_var('SURREAL_USER','root')
    env['SURREAL_PASS']=password
    launcher=subprocess.run([surreal,'db','version'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5).returncode==0
    cmd=[surreal]+(['db','start'] if launcher else ['start'])
    cmd+=['--bind','127.0.0.1:8001',f'surrealkv://{ROOT / "data" / "surreal"}']
    log_path=ROOT/'data'/'surreal.log'
    with log_path.open('ab') as log:
        process=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    for i in range(50):
        if alive():
            print('SurrealDB local opérationnel : http://127.0.0.1:8001')
            return process
        if process.poll() is not None:
            print('SurrealDB a échoué : voir data/surreal.log')
            return None
        time.sleep(.1)
    print('SurrealDB met du temps à démarrer ; les écritures seront mises en attente si nécessaire.')
    return process


if __name__=='__main__':
    os.chdir(ROOT)
    process=spawn_database()
    try:
        from app import main
        sys.exit(main())
    finally:
        if process and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=4)
            except subprocess.TimeoutExpired:process.kill()
