"""Jev 1.14 : jugements récurrents fondés sur l'histoire subjective de chaque agent.

La logique finale reste explicite en Python; TypeSafe n'agit pas directement sur le monde.
Une seule destination internet possible, sans redirection ni retry automatique.
"""
from __future__ import annotations
import json
import ssl
import urllib.error
import urllib.request
from .settings import read_key
from .mind import ACTIONS, EMOTIONS, PRIORITIES

URL='https://api.typesafe.ai/v1/systemone'

def secure_tls_context():
 """Valide TLS avec les certificats macOS (ou un bundle CA connu). Jamais de mode insecure."""
 try:
  import truststore
  return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
 except ImportError:
  try:
   import certifi
  except ImportError:
   return ssl.create_default_context()
  return ssl.create_default_context(cafile=certifi.where())

SOCIAL_QUESTIONS={
 'tone':{'type':'choice','instructions':'How would the listener interpret this utterance, considering the listener’s private history?',
  'criteria':{'kind':'Warm and supportive toward the listener.',
              'ambiguous':'The intent is mixed or unclear.',
              'hurtful':'Accusing, humiliating, rejecting, or hurtful.',
              'practical':'An ordinary factual exchange.'}},
 'threat':{'type':'noul','instructions':'Would the listener perceive a threat to personal security or trust from the utterance?'},
 'reconcile':{'type':'noul','instructions':'Does this utterance offer the listener credible reasons to increase trust in this speaker?'},
 'upset':{'type':'score','instructions':'How upsetting is the utterance for this specific listener?',
  'criteria':['No distress.','Mild discomfort.','Disappointment or defensiveness.','Strong distress.']},
 'claim_supported':{'type':'noul','instructions':'Does the utterance contain first-hand evidence supporting the subject mentioned, rather than mere repetition of a rumor?'},
}

APPRAISAL_QUESTIONS={
 'priority':{'type':'choice',
  'instructions':'Given this person’s present needs, worldview, social ties and memories, which single next activity is psychologically most compelling? Do not ignore immediate hunger or fatigue.',
  'criteria':{'seek_food':'Find or obtain food and protect survival.',
   'rest':'Withdraw to rest and recover energy.', 'work':'Work for income and supplies.',
   'socialise':'Meet, negotiate, or ask somebody for help.',
   'pray':'Attend church, pray, or seek a preacher.',
   'study':'Investigate evidence, read, or consult a scholar.',
   'campaign':'Discuss candidates, political influence, and tomorrow’s vote.',
   'observe':'Observe quietly, reflecting before taking action.'}},
 'emotion':{'type':'choice','instructions':'Which affect is most salient for the person now, as a subjective experience?',
  'criteria':{'peur':'Fear or apprehension.', 'colere':'Anger or resentment.',
   'compassion':'Compassion and concern for others.', 'curiosite':'Curiosity or doubt.',
   'joie':'Joy or optimism.', 'calme':'Calm or indifference.'}},
 'political_priority':{'type':'choice','instructions':'Which political value currently most strongly guides the person, considering remembered experiences?',
  'criteria':{'solidarite':'Redistribution to people lacking basic necessities.',
   'ordre':'Security, rules and institutional stability.', 'commerce':'Trade, entrepreneurship and savings.',
   'liberte':'Freedom of thought and autonomy.', 'tradition':'Religious tradition and clergy authority.',
   'preuves':'Public evidence, education and fair inquiry.'}},
 'evidence':{'type':'score','instructions':'How does the person’s currently available evidence affect confidence in the singled-out belief? Treat gossip and repetition as weak evidence.',
  'criteria':['Direct evidence substantially contradicts the belief.',
   'Some reliable evidence counts against the belief.',
   'Insufficient or conflicting evidence to change confidence.',
   'Some reliable evidence supports the belief.',
   'Direct evidence substantially supports the belief.']},
 'direct_observation':{'type':'noul','instructions':'Does the person personally possess direct, independent observations relevant to assessing the singled-out belief?'},
 'social_risk':{'type':'noul','instructions':'Considering the memories and interpersonal relationships, does the person expect social rejection if they express their beliefs openly?'},
 'salient_topic':{'type':'choice','instructions':'Which theme is most present in this person’s attention given their recent lived experiences?',
  'criteria':{'foi':'Church, sermons and religious authority.',
   'sorcellerie':'Accusations, witchcraft fears and scapegoating.',
   'politique':'Election, candidates and political influence.',
   'survie':'Food, shelter, health and direct survival needs.',
   'inegalites':'Wealth, poverty, taxes and allocation of municipal resources.',
   'relations':'Friendships, distrust, reputation and belonging.',
   'preuves':'Evidence, contradictions and testing claims.'}},
 'trust_in_community':{'type':'noul','instructions':'Does this person currently feel that the community can be trusted to protect their interests?'},
}

class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  raise urllib.error.HTTPError(req.full_url,code,'Redirection bloquée',headers,fp)

