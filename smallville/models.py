"""Chaque LLM dialogue LOCAL. Apple FM (macOS 26) sinon MLX local ou dialogue scripté."""
import asyncio,json,platform,re,time,urllib.request

class Scripted:
 name='scripted'
 def speak(self,a,b,ctx,heard=''):
  subject=ctx.get('topic','')
  if heard:
   if ctx.get('stance')=='guarded':return 'Je ne suis pas sûr de te croire. Il faut qu’on en discute.'
   if ctx.get('stance')=='warm':return 'Merci de me l’avoir dit. Ça compte pour moi.'
   return 'C’est intéressant. Je vais y réfléchir avant de décider.'
  if subject:return f"Bonjour {b['name']}. Je voulais te parler de quelque chose : {subject}"
  return f"Bonjour {b['name']} ! Comment vas-tu aujourd’hui ?"
 def reflect(self,a,mem):
  return 'Je retiens de ma journée : '+(' ; '.join(x['content'][:75] for x in mem[:3]) or 'une journée calme.')

class Apple:
 name='apple'
 def __init__(self):
  self.fm=None;self.reason=''
  try:
   if platform.system()!='Darwin':raise RuntimeError('Apple Foundation Models exige macOS 26+')
   import apple_fm_sdk as fm
   ok,reason=fm.SystemLanguageModel().is_available()
   if not ok:raise RuntimeError(str(reason))
   self.fm=fm
  except Exception as e:self.reason=str(e)
 def query(self,system,prompt):
  async def inner():
   session=self.fm.LanguageModelSession(instructions=system)
   result=await session.respond(prompt)
   return str(getattr(result,'content',result))
  return asyncio.run(inner())
 def speak(self,a,b,ctx,heard=''):
  system=(f"Tu es {a['name']}, personnage d'une société fictive. {a['bio']} "
   f"But: {a['goal']}. Tu ne connais que TES propres souvenirs, croyances et ce qui t'a été dit. Des croyances sont infondées, d'autres contredites, ne les affirme pas comme des certitudes si elles sont fragiles. Le village est pieux, soupçonneux, politique ; le meurtre est illégal et exceptionnel. "
   "Une seule réplique en français naturel, 1 ou 2 phrases, 40 mots maximum. "
   "Aucune narration, aucun préfixe de personnage, ne devine pas les secrets des autres. "
   "Respecte les rendez-vous et les engagements du personnage ; ne prétends pas avoir réalisé une action encore projetée.")
  prompt=json.dumps({'destinataire':b['name'],'mes_emotions':ctx['affect'],
   'mes_traits':ctx['traits'],'mon_opinion_de_l_autre':ctx['relation'],
   'ma_vision_du_monde':ctx.get('worldview'),
   'mes_emotions_dynamiques':ctx.get('emotions'),
   'mon_reseau_de_saillance':ctx.get('salience'),
   'mon_intention_actuelle':ctx.get('intention'),
   'mon_niveau_de_confiance_communautaire':ctx.get('community_trust'),
   'ma_crainte_de_mexprimer':ctx.get('expression_inhibition'),
   'experience_courante':ctx.get('present_experience'),
   'mes_jugements_recents':ctx.get('mental_trace'),
   'ma_priorite_politique':ctx.get('political_priority'),
   'heure_simulee':ctx.get('time'),
   'mon_projet_actuel':ctx.get('executive_project'),
   'mes_rendez_vous_prevus':ctx.get('prospective_agenda'),
   'mes_souvenirs':ctx['memories'],'mes_croyances':ctx['beliefs'],
   'sujet':ctx['topic'],'intention':ctx['stance'],'phrase_entendue':heard,
   'vie_materielle':ctx.get('resources'),'reseau_percu':ctx.get('graph_neighborhood'),
   'public':ctx.get('group',[])},ensure_ascii=False)
  return clean(self.query(system,prompt))
 def reflect(self,a,mem):
  return clean(self.query(f"Tu es {a['name']}. {a['bio']} Décris en deux phrases "
     "à la première personne ce que tu as appris, et comment cela influe sur ton conatus et tes choix. N'invente pas de faits.",
     json.dumps({'memoires':[m['content'] for m in mem[:8]],
       'conatus':a.get('conatus'),'but':a.get('goal'),'religiosite':a.get('religiosity'),
       'soupcon':a.get('suspicion'),'ressources':a.get('provisions'),
       'monde_percu':a.get('worldview'),'emotions':a.get('emotions'),
       'salience':a.get('salience'),'intention':a.get('intention'),
       'priorite_politique':a.get('political_priority'),
       'dernier_jugement':a.get('mental_trace'),
       'graphe_memoriel':str(a.get('graph_context') or '')[:1400]},ensure_ascii=False)),450)

class MLX:
 name='mlx_local'
 URL='http://127.0.0.1:8080/v1/chat/completions'
 def query(self,system,prompt):
  data=json.dumps({'model':'local-model','messages':[{'role':'system','content':system},
      {'role':'user','content':prompt}],'temperature':.75,'max_tokens':135}).encode()
  req=urllib.request.Request(self.URL,data=data,headers={'Content-Type':'application/json'})
  with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req,timeout=60) as r:
   obj=json.loads(r.read(120000))
  return clean(obj['choices'][0]['message']['content'])
 def speak(self,a,b,ctx,heard=''):
  return self.query(f"Tu es {a['name']}. {a['bio']} Réplique en français en deux phrases, pas de narration.",
      json.dumps({'autre':b['name'],'context':ctx,'heard':heard},ensure_ascii=False))
 def reflect(self,a,mem):
  return self.query(f"Tu es {a['name']}. Résume tes souvenirs en deux phrases.",
      json.dumps(mem[:8],ensure_ascii=False))

def clean(text,limit=290):
 text=re.sub(r'\s+',' ',str(text or '')).strip().strip('"“”')
 return (text[:limit].strip() or 'Il me faut un peu de temps pour y réfléchir.')

class LocalBrain:
 def __init__(self,cfg):
  self.script=Scripted();self.apple=None;self.reason=''
  mode=cfg['backend']
  if mode in ('auto','apple'):
   self.apple=Apple()
   if self.apple.fm:self.active=self.apple;self.reason='Modèle Apple sur appareil'
   else:self.active=self.script;self.reason='Apple indisponible : '+self.apple.reason
  elif mode=='mlx_local':self.active=MLX();self.reason='Serveur MLX sur 127.0.0.1:8080 (aucun cloud)'
  else:self.active=self.script;self.reason='Dialogues scriptés pour tester sans modèle'
 @property
 def name(self):return self.active.name
 def speak(self,*args,**kwargs):
  start=time.monotonic()
  try:return self.active.speak(*args,**kwargs),self.active.name,None,time.monotonic()-start
  except Exception as e:return self.script.speak(*args,**kwargs),'scripted-fallback',str(e),time.monotonic()-start
 def reflect(self,*args):
  start=time.monotonic()
  try:return self.active.reflect(*args),self.active.name,None,time.monotonic()-start
  except Exception as e:return self.script.reflect(*args),'scripted-fallback',str(e),time.monotonic()-start
