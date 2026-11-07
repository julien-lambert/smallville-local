"""Tests offline : zéro requête TypeSafe ou autre service réseau public."""
import copy,json,os,sys,tempfile,threading,time,unittest,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from smallville.store import Store
from smallville.seed import new_world,WIDTH,HEIGHT,SECRETS
from smallville.sim import Simulation,find_path
from smallville.settings import DEFAULT
from smallville.jev import Jev,decide,URL

class Case(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.store=Store(os.path.join(self.tmp.name,'test.sqlite3'))
  self.cfg=copy.deepcopy(DEFAULT);self.cfg['backend']='scripted'
  self.sim=Simulation(self.store,self.cfg)
 def test_six_agents_and_closed_map(self):
  s=self.sim.public()
  self.assertEqual(len(s['agents']),6)
  self.assertEqual(len(s['grid']),HEIGHT)
  self.assertEqual(len(s['grid'][0]),WIDTH)
  self.assertTrue(s['paused'])
  for a in s['agents'].values():
   self.assertNotIn(s['grid'][a['y']][a['x']],('tree','building'))
 def test_pathfinding(self):
  grid=self.sim.state['grid']
  path=find_path(grid,[10,10],[23,14])
  self.assertGreater(len(path),10)
  for x,y in path:self.assertNotIn(grid[y][x],('tree','building'))
 def test_private_beliefs(self):
  known={b['proposition'] for b in self.store.beliefs('alice')}
  self.assertIn(SECRETS['alice'],known)
  self.assertNotIn(SECRETS['alice'],[b['proposition'] for b in self.store.beliefs('basile')])
 def test_private_injection_and_export_without_secrets(self):
  text='La bibliothèque sera fermée demain.'
  self.sim.give_information('emma',text)
  self.assertTrue(any(b['proposition']==text for b in self.store.beliefs('emma')))
  self.assertFalse(any(b['proposition']==text for b in self.store.beliefs('dorian')))
  self.assertNotIn('TYPESAFE_API_KEY',json.dumps(self.sim.export()))
 def test_tick_and_persistence(self):
  self.sim.step();self.sim.step()
  self.assertEqual(self.sim.state['minute'],482)
  self.store.save(self.sim.state)
  reopened=Simulation(self.store,self.cfg)
  self.assertEqual(reopened.state['minute'],482)
 def test_social_conversation_and_rumor(self):
  a,b='alice','basile';minute=501
  self.sim._conversation('alice-basile',a,b,minute,self.sim.epoch)
  self.assertEqual(len(self.store.all('SELECT id FROM dialogues')),2)
  self.assertTrue(any(SECRETS['alice']==x['proposition'] for x in self.store.beliefs('basile')))
  self.assertEqual(self.store.budget(self.cfg)['calls'],0)
  self.assertTrue(self.store.memories('basile'))
 def test_traits_drift_bounded(self):
  a=self.sim.state['agents']['alice'];original=a['traits']['agreeableness']
  a['experiences']={'positive':250,'negative':0,'social':5}
  self.sim._new_day(1)
  self.assertLessEqual(a['traits']['agreeableness']-original,.005001)
 def test_reset_never_erases_money(self):
  rid,reason=self.store.reserve_jev(500,self.cfg,'{}')
  self.assertIsNotNone(rid)
  self.store.finish_jev(rid,error='timeout')
  initial=self.store.budget(self.cfg)
  self.sim.reset()
  final=self.store.budget(self.cfg)
  self.assertEqual(final['calls'],initial['calls'])
  self.assertEqual(final['used_or_reserved_usd'],initial['used_or_reserved_usd'])
 def test_jev_disabled_prevents_any_call(self):
  self.sim.jev.key='example_key'
  def forbidden(*a,**k):raise AssertionError('Network should not be touched')
  self.sim.jev.opener.open=forbidden
  a=self.sim.state['agents']['alice'];b=self.sim.state['agents']['basile']
  response,msg=self.sim.jev.judge(500,a,b,'bonjour',{},[],[])
  self.assertIsNone(response)
  self.assertEqual(self.store.budget(self.cfg)['calls'],0)
 def test_jev_payload_answer_schema_in_memory(self):
  self.cfg['jev_enabled']=True
  self.sim.jev.key='test-do-not-send'
  class FakeResponse:
   url=URL
   def __enter__(self):return self
   def __exit__(self,*args):return False
   def read(self,n):
    return json.dumps({'model':'jev-1.14.0','answers':{
      'tone':{'choice':'kind','probabilities':{'kind':.9}},
      'threat':{'noul':.1},'reconcile':{'noul':.88},'upset':{'score':.3}},
      'usage':{'input_tokens':1000}}).encode()
  captured=[]
  def fake_open(req,timeout=0):
   self.assertEqual(req.full_url,URL)
   self.assertEqual(req.get_header('Authorization'),'Bearer test-do-not-send')
   captured.append(json.loads(req.data));return FakeResponse()
  self.sim.jev.opener.open=fake_open
  a=self.sim.state['agents']['alice'];b=self.sim.state['agents']['basile']
  result,error=self.sim.jev.judge(500,a,b,'Merci de ton aide.',self.sim.state['relations']['alice']['basile'],[],[])
  self.assertIsNone(error)
  self.assertEqual(len(captured),1)
  self.assertEqual(len(captured[0]['questions']),4)
  self.assertEqual(decide(result,a,{})['stance'],'warm')
  self.assertEqual(self.store.budget(self.cfg)['calls'],1)
  result2,error2=self.sim.jev.judge(501,a,b,'Encore.',{},[],[])
  self.assertIsNone(result2)
  self.assertIn('Délai',error2)
  self.assertEqual(len(captured),1)

if __name__=='__main__':unittest.main()
