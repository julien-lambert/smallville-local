"""Local-only configuration. No remote inference except explicitly enabled Jev."""
import json, os
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
DATA=ROOT/'data'; DATA.mkdir(exist_ok=True)
DEFAULT={
 'backend':'auto','mlx_url':'http://127.0.0.1:8080/v1/chat/completions',
 'tick_seconds':0.85,'jev_enabled':False,'jev_model':'jev-1.14.0',
 'jev_budget_usd':4.50,'jev_max_calls_total':12000,'jev_max_calls_day':700,
 'jev_max_calls_24h':6000,'jev_min_interval_seconds':1,'jev_max_payload_bytes':12000,
 'seed':14712}

def load():
    cfg=DEFAULT.copy(); p=DATA/'settings.json'
    if p.exists():
        try:
            saved=json.loads(p.read_text())
            # Migration automatique des QUOTAS PAR DÉFAUT V1 : ne pas conserver
            # 8 appels/jour si l'utilisateur n'avait pas modifié les valeurs.
            old_defaults={'jev_budget_usd':.75,'jev_max_calls_total':100,
                          'jev_max_calls_day':8,'jev_max_calls_24h':24,
                          'jev_min_interval_seconds':30,'jev_max_payload_bytes':7000}
            for k,v in saved.items():
                if k in DEFAULT and not(k in old_defaults and v==old_defaults[k]):
                    cfg[k]=v
        except (ValueError,OSError):pass
    cfg['jev_budget_usd']=max(0,min(float(cfg['jev_budget_usd']),4.50))
    cfg['tick_seconds']=max(.15,min(float(cfg['tick_seconds']),8))
    cfg['jev_max_calls_total']=max(0,min(int(cfg['jev_max_calls_total']),12000))
    cfg['jev_max_calls_day']=max(0,min(int(cfg['jev_max_calls_day']),700))
    cfg['jev_max_calls_24h']=max(0,min(int(cfg['jev_max_calls_24h']),6000))
    cfg['jev_min_interval_seconds']=max(1,min(int(cfg['jev_min_interval_seconds']),60))
    cfg['jev_max_payload_bytes']=max(2000,min(int(cfg['jev_max_payload_bytes']),12000))
    if cfg['backend'] not in ('auto','apple','mlx_local','scripted'):cfg['backend']='auto'
    cfg['mlx_url']=DEFAULT['mlx_url'] # no remote URL via config
    return cfg

def save(cfg):
    p=DATA/'settings.json'; tmp=DATA/'settings.tmp'
    tmp.write_text(json.dumps({k:cfg[k] for k in DEFAULT},ensure_ascii=False,indent=2))
    os.chmod(tmp,0o600);tmp.replace(p)

def read_var(name,default=''):
    if name in os.environ:return os.environ[name].strip()
    p=ROOT/'.env'
    if p.exists():
        for l in p.read_text().splitlines():
            if l.startswith(name+'='):return l.split('=',1)[1].strip().strip('\"')
    return default

def read_key():
    return read_var('TYPESAFE_API_KEY')
