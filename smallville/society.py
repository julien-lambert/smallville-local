"""Institutions et psychologie sociale de Salem-sur-Brume.

Élections transparentes et déterministes conditionnées par croyances privées.
Les sommes transférées préservent exactement la masse monétaire.
"""
import math
import random
from collections import Counter
from .seed import PLACES


def clamp(x,lo=0,hi=1): return max(lo,min(hi,float(x)))


def psyche(agent):
    """Conatus opérationnel : persévérer dans son existence sans héroïsation de la violence."""
    a=agent
    protective=.36*a['health']+.17*a['hope']+.15*a['security']+.16*a['energy']+.16*(1-a['hunger'])
    a['conatus']=round(clamp(protective,.06,1),4)
    if a['hunger']>.7 or a['health']<.38:
        a['thought']='Je dois préserver ma vie : chercher du pain et de l’aide.'
    elif a['stress']>.75:
        a['thought']='La peur m’envahit ; je dois me rapprocher de personnes fiables.'


def derive_religious_suspicion(a,beliefs):
    """Les accusations infondées sont des croyances, jamais une vérité du monde."""
    text=' '.join(x['proposition'].lower() for x in beliefs[:25])
    return clamp(a['suspicion']+.1*('sorcellerie' in text)+.06*('hérésie' in text)-.14*a['reasoning']*(1-a['credulity']))


def vote_candidate(a,agents,rel,candidates,beliefs,seed):
    rng=random.Random(seed)
    fear=derive_religious_suspicion(a,beliefs)
    scores=[]
    for cid in candidates:
        b=agents[cid];relationship=rel.get(cid,{'trust':1,'affinity':1,'tension':0})
        proximity=1-abs(a['religiosity']-b['religiosity'])
        stability=(b['reasoning']+b['generosity']+b['tolerance'])/3
        socioeconomic=1-abs(math.log1p(a['capital'])-math.log1p(b['capital']))/8
        score=(1.15*relationship['trust']+.45*relationship['affinity']+.8*proximity+
               .4*stability+.22*socioeconomic+.2*a['ambition']*b['ambition']+
               .2*fear*b['suspicion']-.3*a['tolerance']*b['aggression'])
        if cid==a['id']:score+=.48*a['ambition']
        # Un jugement Jev récent est un signal de préférence, non une obligation.
        if a.get('candidate_preference')==cid and a.get('last_jev_minute',-99999)>-1000:
            score+=.85
        focus=a.get('political_priority')
        if focus=='solidarite':score+=.25*b['generosity']
        if focus=='ordre':score+=.24*b['conscientiousness'] if 'conscientiousness' in b else .24*b['traits']['conscientiousness']
        if focus=='tradition':score+=.24*b['religiosity']
        if focus=='preuves':score+=.25*b['reasoning']
        if focus=='liberte':score+=.23*b['tolerance']
        if focus=='commerce':score+=.21*b['ambition']
        if cid=='emma' and a['generosity']>.75:score+=.12
        # Une information acquise par cet électeur influence ses préférences.
        if any(cid in x['proposition'].lower() and any(w in x['proposition'].lower() for w in ('fraude','ment','peur'))
               for x in beliefs):score-=.38*clamp(a['reasoning']+.3)
        scores.append((cid,score))
    weights=[math.exp(3*(v-max(y for _,y in scores))) for _,v in scores]
    chosen=rng.choices([x for x,_ in scores],weights=weights)[0]
    return chosen, dict((k,round(v,4)) for k,v in scores)


