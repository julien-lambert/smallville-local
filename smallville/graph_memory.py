"""Mémoire relationnelle : retrieval centré sur l'agent et provenance vérifiable.

SurrealDB est interrogé en graphe (flèches) lorsqu'il est disponible. Le repli
SQLite conserve les *mêmes frontières épistémiques* : seules les observations,
les croyances et les influences effectivement reçues sont visibles par l'agent.
L'observateur peut consulter séparément l'analyse des diffusions globales.
"""
from __future__ import annotations
from collections import defaultdict
import re

from .mind import category
from .graph import identifier, quoted


def terms(value):
    return set(re.findall(r"[\wÀ-ÿ]{4,}", str(value).lower()))


def relevance(text, query):
    a,b=terms(text),terms(query)
    return min(1.0,len(a&b)/max(1,min(len(b),7)))


def _records(response, slot):
    try:
        data=response[slot]['result']
        if isinstance(data,dict):return [data]
        return data if isinstance(data,list) else []
    except (KeyError,IndexError,TypeError):return []


class GraphMemory:
    def __init__(self,bridge,store):
        self.bridge,self.store=bridge,store

    def _graph_records(self,run_id,agent_id):
        """Un seul appel local, cinq traversées bornées, aucun scan du graphe global."""
        r,a=identifier(run_id),identifier(agent_id)
        root=f'agent:{r}_{a}'
        sql=' '.join((
            f'SELECT minute,kind,content,importance,source FROM {root}->remembers->memory WHERE run_id={quoted(r)} ORDER BY minute DESC LIMIT 90;',
            f'SELECT minute,proposition,confidence,source FROM {root}->holds->belief WHERE run_id={quoted(r)} ORDER BY minute DESC LIMIT 60;',
            f'SELECT minute,proposition,before,after,source FROM {root}->revised->belief_revision WHERE run_id={quoted(r)} ORDER BY minute DESC LIMIT 70;',
            f'SELECT minute,in,belief FROM {root}<-influenced WHERE run_id={quoted(r)} ORDER BY minute DESC LIMIT 65;',
            f'SELECT minute,out,trust,tension,familiarity FROM {root}->knows WHERE run_id={quoted(r)} ORDER BY familiarity DESC LIMIT 25;'
        ))
        data=self.bridge.query(sql,timeout=2.0)
        return tuple(_records(data,i) for i in range(5))

    def _sqlite_records(self,agent_id):
        mem=self.store.memories(agent_id,90)
        beliefs=self.store.beliefs(agent_id,60)
        changes=self.store.belief_history(agent_id,70)
        # Tous les évènements d'influence du repli SQLite appartiennent à l'agent.
        influences=[{'belief':b['proposition'],'minute':b['minute'],'in':b['source']}
                    for b in beliefs if b.get('source')]
        return mem,beliefs,changes,influences,[]

    def context(self,run_id,agent_id,query,minute,salience=None):
        salience=salience or {}
        source='sqlite'
        if self.bridge.status=='connecté':
            try:
                memories,beliefs,changes,influences,edges=self._graph_records(run_id,agent_id)
                # Au premier démarrage le journal SQLite peut précéder le graphe :
                # garder l'état subjectif actuel pendant la synchronisation.
                if not memories or not beliefs:
                    sm,sb,sc,si,se=self._sqlite_records(agent_id)
                    memories=memories or sm;beliefs=beliefs or sb
                    changes=changes or sc;influences=influences or si;edges=edges or se
                    source='surrealdb + sqlite (synchronisation)'
                else:source='surrealdb'
            except Exception:
                memories,beliefs,changes,influences,edges=self._sqlite_records(agent_id)
        else:
            memories,beliefs,changes,influences,edges=self._sqlite_records(agent_id)
        def ranking(row,field,base=0.0):
            text=row.get(field) or ''
            age=max(0,minute-int(row.get('minute') or 0))
            return (base+.43*relevance(text,query)+
                    .22*salience.get(category(text),.45)+
                    .18/(1+age/550)+.17*float(row.get('importance') or .5))
        memories=sorted(memories,key=lambda m:ranking(m,'content'),reverse=True)[:7]
        beliefs=sorted(beliefs,key=lambda b:ranking(b,'proposition',.07),reverse=True)[:6]
        revision_map=defaultdict(list)
        for change in changes:
            revision_map[change.get('proposition','')].append(change)
        evidence=[]
        for b in beliefs:
            proposition=str(b.get('proposition',''))
            history=revision_map.get(proposition,[])[:3]
            evidence.append({'proposition':proposition[:250],
               'confiance':round(float(b.get('confidence') or 0),3),
               'source_declaree':str(b.get('source') or 'inconnue')[:90],
               'evolution':[{'avant':h.get('before'),'apres':h.get('after'),
                             'minute':h.get('minute'),'cause':str(h.get('source') or '')[:80]} for h in history],
               'observation_directe':str(b.get('source') or '').lower() in ('observation privée','personnel')})
        known={str(x.get('in') or '') for x in influences}
        network={'sources_distinctes':len(known),
           'influences_recues':[{'source':str(i.get('in') or '')[-40:],
                                 'theme':str(i.get('belief') or '')[:145],
                                 'minute':i.get('minute')} for i in influences[:5]],
           'liens_de_confiance':len(edges)}
        return {'origine':source,'souvenirs':[{'texte':str(m.get('content') or '')[:250],
            'importance':round(float(m.get('importance') or .5),2),
            'source':str(m.get('source') or '')[:75],
            'minute':m.get('minute')} for m in memories],
            'croyances':evidence,'provenance':network,
            'avertissement':'Ceci est la connaissance subjective de cet agent, pas la vérité du monde.'}

    def observer_influences(self,run_id,max_edges=1200):
        """Visualisation observateur : permet de suivre une rumeur entre agents."""
        if self.bridge.status!='connecté':return {'available':False,'links':[]}
        r=identifier(run_id)
        try:
            data=self.bridge.query('SELECT in,out,belief,minute FROM influenced '
                f'WHERE run_id={quoted(r)} ORDER BY minute DESC LIMIT {int(max_edges)};',timeout=3)
            edges=_records(data,0)
            links=[{'from':str(e.get('in','')).rsplit('_',1)[-1],
                    'to':str(e.get('out','')).rsplit('_',1)[-1],
                    'claim':str(e.get('belief',''))[:200],
                    'minute':e.get('minute')} for e in edges]
            counts=defaultdict(int);by_claim=defaultdict(list)
            for edge in links:
                counts[edge['from']]+=1
                by_claim[edge['claim']].append(edge)
            cascades=[]
            # Les chaînes sont reconstruite en suivant les transmissions datées.
            # C'est une trajectoire observée, non une preuve que la rumeur est vraie.
            for claim,seq in by_claim.items():
                seq=sorted(seq,key=lambda e:int(e['minute'] or 0))
                received={};parents={};participants=set();depths={}
                for edge in seq:
                    src,dst=edge['from'],edge['to']
                    participants.update((src,dst))
                    if dst not in received:
                        received[dst]=edge['minute'];parents[dst]=src
                        depths[dst]=min(10,depths.get(src,0)+1)
                roots=sorted({e['from'] for e in seq if e['from'] not in received})
                cascades.append({'proposition':claim,'diffusions':len(seq),
                    'habitants_touches':len(participants),'profondeur_max':max(depths.values(),default=0),
                    'origines_presumees':roots[:8],
                    'premiere_minute':seq[0]['minute'],'derniere_minute':seq[-1]['minute'],
                    'chaines':[{'de':dest,'source':src,'minute':received[dest]} for dest,src in list(parents.items())[:18]]})
            return {'available':True,'links':links[:300],
                'transmissions_observees':len(edges),
                'cascades':sorted(cascades,key=lambda x:-x['habitants_touches'])[:12],
                'diffuseurs_principaux':[{'agent':a,'transmissions':n} for a,n in
                  sorted(counts.items(),key=lambda item:-item[1])[:10]]}
        except Exception as exc:
            return {'available':False,'links':[],'reason':str(exc)[:160]}
