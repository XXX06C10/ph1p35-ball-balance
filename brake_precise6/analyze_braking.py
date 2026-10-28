from pathlib import Path
import json,sys,statistics,collections
r=Path(__file__).resolve().parent;sys.path.insert(0,str(r/'host'))
from cascade_protocol import parse_diag
from decode_serial import parse_record
result=[]
for p in sorted((r/'host/logs').glob('20261025_12*.txt')):
 lines=p.read_text(encoding='utf-8-sig').splitlines();ds=[q for l in lines if(q:=parse_diag(l))];vs=[q for l in lines if(q:=parse_record(l))]
 runs=[];part=[]
 for d in ds:
  if d['flags']&4:part.append(d)
  elif part:runs.append(part);part=[]
 if part:runs.append(part)
 item={'file':p.name,'VIS_records':len(vs),'faults':dict(collections.Counter(q['F'] for q in vs)),'runs':[]}
 for part in runs:
  t0=part[0]['time_ms'];crossings=[];prev=part[0];seen=set();frames=[]
  for q in part:
   if q['frame_ms'] in seen:continue
   seen.add(q['frame_ms']);frames.append(q)
   if (q['x']-q['center'])*(prev['x']-prev['center'])<0:
    crossings.append({k:q[k] for k in ['time_ms','x','center','velocity_q4','position','reference_q8','frequency_hz','neutral']})
   prev=q
  trace=[];slot=-1
  for q in part:
   k=(q['time_ms']-t0)//500
   if k==slot:continue
   slot=k;trace.append({k:q[k] for k in ['time_ms','x','center','position','reference_q8','frequency_hz','velocity_q4','spent','command_position','neutral']})
  item['runs'].append({'start_ms':t0,'duration_ms':part[-1]['time_ms']-t0,'frame_count':len(frames),'P_range':[min(q['position'] for q in part),max(q['position'] for q in part)],'center_crossings':crossings,'trace_500ms':trace})
 result.append(item)
(r/'braking_log_analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
for q in result:
 print(q['file'],'faults',q['faults'])
 for run in q['runs']:
  print('run',run['duration_ms'],'ms P',run['P_range'],'crossings',len(run['center_crossings']))
  for row in run['center_crossings'][:8]:print(row)
  print('tail',run['trace_500ms'][-5:])
