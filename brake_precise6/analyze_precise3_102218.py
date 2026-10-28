from pathlib import Path
import sys,json,collections
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R/'host'))
from asym_protocol import parse_diag,parse_record
ds=[];vs=[];last=0
for line in (R/'host/logs/20261027_102218_274.txt').read_text(errors='replace').splitlines():
 if line.startswith('D2'):
  d=parse_diag(line)
  if d:ds.append(d);last=d['time_ms']
 elif line.startswith('VIS=6'):
  d=parse_record(line)
  if d:d['time_ms']=last;vs.append(d)
faults=[];prev=0
for d in ds:
 if d['fault'] and not prev:
  t=d['time_ms'];faults.append({'time':t,'fault':d['fault'],'diag_before':[x for x in ds if t-1500<=x['time_ms']<=t+100],'vis_before':[x for x in vs if t-1500<=x['time_ms']<=t+250]})
 prev=d['fault']
groups=[];g=[]
for d in ds+[dict(flags=0)]:
 if d['flags']&4:g.append(d)
 elif g:groups.append(g);g=[]
sessions=[];stops=[]
for k,g in enumerate(groups):
 frames=list({d['frame_ms']:d for d in g if d['flags']&8}.values())
 sess={'session':k+1,'start':g[0]['time_ms'],'end':g[-1]['time_ms'],'duration':g[-1]['time_ms']-g[0]['time_ms'],'phase_counts':dict(collections.Counter((d['flags']>>9)&3 for d in frames)),'final':g[-1]}
 sessions.append(sess)
 chunk=[]
 def emit():
  if len(chunk)>1 and chunk[-1]['time_ms']-chunk[0]['time_ms']>=1500:
   stops.append({'session':k+1,'start':chunk[0]['time_ms'],'end':chunk[-1]['time_ms'],'duration':chunk[-1]['time_ms']-chunk[0]['time_ms'],'error':[min(d['x']-d['center'] for d in chunk),max(d['x']-d['center'] for d in chunk)],'P':[min(d['position'] for d in chunk),max(d['position'] for d in chunk)],'ref':[min(d['reference_q8']/256 for d in chunk),max(d['reference_q8']/256 for d in chunk)],'phases':dict(collections.Counter((d['flags']>>9)&3 for d in chunk)),'Hz':dict(collections.Counter(d['frequency_hz'] for d in chunk)),'speedmax':max(abs(d['velocity_q4'])/16 for d in chunk)})
 for d in frames:
  if abs(d['x']-d['center'])<=35 or (chunk and max(max(x['x'] for x in chunk),d['x'])-min(min(x['x'] for x in chunk),d['x'])>6):emit();chunk=[]
  if abs(d['x']-d['center'])>35:chunk.append(d)
 emit()
report={'sessions':sessions,'stops':stops,'fault_events':faults}
out=R/'evidence/precise4_measurement';out.mkdir(exist_ok=True)
(out/'analysis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'sessions':sessions,'stops':stops,'faults':[{'time':x['time'],'fault':x['fault'],'VIS':[{k:r[k] for k in ['time_ms','BX','C','P','MT','MC','MS','SP','F','AR','TS']} for r in x['vis_before']]} for x in faults]},indent=2))
