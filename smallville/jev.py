"""Strictement une destination réseau publique, aucun retry, consentement explicite."""
import json,ssl,urllib.request,urllib.error
from .settings import read_key
URL='https://api.typesafe.ai/v1/systemone'
# Les questions ne sont pas des commandes d'action. Le modèle fournit des indices.
QUESTIONS={
 'tone':{'type':'choice','instructions':'How does the listener interpret the social tone of the last utterance?',
 'criteria':{'kind':'Warm and supportive toward the listener.',
             'ambiguous':'The intent is unclear or mixed.',
             'hurtful':'Critical, dismissive, blaming or hurtful.',
             'practical':'Ordinary factual exchange with little emotional content.'}},
 'threat':{'type':'noul','instructions':'Would the listener likely perceive the utterance as personal rejection or a threat to trust?'},
 'reconcile':{'type':'noul','instructions':'Does the utterance provide credible reason for the listener to improve trust in the speaker?'},
 'upset':{'type':'score','instructions':'How upsetting is the utterance for this specific listener?',
 'criteria':['The listener is not upset.','The listener is slightly uncomfortable.',
             'The listener is disappointed and defensive.','The listener is strongly hurt.']}}

class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  raise urllib.error.HTTPError(req.full_url,code,'Redirection bloquée',headers,fp)

class Jev:
 def __init__(self,store,cfg):
  self.store=store;self.cfg=cfg;self.key=read_key()
  self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),
   urllib.request.HTTPSHandler(context=ssl.create_default_context()),NoRedirect())
 def judge(self,minute,listener,speaker,message,relation,memories,beliefs):
  if not self.cfg['jev_enabled']:return None,'désactivé'
  if not self.key:return None,'clé absente'
  state={
   'listener':{'name':listener['name'],'bio':listener['bio'],
    'personality':{k:round(v,2) for k,v in listener['traits'].items()},
    'mood':round(listener['mood'],2),'stress':round(listener['stress'],2)},
   'speaker':speaker['name'],'subjective_relationship':relation,
   'listener_relevant_memories':[m['content'][:180] for m in memories[:3]],
   'listener_beliefs':[b['proposition'][:180] for b in beliefs[:3]],
   'utterance':message[:300]}
  payload=json.dumps({'model':self.cfg['jev_model'],'state':state,'questions':QUESTIONS},
   ensure_ascii=False,separators=(',',':'))
  ident,reason=self.store.reserve_jev(minute,self.cfg,payload)
  if not ident:return None,reason
  req=urllib.request.Request(URL,data=payload.encode(),method='POST',headers={
    'Authorization':'Bearer '+self.key,'Content-Type':'application/json',
    'Accept':'application/json','User-Agent':'SmallvilleLocal/1.0'})
  try:
   with self.opener.open(req,timeout=14) as r:
    if r.url!=URL:raise RuntimeError('Destination inattendue')
    result=json.loads(r.read(160000))
   a=result.get('answers')
   if not isinstance(a,dict) or not all(k in a for k in QUESTIONS):
    raise ValueError('Réponse Jev incomplète')
   self.store.finish_jev(ident,data=result)
   return a,None
  except Exception as e:
   self.store.finish_jev(ident,error=f'{type(e).__name__}: {str(e)[:120]}')
   return None,f'Jev indisponible : {type(e).__name__} ; aucun retry'

def decide(answers,listener,relation):
 """Règles d'action transparentes, Jev utilisé seulement pour les appréciations."""
 if not answers:
  if relation['trust']<.35 and listener['traits']['neuroticism']>.5:
   return {'stance':'guarded','trust_delta':-.008,'mood_delta':-.025,'from':'rules'}
  return {'stance':'warm' if relation['affinity']>.54 else 'curious',
          'trust_delta':.006,'mood_delta':.012,'from':'rules'}
 def number(id,field,default):
  try:return float(answers[id][field])
  except (KeyError,TypeError,ValueError):return default
 tone=answers.get('tone',{}).get('choice','ambiguous')
 if number('threat','noul',.5)>=.72 and number('upset','score',1.5)>=1.7:
  return {'stance':'guarded','trust_delta':-.05,'mood_delta':-.09,'from':'jev'}
 if number('reconcile','noul',.5)>=.7 and tone=='kind':
  return {'stance':'warm','trust_delta':.043,'mood_delta':.07,'from':'jev'}
 if tone=='hurtful':return {'stance':'guarded','trust_delta':-.035,'mood_delta':-.05,'from':'jev'}
 return {'stance':'curious','trust_delta':.005,'mood_delta':.007,'from':'jev'}
