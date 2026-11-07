"""Exécutif BDI : intentions stables, sous-objectifs, agenda, projets contrefactuels.

L'agent conserve une mémoire prospective. Les projets et les actes sont séparés :
une intention déclarée n'est jamais comptabilisée comme une action réussie.
"""
from __future__ import annotations
import math

KINDS=('survival','investigate','alliance','campaign','faith','income','protest')
DESCRIPTIONS={
 'survival':'Garantir nourriture et sécurité pour les prochains jours',
 'investigate':'Vérifier une affirmation auprès de plusieurs sources',
 'alliance':'Gagner un allié fiable pour atteindre un but',
 'campaign':'Préparer une intervention au scrutin municipal',
 'faith':'Participer à la vie spirituelle de la communauté',
 'income':'Maintenir un revenu et des réserves',
 'protest':'Contester publiquement une décision jugée injuste',
}

def ensure(a):
    a.setdefault('alive',True)
    ex=a.setdefault('executive',{})
    ex.setdefault('project',None)
    ex.setdefault('history',[])
    ex.setdefault('agenda',[])
    ex.setdefault('future_scenarios',[])
    ex.setdefault('jev_project',None)
    ex.setdefault('commitment_strength',.68)
    ex.setdefault('tactic','sincere')
    ex.setdefault('norm_strategy','obey')
    ex.setdefault('last_revision',-99999)
    ex.setdefault('counterfactuals',[])
    return ex

def _project_steps(kind,a,world,minute,target=None):
    workplace=a.get('workplace','marche')
    recipe={
        'survival':[('visit','grenier',None),('check','marche',None)],
        'investigate':[('research','ecole',None),('consult','marche',target)],
        'alliance':[('approach','marche',target),('negotiate','place',target)],
        'campaign':[('prepare','ecole',None),('speak','place',None)],
        'faith':[('reflect','eglise',None),('attend','place',None)],
        'income':[('work',workplace,None),('trade','marche',None)],
        'protest':[('organize','taverne',target),('petition','mairie',None)]
    }
    from .seed import PLACES
    result=[]
    for index,(action,place,other) in enumerate(recipe[kind]):
        if place not in PLACES:place='place'
        result.append({'step':index,'action':action,'place':place,'target':other,
                       'due':minute+80+index*150,'status':'pending','attempts':0})
    return result

def _target(a,world):
    ties=world['relations'].get(a['id'],{})
    candidates=[(bid,rel) for bid,rel in ties.items()
                if world['agents'].get(bid,{}).get('alive',True) and bid!=a['id']]
    if not candidates:return None
    candidates.sort(key=lambda item:(-item[1]['trust']-.3*item[1].get('familiarity',0),item[0]))
    return candidates[0][0]

def scores(a,world,minute):
    ex=ensure(a)
    values=a.get('worldview',{})
    election=world.get('politics',{})
    before_vote=election.get('phase')=='campaign'
    hunger=a['hunger'];risk=1-a['health'];energy=a['energy']
    result={
      'survival':.22+1.5*hunger+.9*risk+.3*(a.get('provisions',0)<2),
      'investigate':.15+.9*a['reasoning']+.3*values.get('empirical_evidence',.5),
      'alliance':.12+.6*a['loneliness']+.35*a['ambition']+.2*a['social'],
      'campaign':.08+.95*a['ambition']*(1 if before_vote else .25)+.28*a['political_bias'],
      'faith':.12+.7*a['religiosity']+.15*a['stress'],
      'income':.15+.7*(1-min(a['coins']/100,1))+.4*(1-energy),
      'protest':.03+.4*a['tolerance']+.4*a['stress']+.2*(1-a['community_trust']),
    }
    if a['energy']<.2:result['survival']+=.4
    if ex.get('jev_project') in KINDS and a.get('last_jev_minute',-99999)>=minute-240:
        result[ex['jev_project']]+=1.25
    project=ex['project']
    if project and project.get('status')=='active':
        result[project['kind']]+=max(.05,ex['commitment_strength'])*1.2
    return result

def _choose(a,world,rng,minute):
    ranking=scores(a,world,minute)
    if a['hunger']>.80 or a['health']<.27:return 'survival'
    order=sorted(ranking,key=lambda k:(-ranking[k],k))[:3]
    temp=max(.08,.4*(1-a['reasoning'])+.10)
    weights=[math.exp((ranking[k]-max(ranking.values()))/temp) for k in order]
    return rng.choices(order,weights=weights)[0]

