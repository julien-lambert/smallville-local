"""Salem-sur-Brume : microsociété close, cognition locale, jugement Jev parcimonieux.

Tous les habitants peuvent croire des choses fausses. Rien ne transforme une croyance
subjective en fait. La charte interdit le meurtre mais le monde peut connaître des infractions exceptionnelles.
"""
from __future__ import annotations
import copy
import queue
import random
import re
import threading
import time
import uuid
from collections import deque
from .seed import WIDTH, HEIGHT, WORLD_VERSION, SECRETS, ANNOUNCEMENT, PLACES, migrate_world, new_world
from .models import LocalBrain
from .jev import Jev, decide
from .graph import GraphBridge
from .graph_memory import GraphMemory
from .social_truth import explicitly_shared
from . import executive
from .transgression import deception, disobedience, confrontation
from .society import clamp, election, psyche
from .mind import ensure_mind, emotion_decay, arousal, category, apply_appraisal


def limit(x,lo=0,hi=1): return max(lo,min(hi,float(x)))


def find_path(grid, a, b):
    a=tuple(a);b=tuple(b)
    h=len(grid);w=len(grid[0])
    if a==b:return []
    if not(0<=b[0]<w and 0<=b[1]<h) or grid[b[1]][b[0]] in ('tree','building'):return []
    q=deque([a]);prev={a:None}
    while q:
        x,y=q.popleft()
        if (x,y)==b:break
        for nxt in ((x+1,y),(x,y+1),(x-1,y),(x,y-1)):
            xx,yy=nxt
            if 0<=xx<w and 0<=yy<h and nxt not in prev and grid[yy][xx] not in ('tree','building'):
                prev[nxt]=(x,y);q.append(nxt)
    if b not in prev:return []
    path=[]
    while b!=a:path.append(list(b));b=prev[b]
    return path[::-1]


