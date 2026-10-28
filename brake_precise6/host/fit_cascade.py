"""Fit guarded ball/beam calibration and choose bounded gains; no hardware IO."""
from pathlib import Path
import argparse,json,math,statistics,sys,bisect
from cascade_protocol import parse_diag,decode_config,DEFAULT,encode_config

def solve(a,b):
 n=len(b);m=[list(map(float,a[i]))+[float(b[i])] for i in range(n)]
 for col in range(n):
  p=max(range(col,n),key=lambda j:abs(m[j][col]))
  if abs(m[p][col])<1e-10:raise ValueError('Calibration is not sufficiently excited')
  m[col],m[p]=m[p],m[col];v=m[col][col];m[col]=[x/v for x in m[col]]
  for j in range(n):
   if j!=col:
    v=m[j][col];m[j]=[x-v*y for x,y in zip(m[j],m[col])]
 return [m[i][-1] for i in range(n)]
def least_squares(x,y,weights=None):
 weights=weights or [1.0]*len(y);n=len(x[0]);a=[[0.0]*n for _ in range(n)];b=[0.0]*n
 for row,value,w in zip(x,y,weights):
  for i in range(n):
   b[i]+=w*row[i]*value
   for j in range(n):a[i][j]+=w*row[i]*row[j]
 return solve(a,b)
def robust_fit(x,y):
 p=least_squares(x,y)
 for _ in range(6):
  residual=[a-sum(v*q for v,q in zip(row,p)) for row,a in zip(x,y)]
  scale=max(0.01,statistics.median(map(abs,residual))*1.4826)
  w=[min(1.0,1.5*scale/max(abs(e),1e-9)) for e in residual];p=least_squares(x,y,w)
 return p

def quality(points,p):
 y=[q['a'] for q in points];mean=statistics.mean(y);den=sum((v-mean)**2 for v in y)
 ss=sum((q['a']-(p[0]*q['p']+p[1]-p[2]*q['v']))**2 for q in points)
 return 1-ss/max(den,1e-9)
def interpolate(ts,ys,t):
 k=bisect.bisect_left(ts,t)
 if k<=0:return ys[0]
 if k>=len(ts):return ys[-1]
 f=(t-ts[k-1])/max(ts[k]-ts[k-1],1e-9)
 return ys[k-1]*(1-f)+ys[k]*f

def position_basis(rows,drag,delay):
 # One continuous finite profile: do not invent independent velocity resets per cycle.
 ts=[r['time_ms']/1000 for r in rows];ps=[r['position']-r['neutral'] for r in rows]
 seen=set();data=[];cycle=0;previous=rows[0]['cal_phase']
 for r in rows:
  if previous==4 and r['cal_phase']==0:cycle+=1
  previous=r['cal_phase']
  if r['frame_ms'] in seen:continue
  seen.add(r['frame_ms']);data.append((r['frame_ms']/1000,float(r['x']),cycle))
 points=[];t0=data[0][0];last=t0;vp=0.;xp=0.
 for t,x,cycle in data:
  dt=t-last
  if dt<0 or dt>.15:raise ValueError('Calibration has a long missing-frame interval')
  pin=(interpolate(ts,ps,last-delay)+interpolate(ts,ps,t-delay))*.5
  if drag:
   fade=math.exp(-drag*dt);g=(1-fade)/drag
   xp+=vp*g+pin*(dt-g)/drag;vp=vp*fade+pin*g
   elapsed=t-t0;gv=(1-math.exp(-drag*elapsed))/drag;gd=(elapsed-gv)/drag
  else:
   xp+=vp*dt+.5*pin*dt*dt;vp+=pin*dt;gv=t-t0;gd=.5*gv*gv
  points.append({'cycle':cycle,'x':x,'p':xp,'d':gd,'g':gv});last=t
 return points

def fit_basis(points,cycles):
 part=[q for q in points if q['cycle'] in cycles]
 return robust_fit([[q['p'],q['d'],1,q['g']] for q in part],[q['x'] for q in part])

