"""Tests de régression : tous les tests utilisent de fausses réponses Jev, aucun cloud."""
import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from sys import path
path.insert(0,str(Path(__file__).resolve().parents[1]))
from smallville.store import Store
from smallville.seed import new_world, migrate_world, WIDTH, HEIGHT, PEOPLE, SECRETS, TOTAL_BUDGET
from smallville.sim import Simulation, find_path
from smallville.settings import DEFAULT
from smallville.jev import decide, URL
from smallville.graph import GraphBridge, statement, HOST

class SocietyCase(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=Store(os.path.join(self.tmp.name,'test.sqlite3'))
        self.cfg=copy.deepcopy(DEFAULT);self.cfg['backend']='scripted'
        self.sim=Simulation(self.store,self.cfg)

    def test_population_distribution_and_no_killing(self):
        w=self.sim.state;agents=w['agents'];self.assertEqual(len(agents),25)
        self.assertEqual(len(w['grid']),HEIGHT);self.assertEqual(len(w['grid'][0]),WIDTH)
        self.assertEqual(len(w['relations']),25)
        for aid,a in agents.items():
            self.assertNotIn(w['grid'][a['y']][a['x']],('tree','building'))
            self.assertGreater(a['health'],0)
            for k in ('conatus','reasoning','aggression','religiosity','credulity'):
                self.assertGreaterEqual(a[k],0);self.assertLessEqual(a[k],1)
            self.assertEqual(len(w['relations'][aid]),24)
        self.assertTrue(w['laws']['murder_forbidden'])
        self.assertTrue(w['laws']['executions_forbidden'])
        capitals=sorted(a['capital'] for a in agents.values())
        self.assertGreater(capitals[-1]/capitals[0],10)
        self.assertIn('Gédéon',[a['name'] for a in agents.values()])

    def test_find_path_closed_world(self):
        path=find_path(self.sim.state['grid'],[22,16],[7,9]);self.assertGreater(len(path),10)
        self.assertTrue(all(self.sim.state['grid'][y][x] not in ('tree','building') for x,y in path))
        self.assertEqual(find_path(self.sim.state['grid'],[22,17],[-1,100]),[])

    def test_private_and_public_beliefs(self):
        message='La guérisseuse sera candidate demain.'
        self.sim.give_information('alice',message,mode='belief')
        self.assertIn(message,[x['proposition'] for x in self.store.beliefs('alice')])
        self.assertNotIn(message,[x['proposition'] for x in self.store.beliefs('noe')])
        self.sim.give_information('alice','Le vieux moulin va fermer.',scope='public')
        self.assertEqual(sum('Le vieux moulin va fermer.' in [b['proposition'] for b in self.store.beliefs(x)] for x in self.sim.state['agents']),25)
        self.assertNotIn('TYPESAFE_API_KEY',json.dumps(self.sim.export()))

    def test_persistence_and_migration_six_agents(self):
        state=new_world(72)
        state['agents']={k:v for k,v in list(state['agents'].items())[:6]}
        state['relations']={k:{kk:vv for kk,vv in val.items() if kk in state['agents']}
                            for k,val in state['relations'].items() if k in state['agents']}
        state['version']=1;state['agents']['alice']['mood']=.38
        self.store.save(state)
        reopened=Simulation(self.store,self.cfg)
        self.assertEqual(len(reopened.state['agents']),25)
        self.assertAlmostEqual(reopened.state['agents']['alice']['mood'],.38)
        self.assertTrue(reopened.state['paused'])
        self.assertEqual(reopened.state['minute'],state['minute'])

    def test_pair_conversation_gossip_and_graph(self):
        self.sim._conversation('alice-basile','alice','basile',501,self.sim.epoch)
        self.assertEqual(len(self.store.all('SELECT id FROM dialogues')),2)
        self.assertTrue(any(SECRETS['alice']==x['proposition'] for x in self.store.beliefs('basile')))
        self.assertEqual(self.store.budget(self.cfg)['calls'],0)
        self.assertTrue(self.store.memories('basile'))
        self.assertGreater(self.store.outbox_count(),650)

    def test_group_conversation_and_assembly(self):
        minute=600;ids=['gideon','judith','lucien','samuel']
        self.sim._group_conversation('group-'+str(minute),ids,minute,self.sim.epoch)
        self.assertEqual(len(self.store.assemblies()),0) # worker doesn't invent attendance
        self.assertGreaterEqual(len(self.store.all('SELECT * FROM dialogues WHERE listener=?',('group',))),2)
        for aid in ids:
            self.assertTrue(self.store.memories(aid))
        self.assertGreaterEqual(len(self.store.all('SELECT id FROM events WHERE type=?',('group_dialogue',))),2)

    def test_election_budget_sealed_one_person_one_vote(self):
        s=self.sim.state;initial=s['resources']['currency_supply_initial']
        s['minute']=s['politics']['election_minute']-1
        self.sim.step()
        result=s['politics']['result'];self.assertEqual(result['turnout'],25)
        self.assertEqual(len(self.store.ballots()),25)
        self.assertEqual(len(result['ballots']),25)
        self.assertEqual(len(result['allocation']),25)
        self.assertEqual(sum(result['allocation'].values()),TOTAL_BUDGET)
        self.assertEqual(sum(result['tally'].values()),25)
        self.assertEqual(s['politics']['phase'],'complete')
        self.assertEqual(s['resources']['treasury']+sum(a['coins'] for a in s['agents'].values()),initial)
        self.sim.step();self.assertEqual(len(self.store.ballots()),25)

    def test_daily_economy_preserves_currency_and_conatus(self):
        r=self.sim.state['resources'];initial=r['currency_supply_initial']
        self.sim._new_day(1)
        self.assertEqual(r['treasury']+sum(a['coins'] for a in self.sim.state['agents'].values()),initial)
        for a in self.sim.state['agents'].values():
            self.assertGreater(a['health'],0);self.assertGreater(a['conatus'],0)
            self.assertGreater(a['reflections'],0)

    def test_reset_never_erases_jev_budget(self):
        rid,_=self.store.reserve_jev(500,self.cfg,'{}');self.assertIsNotNone(rid)
        self.store.finish_jev(rid,error='timeout');initial=self.store.budget(self.cfg)
        old_run=self.sim.state['run_id'];self.sim.reset()
        self.assertEqual(initial['used_or_reserved_usd'],self.store.budget(self.cfg)['used_or_reserved_usd'])
        self.assertNotEqual(self.sim.state['run_id'],old_run)
        self.assertGreater(self.store.outbox_count(),0)

    def test_jev_budget_zero_cloud_calls(self):
        self.sim.jev.key='dummy'
        self.sim.jev.opener.open=lambda *a,**k: self.fail('Réseau interdit')
        a=self.sim.state['agents']['alice'];b=self.sim.state['agents']['basile']
        response,_=self.sim.jev.judge(500,a,b,'bonjour',{},[],[])
        self.assertIsNone(response)
        self.assertEqual(self.store.budget(self.cfg)['calls'],0)

    def test_jev_faux_response_single_batched_request(self):
        self.cfg['jev_enabled']=True;self.sim.jev.key='TEST_ONLY'
        class Fake:
            url=URL
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def read(self,n):return json.dumps({'model':'jev-1.14.0','answers':{
                'tone':{'choice':'kind'},'threat':{'noul':.1},'reconcile':{'noul':.88},'upset':{'score':.3},'claim_supported':{'noul':.92}},
                'usage':{'input_tokens':1000}}).encode()
        calls=[]
        def intercept(req,timeout=0):
            self.assertEqual(req.full_url,URL)
            self.assertEqual(req.get_header('Authorization'),'Bearer TEST_ONLY')
            calls.append(json.loads(req.data));return Fake()
        self.sim.jev.opener.open=intercept
        a,b=self.sim.state['agents']['alice'],self.sim.state['agents']['basile']
        response,error=self.sim.jev.judge(500,a,b,'Merci.',self.sim.state['relations']['alice']['basile'],[],[])
        self.assertIsNone(error)
        self.assertEqual(len(calls),1)
        self.assertEqual(len(calls[0]['questions']),5)
        self.assertEqual(decide(response,a,{})['stance'],'warm')
        again,error=self.sim.jev.judge(501,a,b,'Encore.',{},[],[])
        self.assertIsNone(again);self.assertIn('Délai',error)

    def test_surreal_graph_escaping_and_outbox(self):
        s=statement('belief',{'run_id':'test123','id':'1','agent':'alice','source':'basile',
           'data':{'proposition':'"; DELETE agent; --','confidence':.32,'minute':500}})
        self.assertIn('agent:test123_alice->holds:',s)
        self.assertIn('influenced:',s)
        self.assertIn('\\"; DELETE agent; --',s)
        self.assertEqual(HOST,'http://127.0.0.1:8001')
        bridge=GraphBridge(self.store);bridge.password='test-not-real';written=[]
        def fake_query(sql,timeout=2):
            written.append(sql);return [{'status':'OK','result':[]} for _ in sql.split(';') if _.strip()]
        bridge.query=fake_query
        count=bridge.flush(12)
        self.assertEqual(count,12)
        self.assertEqual(bridge.synced,12)
        self.assertGreater(self.store.outbox_count(),0)
        self.assertTrue(any('UPSERT' in x for x in written))


    def test_mind_initialized_and_subjective(self):
        agents=self.sim.state['agents']
        for a in agents.values():
            self.assertEqual(set(a['worldview']) >= {'religious_authority','empirical_evidence','political_equality'},True)
            self.assertIn('sorcellerie',a['salience'])
            self.assertIn('fear',a['emotions'])
            self.assertEqual(a['decisions'],0)
        self.assertNotEqual(agents['basile']['worldview']['religious_authority'],
                            agents['lucien']['worldview']['religious_authority'])

    def test_jev_appraisal_revises_belief_and_future_action(self):
        from smallville.mind import apply_appraisal
        self.cfg['jev_enabled']=True
        self.sim.jev.key='TEST_ONLY'
        original=self.sim.state['agents']['alice']['decisions']
        mocked={
          'priority':{'choice':'pray'},'emotion':{'choice':'peur'},
          'political_priority':{'choice':'tradition'},
          'evidence':{'score':0},'direct_observation':{'noul':.96},
          'social_risk':{'noul':.7},'candidate':{'choice':'gideon'}}
        calls=[]
        def fake_appraise(minute,agent,memories,beliefs,relations,public,candidates):
            calls.append({'agent':agent,'memories':memories,'beliefs':beliefs,'relations':relations,'public':public})
            return mocked,None
        self.sim.jev.appraise=fake_appraise
        initial={b['proposition']:b['confidence'] for b in self.store.beliefs('alice',50)}
        self.sim._appraise('alice','information-recue',500,self.sim.epoch)
        a=self.sim.state['agents']['alice']
        self.assertEqual(len(calls),1)
        self.assertIn('worldview',calls[0]['agent'])
        self.assertIn('memories',calls[0])
        self.assertGreater(a['decisions'],original)
        self.assertEqual(a['intention'],'pray')
        self.assertEqual(a['candidate_preference'],'gideon')
        self.assertGreater(a['emotions']['fear'],0.0)
        self.assertTrue(any(b['confidence']<initial.get(b['proposition'],0) for b in self.store.beliefs('alice',50)
                            if b['proposition'] in initial))
        self.assertTrue(self.store.belief_history('alice'))
        self.assertEqual(self.store.budget(self.cfg)['calls'],0)  # No paid API in mocked test

    def test_apple_prompt_contains_live_mind(self):
        import json
        from smallville.models import Apple
        a=self.sim.state['agents']['alice']
        b=self.sim.state['agents']['basile']
        captured=[]
        apple=Apple()
        apple.query=lambda sys,prompt:(captured.append(json.loads(prompt)) or 'Je souhaite en parler.')
        _,_,_,_,_,ctx=self.sim._ctx('alice','basile','la foi')
        apple.speak(a,b,ctx)
        self.assertEqual(captured[-1]['ma_vision_du_monde'],a['worldview'])
        self.assertEqual(captured[-1]['mes_emotions_dynamiques'],a['emotions'])
        a['worldview']['empirical_evidence']=.9
        _,_,_,_,_,ctx2=self.sim._ctx('alice','basile','les preuves')
        apple.speak(a,b,ctx2)
        self.assertEqual(captured[-1]['ma_vision_du_monde']['empirical_evidence'],.9)

    def test_budget_larger_but_bounded(self):
        self.assertEqual(self.cfg['jev_budget_usd'],4.25)
        self.assertGreater(self.cfg['jev_max_calls_total'],100)
        self.assertLessEqual(self.cfg['jev_budget_usd'],5)
        self.assertGreater(self.store.budget(self.cfg)['max_calls_day'],8)

if __name__=='__main__':unittest.main()
