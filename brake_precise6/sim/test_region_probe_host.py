from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'host'))
from region_probe import parse_event,encode_event,analyze,summary
from cascade_protocol import encode_diag
from fit_cascade import position_basis

class ProbeHost(unittest.TestCase):
 def test_event_roundtrip(self):
  e={'sequence':65535,'time_ms':5000,'events':7,'position':-31,'command_position':-24,'state':6,'pending':1,'commands':-1,'delta':-2,'diagnostic_flags':32,'phase':11,'status':1,'selection':1,'reason':0}
  line=encode_event(e);self.assertEqual(len(line),58);self.assertEqual(parse_event(line),e)
  self.assertIsNone(parse_event(line[:10]+'F'+line[11:]));self.assertIsNone(parse_event(line[:-5]))
 def test_loss_and_overflow_rejected(self):
  r=analyze(encode_event({'sequence':1})+encode_event({'sequence':3,'diagnostic_flags':128}))
  self.assertEqual(r['status'],'INVALID');self.assertTrue(any('序号' in s for s in r['errors']));self.assertTrue(any('溢出' in s for s in r['errors']));self.assertIsNone(r['parameters'])
 def test_no_motion_no_parameters(self):
  self.assertIsNone(analyze('VIS=5\n')['parameters'])
  self.assertEqual(analyze('')['status'],'INVALID')
 def test_real_uart_log(self):
  log=Path(__file__).parent/'results/tb_region_probe.log'
  if not log.exists():self.skipTest('run RTL integration first')
  raw=log.read_bytes();text=raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8-sig')
  if 'REGION_PROBE_ALL_PASS' not in text:self.skipTest('integration is still running')
  lines=[s.split(' ',1)[1] for s in text.splitlines() if s.startswith('PROBE_WIRE ')]
  es=[parse_event(s) for s in lines if s.startswith('E1')];self.assertTrue(len(es)>100);self.assertTrue(all(e is not None for e in es))
  self.assertTrue(all((b['sequence']-a['sequence'])%65536==1 for a,b in zip(es,es[1:])))
 def test_qualified_measurement_only(self):
  # A continuous measured trajectory, three alternating pairs. Identification
  # validates held-out cycles; no random/noisy assumed-plant controller acceptance.
  events=[];rows=[];modelrows=[];seq=0;t=0;fr=0
  def event(selection,status,phase=0,ev=8,pos=0,mc=0):
   nonlocal seq
   events.append((t,encode_event({'sequence':seq,'time_ms':t,'events':ev,'selection':selection,'status':status,'phase':phase,'position':pos,'command_position':mc})));seq+=1
  for kind in (2,3):
   event(kind,0);event(kind,1)
   for i in range(501):
    t+=20;fr+=1;rows.append((t,encode_diag({'time_ms':t,'frame_ms':t,'frame_number':fr,'selection':kind,'cal_status':1,'flags':8,'x':960,'center':960})))
   event(kind,2);t+=100
  event(1,0);event(1,1);x=960.;v=0.;p=0;command=0
  for leg in range(12):
   sign=1 if leg in (0,6,8) else (-1 if leg in (2,4,10) else 0);dest=8*sign
   event(1,1,leg);remaining=abs(dest-p);direction=1 if dest>p else -1
   duration=1000
   for ms in range(0,duration,20):
    if remaining and ms%80==0:
     command+=direction;event(1,1,leg,1,p,command);t+=12;p+=direction;remaining-=1;event(1,1,leg,2,p,command);t-=12
    # Integrated physical response with small, nonzero damping.
    v+=(-4*p-.3*v)*.02;x+=v*.02;t+=20;fr+=1
    modelrows.append({'time_ms':t,'frame_ms':t,'frame_number':fr,'selection':1,'cal_status':1,'cal_phase':leg,'flags':8,'x':0,'center':960,'position':p,'neutral':0})
  event(1,2,11)
  basis=position_basis([dict(r,cal_phase=(4 if r['cal_phase']%4==3 else r['cal_phase']%4)) for r in modelrows],0.,0.)
  for r,q in zip(modelrows,basis):r['x']=round(960-4*q['p']);rows.append((r['time_ms'],encode_diag(r)))
  text=''.join(s for _,s in sorted(events+rows,key=lambda q:q[0]));r=analyze(text)
  self.assertEqual(r['status'],'MEASUREMENT_QUALIFIED_PENDING_REGION_DESIGN',r['errors']);self.assertGreaterEqual(r['ball_response']['R2_holdout'],.70);self.assertIsNone(r['parameters'])
  # Missing an event must invalidate the same otherwise identifiable data.
  r=analyze(text.replace(events[10][1],'',1));self.assertEqual(r['status'],'INVALID')

if __name__=='__main__':unittest.main()