def position_quality(points,parameters):
 err=sum((q['x']-(parameters[0]*q['p']+parameters[1]*q['d']+parameters[2]+parameters[3]*q['g']))**2 for q in points)
 matrix=[[1,q['g'],q['d']] for q in points];values=[q['x'] for q in points];p=least_squares(matrix,values)
 base=sum((v-sum(z*w for z,w in zip(row,p)))**2 for row,v in zip(matrix,values))
 return 1-err/max(base,1e-9)

def identify(rows):
 best=None
 for drag in [0.,.1,.2,.3,.5,.75,1.,2.,4.]:
  for delay in range(0,121,2):
   try:
    points=position_basis(rows,drag,delay/1000);cycles=sorted({q['cycle'] for q in points})
    if cycles!=[0,1,2]:continue
    scores=[]
    for held in cycles:
     p=fit_basis(points,[c for c in cycles if c!=held]);scores.append(position_quality([q for q in points if q['cycle']==held],p))
    parameters=fit_basis(points,cycles);b,d=parameters[:2]
    if abs(b)<.05:continue
    score=min(scores)
    if best is None or score>best[0]:best=(score,parameters,drag,delay,scores,points)
   except (ValueError,OverflowError,ZeroDivisionError):continue
 if best is None:raise ValueError('Three excited,complete calibration cycles could not be fitted')
 score,parameters,drag,delay,scores,points=best;b,d=parameters[:2]
 if score<.70:raise ValueError(f'Continuous-position cross-validation R2={score:.3f}<0.70; repeat untouched calibration or use8 counts')
 signs=[fit_basis(points,[c])[0] for c in [0,1,2]]
 if any(q*b<=0 or not .5<=abs(q/b)<=2 for q in signs):raise ValueError('Tilt gain/direction is not repeatable; inspect transmission/beam-angle feedback')
 if abs(parameters[3])>30:raise ValueError('Ball was moving too fast at calibration start; repeat from a stationary center')
 return {'center':rows[0]['center'],'b':b,'d':d,'c':drag,'delay_ms':delay,'neutral':rows[0]['neutral'],
 'R2_holdout':score,'R2_each_cycle':scores,'cycle_b':signs,'initial_velocity':parameters[3],
 'method':'continuous integrated position model;leave-one-cycle-out validation;no per-cycle state resets','units':'x UART pixels;P encoder counts;t seconds'}

