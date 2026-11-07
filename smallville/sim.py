"""Moteur de monde fermé: décisions micro-locales, dialogues Apple, jugements Jev.
Le monde n'a AUCUN accès aux états mentaux privés des autres personnages.
"""
import copy,queue,random,re,threading,time
from collections import deque
from .seed import WIDTH,HEIGHT,SECRETS,new_world
from .models import LocalBrain
from .jev import Jev,decide

def limit(x,lo=0,hi=1):return max(lo,min(hi,float(x)))

def find_path(grid,a,b):
 a=tuple(a);b=tuple(b)
 if a==b:return []
 if not(0<=b[0]<WIDTH and 0<=b[1]<HEIGHT) or grid[b[1]][b[0]] in ('tree','building'):return []
 q=deque([a]);prev={a:None}
 while q:
  x,y=q.popleft()
  if (x,y)==b:break
  for next in ((x+1,y),(x,y+1),(x-1,y),(x,y-1)):
   xx,yy=next
   if 0<=xx<WIDTH and 0<=yy<HEIGHT and next not in prev and grid[yy][xx] not in ('tree','building'):
    prev[next]=(x,y);q.append(next)
 if b not in prev:return []
 path=[]
 while b!=a:path.append(list(b));b=prev[b]
 return path[::-1]

