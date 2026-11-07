import random
WIDTH,HEIGHT=32,24
BUILDINGS=[
 ('Maison commune',3,3,6,4,'#b97568',(6,7)),
 ('Bibliothèque',20,3,8,5,'#7695b3',(23,8)),
 ('Café',21,15,7,4,'#c69c78',(23,14)),
 ('Atelier',3,16,7,5,'#9a846d',(7,15)),
 ('Serre',13,18,5,4,'#70a588',(15,17))]
CHARACTERS=[
 ('alice','Alice','#f3bac0','Sociable, imaginative, sensible aux engagements.',[.85,.58,.86,.72,.62],(10,10),'Organiser une fête communautaire.'),
 ('basile','Basile','#a7c4f7','Artisan réservé, loyal, méthodique et indépendant.',[.43,.91,.30,.57,.27],(7,13),'Fabriquer un meuble à l’atelier.'),
 ('chloe','Chloé','#f3d383','Lectrice curieuse, spontanée et chaleureuse.',[.91,.55,.70,.81,.41],(23,10),'Écrire une chronique du village.'),
 ('dorian','Dorian','#9ccfa9','Jardinier sceptique, prudent et autonomiste.',[.63,.79,.34,.45,.50],(12,15),'Préserver l’eau du jardin.'),
 ('emma','Emma','#d3b6ee','Médiatrice empathique, discrète et conciliante.',[.75,.70,.58,.95,.35],(18,14),'Résoudre les conflits locaux.'),
 ('felix','Félix','#f1b08c','Charmeur, impatient, ambitieux, compétitif.',[.61,.63,.87,.40,.65],(27,12),'Gagner de l’influence au village.')]
SECRETS={
 'alice':'Alice prévoit une fête pour demain soir sur la place du village.',
 'basile':'Basile envisage d’abandonner un projet d’atelier.',
 'chloe':'Chloé pense que la place va être rénovée.',
 'dorian':'Le jardin souffre d’une sécheresse locale.',
 'emma':'Emma pense que Basile et Félix se comprennent mal.',
 'felix':'Félix veut organiser une élection pour un conseil de village.'}
TRAITS=['openness','conscientiousness','extraversion','agreeableness','neuroticism']

def new_world(seed=14712):
 r=random.Random(seed)
 grid=[['grass' for x in range(WIDTH)] for y in range(HEIGHT)]
 for y in range(HEIGHT):
  for x in range(WIDTH):
   if 14<=x<=17 or 10<=y<=13:grid[y][x]='road'
   elif r.random()<.046 and not (10<=x<=20 and 6<=y<=18):grid[y][x]='tree'
 for y in range(10,14):
  for x in range(14,18):grid[y][x]='plaza'
 buildings=[]
 for name,x,y,w,h,color,(dx,dy) in BUILDINGS:
  buildings.append(dict(name=name,x=x,y=y,w=w,h=h,color=color,door=[dx,dy]))
  for yy in range(y,y+h):
   for xx in range(x,x+w):grid[yy][xx]='building'
  grid[dy][dx]='road'
 agents={}
 for id,name,color,bio,traits,(x,y),goal in CHARACTERS:
  grid[y][x]='road'
  agents[id]=dict(id=id,name=name,color=color,bio=bio,goal=goal,
   traits=dict(zip(TRAITS,traits)),original_traits=dict(zip(TRAITS,traits)),
   x=x,y=y,destination=[x,y],activity='observe',thought='Je découvre ma journée.',
   energy=.86,social=.52,mood=.2,stress=.2,loneliness=.25,
   last_social=-100,last_plan=-100,dialogue='',dialogue_until=0,
   experiences={'positive':0,'negative':0,'social':0})
 rel={a:{} for a in agents}
 for a in agents:
  for b in agents:
   if a==b:continue
   base=.47+r.uniform(-.12,.12)
   if frozenset([a,b]) in [frozenset(['alice','chloe']),frozenset(['emma','alice'])]:base=.75
   if frozenset([a,b])==frozenset(['felix','dorian']):base=.25
   rel[a][b]=dict(trust=round(base,3),affinity=round(base,3),
                  tension=round((1-base)*.5,3),familiarity=.15)
 return dict(version=1,seed=seed,minute=480,ticks=0,paused=True,grid=grid,
   buildings=buildings,agents=agents,relations=rel,seen_pairs={},conversations_today=0,
   last_day=0)
