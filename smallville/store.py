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
CREATE TABLE IF NOT EXISTS dialogues(id INTEGER PRIMARY KEY AUTOINCREMENT, minute INTEGER, speaker TEXT, listener TEXT, content TEXT, backend TEXT);
CREATE TABLE IF NOT EXISTS jev_ledger(id INTEGER PRIMARY KEY AUTOINCREMENT, minute INTEGER, day INTEGER, t REAL, status TEXT, reserved REAL, amount REAL, tokens INTEGER, response TEXT, error TEXT);
CREATE TABLE IF NOT EXISTS model_log(id INTEGER PRIMARY KEY AUTOINCREMENT, minute INTEGER, agent TEXT, task TEXT, model TEXT, latency REAL, error TEXT);
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
 def event(self,minute,kind,a,b,text,details=None):
    return self.execute('INSERT INTO events(minute,type,actor,target,text,details) VALUES(?,?,?,?,?,?)',(minute,kind,a,b,text[:700],json.dumps(details or {},ensure_ascii=False)))
 def memory(self,agent,minute,kind,text,importance=.6,source=None):
    self.execute('INSERT INTO memories(agent,minute,kind,content,importance,source) VALUES(?,?,?,?,?,?)',(agent,minute,kind,text[:1200],max(0,min(1,importance)),source))
 def memories(self,agent,n=50):return self.all('SELECT minute,kind,content,importance,source FROM memories WHERE agent=? ORDER BY id DESC LIMIT ?',(agent,n))
 def believe(self,agent,text,p,source,minute):
    self.execute('INSERT INTO beliefs(agent,proposition,confidence,source,minute) VALUES(?,?,?,?,?) ON CONFLICT(agent,proposition) DO UPDATE SET confidence=excluded.confidence,source=excluded.source,minute=excluded.minute',(agent,text[:400],max(0,min(1,p)),source,minute))
 def beliefs(self,agent,n=30):return self.all('SELECT proposition,confidence,source,minute FROM beliefs WHERE agent=? ORDER BY minute DESC LIMIT ?',(agent,n))
 def dialogue(self,minute,a,b,text,backend):
    self.execute('INSERT INTO dialogues(minute,speaker,listener,content,backend) VALUES(?,?,?,?,?)',(minute,a,b,text[:400],backend))
 def log_model(self,minute,aid,task,model,latency,error=None):
    self.execute('INSERT INTO model_log(minute,agent,task,model,latency,error) VALUES(?,?,?,?,?,?)',(minute,aid,task,model,float(latency),str(error)[:300] if error else ''))
 def ledger(self):return self.all('SELECT id,minute,day,t,status,reserved,amount,tokens,error FROM jev_ledger ORDER BY id DESC')
 def budget(self,cfg):
    rows=self.ledger();money=sum(x['amount'] if x['amount'] is not None else x['reserved'] for x in rows)
    return {'used_or_reserved_usd':round(money,8),'budget_usd':cfg['jev_budget_usd'],'calls':len(rows),'successful':sum(x['status']=='ok' for x in rows),'known_input_tokens':sum(x['tokens'] or 0 for x in rows)}
 def reserve_jev(self,minute,cfg,payload):
    data=payload.encode('utf8');n=len(data)
    if n>cfg['jev_max_payload_bytes']:return None,'Requête Jev trop longue'
    # Token BPE généralement <= octets; réserver 2× les octets + overhead.
    estimated=2*n+4096;reserve=estimated*0.042/1e6*1.5
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
      for table in ('snapshot','events','memories','beliefs','dialogues','model_log'):
        c.execute('DELETE FROM '+table)
      # Le registre de dépense n'est JAMAIS réinitialisé.