class Simulation:
 def __init__(self,store,cfg):
  self.store,self.cfg=store,cfg
  self.lock=threading.RLock();self.state=store.snap() or new_world(cfg['seed'])
  self.cognition=LocalBrain(cfg);self.jev=Jev(store,cfg)
  self.tasks=queue.Queue(maxsize=20);self.pending=set();self.closed=threading.Event();self.epoch=0
  self.threads=[]
  if not store.snap():
   for a,secret in SECRETS.items():
    self.store.believe(a,secret,.86,'observation privée',self.state['minute'])
    self.store.memory(a,self.state['minute'],'observation',secret,.82,'personnel')
   self.store.event(480,'world',None,None,'Six habitants commencent leur journée dans le village.')
   self.store.save(self.state)

 def start(self):
  for name,fn in [('horloge',self._clock),('cognition',self._worker)]:
   t=threading.Thread(name='smallville-'+name,target=fn,daemon=True);t.start();self.threads.append(t)
 def close(self):
  self.closed.set()
  with self.lock:self.store.save(self.state)
 def _clock(self):
  while not self.closed.wait(float(self.cfg['tick_seconds'])):
   with self.lock:
    if not self.state['paused']:self._step()
 def step(self):
  with self.lock:self._step()
 def pause(self,value):
  with self.lock:self.state['paused']=bool(value);self.store.save(self.state)

 def _step(self):
  s=self.state;s['minute']+=1;s['ticks']+=1;minute=s['minute']
  rng=random.Random(s['seed']+minute*301)
  day=minute//1440
  if day>s['last_day']:
   self._new_day(day);s['last_day']=day;s['conversations_today']=0
  for a in s['agents'].values():
   a['social']=limit(a['social']-.0012);a['loneliness']=limit(a['loneliness']+.001)
   a['energy']=limit(a['energy']-.0009)
   if a['activity']=='resting':a['energy']=limit(a['energy']+.012);a['stress']=limit(a['stress']-.004)
   if minute%1440<6*60:a['energy']=limit(a['energy']+.003)
   if 'stay_until' not in a:a['stay_until']=0
   if ([a['x'],a['y']]==a['destination'] and minute>=a['stay_until']) or minute-a['last_plan']>130:
    self._plan(a,rng,minute)
   if [a['x'],a['y']]!=a['destination']:
    route=find_path(s['grid'],[a['x'],a['y']],a['destination'])
    if route:a['x'],a['y']=route[0];a['activity']='walking'
    else:a['destination']=[a['x'],a['y']]
   elif a['activity']=='walking':a['activity']='observing'
   if a['dialogue_until']<minute:a['dialogue']=''
  self._social(rng,minute)
  if s['ticks']%4==0:self.store.save(s)

 def _plan(self,a,rng,minute):
  hour=(minute%1440)//60
  if a['energy']<.25 or hour<6:
   dest={'alice':[6,7],'basile':[7,15],'chloe':[23,8],
    'dorian':[12,17],'emma':[15,11],'felix':[23,14]}[a['id']]
   activity='resting';thought='Je devrais récupérer mes forces.'
  elif a['social']<.54 or a['loneliness']>.48:
   dest=rng.choice([[15,11],[15,12],[16,11],[23,14]]);activity='socialising'
   thought='J’aimerais rencontrer quelqu’un.'
  else:
   options={
    'alice':[[15,11],[23,14],[23,8],[15,11]],
    'basile':[[7,15],[7,15],[15,11],[12,17]],
    'chloe':[[23,8],[23,8],[15,11],[23,14]],
    'dorian':[[12,17],[12,17],[15,11],[7,15]],
    'emma':[[15,11],[23,14],[15,11],[23,8]],
    'felix':[[23,14],[15,11],[23,14],[7,15]]}[a['id']]
   dest=rng.choice(options);activity='working';thought='Je poursuis mes activités.'
  a['destination']=dest[:];a['activity']=activity;a['thought']=thought
  a['last_plan']=minute;a['stay_until']=minute+rng.randint(5,17)

 def _social(self,rng,minute):
  if len(self.pending)>=2 or self.tasks.full() or self.state['conversations_today']>=40:return
  agents=list(self.state['agents'].values());candidates=[]
  for i,a in enumerate(agents):
   if minute-a['last_social']<18:continue
   for b in agents[i+1:]:
    if minute-b['last_social']<18:continue
    if abs(a['x']-b['x'])+abs(a['y']-b['y'])>2:continue
    pair='-'.join(sorted([a['id'],b['id']]))
    if pair in self.pending or minute-self.state['seen_pairs'].get(pair,-100)<36:continue
    chance=.21+.05*(a['traits']['extraversion']+b['traits']['extraversion'])
    if rng.random()<chance:candidates.append((a,b,pair))
  if not candidates:return
  a,b,pair=rng.choice(candidates)
  if b['traits']['extraversion']>a['traits']['extraversion'] and rng.random()<.7:a,b=b,a
  self.pending.add(pair);self.state['seen_pairs'][pair]=minute
  self.state['conversations_today']+=1
  for x in (a,b):
   x['last_social']=minute;x['social']=limit(x['social']+.13);x['loneliness']=limit(x['loneliness']-.12)
  self.store.event(minute,'meeting',a['id'],b['id'],f"{a['name']} rencontre {b['name']}.")
  self.tasks.put_nowait(('talk',self.epoch,pair,a['id'],b['id'],minute))
  self.store.save(self.state)

 def _memories(self,aid,other,minute):
  memories=self.store.memories(aid,45)
  words=set(re.findall(r'[\wÀ-ÿ]{4,}',other.lower()))
  def value(m):
   overlap=len(words&set(re.findall(r'[\wÀ-ÿ]{4,}',m['content'].lower())))
   recent=1/(1+max(0,minute-m['minute'])/500)
   return .65*m['importance']+.18*recent+.17*min(overlap,2)/2
  return sorted(memories,key=value,reverse=True)[:6]

 def _ctx(self,aid,other,topic=''):
  with self.lock:
   a=copy.deepcopy(self.state['agents'][aid]);b=copy.deepcopy(self.state['agents'][other])
   rel=copy.deepcopy(self.state['relations'][aid][other]);minute=self.state['minute']
  m=self._memories(aid,b['name']+' '+topic,minute);beliefs=self.store.beliefs(aid,8)
  return a,b,rel,m,beliefs,dict(topic=topic,memories=[x['content'] for x in m],
   beliefs=[{'proposition':x['proposition'],'confidence':round(x['confidence'],2)} for x in beliefs[:5]],
   relation=rel,affect={'mood':a['mood'],'stress':a['stress'],'loneliness':a['loneliness']},
   traits=a['traits'],stance='curious')

 def _utter(self,a,b,text,minute,model):
  with self.lock:
   if a not in self.state['agents']:return
   src=self.state['agents'][a]['name'];dst=self.state['agents'][b]['name']
   self.store.dialogue(minute,a,b,text,model)
   self.store.event(minute,'dialogue',a,b,f"{src} : « {text} »",{'backend':model})
   self.store.memory(a,minute,'parole',f"J'ai dit à {dst} : {text}",.55,b)
   self.store.memory(b,minute,'entendu',f"{src} m'a dit : {text}",.72,a)
   self.state['agents'][a]['dialogue']=text[:135]
   self.state['agents'][a]['dialogue_until']=self.state['minute']+15
   self.state['agents'][a]['activity']='talking'
   self.store.save(self.state)

 def _worker(self):
  while not self.closed.is_set():
   try:item=self.tasks.get(timeout=.4)
   except queue.Empty:continue
   kind,epoch,*args=item
   try:
    if epoch!=self.epoch:continue
    if kind=='talk':self._conversation(*args,epoch)
    elif kind=='reflect':self._reflect(*args,epoch)
   except Exception as e:
    self.store.event(self.state['minute'],'error',None,None,f"Erreur de cognition : {type(e).__name__}: {str(e)[:150]}")
   finally:
    if kind=='talk':
     with self.lock:self.pending.discard(args[0])
    self.tasks.task_done()

 def _conversation(self,pair,aid,bid,minute,epoch):
  own=self.store.beliefs(aid,16);known={b['proposition'] for b in self.store.beliefs(bid,50)}
  unknown=[b for b in own if b['proposition'] not in known]
  shared=random.Random(minute+len(aid)).choice(unknown) if unknown else None
  topic=shared['proposition'] if shared else ''
  a,b,rel,m,beliefs,ctx=self._ctx(aid,bid,topic)
  first,model,error,latency=self.cognition.speak(a,b,ctx)
  self.store.log_model(minute,aid,'speech',model,latency,error)
  if epoch!=self.epoch:return
  self._utter(aid,bid,first,minute,model)
  listener,speaker,relation,mem,beliefs,ctx2=self._ctx(bid,aid,topic)
  answers,error=self.jev.judge(minute,listener,speaker,first,relation,mem,beliefs)
  result=decide(answers,listener,relation)
  with self.lock:
   if epoch!=self.epoch:return
   directed=self.state['relations'][bid][aid]
   directed['trust']=limit(directed['trust']+result['trust_delta'])
   directed['affinity']=limit(directed['affinity']+result['mood_delta']*.3)
   directed['tension']=limit(directed['tension']-result['trust_delta']*.5)
   directed['familiarity']=limit(directed['familiarity']+.025)
   other=self.state['agents'][bid]
   other['mood']=limit(other['mood']+result['mood_delta'],-1,1)
   other['stress']=limit(other['stress']-result['mood_delta']*.4)
   other['thought']='Je suis blessé.' if result['stance']=='guarded' else 'Cette rencontre me fait réfléchir.'
   other['experiences']['social']+=1
   if result['mood_delta']<0:other['experiences']['negative']+=1
   else:other['experiences']['positive']+=1
   if shared:
    # La propagation de croyance a une source et un degré de confiance subjectif.
    conf=limit(float(shared['confidence'])*directed['trust']*.9+.06)
    self.store.believe(bid,topic,conf,aid,minute)
    self.store.memory(bid,minute,'rumeur',f"{speaker['name']} m'a appris : {topic}",.82,aid)
   if answers:
    self.store.event(minute,'jev',bid,aid,'Jev évalue les indices affectifs de la rencontre.',
      {'tone':answers['tone'].get('choice'),'threat':answers['threat'].get('noul'),
       'upset':answers['upset'].get('score'),'delta_trust':round(result['trust_delta'],3)})
   elif self.cfg['jev_enabled']:
    self.store.event(minute,'jev_limit',bid,aid,'Aucun appel Jev : '+(error or 'non disponible'))
   self.store.save(self.state)
  listener,speaker,relation,mem,beliefs,ctx2=self._ctx(bid,aid,topic)
  ctx2['stance']=result['stance']
  reply,model,error,latency=self.cognition.speak(listener,speaker,ctx2,heard=first)
  self.store.log_model(minute,bid,'reply',model,latency,error)
  if epoch!=self.epoch:return
  self._utter(bid,aid,reply,minute,model)
  with self.lock:
   self.state['relations'][aid][bid]['familiarity']=limit(self.state['relations'][aid][bid]['familiarity']+.025)
   self.state['agents'][aid]['experiences']['social']+=1
   self.state['agents'][aid]['mood']=limit(self.state['agents'][aid]['mood']+.009,-1,1)
   self.store.save(self.state)

 def _new_day(self,day):
  minute=self.state['minute']
  for aid,a in self.state['agents'].items():
   prev=a['traits'].copy();e=a['experiences']
   delta=max(-.005,min(.005,(e['positive']-e['negative'])*.0015))
   a['traits']['agreeableness']=limit(a['traits']['agreeableness']+delta)
   a['traits']['neuroticism']=limit(a['traits']['neuroticism']-.75*delta)
   a['traits']['extraversion']=limit(a['traits']['extraversion']+max(-.003,min(.003,(e['social']-4)*.0005)))
   a['experiences']={'positive':0,'negative':0,'social':0}
   self.store.event(minute,'plasticity',aid,None,f"{a['name']} consolide son expérience.",
      {'old':prev,'new':a['traits']})
   if not self.tasks.full():self.tasks.put_nowait(('reflect',self.epoch,aid,minute))
  self.store.save(self.state)
 def _reflect(self,aid,minute,epoch):
  with self.lock:a=copy.deepcopy(self.state['agents'][aid])
  memories=self.store.memories(aid,12)
  reflection,model,error,latency=self.cognition.reflect(a,memories)
  if epoch!=self.epoch:return
  self.store.memory(aid,minute,'reflexion',reflection,.8,'introspection')
  self.store.log_model(minute,aid,'reflection',model,latency,error)
  self.store.event(minute,'reflection',aid,None,f"{a['name']} médite sur les expériences du jour.")

 def give_information(self,aid,text):
  text=' '.join(str(text).split())[:240]
  if len(text)<5:raise ValueError('Information trop courte')
  with self.lock:
   if aid not in self.state['agents']:raise ValueError('Personnage inconnu')
   minute=self.state['minute'];agent=self.state['agents'][aid]
   self.store.believe(aid,text,.81,'observation privée',minute)
   self.store.memory(aid,minute,'information',text,.92,'observateur')
   agent['thought']='Je viens d’apprendre quelque chose.'
   self.store.event(minute,'injection',aid,None,f"{agent['name']} reçoit une information privée.")
   self.store.save(self.state)
  return {'ok':True}
 def reset(self):
  with self.lock:
   if self.pending or not self.tasks.empty():raise ValueError('Attendre la fin des conversations pour recommencer')
   self.epoch+=1;self.store.reset();self.state=new_world(self.cfg['seed'])
   for a,secret in SECRETS.items():
    self.store.believe(a,secret,.86,'observation privée',480)
    self.store.memory(a,480,'observation',secret,.82,'personnel')
   self.store.save(self.state)

 def public(self):
  with self.lock:
   s=copy.deepcopy(self.state)
   s['status']={'brain':self.cognition.name,'brain_note':self.cognition.reason,
    'jev_enabled':self.cfg['jev_enabled'],'jev_key_set':bool(self.jev.key),
    'jev_budget':self.store.budget(self.cfg),'pending_jobs':self.tasks.qsize()+len(self.pending),
    'tick_seconds':self.cfg['tick_seconds']}
   s['events']=self.store.all('SELECT * FROM events ORDER BY id DESC LIMIT 55')
   s['dialogues']=self.store.all('SELECT * FROM dialogues ORDER BY id DESC LIMIT 35')
   s['individual']={a:{'memories':self.store.memories(a,16),'beliefs':self.store.beliefs(a,16)} for a in s['agents']}
   return s
 def export(self):
  with self.lock:
   return {'snapshot':copy.deepcopy(self.state),
    'memories':{a:self.store.memories(a,100000) for a in self.state['agents']},
    'beliefs':{a:self.store.beliefs(a,100000) for a in self.state['agents']},
    'events':self.store.all('SELECT * FROM events ORDER BY id'),
    'dialogues':self.store.all('SELECT * FROM dialogues ORDER BY id'),
    'jev_budget':self.store.budget(self.cfg),'excluded':'API key; Jev request text'}
