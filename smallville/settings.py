"""Local-only configuration. No remote inference except explicitly enabled Jev."""
import json, os
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
DATA=ROOT/'data'; DATA.mkdir(exist_ok=True)
DEFAULT={
 'backend':'auto','mlx_url':'http://127.0.0.1:8080/v1/chat/completions',
 'tick_seconds':0.85,'jev_enabled':False,'jev_model':'jev-1.14.0',
 'jev_budget_usd':0.75,'jev_max_calls_total':100,'jev_max_calls_day':8,
 'jev_max_calls_24h':24,'jev_min_interval_seconds':30,'jev_max_payload_bytes':7000,
 'seed':14712}

def load():
    cfg=DEFAULT.copy(); p=DATA/'settings.json'
    if p.exists():
        try:cfg.update({k:v for k,v in json.loads(p.read_text()).items() if k in DEFAULT})
        except (ValueError,OSError):pass
    cfg['jev_budget_usd']=max(0,min(float(cfg['jev_budget_usd']),4))
    cfg['tick_seconds']=max(.15,min(float(cfg['tick_seconds']),8))
    cfg['jev_max_calls_total']=max(0,min(int(cfg['jev_max_calls_total']),500))
    if cfg['backend'] not in ('auto','apple','mlx_local','scripted'):cfg['backend']='auto'
    cfg['mlx_url']=DEFAULT['mlx_url'] # no remote URL via config
    return cfg

def save(cfg):
    p=DATA/'settings.json'; tmp=DATA/'settings.tmp'
    tmp.write_text(json.dumps({k:cfg[k] for k in DEFAULT},ensure_ascii=False,indent=2))
    os.chmod(tmp,0o600);tmp.replace(p)

def read_key():
    if os.environ.get('TYPESAFE_API_KEY'):return os.environ['TYPESAFE_API_KEY'].strip()
    p=ROOT/'.env'
    if p.exists():
        for l in p.read_text().splitlines():
            if l.startswith('TYPESAFE_API_KEY='):return l.split('=',1)[1].strip().strip('"')
    return ''
