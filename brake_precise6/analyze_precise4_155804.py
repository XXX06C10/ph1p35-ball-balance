from pathlib import Path
import sys,json,hashlib,collections
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R/'host'))
from asym_protocol import parse_diag,parse_record
p=R/'host/logs/20261027_155804_861.txt';ds=[];vs=[];bad=0;last=0
for line in p.read_text().splitlines():
 if line.startswith('D2'):
  d=parse_diag(line)
  if d:ds.append(d);last=d['time_ms']
  else:bad+=1
 elif line.startswith('VIS=6'):
  v=parse_record(line)
  if v:v['time_ms']=last;vs.append(v)
windows=[]
for a,b,label in [(57460,60620,'successful hold'),(116000,121120,'escape24 reached but ball parked'),(210000,215999,'parked68 with subcount target'),(227000,229999,'parked325 with normal speed target')]:
 rows=[d for d in ds if a<=d['time_ms']<=b]
 windows.append(dict(label=label,start_ms=a,end_ms=b,samples=len(rows),x_range=[min(d['x'] for d in rows),max(d['x'] for d in rows)],error_range=[min(d['x']-d['center'] for d in rows),max(d['x']-d['center'] for d in rows)],position_range=[min(d['position'] for d in rows),max(d['position'] for d in rows)],reference_range=[min(d['reference_q8']/256 for d in rows),max(d['reference_q8']/256 for d in rows)],faults=sorted(set(d['fault'] for d in rows)),frequency_nonzero=sum(d['frequency_hz']!=0 for d in rows)))
report=dict(source=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),diag_count=len(ds),vis_count=len(vs),bad_diag_count=bad,all_faults=sorted(set(d['fault'] for d in ds)),centers=sorted(set(d['center'] for d in ds)),windows=windows,firmware_identity='No unique build id in UART; analyzed against precise4 source; no inferred physical success rate')
out=R/'evidence/precise5_measurement';out.mkdir(exist_ok=True)
(out/'analysis_155804.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report,ensure_ascii=False,indent=2))
