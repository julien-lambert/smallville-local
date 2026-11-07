"""Salem-sur-Brume: 25 personnages fictifs, institutions et économie fermée.

Les distributions modélisent des paramètres synthétiques, pas des diagnostics de personnes.
Le patrimoine suit une lognormale; styles cognitifs et agressivité des normales tronquées.
"""
import math
import random
from .mind import ensure_mind

WIDTH, HEIGHT = 44, 32
WORLD_VERSION = 4
ELECTION_HOUR = 16
TOTAL_BUDGET = 2500
START_MINUTE = 8 * 60

# Bâtiments physiques et accès extérieurs librement traversables.
BUILDINGS = [
    ('Église', 3, 3, 8, 6, '#786a83', (7, 9)),
    ('Presbytère', 14, 3, 6, 5, '#806d66', (17, 8)),
    ('Mairie', 32, 3, 9, 6, '#ad776e', (36, 9)),
    ('École', 4, 14, 7, 5, '#8b8270', (11, 17)),
    ('Marché', 32, 14, 9, 5, '#a58b65', (31, 17)),
    ('Grenier', 3, 24, 8, 5, '#857557', (7, 23)),
    ('Dispensaire', 14, 24, 7, 5, '#648f7a', (18, 23)),
    ('Taverne', 33, 24, 8, 5, '#987b59', (36, 23)),
]
PLACES = {
    'eglise': (7, 9), 'presbytere': (17, 8), 'mairie': (36, 9),
    'ecole': (11, 17), 'marche': (31, 17), 'grenier': (7, 23),
    'dispensaire': (18, 23), 'taverne': (36, 23), 'place': (22, 17),
    'champs': (12, 30),
}
TRAITS = ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism']
# Identité, prénom, rôle, biographie, but, lieu professionnel. Il n'y a pas de comportements préordonnés.
PEOPLE = [
 ('alice','Alice','Scribe de paroisse','Pieuse, charitable, attentive aux rumeurs, mais soucieuse des preuves.','Rassurer les familles et garder une communauté soudée.','eglise'),
 ('basile','Basile','Prédicateur rigoriste','Éloquent, soupçonne des influences occultes sans disposer de preuves.','Convaincre les habitants que la discipline protège le village.','eglise'),
 ('chloe','Chloé','Guérisseuse','Instruite et indépendante, ses remèdes suscitent des soupçons injustifiés.','Soigner et défendre sa liberté de conscience.','dispensaire'),
 ('dorian','Dorian','Cultivateur','Méthodique, sceptique face aux accusations, inquiet des récoltes.','Obtenir des réserves de nourriture suffisantes.','champs'),
 ('emma','Emma','Maire sortante','Croyante modérée qui préfère les secours aux sanctions.','Préserver la paix et la justice sociale.','mairie'),
 ('felix','Félix','Négociant ambitieux','Marchand stratégique, exploite parfois les rumeurs pour gagner de l’influence.','Gagner les élections et défendre le commerce.','marche'),
 ('gideon','Gédéon','Prêtre','Prêtre érudit, rigoriste sur le dogme mais opposé à toute violence.','Maintenir l’autorité de l’Église et éviter le sang.','eglise'),
 ('helene','Hélène','Sage-femme','Très attentive aux autres, elle est parfois désignée à tort comme suspecte.','Faire survivre les familles les plus fragiles.','dispensaire'),
 ('isaac','Isaac','Instituteur','Enseigne la logique et les textes religieux; évite les certitudes hâtives.','Former des habitants capables de raisonner.','ecole'),
 ('judith','Judith','Dévote','Foi fervente, craint les malédictions et recherche la reconnaissance du prêtre.','Protéger sa maison en suivant les enseignements.','eglise'),
 ('karim','Karim','Meunier','Travailleur pragmatique attaché aux échanges équitables.','Conserver son moulin et aider ses voisins.','grenier'),
 ('lucien','Lucien','Philosophe rationaliste','Conteste les accusations infondées et étudie les mécanismes du pouvoir.','Faire prévaloir les preuves et le débat.','ecole'),
 ('margot','Margot','Propriétaire foncière','Très fortunée, protectrice des traditions et de ses privilèges.','Conserver ses terres et sa position sociale.','mairie'),
 ('noe','Noé','Apprenti crédule','Jeune enthousiaste qui accorde facilement sa confiance aux autorités.','Être accepté et comprendre les événements du village.','marche'),
 ('olivia','Olivia','Herboriste','Échange des remèdes avec Chloé, redoute la méfiance religieuse.','Vivre de ses plantes sans être exclue.','dispensaire'),
 ('paul','Paul','Garde impulsif','Brutal dans ses propos, agit souvent avant de réfléchir; le meurtre reste interdit.','Obtenir le respect et protéger sa propre sécurité.','mairie'),
 ('quentin','Quentin','Tavernier','Extrêmement sociable, recueille ragots et confidences.','Garder sa taverne fréquentée.','taverne'),
 ('rose','Rose','Colporteuse','Transforme parfois des anecdotes en rumeurs sans intention de nuire.','Recevoir des nouvelles et vendre ses marchandises.','marche'),
 ('samuel','Samuel','Diacre charitable','Profondément croyant, privilégie la compassion à la peur.','Distribuer du pain et apaiser les conflits.','eglise'),
 ('therese','Thérèse','Tisserande','Travaille sans relâche, observe les inégalités et les tensions.','Assurer ses revenus et ceux de ses proches.','marche'),
 ('ulysse','Ulysse','Journalier pauvre','Ne possède presque rien, très sensible aux promesses de secours.','Se nourrir et trouver des alliés fiables.','grenier'),
 ('violette','Violette','Notaire','Connaît les règles de la commune et défend la légalité des scrutins.','Empêcher la fraude et garder les comptes exacts.','mairie'),
 ('william','William','Fermier traditionaliste','Conservateur, méfiant envers les étrangers à son cercle.','Préserver la production et la tradition.','champs'),
 ('xavier','Xavier','Magistrat','Cherche l’ordre, parfois influencé par la peur collective, sans droit de tuer.','Régler les différends selon la charte.','mairie'),
 ('yasmine','Yasmine','Étudiante','Curieuse et critique, questionne les superstitions et admire les érudits.','Apprendre et défendre sa propre pensée.','ecole'),
]
CANDIDATES = ['emma', 'felix', 'basile', 'chloe', 'gideon', 'lucien', 'margot']
SECRETS = {
 'alice':'Alice a entendu parler de guérisons incomprises : elle ne sait pas si la rumeur est vraie.',
 'basile':'Basile croit qu’une hérésie menacerait le village, mais il ne possède aucune preuve.',
 'chloe':'Chloé sait que ses remèdes ont été accusés à tort de sorcellerie.',
 'dorian':'Dorian craint que les récoltes ne suffisent pas à nourrir le village.',
 'emma':'Emma soupçonne Félix d’utiliser la peur pour gagner des voix.',
 'felix':'Félix envisage de faire campagne en amplifiant les soupçons populaires.',
 'gideon':'Gédéon estime que la violence contredit sa mission, malgré sa foi stricte.',
 'helene':'Hélène a soigné discrètement une famille très endettée.',
 'isaac':'Isaac a relevé plusieurs contradictions dans les rumeurs de sorcellerie.',
 'judith':'Judith prend les propos de Basile pour une preuve suffisante.',
 'karim':'Karim connaît la quantité réelle de farine disponible au grenier.',
 'lucien':'Lucien soupçonne un usage politique des accusations de sorcellerie.',
 'margot':'Margot souhaite que les propriétaires influencent davantage le budget.',
 'noe':'Noé a entendu une histoire effrayante à propos de la guérisseuse.',
 'olivia':'Olivia craint que la défiance fasse fermer son atelier.',
 'paul':'Paul se sent méprisé par les personnes instruites.',
 'quentin':'Quentin a entendu des versions incompatibles du même récit.',
 'rose':'Rose ne sait plus d’où vient une rumeur qu’elle a répétée.',
 'samuel':'Samuel a distribué du pain sans informer le conseil.',
 'therese':'Thérèse estime les salaires insuffisants face au prix du grain.',
 'ulysse':'Ulysse possède des réserves pour un seul repas.',
 'violette':'Violette a consulté le règlement interdisant absolument toute mise à mort.',
 'william':'William attribue sans preuve de mauvaises récoltes à de mauvais présages.',
 'xavier':'Xavier veut examiner les accusations, mais refuse toute exécution.',
 'yasmine':'Yasmine collecte des témoignages pour en vérifier les contradictions.',
}
ANNOUNCEMENT = ('Demain à 16 h, les 25 habitants éliront leur maire et proposeront '
                'la répartition de 2 500 écus entre tous les résidents. '
                'La charte interdit le meurtre et les exécutions sans exception.')