class Simulation:
    def __init__(self,store,cfg):
        self.store,self.cfg=store,cfg
        self.lock=threading.RLock()
        previous=store.snap()
        self.state=previous or new_world(cfg['seed'])
        additions=[]
        if previous and (self.state.get('version',0)<WORLD_VERSION or len(self.state.get('agents',{}))<25):
            self.state,additions=migrate_world(self.state,cfg['seed'])
        if not self.state.get('run_id'):
            self.state['run_id']=uuid.uuid4().hex[:12]
        self.store.set_run(self.state['run_id'])
        for a in self.state['agents'].values():
            ensure_mind(a);executive.ensure(a)
        self.state['laws'].update({'murder_forbidden':True,'executions_forbidden':True,
            'violent_actions_forbidden':False,'murder_physically_possible':True})
        self.cognition=LocalBrain(cfg);self.jev=Jev(store,cfg);self.graph=GraphBridge(store)
        self.graph_memory=GraphMemory(self.graph,store)
        self.tasks=queue.Queue(maxsize=18)
        self.judgment_tasks=queue.Queue(maxsize=70)
        self.judgment_pending=set()
        self.pending=set();self.closed=threading.Event();self.epoch=0
        self.threads=[]
        if previous is None:
            for aid,secret in SECRETS.items():
                self.store.believe(aid,secret,.86,'observation privée',self.state['minute'])
                self.store.memory(aid,self.state['minute'],'observation',secret,.85,'personnel')
            for aid in self.state['agents']:
                self.store.believe(aid,ANNOUNCEMENT,.95,'annonce publique',self.state['minute'])
            self.store.event(self.state['minute'],'world',None,None,
              'Vingt-cinq habitants de Salem-sur-Brume commencent la veille des élections. La charte interdit le meurtre.')
        elif additions:
            for aid in additions:
                self.store.believe(aid,SECRETS.get(aid,''),.8,'observation privée',self.state['minute'])
                self.store.memory(aid,self.state['minute'],'observation',SECRETS.get(aid,''),.8,'personnel')
                self.store.believe(aid,ANNOUNCEMENT,.95,'annonce publique',self.state['minute'])
            self.store.event(self.state['minute'],'migration',None,None,
                f'Migration non destructive vers 25 habitants : {len(additions)} arrivants.')
        self._bootstrap_graph()
        self.store.save(self.state)

    def _bootstrap_graph(self):
        if self.store.graph_bootstrapped(self.state['run_id']):return
        for a in self.state['agents'].values():self.store.agent_node(a)
        for aid,others in self.state['relations'].items():
            for bid,rel in others.items():self.store.relation(aid,bid,rel,self.state['minute'])
        self.store.set_graph_bootstrapped(self.state['run_id'])

    def start(self):
        self.graph.start()
        for name,fn in [('horloge',self._clock),('cognition',self._worker),('jugement-jev',self._judgment_worker)]:
            t=threading.Thread(name='smallville-'+name,target=fn,daemon=True)
            t.start();self.threads.append(t)

    def close(self):
        self.closed.set();self.graph.close()
        with self.lock:self.store.save(self.state)

    def _clock(self):
        while not self.closed.wait(float(self.cfg['tick_seconds'])):
            with self.lock:
                if not self.state['paused']:self._step()

    def step(self):
        with self.lock:self._step()

    def advance(self,n):
        n=int(n)
        if not 1<=n<=2400:raise ValueError('Avance entre 1 et 2400 minutes')
        with self.lock:
            if not self.state['paused']:raise ValueError('Mettre en pause avant l’avance rapide')
            if self.cfg.get('jev_enabled'):raise ValueError('Désactiver Jev pour une avance rapide sans dépense')
            for _ in range(n):self._step()
            self.store.save(self.state)
            return self.state['minute']

    def pause(self,value):
        with self.lock:self.state['paused']=bool(value);self.store.save(self.state)

    def _step(self):
        s=self.state;s['minute']+=1;s['ticks']+=1;minute=s['minute']
        rng=random.Random(s['seed']+minute*301)
        day=minute//1440
        if day>s['last_day']:
            self._new_day(day);s['last_day']=day;s['conversations_today']=0;s['group_sessions_today']=0
        for a in s['agents'].values():
            if not a.get('alive',True):continue
            if a.get('detained_until',0)>minute:
                a['activity']='detained';a['destination']=[a['x'],a['y']];continue
            a['social']=limit(a['social']-.0009);a['loneliness']=limit(a['loneliness']+.0007)
            a['energy']=limit(a['energy']-.00045);a['hunger']=limit(a['hunger']+.00029)
            if a['activity']=='resting':
                a['energy']=limit(a['energy']+.009);a['stress']=limit(a['stress']-.0025)
            if minute%1440<6*60:a['energy']=limit(a['energy']+.002)
            if a['hunger']>.88:
                a['health']=limit(a['health']-.00045,.07,1)
                a['hope']=limit(a['hope']-.0001)
            if minute%20==0:psyche(a)
            if minute%15==0:emotion_decay(a)
            if self.cfg.get('jev_enabled') and (minute+sum(ord(c) for c in a['id']))%19==0:
                self._schedule_judgment(a['id'],'routine',minute)
            if ([a['x'],a['y']]==a['destination'] and minute>=a['stay_until']) or minute-a['last_plan']>150:
                if a.get('executive',{}).get('project',{}):
                    project=a['executive']['project']
                    if (project and project['kind']=='survival' and
                            [a['x'],a['y']]==list(PLACES['grenier']) and
                            s['resources']['granary']>0 and
                            minute-a.get('last_food_pickup',-99999)>300):
                        s['resources']['granary']-=1;a['provisions']+=1
                        a['last_food_pickup']=minute
                        self.store.event(minute,'food_aid',a['id'],None,
                            f"{a['name']} reçoit une ration du grenier.",{'rations':1})
                outcome=executive.progress_on_site(a,s,minute)
                if outcome:self._record_project(a,outcome,minute)
                self._plan(a,rng,minute)
            if [a['x'],a['y']]!=a['destination']:
                if not a.get('route') or tuple(a['route'][-1])!=tuple(a['destination']):
                    a['route']=find_path(s['grid'],[a['x'],a['y']],a['destination'])
                if a['route']:
                    a['x'],a['y']=a['route'].pop(0);a['activity']='walking'
                else:a['destination']=[a['x'],a['y']]
            elif a['activity']=='walking':a['activity']='observing'
            if a['dialogue_until']<minute:a['dialogue']=''
        if s['politics']['phase']!='complete' and minute>=s['politics']['election_minute']:
            election(self)
        if minute%15==0 and s['politics']['phase']=='campaign':self._campaign(rng,minute)
        self._social(rng,minute)
        if minute%20==0:
            for agent in s['agents'].values():
                incident=disobedience(agent,minute,s['seed'])
                if incident:
                    self.store.event(minute,'civil_disobedience',agent['id'],None,
                       f"{agent['name']} conteste un édit communal.",incident)
                    self.store.memory(agent['id'],minute,'désobéissance',
                       'J’ai choisi de contester une règle.',.75,'acte personnel')
        if minute%10==0:confrontation(self,minute,rng)
        if s['ticks']%10==0:self.store.save(s)

    def _schedule_judgment(self,aid,trigger,minute,force=False):
        """Ordonnanceur non bloquant : 25 esprits, un seul moteur Jev partagé."""
        if not self.cfg.get('jev_enabled') or not self.jev.key:return False
        a=self.state['agents'].get(aid)
        if not a or not a.get('alive',True) or aid in self.judgment_pending or self.judgment_tasks.full():return False
        if not force and minute-a.get('last_jev_attempt',-99999)<95:return False
        # Une nouvelle information est plus saillante qu'un cycle routinier.
        if force and minute-a.get('last_jev_attempt',-99999)<18:return False
        a['last_jev_attempt']=minute
        self.judgment_pending.add(aid)
        self.judgment_tasks.put_nowait((self.epoch,aid,trigger,minute))
        return True

    def _judgment_worker(self):
        while not self.closed.is_set():
            try:epoch,aid,trigger,minute=self.judgment_tasks.get(timeout=.35)
            except queue.Empty:continue
            try:
                if epoch==self.epoch:self._appraise(aid,trigger,minute,epoch)
            except Exception as exc:
                self.store.event(minute,'error',aid,None,
                    f'Erreur de jugement Jev : {type(exc).__name__}: {str(exc)[:130]}')
            finally:
                with self.lock:self.judgment_pending.discard(aid)
                self.judgment_tasks.task_done()

    def _appraise(self,aid,trigger,minute,epoch):
        # Construire le contexte AU MOMENT de la requête; jamais conserver un prompt figé.
        with self.lock:
            if epoch!=self.epoch:return
            a=copy.deepcopy(self.state['agents'][aid])
            if not a.get('alive',True):return
            executive.ensure(a)
            related=sorted(self.state['relations'][aid].items(),key=lambda x:-x[1]['familiarity'])[:5]
            relations=[{'name':self.state['agents'][bid]['name'],
                        'trust':round(r['trust'],2),'tension':round(r['tension'],2)} for bid,r in related]
            p=self.state['politics']
            public={'current_day':self.state['minute']//1440+1,
                    'time':self.state['minute']%1440,
                    'tomorrow_election':p['phase']=='campaign',
                    'election_in_minutes':max(0,p['election_minute']-self.state['minute']),
                    'charter':'Meurtre et exécutions interdits',
                    'public_budget':p['budget_total']}
            candidates=[{'id':cid,'name':self.state['agents'][cid]['name'],
               'role':self.state['agents'][cid]['role'],
               'goal':self.state['agents'][cid]['goal']} for cid in p['candidates']]
        relevant=self._memories(aid,trigger+' foi preuves élections survie',minute)
        memory_graph=self.graph_memory.context(self.state['run_id'],aid,trigger,minute,a.get('salience'))
        public['memoire_relationnelle']=str(memory_graph)[:1150]
        all_beliefs=self.store.beliefs(aid,45)
        # Une croyance réellement susceptible de changer, pas toujours l'annonce publique.
        selected=sorted(all_beliefs,key=lambda b:(
            .75*a['salience'].get(category(b['proposition']),.4)
            +.20/(1+max(0,minute-b['minute'])/500)
            +.10*(1-b['confidence'])),reverse=True)
        beliefs=selected[:7]
        # Attendre le prochain créneau autorisé n'est pas un retry réseau.
        cooldown=self.store.seconds_until_jev(self.cfg)
        if cooldown and self.closed.wait(cooldown+.03):return
        start=time.monotonic()
        answers,error=self.jev.appraise(minute,a,relevant,beliefs,relations,public,
                              candidates if p['phase']=='campaign' else None)
        self.store.log_model(minute,aid,'jev-'+trigger,'jev-1.14.0' if answers else 'no-jev',
                             time.monotonic()-start,error)
        if not answers:return
        with self.lock:
            if epoch!=self.epoch:return
            current=self.state['agents'][aid]
            focus=beliefs[0] if beliefs else None
            # Si la croyance a changé pendant l'appel, on utilise sa confiance actuelle.
            latest={b['proposition']:b for b in self.store.beliefs(aid,100)}
            prior=latest.get(focus['proposition']) if focus else None
            outcome=apply_appraisal(current,answers,focus,prior['confidence'] if prior else None)
            if answers.get('project',{}).get('choice') in executive.KINDS:
                current['executive']['jev_project']=answers['project']['choice']
            c=answers.get('commitment',{}).get('noul')
            if c is not None:
                current['executive']['commitment_strength']=limit(.35+.60*float(c),.1,.97)
            tactic=answers.get('tactic',{}).get('choice')
            if tactic in ('sincere','withhold','mislead'):
                current['executive']['tactic']=tactic
            norm=answers.get('norm_strategy',{}).get('choice')
            if norm in ('obey','dissent','defy','intimidate'):
                current['executive']['norm_strategy']=norm
            current['last_jev_minute']=self.state['minute']
            # Un jugement Jev influe sur le comportement dès le prochain tick,
            # plutôt que d'attendre l'expiration arbitraire du plan précédent.
            if outcome['intention']!=outcome['before']['intention']:
                current['last_plan']=min(current['last_plan'],self.state['minute']-151)
                current['stay_until']=min(current['stay_until'],self.state['minute'])
            if current['executive'].get('project') and outcome['intention']!=outcome['before']['intention']:
                if current['hunger']>.85:
                    executive.abandon(current,self.state['minute'],'urgence vitale')
            outcome['trigger']=trigger
            if outcome['revision']:
                rev=outcome['revision']
                if abs(rev['after']-rev['before'])>.001:
                    self.store.believe(aid,rev['proposition'],rev['after'],
                        'révision par examen subjectif avec Jev',self.state['minute'])
                    self.store.memory(aid,self.state['minute'],'doute',
                        f"J'ai réexaminé « {rev['proposition'][:160]} » : "
                        f"confiance {rev['before']:.2f} → {rev['after']:.2f}.",.84,'introspection')
                    self.store.event(self.state['minute'],'belief_revision',aid,None,
                        f"{current['name']} reconsidère une croyance.",{'revision':rev})
            self.store.cognitive_trace(aid,self.state['minute'],'jev_appraisal',{
                'trigger':trigger,'before':outcome['before'],'after':outcome['after'],
                'memories_selected':[{'content':m.get('content','')[:180],
                                      'source':m.get('source'),'minute':m.get('minute')} for m in relevant[:6]],
                'beliefs_selected':beliefs[:7],'answers':answers,
                'project':copy.deepcopy(current.get('executive',{}).get('project')),
                'decision':current['intention'],'worldview':current['worldview']})
            self.store.memory(aid,self.state['minute'],'intention',
                f"{current['mental_trace']} (motif : {trigger})",.68,'jugement Jev')
            self.store.event(self.state['minute'],'jev_mind',aid,None,
                f"{current['name']} choisit {outcome['intention']} ; valeur : {outcome['political_priority']}.",
                {'trigger':trigger,'priority':outcome['intention'],'affect':outcome['emotion'],
                 'political_value':outcome['political_priority'],
                 'candidate':outcome['candidate'],'revision':outcome['revision']})
            self.store.queue_graph('state',{'run_id':self.state['run_id'],
              'id':f'{self.state["minute"]}_{aid}_jev_{current["decisions"]}','agent':aid,
              'data':{'minute':self.state['minute'],'trigger':trigger,
                'worldview':current['worldview'],'emotions':current['emotions'],
                'salience':current['salience'],'intent':current['intention'],
                'candidate':current['candidate_preference'],'conatus':current['conatus']}})
            self.store.save(self.state)

    def _record_project(self,agent,change,minute):
        """L'action terminée est datée et exploitable dans le graphe."""
        self.store.event(minute,'plan_progress',agent['id'],None,
            f"{agent['name']} : {change.get('step',change.get('status'))}.",change)
        self.store.queue_graph('project',{'run_id':self.state['run_id'],
            'id':f"{minute}_{agent['id']}_step",'agent':agent['id'],
            'data':{'minute':minute,**change}})

    def _plan(self,a,rng,minute):
        ex=executive.ensure(a)
        old=ex['project']['id'] if ex['project'] else None
        dest,activity,thought=executive.navigate(a,self.state,rng,minute)
        new=ex['project']['id'] if ex['project'] else None
        if new and new!=old:
            proj=ex['project']
            self.store.event(minute,'plan_created',a['id'],proj.get('target'),
               f"{a['name']} décide : {proj['objective']}",
               {'id':proj['id'],'steps':proj['steps'],'origin':proj['origin']})
            self.store.queue_graph('project',{'run_id':self.state['run_id'],
                'id':proj['id'],'agent':a['id'],'data':{'minute':minute,**proj}})
        a['destination']=dest;a['route']=[];a['activity']=activity;a['thought']=thought
        a['last_plan']=minute;a['stay_until']=minute+rng.randint(12,25)

    def _campaign(self,rng,minute):
        if minute%60!=0:return
        active=[c for c in self.state['politics']['candidates']
                if self.state['agents'][c].get('alive',True)]
        if not active:return
        candidate=rng.choice(active)
        a=self.state['agents'][candidate]
        self.store.event(minute,'campaign',candidate,None,
            f"{a['name']} ({a['role']}) promet de défendre : {a['goal']}")
        # La campagne publique informe les électeurs sans leur imposer l'accord.
        for aid in self.state['agents']:
            if aid==candidate:continue
            if rng.random()<.2:
                self.store.memory(aid,minute,'campagne',f"J'ai entendu les promesses de {a['name']}.",.42,candidate)

    def _social(self,rng,minute):
        if len(self.pending)>=2 or self.tasks.full() or self.state['conversations_today']>=32:return
        people=list(self.state['agents'].values())
        free=[a for a in people if a.get('alive',True) and a.get('detained_until',0)<=minute and minute-a['last_social']>=20]
        hubs=[PLACES[k] for k in ('eglise','place','taverne','mairie','marche')]
        if (self.state['group_sessions_today']<4 and minute%15==0 and rng.random()<.45):
            for hub in rng.sample(hubs,len(hubs)):
                group=[a for a in free if abs(a['x']-hub[0])+abs(a['y']-hub[1])<=5]
                if len(group)>=3:
                    participants=rng.sample(group,min(len(group),rng.randint(3,5)))
                    ids=[a['id'] for a in participants];key='group-'+str(minute)
                    self.pending.add(key);self.state['group_sessions_today']+=1
                    self.state['conversations_today']+=1
                    for a in participants:
                        a['last_social']=minute;a['social']=limit(a['social']+.1)
                        a['loneliness']=limit(a['loneliness']-.08)
                    self.store.assembly(minute,ids,'Religiosité, vie communale et élections')
                    self.store.event(minute,'assembly',ids[0],None,
                        'Assemblée de '+', '.join(self.state['agents'][i]['name'] for i in ids)+'.',{'participants':ids})
                    self.tasks.put_nowait(('group',self.epoch,key,ids,minute))
                    return
        candidates=[]
        for i,a in enumerate(free):
            for b in free[i+1:]:
                if abs(a['x']-b['x'])+abs(a['y']-b['y'])>3:continue
                pair='-'.join(sorted([a['id'],b['id']]))
                if pair in self.pending or minute-self.state['seen_pairs'].get(pair,-100)<40:continue
                chance=.14+.1*(a['traits']['extraversion']+b['traits']['extraversion'])/2
                if executive.ensure(a)['project'] and executive.ensure(a)['project'].get('target')==b['id']:chance+=.52
                if executive.ensure(b)['project'] and executive.ensure(b)['project'].get('target')==a['id']:chance+=.52
                if rng.random()<min(.95,chance):candidates.append((a,b,pair))
        if not candidates:return
        a,b,pair=rng.choice(candidates)
        if b['traits']['extraversion']>a['traits']['extraversion'] and rng.random()<.7:a,b=b,a
        self.pending.add(pair);self.state['seen_pairs'][pair]=minute
        self.state['conversations_today']+=1
        for x in (a,b):
            x['last_social']=minute;x['social']=limit(x['social']+.13)
            x['loneliness']=limit(x['loneliness']-.12)
        self.store.event(minute,'meeting',a['id'],b['id'],f"{a['name']} rencontre {b['name']}.")
        self.tasks.put_nowait(('talk',self.epoch,pair,a['id'],b['id'],minute))

    def _memories(self,aid,other,minute):
        memories=self.store.memories(aid,48)
        words=set(re.findall(r'[\wÀ-ÿ]{4,}',other.lower()))
        def value(m):
            overlap=len(words&set(re.findall(r'[\wÀ-ÿ]{4,}',m['content'].lower())))
            recent=1/(1+max(0,minute-m['minute'])/700)
            return .6*m['importance']+.17*recent+.23*min(overlap,3)/3
        current=self.state['agents'].get(aid,{})
        salience=current.get('salience',{})
        def weighted(m):
            return .78*value(m)+.22*salience.get(category(m['content']),.4)
        return sorted(memories,key=weighted,reverse=True)[:7]

    def _ctx(self,aid,other,topic=''):
        with self.lock:
            a=copy.deepcopy(self.state['agents'][aid]);b=copy.deepcopy(self.state['agents'][other]);
            rel=copy.deepcopy(self.state['relations'][aid][other]);minute=self.state['minute'];run_id=self.state['run_id']
        memories=self._memories(aid,b['name']+' '+topic,minute)
        beliefs=self.store.beliefs(aid,15)
        graph_info=self.graph_memory.context(run_id,aid,topic+' '+b['name'],minute,a.get('salience'))
        ctx={'topic':topic,'time':{'minute':minute,'day':minute//1440+1},
             'memories':[x['content'] for x in memories],
             'beliefs':[{'proposition':x['proposition'],'confidence':round(x['confidence'],2)} for x in beliefs[:8]],
             'relation':rel,'affect':{k:a[k] for k in ('mood','stress','loneliness','hunger','hope','conatus')},
             'emotions':a.get('emotions',{}),'worldview':a.get('worldview',{}),
             'salience':a.get('salience',{}),'intention':a.get('intention','observe'),
             'mental_trace':a.get('mental_trace',''),
             'community_trust':a.get('community_trust'),
             'expression_inhibition':a.get('expression_inhibition'),
             'present_experience':{'activity':a.get('activity'),'plan':a.get('destination'),
                                   'reflections':a.get('reflections'),'decisions':a.get('decisions')},
             'political_priority':a.get('political_priority',''),
             'traits':{**a['traits'],**{k:a[k] for k in ('religiosity','credulity','reasoning','aggression','suspicion','tolerance')}},
             'resources':{'provisions':a['provisions'],'coins':a['coins']},
             'graph_neighborhood':graph_info,
             'executive_project':a.get('executive',{}).get('project'),
             'prospective_agenda':a.get('executive',{}).get('agenda',[])[:4],
             'rhetorical_strategy':a.get('executive',{}).get('tactic','sincere'),
             'stance':'curious'}
        return a,b,rel,memories,beliefs,ctx

    def _utter(self,aid,bid,text,minute,model):
        with self.lock:
            if aid not in self.state['agents']:return
            a,b=self.state['agents'][aid],self.state['agents'][bid]
            self.store.dialogue(minute,aid,bid,text,model)
            self.store.event(minute,'dialogue',aid,bid,f'{a["name"]} : « {text} »',{'backend':model})
            self.store.memory(aid,minute,'parole',f"J'ai dit à {b['name']} : {text}",.55,bid)
            self.store.memory(bid,minute,'entendu',f"{a['name']} m'a dit : {text}",.72,aid)
            a['dialogue']=text[:135];a['dialogue_until']=self.state['minute']+15
            a['activity']='talking';self.store.save(self.state)

    def _worker(self):
        while not self.closed.is_set():
            try:item=self.tasks.get(timeout=.4)
            except queue.Empty:continue
            kind,epoch,*args=item
            try:
                if epoch!=self.epoch:continue
                if kind=='talk':self._conversation(*args,epoch)
                elif kind=='group':self._group_conversation(*args,epoch)
                elif kind=='reflect':self._reflect(*args,epoch)
            except Exception as exc:
                self.store.event(self.state['minute'],'error',None,None,
                  f'Erreur de cognition : {type(exc).__name__}: {str(exc)[:140]}')
            finally:
                if kind in ('talk','group'):
                    with self.lock:self.pending.discard(args[0])
                self.tasks.task_done()

    def _diffuse(self,sender,listener,belief,minute,group=False):
        if not belief:return
        a=self.state['agents'][listener];r=self.state['relations'][listener][sender]
        conf=limit(float(belief['confidence'])*(.27+.7*r['trust'])*(.4+.5*a['credulity'])*
                   (1-.38*a['reasoning']*(1-a['credulity']))+.06,.05,.97)
        self.store.believe(listener,belief['proposition'],conf,sender,minute)
        self.store.memory(listener,minute,'rumeur' if not group else 'assemblée',
            f"{self.state['agents'][sender]['name']} m'a raconté : {belief['proposition']}",
            .6+.3*conf,sender)
        r['familiarity']=limit(r['familiarity']+.022)
        arousal(a,category(belief['proposition']),.14)
        a['emotions']['fear']=limit(a['emotions']['fear']+.026*a['suspicion'])
        self.store.relation(listener,sender,r,minute)
        self.store.queue_graph('relation_change',{'run_id':self.state['run_id'],
            'id':f'{minute}_{listener}_{sender}', 'agent':listener,
            'data':{'minute':minute,'actor':listener,'target':sender,'trust':r['trust'],
                    'tension':r['tension'],'context':'transmission de croyance'}})

    def _conversation(self,pair,aid,bid,minute,epoch):
        own=self.store.beliefs(aid,20)
        known={b['proposition'] for b in self.store.beliefs(bid,120)}
        fresh=[b for b in own if b['proposition'] not in known]
        shared=random.Random(minute+len(aid)).choice(fresh) if fresh else None
        if shared and executive.ensure(self.state['agents'][aid]).get('tactic')=='withhold':
            shared=None
        topic=shared['proposition'] if shared else 'le scrutin et l’avenir de la communauté'
        ex=executive.ensure(self.state['agents'][aid]);project=ex.get('project')
        if project and project.get('target')==bid:
            topic=project['objective']+' (je souhaite en parler avec toi)'
            shared=None
        a,b,rel,mem,beliefs,ctx=self._ctx(aid,bid,topic)
        strategy=deception(a,shared,bid,minute)
        if strategy:
            first=strategy['utterance'];model='intentional-deception';error=None;latency=0.0
            self.store.event(minute,'deception',aid,bid,
                f"{a['name']} choisit de tromper {b['name']}.",
                {'private_belief':strategy['internal_belief'],
                 'public_claim':strategy['reported_claim'],'motive':strategy['motive']})
        else:
            first,model,error,latency=self.cognition.speak(a,b,ctx)
        self.store.log_model(minute,aid,'speech',model,latency,error)
        if epoch!=self.epoch:return
        self._utter(aid,bid,first,minute,model)
        listener,speaker,relation,m,beliefs,ctx2=self._ctx(bid,aid,topic)
        spoken=(dict(shared,proposition=strategy['reported_claim'],confidence=.30)
                if strategy else shared)
        answers,error=self.jev.judge(minute,listener,speaker,first,relation,m,beliefs,
            topic=spoken['proposition'] if spoken else None)
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
            other['thought']='Je doute des intentions de mon voisin.' if result['stance']=='guarded' else 'Cette rencontre nourrit ma réflexion.'
            arousal(other,category(topic),.16)
            other['emotions']['anger']=limit(other['emotions']['anger']+.065) if result['stance']=='guarded' else limit(other['emotions']['anger']-.022)
            other['emotions']['compassion']=limit(other['emotions']['compassion']+.03) if result['stance']=='warm' else other['emotions']['compassion']
            other['experiences']['social']+=1
            other['experiences']['negative' if result['mood_delta']<0 else 'positive']+=1
            # Une croyance ne peut être acquise sans communication réelle.
            communicated = (float((answers.get('claim_expressed') or {}).get('noul',0)) >= .70
                            if answers else explicitly_shared(first,spoken['proposition'])) if spoken else False
            if spoken and communicated:
                self._diffuse(aid,bid,spoken,minute)
                if strategy:
                    self.store.memory(bid,minute,'témoignage',
                        f"{a['name']} a affirmé : {strategy['reported_claim']}",.6,aid)
                if answers:
                    # Nuancer la confiance selon les éléments perçus, sans transformer une parole en vérité.
                    support=float(answers.get('claim_supported',{}).get('noul',.5))
                    if support<.25 and not strategy:
                        current_beliefs={x['proposition']:x for x in self.store.beliefs(bid,60)}
                        old=current_beliefs.get(topic)
                        if old:
                            self.store.believe(bid,topic,limit(old['confidence']*.84,.02,.95),
                                              'révision après conversation',minute)
            self.store.relation(bid,aid,directed,minute)
            self.store.queue_graph('relation_change',{'run_id':self.state['run_id'],
              'id':f'{minute}_{bid}_{aid}', 'agent':bid,
              'data':{'minute':minute,'actor':bid,'target':aid,
                      'trust':directed['trust'],'tension':directed['tension'],
                      'mood_delta':result['mood_delta']}})
            if answers:
                self.store.event(minute,'jev',bid,aid,'Jev évalue cette interaction.',
                  {'tone':answers['tone'].get('choice'),'delta_trust':round(result['trust_delta'],3)})
            elif self.cfg['jev_enabled']:
                self.store.event(minute,'jev_limit',bid,aid,'Jev non consulté : '+(error or 'limite'))
        listener,speaker,relation,m,beliefs,ctx2=self._ctx(bid,aid,topic)
        ctx2['stance']=result['stance']
        reply,model,error,latency=self.cognition.speak(listener,speaker,ctx2,heard=first)
        self.store.log_model(minute,bid,'reply',model,latency,error)
        if epoch!=self.epoch:return
        self._utter(bid,aid,reply,minute,model)
        with self.lock:
            self.state['relations'][aid][bid]['familiarity']=limit(self.state['relations'][aid][bid]['familiarity']+.025)
            self.state['agents'][aid]['experiences']['social']+=1
            self.state['agents'][aid]['mood']=limit(self.state['agents'][aid]['mood']+.009,-1,1)
            self.store.relation(aid,bid,self.state['relations'][aid][bid],minute)
            self.store.save(self.state)
            for individual,other_id in ((aid,bid),(bid,aid)):
                changed=executive.contact(self.state['agents'][individual],other_id,minute)
                if changed:self._record_project(self.state['agents'][individual],changed,minute)
            self._schedule_judgment(bid,'rencontre',minute,force=True)

    def _group_conversation(self,key,participants,minute,epoch):
        ids=list(participants)
        for idx,aid in enumerate(ids[:min(3,len(ids))]):
            if epoch!=self.epoch:return
            recipient=ids[(idx+1)%len(ids)]
            own=self.store.beliefs(aid,18)
            topic=next((x['proposition'] for x in own if 'élection' not in x['proposition']),
                'Le vote, les prédicateurs et le partage du pain.')
            a,b,rel,mem,beliefs,ctx=self._ctx(aid,recipient,topic)
            ctx['group']=[self.state['agents'][x]['name'] for x in ids]
            ctx['topic']='En assemblée publique : '+topic
            txt,backend,error,latency=self.cognition.speak(a,b,ctx)
            self.store.log_model(minute,aid,'group-speech',backend,latency,error)
            if epoch!=self.epoch:return
            with self.lock:
                if epoch!=self.epoch:return
                self.store.dialogue(minute,aid,'group',txt,backend)
                self.store.event(minute,'group_dialogue',aid,None,
                    f"{a['name']} dit devant {len(ids)-1} habitants : « {txt} »",{'participants':ids,'backend':backend})
                self.store.memory(aid,minute,'parole_publique',f"J'ai dit en assemblée : {txt}",.68,'assemblée')
                self.state['agents'][aid]['dialogue']=txt[:135]
                self.state['agents'][aid]['dialogue_until']=self.state['minute']+16
                shared=next((x for x in own if x['proposition']==topic),None)
                for bid in ids:
                    if bid==aid:continue
                    self.store.memory(bid,minute,'entendu_en_groupe',f"{a['name']} a dit : {txt}",.65,aid)
                    self.state['agents'][bid]['experiences']['social']+=1
                    if shared and explicitly_shared(txt,shared['proposition']):
                        self._diffuse(aid,bid,shared,minute,group=True)
                    # Une assemblée peut déclencher une nouvelle appréciation Jev
                    # sans forcer d'appel si un quota ou un cooldown est atteint.
                    if shared:self._schedule_judgment(bid,'assemblée',minute,force=True)
                self.store.save(self.state)

    def _daily_economy(self,minute):
        s=self.state;r=s['resources'];agents=s['agents']
        # Causalité matérielle : nourriture, salaire, dépenses, monnaie conservée.
        for a in agents.values():
            if not a.get('alive',True):continue
            if a['provisions']>0:
                a['provisions']-=1;a['hunger']=limit(a['hunger']-.36)
            elif r['granary']>0 and a['coins']>=r['food_price']:
                a['coins']-=r['food_price'];r['treasury']+=r['food_price']
                r['granary']-=1;r['grain_consumed']+=1;a['hunger']=limit(a['hunger']-.31)
                self.store.event(minute,'trade',a['id'],None,f"{a['name']} achète une ration au grenier.")
            else:
                a['hunger']=limit(a['hunger']+.23)
                a['security']=limit(a['security']-.05)
            salary=min(a['income'],r['treasury'])
            if salary>0:
                a['coins']+=salary;r['treasury']-=salary
            if a['workplace']=='champs':
                grain=max(1,round(1.5*s['resources']['field_fertility']))
                r['granary']+=grain;r['grain_produced']+=grain
            psyche(a)
        # Aide entre personnes : conatus et générosité, pas de création monétaire.
        poor=sorted(agents.values(),key=lambda x:(x['provisions'],x['coins']))
        wealthy=sorted(agents.values(),key=lambda x:x['coins']*x['generosity'],reverse=True)
        for receiver in poor[:3]:
            for giver in wealthy:
                if giver['id']!=receiver['id'] and giver['coins']>90 and giver['generosity']>.7 and receiver['coins']<20:
                    amount=min(8,giver['coins']);giver['coins']-=amount;receiver['coins']+=amount
                    self.store.event(minute,'solidarity',giver['id'],receiver['id'],
                        f"{giver['name']} donne {amount} écus à {receiver['name']}.")
                    break
        self.store.event(minute,'economy',None,None,
             f"Grenier : {r['granary']} rations. Trésorerie : {r['treasury']} écus.")
        assert r['treasury']+sum(a['coins'] for a in agents.values())==r['currency_supply_initial']

    def _new_day(self,day):
        minute=self.state['minute']
        self._daily_economy(minute)
        for aid,a in self.state['agents'].items():
            if not a.get('alive',True):continue
            prev=a['traits'].copy();e=a['experiences']
            delta=max(-.004,min(.004,(e['positive']-e['negative'])*.0009))
            a['traits']['agreeableness']=limit(a['traits']['agreeableness']+delta)
            a['traits']['neuroticism']=limit(a['traits']['neuroticism']-.6*delta)
            a['traits']['extraversion']=limit(a['traits']['extraversion']+
                        max(-.002,min(.002,(e['social']-4)*.0003)))
            # Consolidation autonome : expérience + conatus + croyances subjectives.
            beliefs=self.store.beliefs(aid,15)
            past=self._memories(aid,'maire religion communauté survie',minute)
            memory=past[0]['content'][:130] if past else 'une journée calme'
            if a['hunger']>.65:
                reflection=f"Je dois assurer ma subsistance. Je repense à {memory}"
                a['hope']=limit(a['hope']-.01)
            elif a['stress']>.65:
                reflection=f"La défiance m'inquiète. Je repense à {memory}"
                a['suspicion']=limit(a['suspicion']+.002)
            else:
                reflection=f"J'ai appris de mes interactions : {memory} Je dois peser mes choix."
                a['hope']=limit(a['hope']+.005)
            a['thought']=reflection[:180];a['reflections']+=1;a['last_reflection']=minute
            self.store.memory(aid,minute,'reflexion',reflection,.72,'introspection locale')
            self.store.queue_graph('state',{'run_id':self.state['run_id'],'id':f'{minute}_{aid}',
              'agent':aid,'data':{'minute':minute,'traits':a['traits'],'conatus':a['conatus'],
                'religiosity':a['religiosity'],'credulity':a['credulity'],
                'hunger':a['hunger'],'stress':a['stress'],'coins':a['coins'],
                'health':a['health']}})
            self.store.event(minute,'reflection',aid,None,f"{a['name']} consolide son expérience.",
              {'conatus':a['conatus'],'hope':a['hope']})
            self.store.queue_graph('reflection',{'run_id':self.state['run_id'],
              'id':f'{minute}_{aid}','agent':aid,'data':{'minute':minute,'content':reflection}})
            a['experiences']={'positive':0,'negative':0,'social':0}
            ex=executive.ensure(a)
            ex['future_scenarios']=(ex['future_scenarios'] or [])[-2:]
            self.store.memory(aid,minute,'projection',
                'Projection personnelle : '+str(ex['future_scenarios'][-1]['then'] if ex['future_scenarios'] else 'Je préparerai ma journée.'),
                .50,'imaginaire — hypothèse non factuelle')
            if len(self.state['agents'])<=25 and not self.tasks.full():
                self.tasks.put_nowait(('reflect',self.epoch,aid,minute))
            if a['traits']!=prev:
                self.store.event(minute,'plasticity',aid,None,f"{a['name']} fait évoluer son caractère.",
                    {'old':prev,'new':a['traits']})
        self.store.save(self.state)

    def _reflect(self,aid,minute,epoch):
        with self.lock:a=copy.deepcopy(self.state['agents'][aid])
        memories=self._memories(aid,'expériences politiques',minute)
        a['graph_context']=self.graph_memory.context(self.state['run_id'],aid,
             'expériences politiques conatus et croyances',minute,a.get('salience'))
        reflection,model,error,latency=self.cognition.reflect(a,memories)
        if epoch!=self.epoch:return
        self.store.memory(aid,minute,'reflexion_approfondie',reflection,.84,'introspection')
        self.store.log_model(minute,aid,'reflection',model,latency,error)
        with self.lock:
            if epoch==self.epoch:self.state['agents'][aid]['thought']=reflection[:180]

    def give_information(self,aid,text,mode='information',scope='individual'):
        text=' '.join(str(text).split())[:300]
        if len(text)<5:raise ValueError('Information trop courte')
        if mode not in ('information','belief'):raise ValueError('Mode inconnu')
        if scope not in ('individual','public'):raise ValueError('Portée inconnue')
        with self.lock:
            if scope=='individual' and aid not in self.state['agents']:raise ValueError('Personnage inconnu')
            minute=self.state['minute']
            targets=list(self.state['agents']) if scope=='public' else [aid]
            for target in targets:
                a=self.state['agents'][target]
                base=.70 if mode=='information' else .42
                conf=limit(base+.27*a['credulity']-.19*a['reasoning']*(1-a['credulity']),.10,.95)
                src='annonce publique' if scope=='public' else 'observateur'
                self.store.believe(target,text,conf,src,minute)
                self.store.memory(target,minute,'suggestion' if mode=='belief' else 'information',
                    'On me suggère : '+text if mode=='belief' else 'On m’annonce : '+text,.82,src)
                a['thought']='Une nouvelle information modifie mon interprétation de la situation.'
                arousal(a,category(text),.28)
                a['political_bias']=limit(a['political_bias']+(.01 if mode=='belief' else .006),-1,1)
            self.store.event(minute,'injection',aid if scope=='individual' else None,None,
                f'{len(targets)} destinataire(s) reçoivent une {"croyance suggérée" if mode=="belief" else "information"}.',
                {'scope':scope,'mode':mode,'message':text})
            self.store.save(self.state)
            for target in targets:
                self._schedule_judgment(target,'information-recue',minute,force=True)
        return {'ok':True,'recipients':len(targets)}

    def reset(self):
        with self.lock:
            if self.pending or not self.tasks.empty():raise ValueError('Attendre la fin des conversations')
            self.epoch+=1;self.store.reset();self.state=new_world(self.cfg['seed'])
            self.state['run_id']=uuid.uuid4().hex[:12];self.store.set_run(self.state['run_id'])
            for aid,secret in SECRETS.items():
                self.store.believe(aid,secret,.85,'observation privée',self.state['minute'])
            for aid in self.state['agents']:
                self.store.believe(aid,ANNOUNCEMENT,.95,'annonce publique',self.state['minute'])
            self.judgment_pending.clear()
            self._bootstrap_graph();self.store.save(self.state)

    def public(self):
        with self.lock:
            s=copy.deepcopy(self.state)
            s['status']={'brain':self.cognition.name,'brain_note':self.cognition.reason,
                'jev_enabled':self.cfg['jev_enabled'],'jev_key_set':bool(self.jev.key),
                'jev_budget':self.store.budget(self.cfg),'pending_jobs':self.tasks.qsize()+len(self.pending)+self.judgment_tasks.qsize()+len(self.judgment_pending),
                'tick_seconds':self.cfg['tick_seconds'],'graph':self.graph.describe()}
            s['events']=self.store.all('SELECT * FROM events ORDER BY id DESC LIMIT 65')
            s['dialogues']=self.store.all('SELECT * FROM dialogues ORDER BY id DESC LIMIT 45')
            s['individual']={aid:{'memories':self.store.memories(aid,18),
                  'beliefs':self.store.beliefs(aid,18),
                  'belief_history':self.store.belief_history(aid,18)} for aid in s['agents']}
            return s

    def insight(self,aid):
        """Graphe de mémoire et pistes de preuve consultables par le chercheur."""
        with self.lock:
            if aid not in self.state['agents']:raise ValueError('Agent inconnu')
            a=copy.deepcopy(self.state['agents'][aid]);minute=self.state['minute']
            r=self.state['run_id']
            related=copy.deepcopy(self.state['relations'][aid])
        context=self.graph_memory.context(r,aid,
            'religion preuves election maire faim survie soupçon',minute,a.get('salience'))
        context['agent']=aid
        context['relations']=[{'agent':k,'confiance':v['trust'],'tension':v['tension']}
             for k,v in sorted(related.items(),key=lambda x:-x[1]['familiarity'])[:8]]
        return context

    def influence_network(self):
        with self.lock:r=self.state['run_id']
        return self.graph_memory.observer_influences(r)

    def network(self):
        with self.lock:
            agents=self.state['agents'];rel=self.state['relations']
            nodes=[{'id':a['id'],'label':a['name'],'role':a['role'],'wealth':a['capital'],
                    'religiosity':a['religiosity']} for a in agents.values()]
            edges=[{'source':aid,'target':bid,'trust':r['trust'],'tension':r['tension']}
                   for aid,others in rel.items() for bid,r in others.items()
                   if r['trust']>=.57 or r['tension']>=.3]
            return {'run_id':self.state['run_id'],'nodes':nodes,'edges':edges,
                    'graph_db':self.graph.describe(),
                    'ballots':self.store.ballots()[:120],
                    'assemblies':self.store.assemblies()[:150]}

    def export(self):
        with self.lock:
            return {'snapshot':copy.deepcopy(self.state),
              'memories':{aid:self.store.memories(aid,100000) for aid in self.state['agents']},
              'beliefs':{aid:self.store.beliefs(aid,100000) for aid in self.state['agents']},
              'events':self.store.all('SELECT * FROM events ORDER BY id'),
              'dialogues':self.store.all('SELECT * FROM dialogues ORDER BY id'),
              'ballots':self.store.ballots(),'assemblies':self.store.assemblies(),
              'belief_history':self.store.all('SELECT * FROM belief_history ORDER BY id'),
              'model_log':self.store.all('SELECT * FROM model_log ORDER BY id'),
              'cognitive_trace':self.store.all('SELECT * FROM cognitive_trace ORDER BY id'),
              'jev_responses':self.store.all('SELECT id,minute,status,amount,tokens,response,error FROM jev_ledger ORDER BY id'),
              'graph':self.network(),'jev_budget':self.store.budget(self.cfg),
              'excluded':'API keys, HTTP Jev prompts, SurrealDB password'}