def simulate(model,params,scale=1.0,extra_delay=0.0,initial=100.0,frame_dt=.033,backlash=0.0):
 dt=.005;b=model['b']*scale;c=model['c'];d=model['d'];neutral=model['neutral'];limit=32
 x=initial;v=0.;p=neutral;physical=neutral;reference=float(neutral);prev_ref=reference;vel_est=0.;prev_x=x;position_est=x
 kp=params['kp']/4096;kv=params['kv']/256;ki=params['ki']/65536;bias=params['bias']/256
 feedforward=params['feedforward']/256;maximum=params['max_hz'];slew=params['slew_rate'];polarity=-1 if params['polarity'] else 1
 prediction_offset=0.;integral=0.;next_frame=frame_dt;last_frame=0.;desired=neutral;phase=0.;net_pulses=0;spent=0;last_step=-1.;stable_idle=0.;peak=abs(x);tail=[];settled=None
 angle_history=[neutral]*max(1,int((model['delay_ms']/1000+extra_delay)/dt)+1);encoder_queue=[];moving=False
 for i in range(3000):
  t=i*dt
  while encoder_queue and encoder_queue[0][0]<=t:p=encoder_queue.pop(0)[1]
  if t>=next_frame:
   noise=.15*math.sin(t*17);measured=float(round(x+noise));elapsed=t-last_frame;predicted_position=position_est+vel_est*elapsed;residual=measured-predicted_position
   position_est=measured if abs(residual)>32 else predicted_position+.5*residual;vel_est=0. if abs(residual)>32 else vel_est+residual/16/max(elapsed,dt);prev_x=measured;last_frame=t;next_frame+=frame_dt
   predicted=measured+vel_est*params['delay_ms']/1000
   if abs(measured)<240 and abs(vel_est)<30 and abs(desired-neutral)<limit-.1:integral=max(-4,min(4,integral+polarity*measured*ki*elapsed))
   correction=polarity*((0 if abs(measured)<=5 else kp*predicted)+(0 if abs(vel_est)<3 else kv*vel_est))+max(-8,min(8,bias+integral))
   desired=max(-60,min(60,neutral+max(-limit,min(limit,correction))))
  reference+=max(-slew*dt,min(slew*dt,desired-reference));dr=(reference-prev_ref)/dt;prev_ref=reference
  if t-last_step>=.020:prediction_offset=p-(neutral+net_pulses*1.28)
  predicted=neutral+net_pulses*1.28+prediction_offset if t-last_step<.020 else p
  error=reference-predicted
  if abs(error)<=.5:frequency=0.;moving=False
  elif abs(error)>.75 or moving:
   frequency=error*params['inner_kp']/256+dr*feedforward;moving=True
   frequency=0. if abs(frequency)<5 or frequency*error<=0 else math.copysign(min(maximum,max(20,abs(frequency))),frequency)
  else:frequency=0.
  phase=min(1.0,phase+abs(frequency)*dt) if frequency else 0.
  if phase>=1.0 and t-last_step>=.005-1e-9:
   sign=1 if frequency>0 else -1
   if spent>=64 or abs(net_pulses+sign)>64:simulate.last_failure='pulse/net budget';return None
   phase=0.;net_pulses+=sign;spent+=1;last_step=t;stable_idle=0.
   physical=neutral+net_pulses*1.28
   if abs(physical)>64:simulate.last_failure='feedback range';return None
   encoder_queue.append((t+.012,neutral+int(net_pulses*1.28)))
  if t-last_step>=.12 and abs(error)<=1 and frequency==0:spent=0
  elif spent and t-last_step>5:simulate.last_failure='active timeout';return None
  # Bounded backlash is tested as uncertain angle transmission, not claimed measured.
  angle_history.append(physical);angle=angle_history.pop(0)
  if backlash:angle=neutral+math.copysign(max(0,abs(angle-neutral)-backlash),angle-neutral)
  a=b*(angle-neutral)+d-c*v;v+=a*dt;x+=v*dt;peak=max(peak,abs(x))
  if abs(x)>max(350,abs(initial)*3):simulate.last_failure='ball escaped';return None
  if abs(x)<=10 and abs(v)<=15:
   if settled is None:settled=t
  else:settled=None
  if t>=5:tail.append((x,v))
 if not tail or any(abs(a)>10 or abs(z)>15 for a,z in tail):simulate.last_failure='settling band';return None
 return {'peak':peak,'rms':math.sqrt(statistics.mean(a*a for a,v in tail)),'pulses_net':net_pulses}

def choose_gains(model,max_hz):
 accepted=[];failures={}
 for wn in [.75,1.,1.5,2.,2.5,3.,3.5,4.,5.,6.]:
  for zeta in [.9,1.1,1.3,1.5,1.8,2.,2.5,3.]:
   p=DEFAULT|{'selection':1,'max_hz':max_hz,'amplitude':4,'polarity':int(model['b']>0),'delay_ms':min(120,max(0,round(model['delay_ms']))),
    'kp':round(wn*wn/abs(model['b'])*4096),'kv':round(max(0,2*zeta*wn-model['c'])/abs(model['b'])*256),
    'ki':round(min(.002,wn*wn/abs(model['b'])/50)*65536),'bias':round(max(-8,min(8,-model['d']/model['b']))*256),
    'slew_rate':min(256,max(8,round(max_hz*1.28*.8)))}
   if p['kp']>16384 or p['kv']>2048:continue
   cases=[]
   for scale,delay,initial,fd,backlash in [(1,0,100,.033,0),(.7,.02,100,.033,0),(1.3,.02,-100,.040,0),(1,.04,-100,.025,0),(1,0,60,.033,1)]:
    q=simulate(model,p,scale,delay,initial,fd,backlash)
    if q is None:
     key=(len(cases),simulate.last_failure);failures[str(key)]=failures.get(str(key),0)+1;break
    cases.append(q)
   if len(cases)==5:accepted.append((max(q['rms'] for q in cases)+.01*max(q['peak'] for q in cases),p,wn,zeta,cases))
 choose_gains.debug_failures=failures
 if not accepted:return None
 best=min(accepted,key=lambda z:z[0]);return {'parameters':best[1],'wn':best[2],'zeta':best[3],'robust_model_checks':best[4],'candidate_count':len(accepted)}