def clamp(x, lo=0.01, hi=0.99):
    return round(max(lo,min(hi,x)),4)


def civic_state(minute=START_MINUTE):
    return dict(incumbent='emma', mayor='emma', phase='campaign',
                election_minute=(minute // 1440 + 1)*1440 + ELECTION_HOUR*60,
                budget_total=TOTAL_BUDGET, candidates=CANDIDATES[:], ballots=[],
                result=None, turnout=0, charter='Aucun meurtre ni exécution possible. '
                'La vie de chaque personne est protégée par les lois du monde.')


def new_world(seed=14712):
    rng=random.Random(seed)
    grid=[['grass']*WIDTH for _ in range(HEIGHT)]
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if 20 <= x <= 23 or 16 <= y <= 18 or (x==7 and 9<=y<=24) or (x==36 and 9<=y<=24):
                grid[y][x]='road'
            elif rng.random()<.042 and (x<12 or x>30) and (y<12 or y>22):
                grid[y][x]='tree'
    for y in range(13,22):
        for x in range(18,27):grid[y][x]='plaza'
    buildings=[]
    for name,x,y,w,h,color,(dx,dy) in BUILDINGS:
        for yy in range(y,y+h):
            for xx in range(x,x+w):grid[yy][xx]='building'
        grid[dy][dx]='road'
        buildings.append(dict(name=name,x=x,y=y,w=w,h=h,color=color,door=[dx,dy]))
    # Les accès au grenier/dispensaire/taverne traversent la route sud.
    for pt in PLACES.values():grid[pt[1]][pt[0]]='road' if grid[pt[1]][pt[0]]!='plaza' else 'plaza'
    occupied=set();agents={}
    palette=['#e7a5b1','#98c6f5','#e8c779','#92d0a1','#d1b2ea','#f0a680','#b7d9e3','#e2b486']
    for i,(aid,name,role,bio,goal,workplace) in enumerate(PEOPLE):
        traits={t:clamp(rng.gauss(.52,.18)) for t in TRAITS}
        # Ces variables sont indépendantes : un rôle ne détermine pas l'intelligence ou la violence.
        reasoning=clamp(rng.gauss(.54,.19))
        aggression=clamp(rng.gauss(.42,.18))
        religiosity=clamp(rng.gauss(.72,.22))
        credulity=clamp(rng.gauss(.53,.22))
        suspicion=clamp(rng.gauss(.55,.18))
        generosity=clamp(rng.gauss(.55,.20))
        ambition=clamp(rng.gauss(.45,.23))
        tolerance=clamp(rng.gauss(.55,.20))
        overrides={
            'basile':dict(religiosity=.99,credulity=.77,suspicion=.89,ambition=.76,tolerance=.15),
            'chloe':dict(reasoning=.81,religiosity=.31,credulity=.13,tolerance=.92),
            'emma':dict(ambition=.69,reasoning=.75,generosity=.82,tolerance=.81),
            'felix':dict(ambition=.98,generosity=.22,suspicion=.81),
            'gideon':dict(religiosity=.99,aggression=.08,reasoning=.72),
            'lucien':dict(reasoning=.96,credulity=.12,religiosity=.16),
            'judith':dict(religiosity=.97,credulity=.92),
            'noe':dict(credulity=.96,reasoning=.27),
            'margot':dict(ambition=.91,generosity=.20),
            'paul':dict(aggression=.94,reasoning=.23,tolerance=.18),
            'samuel':dict(religiosity=.96,generosity=.97,tolerance=.88),
            'ulysse':dict(ambition=.17,generosity=.69),
            'yasmine':dict(reasoning=.94,credulity=.13,tolerance=.89),
        }.get(aid,{})
        vals=dict(reasoning=reasoning,aggression=aggression,religiosity=religiosity,
                  credulity=credulity,suspicion=suspicion,generosity=generosity,
                  ambition=ambition,tolerance=tolerance)
        vals.update(overrides)
        # Fortune lognormale très asymétrique; revenus nominaux également hétérogènes.
        wealth_factor={'margot':4.2,'felix':2.6,'ulysse':.17,'noe':.35,'paul':.58,'emma':1.5}.get(aid,1)
        capital=max(2,round(rng.lognormvariate(math.log(70),1.05)*wealth_factor))
        income=max(1,round(rng.lognormvariate(math.log(9),.70)*{'margot':2.7,'felix':2,'ulysse':.35}.get(aid,1)))
        # Distribution des habitations autour de voies accessibles, sans empilement initial.
        possible=[(x,y) for y in range(7,27) for x in range(5,40)
                  if grid[y][x] not in ('building','tree') and (x,y) not in occupied]
        x,y=rng.choice(possible);occupied.add((x,y))
        agent=dict(id=aid,name=name,color=palette[i%len(palette)],role=role,bio=bio,
                   goal=goal,workplace=workplace,home=[x,y],x=x,y=y,destination=[x,y],
                   activity='observing',thought='Je m’interroge sur le scrutin de demain.',
                   traits=traits,original_traits=traits.copy(),
                   reasoning=vals['reasoning'],aggression=vals['aggression'],
                   religiosity=vals['religiosity'],credulity=vals['credulity'],
                   suspicion=vals['suspicion'],generosity=vals['generosity'],
                   ambition=vals['ambition'],tolerance=vals['tolerance'],
                   doctrine='orthodoxie' if vals['religiosity']>.82 else
                            'liberté' if vals['religiosity']<.35 else 'communauté',
                   energy=.82,social=.52,mood=.03,stress=.24,loneliness=.27,
                   hunger=rng.uniform(.13,.33),health=.93,hope=.62,security=.64,
                   conatus=.75,provisions=1 if aid=='ulysse' else rng.randint(2,6),
                   capital=capital,coins=capital,income=income,
                   last_social=-120,last_plan=-120,stay_until=0,route=[],
                   dialogue='',dialogue_until=0,experiences={'positive':0,'negative':0,'social':0},
                   last_reflection=-1,reflections=0,political_bias=0)
        agents[aid]=agent
    for a in agents.values():ensure_mind(a)
    relationships={a:{} for a in agents}
    for aid,a in agents.items():
        for bid,b in agents.items():
            if aid==bid:continue
            closeness=1-abs(a['religiosity']-b['religiosity'])
            base=clamp(.31+.25*closeness+rng.uniform(-.12,.12),.12,.82)
            if {aid,bid} in ({'chloe','dorian'},{'alice','emma'},{'lucien','yasmine'}):base=.83
            if {aid,bid} in ({'basile','chloe'},{'felix','emma'}):base=.19
            relationships[aid][bid]=dict(trust=base,affinity=base,
                                          tension=clamp((1-base)*.43,0,1),familiarity=.15)
    return dict(version=WORLD_VERSION,scenario='Salem-sur-Brume',seed=seed,minute=START_MINUTE,
                ticks=0,paused=True,grid=grid,buildings=buildings,agents=agents,
                relations=relationships,seen_pairs={},conversations_today=0,
                group_sessions_today=0,last_day=0,
                laws={'murder_forbidden':True,'executions_forbidden':True,
                      'violent_actions_forbidden':False,'murder_physically_possible':True,
                       'curfew_hour':22},
                resources={'granary':140,'field_fertility':.73,'grain_produced':0,
                           'grain_consumed':0,'food_price':6,'treasury':4600,
                           'currency_supply_initial':4600+sum(a['coins'] for a in agents.values())},
                politics=civic_state(START_MINUTE),run_id='')


def migrate_world(old, seed=14712):
    """Migration conservatrice d'anciens snapshots V1/V2, sans toucher à la DB privée."""
    if old.get('version',0)>=WORLD_VERSION and len(old.get('agents',{}))==len(PEOPLE):
        return old, []
    new=new_world(old.get('seed',seed))
    original=old.get('agents',{})
    for aid,previous in original.items():
        if aid not in new['agents']:continue
        a=new['agents'][aid]
        for field in ('traits','original_traits','energy','social','mood','stress','loneliness',
                      'hunger','health','hope','security','conatus','provisions','coins',
                      'political_bias','experiences','reflections'):
            if field in previous:a[field]=previous[field]
        for field in ('worldview','emotions','salience','intention','political_priority',
                      'candidate_preference','last_jev_minute','last_jev_attempt','decisions',
                      'revision_count','mental_trace'):
            if field in previous:a[field]=previous[field]
        ensure_mind(a)
        a['capital']=a['coins']
    # Les six relations historiques sont conservées, les autres naissent à l'état de départ.
    for aid,other in old.get('relations',{}).items():
        if aid not in new['relations']:continue
        for bid,rel in other.items():
            if bid in new['relations'][aid]:new['relations'][aid][bid].update(rel)
    new['minute']=old.get('minute',START_MINUTE)
    new['ticks']=old.get('ticks',0)
    new['paused']=True
    new['last_day']=new['minute']//1440
    new['politics']=civic_state(new['minute'])
    # La migration conserve le portefeuille des anciens agents et rétablit l'invariant monétaire.
    new['resources']['currency_supply_initial']=new['resources']['treasury']+sum(a['coins'] for a in new['agents'].values())
    return new,[aid for aid in new['agents'] if aid not in original]
