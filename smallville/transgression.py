"""Normes, mensonge et conflits simulés (abstraits, non graphiques).

Interdiction sociale et possibilité physique sont distinctes. Les actes graves
nécessitent un contexte exceptionnel; aucun détail de réalisation n'est simulé.
"""
from __future__ import annotations
import random
from .executive import ensure,abandon

def deception(a,belief,recipient,minute):
    """La tromperie n'existe que si le sujet sait qu'il contredit sa conviction."""
    ex=ensure(a)
    if ex['tactic']!='mislead' or not belief or float(belief.get('confidence',0))<.78:
        return None
    if a['stress']<.36 and a['ambition']<.72:return None
    claim=str(belief['proposition'])[:185]
    return {'utterance':f"Pour ma part, je soutiens que l'affirmation « {claim} » est fausse.",
            'internal_belief':claim,'reported_claim':f'Il est faux que {claim}',
            'motive':'protéger ses intérêts ou modifier une croyance',
            'recipient':recipient,'minute':minute}

def disobedience(a,minute,seed):
    """Acte de désobéissance civile distinct d'une accusation ou d'une menace."""
    ex=ensure(a)
    if not a.get('alive',True) or minute-ex.get('last_norm_event',-99999)<600:return None
    if ex['norm_strategy'] not in ('dissent','defy'):return None
    rng=random.Random(seed+minute*13+sum(ord(c) for c in a['id']))
    if rng.random()>.017*(.4+.6*a['ambition']):return None
    ex['last_norm_event']=minute
    return {'kind':'civil_disobedience','minute':minute,'agent':a['id'],
            'norm':'interdiction des rassemblements nocturnes / obligation de suivre les édits',
            'reason':'désaccord idéologique ou religieux',
            'reaction':'rappel à l’ordre communal'}

def confrontation(sim,minute,rng):
    """Très rares incidents non létaux, et homicide exceptionnel et sanctionné."""
    living=[a for a in sim.state['agents'].values()
            if a.get('alive',True) and a.get('detained_until',0)<=minute]
    for a in living:
        if a['stress']<.82 or a['aggression']<.85:continue
        ex=ensure(a)
        if ex['norm_strategy']!='intimidate':continue
        for b in living:
            if a['id']==b['id']:continue
            if abs(a['x']-b['x'])+abs(a['y']-b['y'])>1:continue
            relation=sim.state['relations'][a['id']][b['id']]
            if relation['tension']<.82 or relation['trust']>.22:continue
            if rng.random()>.0003:continue
            return apply_incident(sim,a,b,minute,rng)
    return None

def apply_incident(sim,a,b,minute,rng,allow_homicide=True):
    """Transition d'état; aucun détail de réalisation n'est simulé."""
    if not(a.get('alive',True) and b.get('alive',True)) or a['id']==b['id']:return None
    lethal=(allow_homicide and a['stress']>.95 and a['aggression']>.96 and
            sim.state['relations'][a['id']][b['id']]['tension']>.95 and
            rng.random()<.008)
    if lethal:
        b['alive']=False;b['health']=0;b['activity']='deceased';b['route']=[]
        abandon(b,minute,'décès')
        a['detained_until']=minute+2880
        event='homicide'
        details={'victim':b['id'],'suspect':a['id'],'legal':'meurtre interdit et poursuivi',
                 'graphic_details':False,'outcome':'victime décédée; suspect placé en détention'}
        sim.store.event(minute,event,a['id'],b['id'],
                        f"La mort de {b['name']} bouleverse Salem. {a['name']} est placé en détention.",details)
        for witness in sim.state['agents'].values():
            if not witness.get('alive',True):continue
            if abs(witness['x']-b['x'])+abs(witness['y']-b['y'])<=4:
                sim.store.memory(witness['id'],minute,'observation',
                    f"J'ai appris la mort de {b['name']} et l'arrestation de {a['name']}.",.95,'observation')
                witness['emotions']['fear']=min(1,witness['emotions']['fear']+.22)
    else:
        b['stress']=min(1,b['stress']+.13)
        b['security']=max(0,b['security']-.08)
        a['stress']=min(1,a['stress']+.09)
        event='intimidation'
        details={'victim':b['id'],'suspect':a['id'],'legal':'intimidation sanctionnable','graphic_details':False}
        sim.store.event(minute,event,a['id'],b['id'],
                         f"{a['name']} intimide {b['name']}; la communauté réagit.",details)
        a['detained_until']=minute+120
    for rid in (a['id'],b['id']):
        if rid!=a['id'] or b.get('alive',True):
            sim.store.memory(rid,minute,'conflit',
                f"Une confrontation s'est produite entre {a['name']} et {b['name']}.",.86,'événement personnel')
    return event
