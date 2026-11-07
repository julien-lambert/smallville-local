"""BDI, planification, normes et rupture d'engagement : tests sans cloud."""
import random
import tempfile
import unittest
from pathlib import Path
from smallville.executive import create,current,contact,ensure
from smallville.transgression import deception,apply_incident
from smallville.settings import DEFAULT
from smallville.store import Store
from smallville.sim import Simulation

class ExecutiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.sim=Simulation(Store(Path(self.tmp.name)/'db.sqlite3'),dict(DEFAULT,backend='scripted'))
        self.a=self.sim.state['agents']['alice'];self.b=self.sim.state['agents']['basile']
    def test_project_persistent_and_agenda(self):
        project=create(self.a,self.sim.state,random.Random(123),490,kind='investigate')
        self.assertEqual(len(self.a['executive']['agenda']),2)
        next_project,step=current(self.a,self.sim.state,random.Random(321),510)
        self.assertEqual(project['id'],next_project['id'])
        self.assertEqual(step['action'],'research')
        self.assertEqual(self.a['executive']['future_scenarios'][0]['kind'],'hypothesis')
    def test_meeting_needs_actual_contact(self):
        p=create(self.a,self.sim.state,random.Random(15),500,kind='alliance')
        self.assertIsNone(contact(self.a,'unknown',540))
        self.assertEqual(p['step_index'],0)
        change=contact(self.a,p['target'],541)
        self.assertEqual(change['step'],'approach')
        self.assertEqual(p['step_index'],1)
    def test_jev_is_future_preference_not_amnesia(self):
        p=create(self.a,self.sim.state,random.Random(5),500,kind='income')
        self.a['executive']['jev_project']='alliance'
        self.a['last_jev_minute']=501
        proj,_=current(self.a,self.sim.state,random.Random(6),503)
        self.assertEqual(proj['id'],p['id'])
    def test_lie_requires_opposite_to_private_belief(self):
        self.a['executive']['tactic']='mislead';self.a['stress']=.7
        self.assertIsNone(deception(self.a,{'proposition':'La récolte est faible','confidence':.49},'basile',500))
        x=deception(self.a,{'proposition':'La récolte est faible','confidence':.95},'basile',500)
        self.assertIn('fausse',x['utterance'])
        self.assertEqual(x['internal_belief'],'La récolte est faible')
    def test_nonlethal_and_rare_lethal_are_distinct(self):
        self.a['stress']=.99;self.a['aggression']=.99
        self.sim.state['relations']['alice']['basile']['tension']=.99
        class Almost:
            def random(self):return .001
        result=apply_incident(self.sim,self.a,self.b,560,Almost())
        self.assertEqual(result,'homicide')
        self.assertFalse(self.b['alive'])
        self.assertEqual(self.b['health'],0)
        self.assertTrue(self.sim.state['laws']['murder_forbidden'])
        self.assertGreater(self.a['detained_until'],560)
        self.assertIsNone(apply_incident(self.sim,self.a,self.b,560,Almost()))
    def test_non_lethal_conflict(self):
        self.a['stress']=.5;self.a['aggression']=.9
        class Rng:
            def random(self):return 0
        self.assertEqual(apply_incident(self.sim,self.a,self.b,570,Rng()),'intimidation')
        self.assertTrue(self.b['alive'])
    def test_initial_no_crimes_and_conserved_money(self):
        s=self.sim.state
        self.assertTrue(all(a.get('alive',True) for a in s['agents'].values()))
        initial=s['resources']['currency_supply_initial']
        self.sim.advance(30)
        self.assertEqual(s['resources']['treasury']+sum(a['coins'] for a in s['agents'].values()),initial)
        self.assertTrue(any(a['executive']['project'] for a in s['agents'].values()))

if __name__=='__main__':unittest.main()
