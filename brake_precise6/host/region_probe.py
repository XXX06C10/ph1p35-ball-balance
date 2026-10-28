"""Read-only analysis of E1/D1 measurement logs. Never issues motor commands."""
from pathlib import Path
import argparse,bisect,json,statistics,sys
from cascade_protocol import parse_diag
from fit_cascade import identify
FIELDS=[('sequence',2),('time_ms',4),('events',1),('position',4),('command_position',4),('state',1),('pending',1),('commands',2),('delta',2),('diagnostic_flags',1),('phase',1),('status',1),('selection',1),('reason',1)]
def parse_event(line):
 try:
  line=line.strip();assert len(line)==56 and line.startswith('E1')
  raw=bytes.fromhex(line[2:]);check=0
  for b in raw:check^=b
  assert check==0
  d={};i=0
  for key,n in FIELDS:
   d[key]=int.from_bytes(raw[i:i+n],'big',signed=key in ('position','command_position','commands','delta'));i+=n
  assert i==26 and d['selection']<=3 and d['phase']<=11 and d['status'] in (0,1,2,4)
  return d
 except (ValueError,AssertionError):return None
def encode_event(d):
 raw=b''.join((d.get(k,0)&((1<<(n*8))-1)).to_bytes(n,'big') for k,n in FIELDS);xor=0
 for v in raw:xor^=v
 return 'E1'+(raw+bytes([xor])).hex().upper()+'\r\n'
def summary(rows):
 unique={r['frame_ms']:r for r in rows};r=list(unique.values());good=[q for q in r if q['flags']&8]
 xs=[q['x'] for q in good];ps=[q['position'] for q in r]
 expected=len(r)
 if len(r)>1:
  expected=1+sum((b['frame_number']-a['frame_number'])%65536 for a,b in zip(r,r[1:]))
 # A missing observation cannot be counted as a valid detection. Conservative
 # coverage prevents a partially received camera trajectory from qualifying.
 result={'frames':len(r),'expected_frames':expected,'frame_coverage':len(r)/max(1,expected),
         'valid_fraction':len(good)/max(1,expected),'observed_valid_fraction':len(good)/max(1,len(r))}
 if xs:result.update(x_std_px=statistics.pstdev(xs),x_peak_to_peak_px=max(xs)-min(xs))
 if ps:result.update(encoder_peak_to_peak=max(ps)-min(ps))
 if len(good)>2:
  ts=[q['frame_ms']/1000 for q in good];mt=statistics.mean(ts);mx=statistics.mean(xs)
  result['drift_px_s']=sum((t-mt)*(x-mx) for t,x in zip(ts,xs))/max(1e-9,sum((t-mt)**2 for t in ts))
 return result