def ballot_weights(a,agents,rel,beliefs):
    """Proposition budgétaire personnelle; chaque vote a le même poids démocratique."""
    weights={}
    for bid,b in agents.items():
        r=rel.get(bid,{'trust':1.,'affinity':1.,'tension':0.})
        need=clamp(.5*b['hunger']+.25*(1-b['health'])+.25/(1+b['provisions']),.01,1)
        poverty=1/(1+b['capital']/45)
        solidarity=(.35+.7*a['generosity'])*(.52*need+.48*poverty)
        connection=.16*r['trust']+.1*r['affinity']
        cultural=.15*a['religiosity']*(1-abs(a['religiosity']-b['religiosity']))
        privilege=.11*(1-a['generosity'])*min(b['capital']/60,2)
        personal=.60*(1-a['generosity']) if a['id']==bid else 0
        if a.get('political_priority')=='solidarite':solidarity*=1.28
        if a.get('political_priority')=='commerce':privilege*=1.25
        if a.get('political_priority')=='tradition':cultural*=1.25
        prejudice=0
        if any(b['name'].lower() in x['proposition'].lower() and 'sorcellerie' in x['proposition'].lower() for x in beliefs):
            prejudice=.30*derive_religious_suspicion(a,beliefs)*a['credulity']
        weights[bid]=max(.025, .12+solidarity+connection+cultural+privilege+personal-prejudice)
    total=sum(weights.values())
    return {k:round(v/total,7) for k,v in weights.items()}


def integer_allocation(total,weights):
    """Plus forts restes : une somme entière conservée exactement."""
    s=sum(weights.values());raw={k:total*v/s for k,v in weights.items()}
    result={k:math.floor(v) for k,v in raw.items()}
    missing=total-sum(result.values())
    for k in sorted(raw,key=lambda k:(-(raw[k]-result[k]),k))[:missing]:result[k]+=1
    assert sum(result.values())==total
    return result


def election(sim):
    state=sim.state;politics=state['politics']
    if politics['phase']=='complete':return politics['result']
    agents=state['agents'];rel=state['relations'];minute=state['minute']
    candidates=[c for c in politics['candidates'] if c in agents]
    votes=[];weight_sum={aid:0.0 for aid in agents}
    for aid,a in agents.items():
        beliefs=sim.store.beliefs(aid,30)
        selected,scores=vote_candidate(a,agents,rel[aid],candidates,beliefs,state['seed']+minute+sum(ord(c) for c in aid))
        proposal=ballot_weights(a,agents,rel[aid],beliefs)
        for target,v in proposal.items():weight_sum[target]+=v
        rationale=('priorité aux nécessiteux' if a['generosity']>.65 else
                   'défense des traditions' if a['religiosity']>.75 else 'équilibre des intérêts')
        vote={'voter':aid,'candidate':selected,'allocation':proposal,'rationale':rationale,
              'scores':scores}
        votes.append(vote)
        sim.store.ballot(minute,aid,selected,proposal,rationale)
        sim.store.memory(aid,minute,'vote',f"J'ai voté pour {agents[selected]['name']} ; ma priorité est {rationale}.",.86,'scrutin')
    tally=dict(Counter(x['candidate'] for x in votes))
    winner=sorted(candidates,key=lambda c:(-tally.get(c,0),c))[0]
    requested=politics['budget_total'];available=state['resources']['treasury']
    budget=min(requested,available)
    allocation=integer_allocation(budget,weight_sum)
    state['resources']['treasury']-=budget
    for aid,amount in allocation.items():
        agents[aid]['coins']+=amount
        agents[aid]['security']=clamp(agents[aid]['security']+.09*amount/max(1,budget/len(agents)))
        sim.store.memory(aid,minute,'budget',f'La commune me verse {amount} écus du budget voté.',.79,'mairie')
    result={'minute':minute,'mayor':winner,'tally':tally,'allocation':allocation,
            'total':budget,'turnout':len(votes),'ballots':votes}
    politics.update(phase='complete',mayor=winner,turnout=len(votes),result=result,
                    ballots=votes)
    sim.store.event(minute,'election',winner,None,
        f"{agents[winner]['name']} devient maire ({tally[winner]}/{len(votes)} voix).",{'tally':tally})
    sim.store.event(minute,'budget',None,None,
        f'Répartition communale de {budget} écus entre {len(agents)} habitants.',
        {'allocation':allocation,'treasury_remaining':state['resources']['treasury']})
    return result