class Jev:
 def __init__(self,store,cfg):
  self.store=store;self.cfg=cfg;self.key=read_key()
  self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),
    urllib.request.HTTPSHandler(context=secure_tls_context()),NoRedirect())

 def _request(self,minute,state,questions):
  if not self.cfg['jev_enabled']:return None,'désactivé'
  if not self.key:return None,'clé absente'
  payload=json.dumps({'model':self.cfg['jev_model'],'state':state,'questions':questions},
                     ensure_ascii=False,separators=(',',':'),allow_nan=False)
  ident,reason=self.store.reserve_jev(minute,self.cfg,payload)
  if not ident:return None,reason
  request=urllib.request.Request(URL,data=payload.encode(),method='POST',headers={
    'Authorization':'Bearer '+self.key,'Content-Type':'application/json',
    'Accept':'application/json','User-Agent':'SmallvilleLocal/3.0'})
  try:
   with self.opener.open(request,timeout=15) as response:
    if (getattr(response,'url',None) or response.geturl())!=URL:raise RuntimeError('Destination TypeSafe inattendue')
    result=json.loads(response.read(160000))
   answers=result.get('answers')
   if not isinstance(answers,dict) or not all(k in answers for k in questions):
    raise ValueError('Réponse Jev incomplète')
   self.store.finish_jev(ident,data=result)
   return answers,None
  except urllib.error.HTTPError as e:
   # Ne pas exposer le corps serveur (potentiellement rempli de données privées).
   reason=f'HTTP {e.code} depuis TypeSafe (vérifier clé, modèle, question et quota)'
   self.store.finish_jev(ident,error=reason)
   return None, reason
  except Exception as e:
   detail=f'{type(e).__name__}: {str(e)[:170]}'
   self.store.finish_jev(ident,error=detail)
   if 'CERTIFICATE_VERIFY_FAILED' in detail:
    return None,'TLS: certificat non validé. Exécuter VerifierJev.command (truststore requis). '
   return None,detail

 def judge(self,minute,listener,speaker,message,relation,memories,beliefs,topic=None):
  """Évaluation de dialogue (1 appel, 5 jugements parallèles)."""
  state={'listener':{'name':listener['name'],'role':listener.get('role'),
    'biography':listener['bio'],'goal':listener.get('goal'),
    'traits':{k:round(v,2) for k,v in listener['traits'].items()},
    'worldview':listener.get('worldview',{}),'emotions':listener.get('emotions',{}),
    'salience':listener.get('salience',{}),
    'mood':listener['mood'],'stress':listener['stress'],'conatus':listener.get('conatus')},
   'speaker':speaker['name'],'subjective_relationship':relation,
   'listener_relevant_memories':[m['content'][:160] for m in memories[:5]],
   'listener_beliefs':[{'claim':b['proposition'][:160],'confidence':b['confidence']} for b in beliefs[:5]],
   'utterance':message[:330]}
  questions=dict(SOCIAL_QUESTIONS)
  if topic:
   state['proposition_a_communiquer']=str(topic)[:350]
   questions['claim_expressed']={'type':'noul','instructions':
       'Does the utterance explicitly convey the claim in `proposition_a_communiquer`? Mere thematic overlap is insufficient.'}
  return self._request(minute,state,questions)

 def appraise(self,minute,agent,memories,beliefs,relations,public_context,candidates):
  """Un seul appel Jev regroupe cognition, affects, valeur politique et examen de preuve."""
  top=beliefs[0] if beliefs else None
  state={
   'person':{'name':agent['name'],'role':agent['role'],'biography':agent['bio'],
      'lifelong_goal':agent['goal'],
      'traits':{k:round(v,2) for k,v in agent['traits'].items()},
      'worldview':{k:round(v,2) for k,v in agent.get('worldview',{}).items()},
      'emotions':{k:round(v,2) for k,v in agent.get('emotions',{}).items()},
      'salience':{k:round(v,2) for k,v in agent.get('salience',{}).items()},
      'religiosity':agent['religiosity'],'credulity':agent['credulity'],
      'reasoning_style':agent['reasoning'],'aggression':agent['aggression'],
      'fear':agent['stress'],'conatus':agent['conatus'],
      'hunger':agent['hunger'],'health':agent['health'],'energy':agent['energy'],
      'coins':agent['coins'],'food_rations':agent['provisions'],
      'political_priority':agent.get('political_priority')},
   'private_memories':[{'event':m['content'][:165],'importance':round(m['importance'],2)} for m in memories[:6]],
   'private_beliefs':[{'claim':b['proposition'][:165],'confidence':round(b['confidence'],2)} for b in beliefs[:5]],
   'belief_to_review':{'claim':top['proposition'][:250],'confidence':top['confidence']} if top else None,
   'subjective_social_ties':relations[:5],
   'public_situation':public_context,
  }
  questions=APPRAISAL_QUESTIONS.copy()
  if candidates:
   questions['candidate']={'type':'choice',
    'instructions':'For tomorrow’s election, which candidate would this person most likely support given only their memories, beliefs, and public candidate descriptions?',
    'criteria':{c['id']:f"{c['name']} : {c['role']}; {c['goal'][:90]}" for c in candidates}}
  return self._request(minute,state,questions)


def decide(answers,listener,relation):
 """Réactions bornées, dérivées des distributions et non de règles secrètes."""
 if not answers:
  if relation.get('trust',.5)<.35 and listener['traits']['neuroticism']>.5:
   return {'stance':'guarded','trust_delta':-.008,'mood_delta':-.025,'from':'rules'}
  return {'stance':'warm' if relation.get('affinity',.5)>.54 else 'curious',
          'trust_delta':.006,'mood_delta':.012,'from':'rules'}
 def number(key,field,default):
  try:return float(answers[key][field])
  except (KeyError,ValueError,TypeError):return default
 tone=answers.get('tone',{}).get('choice','ambiguous')
 if number('threat','noul',.5)>=.72 and number('upset','score',1.5)>=1.7:
  return {'stance':'guarded','trust_delta':-.05,'mood_delta':-.09,'from':'jev'}
 if number('reconcile','noul',.5)>=.7 and tone=='kind':
  return {'stance':'warm','trust_delta':.043,'mood_delta':.07,'from':'jev'}
 if tone=='hurtful':return {'stance':'guarded','trust_delta':-.035,'mood_delta':-.05,'from':'jev'}
 return {'stance':'curious','trust_delta':.005,'mood_delta':.007,'from':'jev'}