def analyze(text):
 events=[];rows=[];errors=[]
 for line in text.splitlines():
  if line.startswith('E1'):
   e=parse_event(line)
   if e is None:errors.append('E1格式或XOR错误')
   else:events.append(e)
  elif line.startswith('D1'):
   r=parse_diag(line)
   if r is None:errors.append('D1格式或XOR错误')
   else:rows.append(r)
 if not events:errors.append('缺少E1事件：请使用region_probe.bit')
 if any((b['sequence']-a['sequence'])%65536!=1 for a,b in zip(events,events[1:])):errors.append('事件序号丢失或板卡中途重启')
 if any(e['diagnostic_flags']&128 for e in events):errors.append('FPGA事件FIFO溢出，整轮无效')
 if any(e['diagnostic_flags']&15 for e in events):errors.append('存在锁存故障，不能据此生成参数')
 if any(e['status']==4 for e in events):errors.append('本日志包含中止测量，请重新连接并从静态观察开始')
 groups={k:[r for r in rows if r['selection']==k and r['cal_status']==1] for k in (2,3,1)}
 completed={k:sum(e['status']==2 and e['selection']==k and (i==0 or events[i-1]['status']!=2) for i,e in enumerate(events)) for k in groups}
 result={'status':'INVALID','parameters':None,'errors':errors,'static_noise':summary(groups[2]),'neutral_drift':summary(groups[3]),'motor_response':{},'ball_response':{},'completion_counts':completed}
 for k,label in ((2,'静态'),(3,'中立'),(1,'往返')):
  if completed[k]!=1:errors.append(label+'测试须恰好完成一次；重新测试请新建日志')
  if result[{'2':'static_noise','3':'neutral_drift'}.get(str(k),'ball_response')].get('valid_fraction',summary(groups[k])['valid_fraction'])<.95:errors.append(label+'有效识别率低于95%')
 if groups[2] and groups[2][-1]['time_ms']-groups[2][0]['time_ms']<9700:errors.append('静态观察不足10秒')
 if groups[3] and groups[3][-1]['time_ms']-groups[3][0]['time_ms']<9700:errors.append('中立观察不足10秒')
 # Match the first actual encoder transition after each STEP, before the next STEP.
 motion=[e for e in events if e['selection']==1 and e['status']==1]
 steps=[i for i,e in enumerate(motion) if e['events']&1];latencies=[];first_edges=[]
 for j,i in enumerate(steps):
  end=steps[j+1] if j+1<len(steps) else len(motion)
  later=next((e for e in motion[i+1:end] if e['events']&2),None)
  if later:
   latency=later['time_ms']-motion[i]['time_ms'];latencies.append(latency)
   first_edges.append({'step_ms':motion[i]['time_ms'],'latency_ms':latency,'position_delta':later['position']-motion[i]['position'],'leg':motion[i]['phase']})
 result['motor_response']={'step_count':len(steps),'matched_first_encoder_edges':len(latencies),'latency_ms_median':statistics.median(latencies) if latencies else None,'latency_ms_max':max(latencies) if latencies else None,'resolution_ms':1}
 legs=[]
 for leg in range(12):
  part=[e for e in motion if e['phase']==leg]
  if len(part)>1:
   dp=part[-1]['position']-part[0]['position'];dm=part[-1]['command_position']-part[0]['command_position']
   legs.append({'leg':leg,'position_delta':dp,'pulse_net':dm,'counts_per_pulse':dp/dm if dm else None,'first_edge_delay_ms':next((q['latency_ms'] for q in first_edges if q['leg']==leg),None)})
 result['motor_response'].update(legs=legs,first_edges=first_edges,backlash_note='比较换向腿首个反馈延迟及计数/脉冲比例；单次编码器量化不能直接当作机械回差角。')
 if any(q['counts_per_pulse'] is not None and q['counts_per_pulse']<=0 for q in legs):errors.append('存在电机反馈方向不一致的腿')
 if not latencies or len(latencies)<len(steps)*.95:errors.append('STEP到编码器事件匹配率不足95%')
 active=groups[1];phases={r['cal_phase'] for r in active}
 if phases!=set(range(12)):errors.append('三对往返的12条腿数据不完整')
 # Existing continuous integrated model expects four phases per cycle; map only
 # the leg index, preserving frame times, measured position, and velocity continuity.
 fitrows=[dict(r,cal_phase=(4 if r['cal_phase']%4==3 else r['cal_phase']%4)) for r in active]
 if not errors:
  try:
   model=identify(fitrows);result['ball_response']=model;result['status']='MEASUREMENT_QUALIFIED_PENDING_REGION_DESIGN'
  except (ValueError,ArithmeticError) as exc:errors.append(str(exc))
 result['explanation']='仅完成实机测量和质量判定；未生成控制增益，未通过区域保持实板验收。'
 return result
def main():
 p=argparse.ArgumentParser();p.add_argument('log',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
 raw=a.log.read_bytes();text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig',errors='replace')
 r=analyze(text);out=a.output or a.log.with_suffix('.probe.json');out.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(r,ensure_ascii=False,indent=2))
 return 0
if __name__=='__main__':sys.exit(main())
