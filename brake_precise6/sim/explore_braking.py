"""Independent approximate plant exploration; actual RTL regression is authoritative."""
import math,json,statistics
from pathlib import Path
def speed_cap(d,linear=2):
 if d<=64:return linear*d
 if d<=256:return 128+(d-64)*.5
 return min(400,224+(d-256)*.25)
def simulate(b=-10,initial=300,initial_v=0,kind='new',kv=.15625,base=.08,span_time=.005,linear=2,noise_amp=0):
 dt=.001;x=float(initial);v=float(initial_v);p=0.;actual=0.;ref=0.;prev_ref=0.;net=0;spent=0;phase=0.;freq=0.;desired=0.;offset=0.;last_step=-1.;pause_until=0.;next_frame=.033;last_frame=0.;prev_x=x;vest=0.;xest=x;first=True;moving=False;quiet=0.;integral=0.;tail=[];trace=[];cross=None;overshoot=0.;settled=None;total=0;checkpoints=0;maxspeed=0.;minx=x;maxx=x;guard=None
 maxrate=200 if kind=='new' else 100;slew=200 if kind=='new' else 102;lim=60 if kind=='new' else 48
 history=[0.]*20;encq=[];prev_sign=x
 center_window=[x]*4;last_dir=0
 for i in range(18000):
  t=i*dt
  while encq and encq[0][0]<=t:p=encq.pop(0)[1]
  if t>=next_frame:
   measured=float(round(x+noise_amp*math.sin(t*71)));elapsed=t-last_frame;dx=measured-prev_x
   if kind=='new':vest=0. if first or abs(dx)>128 else .5*vest+.5*dx/elapsed
   else:
    prediction=xest+vest*elapsed;residual=measured-prediction;xest=measured if first or abs(residual)>128 else prediction+.5*residual
    vest=0. if first or abs(residual)>128 else vest+residual/16/elapsed
   first=False;prev_x=measured;last_frame=t;next_frame+=.033
   center_window=(center_window+[measured])[-4:]
   if kind=='new' and abs(measured)<=3 and max(center_window)-min(center_window)<=4:vest=0.
   if abs(measured)<240 and abs(vest)<30 and abs(desired)<lim-.1:integral=max(-4,min(4,integral+measured*.002*elapsed))
   if kind=='new':
    toward=measured*vest<0;sgn=1 if vest>=0 else -1;span=max(0,lim-sgn*p)
    predicted=measured+vest*(base+span*span_time)
    d=max(0,predicted*(1 if measured>=0 else -1)) if toward else abs(measured)
    goal=-(1 if measured>=0 else -1)*speed_cap(d,linear)
    if abs(measured)<=3 and abs(vest)<=8:goal=0.
    correction=kv*((0 if abs(vest)<3 else vest)-goal)+integral
   else:correction=(0 if abs(measured)<=3 else .2*(measured+vest*.02))+(0 if abs(vest)<3 else .15625*vest)+integral
   desired=max(-60,min(60,max(-lim,min(lim,correction))))
  if i%5==0:
   if t>=pause_until:
    ref+=max(-slew*.005,min(slew*.005,desired-ref))
   dr=(ref-prev_ref)/.005;prev_ref=ref
   if t-last_step>=.020:offset=p-net*1.28
   predicted=net*1.28+offset if t-last_step<.020 else p;err=ref-predicted
   if abs(err)<=.5:freq=0.;moving=False
   elif abs(err)>.75 or moving:
    freq=err*32+dr*.78125;moving=True
    freq=0. if abs(freq)<5 or freq*err<=0 else math.copysign(min(maxrate,max(20,abs(freq))),freq)
   else:freq=0.
  if t<pause_until:freq=0.
  if kind=='new' and freq and (1 if freq>0 else -1)!=last_dir and t-last_step<.020:freq=0.
  phase=min(1.,phase+abs(freq)*dt) if freq else 0.
  if phase>=1 and t-last_step>=.005-1e-9:
   sign=1 if freq>0 else -1
   net+=sign;spent+=1;total+=1;last_step=t;last_dir=sign;phase=0.;actual=net*1.28;encq.append((t+.012,math.trunc(actual)))
   if abs(net)>64 or abs(actual)>64:guard='hard limit';break
   if spent>=48:
    pause_until=t+.045;spent=0;checkpoints+=1
  if i>0 and abs(t-pause_until)<.0011:ref=p;prev_ref=p;offset=p-net*1.28
  history.append(actual);angle=history.pop(0);a=b*angle-.2*v;v+=a*dt;x+=v*dt
  minx=min(minx,x);maxx=max(maxx,x);maxspeed=max(maxspeed,abs(v))
  if initial and x*initial<0:overshoot=max(overshoot,abs(x))
  if abs(x)<=10 and abs(v)<=15:
   if settled is None:settled=t
  else:settled=None
  if t>=8:tail.append(x*x)
  if i%20==0:trace.append((t,x,v,p,ref,vest,desired,freq))
  if abs(x)>1800:guard='escaped';break
 return dict(b=b,initial=initial,initial_v=initial_v,kind=kind,kv=kv,base=base,span_time=span_time,settled=settled,overshoot=overshoot,rms=math.sqrt(statistics.mean(tail)) if tail else 999,guard=guard,total=total,checkpoints=checkpoints,peak_speed=maxspeed,range=[minx,maxx]),trace
if __name__=='__main__':
 cases=[(-5,100,0),(-10,-100,0),(-20,100,0),(-10,400,-400),(-20,400,-800),(-5,400,-200)]
 passed=[]
 for kv in [.09375,.125,.15625,.1875,.25]:
  for base in [.04,.08,.12]:
   for st in [.0025,.005]:
    rows=[simulate(b,x,v,kv=kv,base=base,span_time=st)[0] for b,x,v in cases]
    if all(not q['guard'] and q['settled'] is not None for q in rows):passed.append((max(q['settled'] for q in rows)+.01*sum(q['overshoot'] for q in rows),kv,base,st,rows))
 passed.sort(key=lambda q:q[0]);root=Path(__file__).resolve().parent
 (root/'results/braking_search.json').write_text(json.dumps({'assumed_plants_only':True,'candidates_passed':len(passed),'best':passed[:5],'old':[simulate(b,x,v,kind='old')[0] for b,x,v in cases]},indent=2),encoding='utf-8')
 for q in passed[:5]:print(q[:4],[(round(z['settled'],2),round(z['overshoot'],1),round(z['rms'],1)) for z in q[4]])
 print('OLD',[(q[0]['guard'],q[0]['settled'],round(q[0]['overshoot'],1)) for q in [simulate(b,x,v,kind='old') for b,x,v in cases]])
