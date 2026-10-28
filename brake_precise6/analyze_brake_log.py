"""Read-only VIS6/D2 trace statistics; no identification or serial commands."""
from pathlib import Path
import argparse,collections,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'host'))
from asym_protocol import parse_diag,parse_record

def analyze(path):
 rows=[];vis=[];bad=collections.Counter()
 for line in Path(path).read_text(errors='replace').splitlines():
  if line.startswith('D2'):
   r=parse_diag(line)
   if r:rows.append(r)
   else:bad['D2']+=1
  elif line.startswith('VIS=6'):
   r=parse_record(line)
   if r:vis.append(r)
   else:bad['VIS6']+=1
  else:bad['other']+=1
 boots=[];g=[];last=-1
 for r in rows:
  if r['time_ms']<last:boots.append(g);g=[]
  g.append(r);last=r['time_ms']
 if g:boots.append(g)
 sessions=[]
 for boot,data in enumerate(boots):
  g=[]
  for r in data+[{'flags':0}]:
   if r['flags']&4:g.append(r)
   elif g:
    frames=list({r['frame_ms']:r for r in g if r['flags']&8}.values())
    near=[r for r in g if r['flags']&8 and abs(r['x']-r['center'])<=25]
    nz=[r['frequency_hz'] for r in near if r['frequency_hz']]
    fast=[r for r in frames if 15<abs(r['x']-r['center'])<=64 and (r['x']-r['center'])*r['velocity_q4']<0 and abs(r['velocity_q4'])>=960]
    sessions.append({'boot':boot,'start_ms':g[0]['time_ms'],'end_ms':g[-1]['time_ms'],'duration_ms':g[-1]['time_ms']-g[0]['time_ms'],'center':g[0]['center'],'valid_frames':len(frames),'near_nonzero_direction_changes_including_separate_visits':sum(a*b<0 for a,b in zip(nz,nz[1:])),'fast_inward_near_frames':len(fast),'fast_inward_near_peak_command_hz':max([abs(r['frequency_hz']) for r in fast],default=0)})
    g=[]
 return {'status':'OBSERVATIONS_ONLY_NOT_PHYSICAL_IDENTIFICATION','file':str(path),'D2_records':len(rows),'VIS6_records':len(vis),'bad_or_partial_lines':dict(bad),'boots':len(boots),'sessions':sessions,'faults':dict(collections.Counter(r['fault'] for r in rows)),'stop_reason_fault_pairs':{str(k):v for k,v in collections.Counter((r['SR'],r['F']) for r in vis).items()}}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('log');p.add_argument('--output',required=True);a=p.parse_args()
 d=analyze(a.log);Path(a.output).write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(d,indent=2))
