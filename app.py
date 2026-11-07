#!/usr/bin/env python3
"""Point d'entrée : bibliothèques standard Python uniquement (hors SDK Apple facultatif)."""
from __future__ import annotations
import json,logging,signal,sys
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from smallville.settings import ROOT,load,save
from smallville.store import Store
from smallville.sim import Simulation

HOST='127.0.0.1';PORT=8000
STATIC=ROOT/'static'
FILES={'/':'index.html','/index.html':'index.html','/app.js':'app.js','/style.css':'style.css'}
MIMES={'html':'text/html; charset=utf-8','js':'application/javascript; charset=utf-8','css':'text/css; charset=utf-8'}

class Handler(BaseHTTPRequestHandler):
 server_version='SmallvilleLocal/2.0'
 def log_message(self,format,*args):
  # Ne pas consigner de corps de requêtes ou de secrets.
  if not self.path.startswith('/api/state'):
   print('[HTTP]',self.address_string(),format%args,flush=True)
 def headers_common(self):
  self.send_header('X-Content-Type-Options','nosniff')
  self.send_header('Referrer-Policy','no-referrer')
  self.send_header('Cache-Control','no-store')
  self.send_header('X-Frame-Options','DENY')
  self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
 def reply(self,data,status=200,mime='application/json; charset=utf-8',extra=None):
  if isinstance(data,(dict,list)):
   data=json.dumps(data,ensure_ascii=False,allow_nan=False).encode('utf-8')
  elif isinstance(data,str):data=data.encode('utf-8')
  self.send_response(status);self.send_header('Content-Type',mime)
  self.send_header('Content-Length',str(len(data)));self.headers_common()
  if extra:
   for k,v in extra.items():self.send_header(k,v)
  self.end_headers();self.wfile.write(data)
 def do_GET(self):
  path=urlsplit(self.path).path
  if path in FILES:
   file=STATIC/FILES[path]
   if not file.is_file():return self.reply({'error':'Fichier absent'},404)
   return self.reply(file.read_bytes(),mime=MIMES[file.suffix.lstrip('.')])
  if path=='/api/state':return self.reply(self.server.village.public())
  if path=='/api/health':return self.reply({'ok':True,'port':PORT,'bound_to':'127.0.0.1','surrealdb':self.server.village.graph.describe()})
  if path=='/api/graph':return self.reply(self.server.village.network())
  if path=='/api/influences':return self.reply(self.server.village.influence_network())
  if path=='/api/insight':
   aid=parse_qs(urlsplit(self.path).query).get('agent',[''])[0]
   try:return self.reply(self.server.village.insight(aid))
   except ValueError:return self.reply({'error':'Agent inconnu'},404)
  if path=='/api/export':
   return self.reply(self.server.village.export(),extra={'Content-Disposition':'attachment; filename="smallville_export.json"'})
  return self.reply({'error':'Chemin introuvable'},404)
 def do_POST(self):
  origin=self.headers.get('Origin','')
  if origin not in ('','http://127.0.0.1:8000','http://localhost:8000'):
   return self.reply({'error':'Origine non locale refusée'},403)
  if self.headers.get('X-Smallville')!='1' or 'application/json' not in self.headers.get('Content-Type',''):
   return self.reply({'error':'En-tête local de contrôle requis'},403)
  try:
   length=int(self.headers.get('Content-Length','0'))
   if length<2 or length>12000:return self.reply({'error':'Corps trop volumineux'},413)
   data=json.loads(self.rfile.read(length))
   if not isinstance(data,dict):raise ValueError('Objet JSON requis')
   app=self.server.village
   path=urlsplit(self.path).path
   if path=='/api/pause':app.pause(bool(data.get('paused',True)));return self.reply({'ok':True})
   if path=='/api/step':
    if not app.state['paused']:raise ValueError('Mettre en pause avant de faire un pas')
    app.step();return self.reply({'ok':True})
   if path=='/api/speed':
    seconds=float(data.get('tick_seconds'))
    if not .15<=seconds<=8:raise ValueError('Vitesse hors limites')
    self.server.cfg['tick_seconds']=seconds
    return self.reply({'ok':True,'tick_seconds':seconds})
   if path=='/api/jev':
    enabled=data.get('enabled') is True
    if enabled and not app.jev.key:raise ValueError('Clé Jev absente. Relance Installer.command')
    self.server.cfg['jev_enabled']=enabled
    self.server.store.event(app.state['minute'],'settings',None,None,
       'Jev '+('activé explicitement' if enabled else 'désactivé'))
    return self.reply({'ok':True,'jev_enabled':enabled})
   if path in ('/api/whisper','/api/inject'):
    return self.reply(app.give_information(str(data.get('agent','')),str(data.get('text','')),
       str(data.get('mode','information')),str(data.get('scope','individual'))))
   if path=='/api/advance':
    return self.reply({'ok':True,'minute':app.advance(int(data.get('minutes',60)))})
   if path=='/api/reset':
    if data.get('confirm')!='RESET':raise ValueError('Confirmation RESET exigée')
    app.pause(True);app.reset();return self.reply({'ok':True,'jev_ledger_preserved':True})
   return self.reply({'error':'Action inconnue'},404)
  except (ValueError,TypeError) as e:return self.reply({'error':str(e)},400)
  except Exception as e:
   print('Erreur serveur :',repr(e),file=sys.stderr,flush=True)
   return self.reply({'error':'Erreur interne'},500)

class LocalServer(ThreadingHTTPServer):
 allow_reuse_address=True
 daemon_threads=True
 def __init__(self,addr,handler,store,cfg,village):
  super().__init__(addr,handler);self.store=store;self.cfg=cfg;self.village=village

def main():
 cfg=load()
 # Sécurité budgétaire : aucun appel Jev sans réactivation à chaque démarrage.
 cfg['jev_enabled']=False
 store=Store();village=Simulation(store,cfg)
 try:srv=LocalServer((HOST,PORT),Handler,store,cfg,village)
 except OSError as e:
  print(f'Port {PORT} indisponible : {e}',file=sys.stderr);return 1
 print('\nSmallville Local — serveur prêt : http://127.0.0.1:8000',flush=True)
 print(f'Cognition : {village.cognition.name} — {village.cognition.reason}',flush=True)
 print(f'Clé Jev : {"présente" if village.jev.key else "absente"} | Jev : DÉSACTIVÉ au démarrage',flush=True)
 print(f'Budget application Jev : ${cfg["jev_budget_usd"]:.2f} | SurrealDB local : 127.0.0.1:8001 (file persistante) | Ctrl+C pour arrêter\n',flush=True)
 village.start()
 try:srv.serve_forever(poll_interval=.35)
 except KeyboardInterrupt:pass
 finally:srv.shutdown();srv.server_close();village.close()
 return 0
if __name__=='__main__':sys.exit(main())