def create(a,world,rng,minute,kind=None):
    ex=ensure(a)
    kind=kind if kind in KINDS else _choose(a,world,rng,minute)
    target=_target(a,world) if kind in ('alliance','investigate','protest') else None
    steps=_project_steps(kind,a,world,minute,target)
    plan={'id':f"{a['id']}_{minute}_{kind}",'kind':kind,
          'objective':DESCRIPTIONS[kind],'target':target,'created':minute,
          'deadline':minute+720,'step_index':0,'steps':steps,'status':'active',
          'reason':f"Conatus={a['conatus']:.2f} ; priorités={kind}",
          'origin':'Jev' if ex.get('jev_project')==kind and a.get('decisions',0)>0 else 'politique locale'}
    ex['project']=plan
    ex['agenda']=[{'minute':x['due'],'place':x['place'],'action':x['action'],
                   'target':x['target'],'status':'planned'} for x in steps]
    ex['future_scenarios']=[
      {'at':minute,'kind':'hypothesis','if':f"Je réussis {kind}",
       'then':f"J'améliore mes chances de {a.get('goal','progresser')[:85]}"},
      {'at':minute,'kind':'hypothesis','if':f"Je ne parviens pas à {kind}",
       'then':'Je devrai chercher une autre voie ou réviser mon but.'},
    ]
    return plan

def current(a,world,rng,minute):
    ex=ensure(a)
    project=ex['project']
    if project is None or project['status']!='active':
        project=create(a,world,rng,minute)
    if a['hunger']>.9 and project['kind']!='survival':
        abandon(a,minute,'urgence alimentaire')
        project=create(a,world,rng,minute,'survival')
    if minute>project['deadline']:
        abandon(a,minute,'échéance dépassée')
        project=create(a,world,rng,minute)
    index=project['step_index']
    if index>=len(project['steps']):
        project['status']='done'
        ex['history'].append(project);ex['history']=ex['history'][-12:]
        ex['project']=None
        project=create(a,world,rng,minute)
    return project,project['steps'][project['step_index']]

def finish_step(a,minute,why='activité accomplie'):
    ex=ensure(a);project=ex['project']
    if not project or project['status']!='active':return None
    i=project['step_index']
    if i>=len(project['steps']):return None
    step=project['steps'][i];step['status']='done';step['completed']=minute
    step['outcome']=why
    project['step_index']+=1
    for item in ex['agenda']:
        if item['action']==step['action'] and item['status']=='planned':
            item['status']='done';break
    if project['step_index']>=len(project['steps']):
        project['status']='done';project['completed']=minute
        ex['history'].append(project);ex['history']=ex['history'][-12:]
        ex['project']=None
    return {'project':project['id'],'kind':project['kind'],
            'step':step['action'],'outcome':why,'status':project['status']}

def contact(a,other_id,minute):
    ex=ensure(a);project=ex['project']
    if not project or project.get('status')!='active':return None
    if project.get('target')!=other_id:return None
    i=project['step_index']
    if i<len(project['steps']) and project['steps'][i]['action'] in ('approach','negotiate','consult','organize'):
        return finish_step(a,minute,f'rencontre effectivement observée avec {other_id}')
    return None

def abandon(a,minute,why):
    ex=ensure(a);project=ex['project']
    if not project:return None
    project['status']='abandoned';project['closed']=minute;project['reason_closed']=why
    ex['history'].append(project);ex['history']=ex['history'][-12:]
    ex['project']=None;ex['last_revision']=minute
    return project

def navigate(a,world,rng,minute):
    from .seed import PLACES
    ex=ensure(a)
    if not a.get('alive',True):return list(a['home']),'deceased',''
    if a['energy']<.20 or minute%1440<330:
        return a['home'][:],'resting','Je récupère des forces avant de poursuivre mes engagements.'
    project,step=current(a,world,rng,minute)
    place=step['place']; destination=list(PLACES.get(place,PLACES['place']))
    activity={
      'visit':'seeking_food','check':'shopping','research':'investigating',
      'consult':'investigating','approach':'socialising','negotiate':'negotiating',
      'prepare':'planning','speak':'campaigning','reflect':'praying',
      'attend':'socialising','work':'working','trade':'trading',
      'organize':'organizing','petition':'protesting'
    }.get(step['action'],'observing')
    thought=f"Projet : {project['objective']}. Étape : {step['action']} à {place}."
    return destination,activity,thought

def progress_on_site(a,world,minute):
    ex=ensure(a);project=ex['project']
    if not project or project['status']!='active':return None
    i=project['step_index']
    if i>=len(project['steps']):return None
    step=project['steps'][i]
    from .seed import PLACES
    if [a['x'],a['y']]!=list(PLACES.get(step['place'],(-999,-999))):return None
    if step['action'] in ('approach','negotiate','consult','organize'):
        if minute>step['due']+70:
            step['attempts']+=1;step['due']=minute+100
            for slot in ex['agenda']:
                if slot['action']==step['action'] and slot['status']=='planned':slot['minute']=step['due']
            if step['attempts']>=3:
                abandon(a,minute,'rencontre impossible après plusieurs tentatives')
                return {'status':'abandoned','reason':'rendez-vous manqué'}
        return None
    if minute-a.get('last_plan',minute)<12:return None
    return finish_step(a,minute)
