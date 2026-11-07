"""SQLite, provenance, budget ledger conservé même lors d'un reset."""
import json,sqlite3,threading,time
from contextlib import contextmanager
from .settings import DATA

SCHEMA='''
CREATE TABLE IF NOT EXISTS snapshot(id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, minute INTEGER, type TEXT, actor TEXT, target TEXT, text TEXT, details TEXT);
CREATE TABLE IF NOT EXISTS memories(id INTEGER PRIMARY KEY AUTOINCREMENT, agent TEXT, minute INTEGER, kind TEXT, content TEXT, importance REAL, source TEXT);
CREATE INDEX IF NOT EXISTS ix_memory ON memories(agent,minute DESC);
CREATE TABLE IF NOT EXISTS beliefs(id INTEGER PRIMARY KEY AUTOINCREMENT, agent TEXT, proposition TEXT, confidence REAL, source TEXT, minute INTEGER, UNIQUE(agent, proposition));
CREATE TABLE IF NOT EXISTS belief_history(id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, agent TEXT, proposition TEXT, before REAL, after REAL, source TEXT, minute INTEGER);
CREATE INDEX IF NOT EXISTS ix_belief_history ON belief_history(run_id, agent, minute DESC);
CREATE TABLE IF NOT EXISTS dialogues(id INTEGER PRIMARY KEY AUTOINCREMENT, minute INTEGER, speaker TEXT, listener TEXT, content TEXT, backend TEXT);
CREATE TABLE IF NOT EXISTS jev_ledger(id INTEGER PRIMARY KEY AUTOINCREMENT, minute INTEGER, day INTEGER, t REAL, status TEXT, reserved REAL, amount REAL, tokens INTEGER, response TEXT, error TEXT);
CREATE TABLE IF NOT EXISTS model_log(id INTEGER PRIMARY KEY AUTOINCREMENT, minute INTEGER, agent TEXT, task TEXT, model TEXT, latency REAL, error TEXT);
CREATE TABLE IF NOT EXISTS graph_outbox(id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, payload TEXT NOT NULL, synced INTEGER NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS ix_graph_pending ON graph_outbox(synced,id);
CREATE TABLE IF NOT EXISTS ballots(id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, minute INTEGER, voter TEXT, candidate TEXT, allocation TEXT, rationale TEXT);
CREATE TABLE IF NOT EXISTS assemblies(id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, minute INTEGER, participants TEXT, topic TEXT);
CREATE TABLE IF NOT EXISTS graph_bootstrap(run_id TEXT PRIMARY KEY);
'''
class Store:
 def __init__(self,path=None):
    self.path=str(path or DATA/'smallville.sqlite3');self.lock=threading.RLock()
    with self.connection() as c:c.executescript(SCHEMA)
 @contextmanager
 def connection(self):
    c=sqlite3.connect(self.path,timeout=10)
    try:
     c.row_factory=sqlite3.Row
     c.execute('PRAGMA journal_mode=WAL')
     c.execute('PRAGMA busy_timeout=10000')
     yield c
     c.commit()
    except BaseException:
     c.rollback()
     raise
    finally:
     c.close()
 def execute(self,sql,params=()):
    with self.lock, self.connection() as c:
     cur=c.execute(sql,params);return cur.lastrowid
 def all(self,sql,params=()):
    with self.connection() as c:return [dict(r) for r in c.execute(sql,params)]
 def snap(self):
    r=self.all('SELECT payload FROM snapshot WHERE id=1')
    return json.loads(r[0]['payload']) if r else None
 def save(self,state):
    self.execute('INSERT INTO snapshot(id,payload) VALUES(1,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload',(json.dumps(state,ensure_ascii=False),))
 def queue_graph(self,kind,payload):
    return self.execute('INSERT INTO graph_outbox(kind,payload) VALUES(?,?)', (kind,json.dumps(payload,ensure_ascii=False)))
 def outbox(self,n=30):
    return self.all('SELECT * FROM graph_outbox WHERE synced=0 ORDER BY id LIMIT ?', (n,))
 def outbox_count(self):
    return self.all('SELECT COUNT(*) AS n FROM graph_outbox WHERE synced=0')[0]['n']
 def mark_synced(self, ids):
    if not ids:return
    with self.lock,self.connection() as c:
      c.executemany('UPDATE graph_outbox SET synced=1 WHERE id=?',[(i,) for i in ids])
 def set_run(self,run_id): self.run_id=run_id
 def _queue(self,c,kind,payload):
    if not getattr(self,'run_id',None):return
    payload={'run_id':self.run_id,**payload}
    c.execute('INSERT INTO graph_outbox(kind,payload) VALUES(?,?)',(kind,json.dumps(payload,ensure_ascii=False)))
 def graph_bootstrapped(self,r):
    return bool(self.all('SELECT run_id FROM graph_bootstrap WHERE run_id=?',(r,)))
 def set_graph_bootstrapped(self,r):
    self.execute('INSERT OR IGNORE INTO graph_bootstrap(run_id) VALUES(?)',(r,))
 def agent_node(self,a):
    self.queue_graph('agent',{'run_id':self.run_id,'id':a['id'],'data':{
      'name':a['name'],'role':a['role'],'bio':a['bio'],'capital':a['capital'],
      'religiosity':a['religiosity'],'reasoning':a['reasoning'],
      'aggression':a['aggression'],'credulity':a['credulity']}})
 def relation(self,aid,bid,rel,minute):
    self.queue_graph('relation',{'run_id':self.run_id,'from':aid,'to':bid,
      'data':{**rel,'minute':minute}})
 def event(self,minute,kind,a,b,text,details=None):
    with self.lock,self.connection() as c:
      detail=json.dumps(details or {},ensure_ascii=False)
      cur=c.execute('INSERT INTO events(minute,type,actor,target,text,details) VALUES(?,?,?,?,?,?)',
        (minute,kind,a,b,text[:700],detail))
      self._queue(c,'event',{'id':str(cur.lastrowid),'agent':a,'data':{
        'minute':minute,'kind':kind,'actor':a,'target':b,'text':text[:700],
        'details':details or {}}})
      return cur.lastrowid
 def memory(self,agent,minute,kind,text,importance=.6,source=None):
    with self.lock,self.connection() as c:
      cur=c.execute('INSERT INTO memories(agent,minute,kind,content,importance,source) VALUES(?,?,?,?,?,?)',
        (agent,minute,kind,text[:1200],max(0,min(1,importance)),source))
      self._queue(c,'memory',{'id':str(cur.lastrowid),'agent':agent,'data':{
        'minute':minute,'kind':kind,'content':text[:1200],
        'importance':max(0,min(1,importance)),'source':source}})
 def memories(self,agent,n=50):return self.all('SELECT minute,kind,content,importance,source FROM memories WHERE agent=? ORDER BY id DESC LIMIT ?',(agent,n))
 def believe(self,agent,text,p,source,minute):
    proposition=text[:400];confidence=max(0,min(1,float(p)))
    with self.lock,self.connection() as c:
      old=c.execute('SELECT confidence FROM beliefs WHERE agent=? AND proposition=?',(agent,proposition)).fetchone()
      prev=old['confidence'] if old else None
      c.execute('INSERT INTO beliefs(agent,proposition,confidence,source,minute) VALUES(?,?,?,?,?) ON CONFLICT(agent,proposition) DO UPDATE SET confidence=excluded.confidence,source=excluded.source,minute=excluded.minute',
        (agent,proposition,confidence,source,minute))
      row=c.execute('SELECT id FROM beliefs WHERE agent=? AND proposition=?',(agent,proposition)).fetchone()
      self._queue(c,'belief',{'id':str(row['id']),'agent':agent,'source':source,'data':{
        'proposition':proposition,'confidence':confidence,'source':source,'minute':minute}})
      if prev is None or abs(prev-confidence)>1e-5:
        cur=c.execute('INSERT INTO belief_history(run_id,agent,proposition,before,after,source,minute) VALUES(?,?,?,?,?,?,?)',
          (getattr(self,'run_id',''),agent,proposition,prev,confidence,source,minute))
        self._queue(c,'belief_revision',{'id':str(cur.lastrowid),'agent':agent,'belief_id':str(row['id']),'data':{
          'proposition':proposition,'before':prev,'after':confidence,
          'source':source,'minute':minute}})
 def belief_history(self,agent,n=40):
    return self.all('SELECT minute,proposition,before,after,source FROM belief_history WHERE agent=? ORDER BY id DESC LIMIT ?', (agent,n))
 def beliefs(self,agent,n=30):return self.all('SELECT proposition,confidence,source,minute FROM beliefs WHERE agent=? ORDER BY minute DESC LIMIT ?',(agent,n))
 def dialogue(self,minute,a,b,text,backend):
    with self.lock,self.connection() as c:
      cur=c.execute('INSERT INTO dialogues(minute,speaker,listener,content,backend) VALUES(?,?,?,?,?)',(minute,a,b,text[:400],backend))
      self._queue(c,'dialogue',{'id':str(cur.lastrowid),'agent':a,'listener':b,'data':{
        'minute':minute,'speaker':a,'listener':b,'content':text[:400],'backend':backend}})
 def ballot(self,minute,voter,candidate,allocation,rationale):
    with self.lock,self.connection() as c:
      cur=c.execute('INSERT INTO ballots(run_id,minute,voter,candidate,allocation,rationale) VALUES(?,?,?,?,?,?)',
       (self.run_id,minute,voter,candidate,json.dumps(allocation),rationale[:300]))
      self._queue(c,'ballot',{'id':str(cur.lastrowid),'agent':voter,'candidate':candidate,
       'data':{'minute':minute,'voter':voter,'candidate':candidate,'allocation':allocation,'rationale':rationale[:300]}})
 def assembly(self,minute,participants,topic):
    with self.lock,self.connection() as c:
      cur=c.execute('INSERT INTO assemblies(run_id,minute,participants,topic) VALUES(?,?,?,?)',
       (self.run_id,minute,json.dumps(participants),topic[:400]))
      self._queue(c,'assembly',{'id':str(cur.lastrowid),'participants':participants,
       'data':{'minute':minute,'participants':participants,'topic':topic[:400]}})
 def ballots(self):return self.all('SELECT * FROM ballots ORDER BY id DESC')
 def assemblies(self):return self.all('SELECT * FROM assemblies ORDER BY id DESC')
 def log_model(self,minute,aid,task,model,latency,error=None):
    self.execute('INSERT INTO model_log(minute,agent,task,model,latency,error) VALUES(?,?,?,?,?,?)',(minute,aid,task,model,float(latency),str(error)[:300] if error else ''))
 def ledger(self):return self.all('SELECT id,minute,day,t,status,reserved,amount,tokens,error FROM jev_ledger ORDER BY id DESC')
 def budget(self,cfg):
    rows=self.ledger();money=sum(x['amount'] if x['amount'] is not None else x['reserved'] for x in rows)
    return {'used_or_reserved_usd':round(money,8),'budget_usd':cfg['jev_budget_usd'],
            'remaining_usd':round(max(0,cfg['jev_budget_usd']-money),8),
            'max_calls_total':cfg['jev_max_calls_total'],
            'max_calls_day':cfg['jev_max_calls_day'],
            'max_calls_24h':cfg['jev_max_calls_24h'],'calls':len(rows),'successful':sum(x['status']=='ok' for x in rows),'known_input_tokens':sum(x['tokens'] or 0 for x in rows)}
 def seconds_until_jev(self,cfg):
    rows=self.all('SELECT MAX(t) AS last_call FROM jev_ledger')
    last=rows[0]['last_call'] if rows else None
    return max(0.0,float(cfg['jev_min_interval_seconds'])-(time.time()-float(last))) if last else 0.0
 def reserve_jev(self,minute,cfg,payload):
    data=payload.encode('utf8');n=len(data)
    if n>cfg['jev_max_payload_bytes']:return None,'Requête Jev trop longue'
    # Réservation conservatrice : un token d'entrée consomme normalement
    # au plus un octet UTF-8 plus les encadrements/surcharge API.
    # Le montant retenu reste le MAX entre réserve et usage facturé observé.
    estimated=n+4096;reserve=estimated*0.042/1e6*1.2
    now=time.time()
    with self.lock,self.connection() as c:
      c.execute('BEGIN IMMEDIATE')
      rows=[dict(r) for r in c.execute('SELECT day,t,COALESCE(amount,reserved) AS money FROM jev_ledger')]
      if sum(r['money'] for r in rows)+reserve>cfg['jev_budget_usd']:return None,'Plafond Jev atteint'
      if len(rows)>=cfg['jev_max_calls_total']:return None,'Quota total Jev atteint'
      if sum(r['day']==minute//1440 for r in rows)>=cfg['jev_max_calls_day']:return None,'Quota Jev du jour simulé atteint'
      if sum(r['t']>now-86400 for r in rows)>=cfg['jev_max_calls_24h']:return None,'Quota Jev de 24 h atteint'
      if rows and now-max(r['t'] for r in rows)<cfg['jev_min_interval_seconds']:return None,'Délai minimal entre requêtes Jev'
      cur=c.execute('INSERT INTO jev_ledger(minute,day,t,status,reserved) VALUES(?,?,?,?,?)',(minute,minute//1440,now,'reserved',reserve))
      return cur.lastrowid,None
 def finish_jev(self,id,data=None,error=None):
    if error:self.execute('UPDATE jev_ledger SET status=?,error=? WHERE id=?',('uncertain',str(error)[:300],id));return
    tokens=(data.get('usage') or {}).get('input_tokens')
    try:tokens=max(0,int(tokens))
    except (TypeError,ValueError):tokens=None
    old=self.all('SELECT reserved FROM jev_ledger WHERE id=?',(id,))[0]['reserved']
    # Garder la réserve majorante pour un contrôle conservateur.
    amount=max(old,tokens*0.042/1e6) if tokens is not None else old
    # Ne pas stocker les messages privés ni la clé dans le journal Jev.
    self.execute('UPDATE jev_ledger SET status=?,amount=?,tokens=?,response=? WHERE id=?',('ok',amount,tokens,json.dumps({'model':data.get('model'),'answers':data.get('answers')},ensure_ascii=False)[:8000],id))
 def reset(self):
    with self.lock,self.connection() as c:
      for table in ('snapshot','events','memories','beliefs','belief_history','dialogues','model_log'):
        c.execute('DELETE FROM '+table)
      # Le registre de dépense n'est JAMAIS réinitialisé.
