import sys,json,collections
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'host'))
from asym_protocol import parse_diag,parse_record
ds=[];vs=[];t=0
for l in Path('host/logs/20261027_211211_252.txt').read_text().splitlines():
 if l.startswith('D2'):
  d=parse_diag(l)
  if d:ds.append(d);t=d['time_ms']
 elif l.startswith('VIS=6'):
  d=parse_record(l)
  if d:d['time_ms']=t;vs.append(d)
def report(g):
 return dict(time=[g[0]['time_ms'],g[-1]['time_ms']],error=[min(d['x']-d['center'] for d in g),max(d['x']-d['center'] for d in g)],P=[min(d['position'] for d in g),max(d['position'] for d in g)],R=[min(d['reference_q8']/256 for d in g),max(d['reference_q8']/256 for d in g)],V=[min(d['velocity_q4']/16 for d in g),max(d['velocity_q4']/16 for d in g)],phase=dict(collections.Counter((d['flags']>>9)&3 for d in g)),Hznonzero=sum(d['frequency_hz']!=0 for d in g))

import hashlib
R=Path(__file__).resolve().parent
epoch=0;last=0
for d in ds:
 if d['time_ms']<last:epoch+=1
 last=d['time_ms'];d['epoch']=epoch
windows=[]
for a,b in [(100000,112000),(120000,126000),(165000,169000)]:
 g=[d for d in ds if d['epoch']==1 and a<=d['time_ms']<b and d['flags']&4 and d['flags']&8]
 windows.append(report(g))
faults=[];prev=0
for i,d in enumerate(ds):
 if d['fault'] and not prev:faults.append({'first':d,'preceding':ds[max(0,i-20):i]})
 prev=d['fault']
p=R/'host/logs/20261027_211211_252.txt'
result={'source':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'D2_count':len(ds),'VIS6_count':len(vs),'epochs':epoch+1,'windows':windows,'fault_events':faults,'centres':sorted(set(d['center'] for d in ds)),'interpretation':'Main stalls occur outside HOLD; assistance repeatedly withdrawn under coordinate jitter; F2 already present at trace start and new F2 at epoch1 169660ms. No automatic fault reset; UART has no unique build id.'}
out=R/'evidence/precise6_measurement';out.mkdir(exist_ok=True)
(out/'analysis_211211.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
import shutil
shutil.copy2(p,out/p.name)
print(json.dumps({k:v for k,v in result.items() if k!='fault_events'},ensure_ascii=False,indent=2))
