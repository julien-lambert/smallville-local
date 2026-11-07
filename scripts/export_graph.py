#!/usr/bin/env python3
"""Export scientifique du graphe SurrealDB local, aucune connexion externe.

Usage: python scripts/export_graph.py [--run RUN_ID] [--output path.json]
"""
import argparse
import json
import pathlib
import sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from smallville.store import Store
from smallville.graph import GraphBridge,quoted,identifier

NODE_TABLES=('agent','memory','belief','dialogue','event','ballot','assembly','reflection','state','relation_change')
EDGE_TABLES=('knows','remembers','holds','heard','uttered','influenced','voted_for','casts','attends','acts_in','reflects_on','experienced','relates')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',help='Identifiant d’expérience (défaut: expérience active)')
    p.add_argument('--output',help='Chemin de sortie JSON (défaut: data/exports/...)')
    args=p.parse_args()
    store=Store();run=identifier(args.run or (store.snap() or {}).get('run_id',''))
    if not run:raise SystemExit('Aucune simulation créée.')
    bridge=GraphBridge(store)
    result={'run_id':run,'tables':{},'source':'SurrealDB local','endpoint':'127.0.0.1:8001'}
    for table in NODE_TABLES+EDGE_TABLES:
        # pagination simple, 250 entités par page pour préserver la mémoire
        rows=[];offset=0
        while True:
            query=f'SELECT * FROM {table} WHERE run_id = {quoted(run)} LIMIT 250 START {offset};'
            res=bridge.query(query,timeout=6)
            batch=res[0]['result'] if res else []
            if not isinstance(batch,list):raise RuntimeError('Résultat SurrealDB invalide pour '+table)
            rows.extend(batch)
            if len(batch)<250:break
            offset+=250
        result['tables'][table]=rows
        print(f'{table:18s} : {len(rows)} éléments')
    path=pathlib.Path(args.output) if args.output else ROOT/'data'/'exports'/f'graph_{run}.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str))
    print('Export terminé :',path)

if __name__=='__main__':main()