def analyze(log):
 rows=[];bad=0;resets=0
 for line in log.read_text(encoding='utf-8-sig',errors='replace').splitlines():
  q=parse_diag(line)
  if q:
   if rows and q['time_ms']<rows[-1]['time_ms']:rows=[];resets+=1
   rows.append(q)
  elif line.startswith('D1'):bad+=1
 if not rows:raise ValueError('No valid D1 diagnostic records; use the cascade firmware/panel')
 metadata=log.with_suffix('.commands.jsonl');configs={}
 if metadata.exists():
  for line in metadata.read_text(encoding='utf-8-sig').splitlines():
   try:q=decode_config(json.loads(line)['packet'])
   except (KeyError,ValueError,TypeError):q=None
   if q:configs[q['sequence']]=q
 motor_rates=[]
 for q in rows:
  cfg=configs.get(q['sequence'])
  if q['selection']==2 and q['cal_status']==2 and q['fault']==0 and cfg:motor_rates.append(cfg['max_hz'])
 if not motor_rates:raise ValueError('No completed motor calibration with matching command metadata; run50Hz first')
 seq=next((q['sequence'] for q in reversed(rows) if q['selection']==3 and q['cal_status'] in (1,2,4)),None)
 if seq is None or not any(q['sequence']==seq and q['selection']==3 and q['cal_status']==2 and q['fault']==0 for q in rows):raise ValueError('Latest ball calibration did not complete; an aborted profile is not usable')
 use=[q for q in rows if q['sequence']==seq and q['selection']==3 and q['cal_status']==1 and q['fault']==0 and q['flags']&14==14 and not q['flags']&16]
 if len(use)<60:raise ValueError('Fewer than60 valid diagnostic samples in latest completed ball profile')
 if len({q['neutral'] for q in use})!=1:raise ValueError('Neutral changed during calibration')
 if sum(q['position']-q['neutral']>=2 for q in use)<8 or sum(q['position']-q['neutral']<=-2 for q in use)<8:raise ValueError('Both tilt directions need enough measured excursion; use8-count profile if4 is too weak')
 model=identify(use)
 qualified=[q for hz in sorted(set(motor_rates)) if (q:=choose_gains(model,hz))]
 chosen=min(qualified,key=lambda q:max(x['rms'] for x in q['robust_model_checks'])) if qualified else None
 if not chosen:return {'status':'MODEL_FIT_BUT_NO_SAFE_PARAMETERS','model':model,'reason':'No tested bounded gains met5s recovery/10s hold across model uncertainty; do not apply an unqualified profile','physical_pass':False}
 return {'status':'ACCEPTED_PENDING_PHYSICAL_VALIDATION','model':model,**chosen,'C_packet_example':encode_config(chosen['parameters']),
  'diagnostics':{'valid_records':len(rows),'bad_D1_lines':bad,'hardware_resets':resets,'ball_sequence':seq},
  'verified_control_context':{'L':32,'DZ':5},'camera_context':camera_context(log),'physical_pass':False,'limitations':'Fitted motor angle is an indirect beam-angle proxy; model simulation does not certify physical centering. Apply while stopped,then physicalK2.'}

def camera_context(log):
 sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
 from decode_serial import parse_record
 records=[q for line in log.read_text(encoding='utf-8-sig',errors='replace').splitlines() if (q:=parse_record(line))]
 return {k:records[-1][k] for k in ['AE','AG','RL','RT','RR','RB']} if records else None

def main():
 sys.stdout.reconfigure(encoding='utf-8');ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('log',type=Path);ap.add_argument('--output',type=Path);ap.add_argument('--quiet',action='store_true');a=ap.parse_args()
 try:r=analyze(a.log)
 except (ValueError,AssertionError,ZeroDivisionError) as e:r={'status':'REJECTED','reason':str(e),'physical_pass':False}
 out=a.output or a.log.with_suffix('.cascade.json');out.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
 print(r['status'] if a.quiet else json.dumps(r,ensure_ascii=False,indent=2));return 0 if r['status']=='ACCEPTED_PENDING_PHYSICAL_VALIDATION' else 2
if __name__=='__main__':raise SystemExit(main())
