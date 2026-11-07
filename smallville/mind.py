"""Cognition subjective des agents : monde perçu, valence émotionnelle et saillance.

Ce sont des variables de simulation, non des mesures cliniques. Les traits lents
évoluent moins vite que les émotions; aucune pensée n'accède à l'état privé d'autrui.
"""
from __future__ import annotations
import math

TOPICS = ('foi', 'sorcellerie', 'politique', 'survie', 'inegalites', 'relations', 'preuves')
ACTIONS = ('seek_food', 'rest', 'work', 'socialise', 'pray', 'study', 'campaign', 'observe')
PRIORITIES = ('solidarite', 'ordre', 'commerce', 'liberte', 'tradition', 'preuves')
EMOTIONS = ('peur', 'colere', 'compassion', 'curiosite', 'joie', 'calme')


def clamp(x, lo=0.0, hi=1.0):
    return round(max(lo, min(hi, float(x))), 4)


def initial_mind(a):
    """Mêmes domaines pour tous, mais valeurs individuelles issues de la biographie."""
    religiosity = a['religiosity']
    generosity = a['generosity']
    reasoning = a['reasoning']
    suspicion = a['suspicion']
    return dict(
        worldview={
            'religious_authority':clamp(religiosity * (.50 + .42 * a['credulity'])),
            'empirical_evidence':clamp(reasoning * (1 - .30 * a['credulity'])),
            'collective_solidarity':clamp(generosity),
            'institutional_order':clamp(.40 * religiosity + .50 * a['traits']['conscientiousness']),
            'tolerance_of_dissent':clamp(a['tolerance']),
            'perceived_witchcraft_risk':clamp(.15 + .53 * suspicion * religiosity),
            'political_equality':clamp(.25 + .60 * generosity - .12 * a['ambition']),
        },
        emotions={'fear':clamp(.24 + .38 * suspicion), 'anger':clamp(.12 + .35 * a['aggression']),
                  'compassion':clamp(generosity), 'curiosity':clamp(reasoning),
                  'shame':.12, 'joy':.35},
        salience={'foi':clamp(.20 + .57 * religiosity),
                  'sorcellerie':clamp(.12 + .51 * suspicion),
                  'politique':clamp(.55 + .25 * a['ambition']),
                  'survie':clamp(.30 + .45 * a['hunger']),
                  'inegalites':clamp(.26 + .40 * generosity),
                  'relations':clamp(.36 + .36 * a['traits']['extraversion']),
                  'preuves':clamp(.20 + .60 * reasoning)},
        intention='observe',political_priority='solidarite' if generosity>.6 else 'tradition',
        candidate_preference=None,last_jev_minute=-99999,last_jev_attempt=-99999,
        expression_inhibition=clamp(.20+.38*a['suspicion']),community_trust=clamp(.35+.35*a['tolerance']),
        decisions=0,revision_count=0,mental_trace='',pending_evidence=None)


def ensure_mind(a):
    """Migration additive de sauvegardes anciennes sans altérer les valeurs acquises."""
    defaults=initial_mind(a)
    for k, v in defaults.items():
        if k not in a:
            a[k]=v
        elif isinstance(v,dict) and isinstance(a[k],dict):
            for sub, val in v.items():a[k].setdefault(sub,val)
    return a


def category(text):
    lower=(text or '').lower()
    if any(w in lower for w in ('sorc','hérés','démon','maléd','accus')):return 'sorcellerie'
    if any(w in lower for w in ('églis','prêtr','dieu','foi','relig','prière')):return 'foi'
    if any(w in lower for w in ('maire','élect','vote','scrutin','conseil','campagne')):return 'politique'
    if any(w in lower for w in ('pain','faim','ration','grain','malad','soign','mour','viv')):return 'survie'
    if any(w in lower for w in ('riche','pauvre','écu','impôt','revenu','budget')):return 'inegalites'
    if any(w in lower for w in ('preuve','témoign','observation','vérif','contradic')):return 'preuves'
    return 'relations'


def arousal(a,topic,intensity=.12):
    ensure_mind(a)
    a['salience'][topic]=clamp(a['salience'].get(topic,.4)+intensity)
    for k in a['salience']:
        if k!=topic:a['salience'][k]=clamp(.999*a['salience'][k])


def emotion_decay(a):
    ensure_mind(a)
    baselines={'fear':.25,'anger':.19,'compassion':a['generosity'],
               'curiosity':a['reasoning'],'shame':.12,'joy':.35}
    for k,value in a['emotions'].items():
        a['emotions'][k]=clamp(value*.986+baselines[k]*.014)
    a['emotions']['fear']=clamp(a['emotions']['fear']+.006*a['stress'])
    a['salience']['survie']=clamp(.985*a['salience']['survie']+.015*a['hunger'])


