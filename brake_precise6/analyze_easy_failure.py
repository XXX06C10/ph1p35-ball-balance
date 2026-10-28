from pathlib import Path
import sys,json,collections,statistics
r=Path(__file__).resolve().parent;sys.path.insert(0,str(r/'host'))
from cascade_protocol import parse_diag
from decode_serial import parse_record
result=[]
for p in sorted((r/'host/logs').glob('20261024_213*.txt')):
 lines=p.read_text(encoding='utf-8-sig').splitlines();ds=[q for l in lines if(q:=parse_diag(l))];vs=[q for l in lines if(q:=parse_record(l))]
 runs=[];run=[]
 for d in ds:
  if d['flags']&4:run.append(d)
  elif run:runs.append(run);run=[]
 if run:runs.append(run)
 item={'file':p.name,'first_fault':next((q for q in vs if q['F']),None),'runs':[]}
 for run in runs:
  start=run[0]['time_ms'];picked=[];last=-1
  for q in run:
   t=(q['time_ms']-start)//250
   if t!=last:
    picked.append({k:q[k] for k in ['time_ms','x','center','position','reference_q8','velocity_q4','frequency_hz','spent','command_position','neutral']});last=t
  item['runs'].append({'start_ms':start,'duration_ms':run[-1]['time_ms']-start,'samples':len(run),'P_range':[min(q['position'] for q in run),max(q['position'] for q in run)],'trace_250ms':picked})
 result.append(item)
(r/'easy_failure_analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result[-1],ensure_ascii=False,indent=2))
