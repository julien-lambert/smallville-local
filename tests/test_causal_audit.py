"""Régressions inspirées des erreurs du corpus : parole, mémoire, budget, décès."""
import tempfile
import unittest
from pathlib import Path
from smallville.settings import DEFAULT
from smallville.store import Store
from smallville.sim import Simulation
from smallville.seed import SECRETS
from smallville.transgression import apply_incident

class AuditCausalityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.sim=Simulation(Store(Path(self.tmp.name)/'salem.db'),dict(DEFAULT,backend='scripted',jev_enabled=False))

    def test_lying_does_not_transmit_private_true_belief(self):
        a=self.sim.state['agents']['alice'];a['executive']['tactic']='mislead';a['stress']=.83
        original=SECRETS['alice']
        self.assertNotIn(original,[b['proposition'] for b in self.sim.store.beliefs('basile')])
        self.sim._conversation('alice-basile','alice','basile',540,self.sim.epoch)
        heard=[x['proposition'] for x in self.sim.store.beliefs('basile')]
        self.assertNotIn(original,heard)
        self.assertTrue(any('faux que' in x for x in heard),heard)
        self.assertGreaterEqual(len(self.sim.store.all("SELECT * FROM events WHERE type='deception'")),1)

    def test_cognitive_decision_trace_has_before_after_and_export(self):
        self.sim.cfg['jev_enabled']=True
        self.sim.jev.key='TEST_ONLY'
        self.sim.jev.appraise=lambda *args:(
            {'priority':{'choice':'study'},'emotion':{'choice':'curiosite'},
             'political_priority':{'choice':'preuves'},'evidence':{'score':3},
             'direct_observation':{'noul':.4},'social_risk':{'noul':.5},
             'project':{'choice':'investigate'},'commitment':{'noul':.8},
             'tactic':{'choice':'sincere'},'norm_strategy':{'choice':'obey'}},None)
        self.sim._appraise('alice','test',510,self.sim.epoch)
        traces=self.sim.store.all('SELECT * FROM cognitive_trace')
        self.assertEqual(len(traces),1)
        self.assertIn('before',traces[0]['payload'])
        data=self.sim.export()
        self.assertTrue(data['cognitive_trace'])
        self.assertIn('belief_history',data)
        self.assertIn('model_log',data)

    def test_vote_after_homicide_has_one_fewer_voter_and_no_dead_beneficiary(self):
        a=self.sim.state['agents']['alice'];b=self.sim.state['agents']['basile']
        a['aggression']=.99;a['stress']=.99
        self.sim.state['relations']['alice']['basile']['tension']=.99
        class Rng:
            def random(self):return .001
        self.assertEqual(apply_incident(self.sim,a,b,540,Rng()),'homicide')
        initial=self.sim.state['resources']['currency_supply_initial']
        self.sim.state['minute']=self.sim.state['politics']['election_minute']-1
        self.sim.step()
        res=self.sim.state['politics']['result']
        self.assertEqual(res['turnout'],24)
        self.assertNotIn('basile',res['allocation'])
        self.assertEqual(sum(res['allocation'].values()),res['total'])
        self.assertEqual(self.sim.state['resources']['treasury']+sum(x['coins'] for x in self.sim.state['agents'].values()),initial)

if __name__=='__main__':unittest.main()