def belief_revision(old, evidence_score, evidence_is_direct, credulity, reasoning):
    """Règle conservatrice : le jugement Jev est une indication, pas une vérité.
    evidence_score de 0 (contradiction forte) à 4 (corroboration forte).
    Sans observation directe, seule une révision faible est admise.
    """
    direction=max(-1,min(1,(float(evidence_score)-2)/2))
    strength=.12 if evidence_is_direct else .032
    strength*=.50 + .45*reasoning + .12*credulity
    return clamp(float(old)+direction*strength, .03, .97)


def apply_appraisal(a,answers, belief=None, prior_confidence=None):
    """Transitions bornées, auditées : choix, croyances, affects et monde perçu."""
    ensure_mind(a)
    get=lambda key,field,default: (answers.get(key) or {}).get(field,default)
    choice=get('priority','choice','observe')
    if choice not in ACTIONS:choice='observe'
    emotion=get('emotion','choice','calme')
    if emotion not in EMOTIONS:emotion='calme'
    priority=get('political_priority','choice',a['political_priority'])
    if priority not in PRIORITIES:priority=a['political_priority']
    candidate=get('candidate','choice',None)
    if candidate not in ('emma','felix','basile','chloe','gideon','lucien','margot'):candidate=None
    ename={'peur':'fear','colere':'anger','compassion':'compassion','curiosite':'curiosity','joie':'joy','calme':'joy'}[emotion]
    before={'worldview':a['worldview'].copy(),'emotions':a['emotions'].copy(),
            'salience':a['salience'].copy(),'intention':a['intention']}
    a['emotions'][ename]=clamp(a['emotions'][ename]+.10)
    if emotion=='peur':a['stress']=clamp(a['stress']+.025)
    if emotion=='compassion':a['worldview']['collective_solidarity']=clamp(a['worldview']['collective_solidarity']+.009)
    if emotion=='curiosite':a['worldview']['empirical_evidence']=clamp(a['worldview']['empirical_evidence']+.008)
    if priority=='solidarite':a['worldview']['political_equality']=clamp(a['worldview']['political_equality']+.009)
    if priority=='ordre':a['worldview']['institutional_order']=clamp(a['worldview']['institutional_order']+.009)
    if priority=='preuves':a['worldview']['empirical_evidence']=clamp(a['worldview']['empirical_evidence']+.009)
    if priority=='tradition':a['worldview']['religious_authority']=clamp(a['worldview']['religious_authority']+.007)
    topic=get('salient_topic','choice',None)
    if topic in TOPICS:arousal(a,topic,.11)
    risk=get('social_risk','noul',None)
    communal=get('trust_in_community','noul',None)
    if risk is not None:
        a['expression_inhibition']=clamp(.90*a['expression_inhibition']+.10*float(risk))
    if communal is not None:
        a['community_trust']=clamp(.94*a['community_trust']+.06*float(communal))
    # Les affects et le climat social s'influencent réciproquement.
    a['emotions']['fear']=clamp(a['emotions']['fear']+.028*(a['expression_inhibition']-.35))
    a['worldview']['tolerance_of_dissent']=clamp(
        .997*a['worldview']['tolerance_of_dissent']+.003*(1-a['expression_inhibition']))
    a['political_priority']=priority
    a['candidate_preference']=candidate or a.get('candidate_preference')
    a['intention']=choice
    a['decisions']+=1
    a['mental_trace']=(f'Priorité : {choice} ; affect : {emotion} ; politique : {priority}; '
                       f'sujet saillant : {topic or "non déterminé"}; confiance communautaire : {a["community_trust"]:.2f}')
    revised=None
    if belief is not None and prior_confidence is not None:
        score=get('evidence','score',2)
        direct=get('direct_observation','noul',.5)
        try:
            new=belief_revision(prior_confidence,score,float(direct)>.70,a['credulity'],a['reasoning'])
            revised=dict(before=prior_confidence,after=new,score=score,direct=direct,
                         proposition=belief['proposition'])
            if abs(new-prior_confidence)>.001:a['revision_count']+=1
            arousal(a,category(belief['proposition']),.055)
        except (ValueError,TypeError):pass
    return {'before':before,'after':{'worldview':a['worldview'].copy(),'emotions':a['emotions'].copy(),
            'salience':a['salience'].copy(),'intention':a['intention']},
            'intention':choice,'emotion':emotion,'political_priority':priority,
            'candidate':candidate,'revision':revised}
