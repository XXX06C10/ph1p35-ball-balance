"""Host acceptance checks use actual UART plus independently synthesized noisy plant data."""
from pathlib import Path
import json,sys,math,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'host'))
from cascade_protocol import DEFAULT,encode_config,decode_config,parse_diag,encode_diag
from fit_cascade import identify,analyze,choose_gains

def synthetic(log,broken=False):
 p=DEFAULT|{'sequence':10,'selection':2,'max_hz':100,'amplitude':16}
 q=DEFAULT|{'sequence':11,'selection':3,'max_hz':50,'amplitude':8}
 meta=[{'packet':encode_config(c)} for c in [p,q]]
 log.with_suffix('.commands.jsonl').write_text('\n'.join(json.dumps(c) for c in meta),encoding='utf-8')
 lines=[encode_diag({'time_ms':1000,'frame_ms':990,'sequence':10,'selection':2,'flags':11,'cal_status':2})]
 x=960.;v=0.;last_x=960;last_frame=2000;rows=[]
 for ms in range(3900):
  local=ms%1300;phase=0 if local<200 else (1 if local<450 else (2 if local<750 else (3 if local<1000 else 4)))
  pos=8 if phase==1 else (-8 if phase==3 else 0)
  b=20 if broken and ms>=2600 else -20
  v+=(b*pos-.2*v)*.001;x+=v*.001
  if ms%33==0:last_x=round(x+.1*math.sin(ms*.23));last_frame=2000+ms
  if ms%20==0:
   row={'time_ms':2000+ms,'frame_ms':last_frame,'sequence':11,'selection':3,'flags':15,'cal_phase':phase,'cal_status':1,
    'x':last_x,'center':960,'position':pos,'reference_q8':pos*256,'neutral':0,'frame_number':ms//33}
   lines.append(encode_diag(row));rows.append(parse_diag(lines[-1]))
 lines.append(encode_diag({'time_ms':5920,'frame_ms':5894,'sequence':11,'selection':3,'flags':11,'cal_phase':4,'cal_status':2,'x':last_x,'center':960}))
 log.write_text(''.join(lines),encoding='utf-8');return rows

class HostTests(unittest.TestCase):
 def test_protocol_bounds(self):
  for field,v in [('max_hz',201),('kp',16385),('kv',2049),('ki',3278),('bias',-2049),('delay_ms',121),('selection',4),('slew_rate',257),('polarity',2)]:
   with self.assertRaises(AssertionError):encode_config(DEFAULT|{field:v})
  p=DEFAULT|{'bias':-2048,'sequence':65535,'polarity':1};self.assertEqual(decode_config(encode_config(p)),p)
  self.assertIsNone(decode_config(encode_config(p).replace('C01','C02',1)))
 def test_actual_uart(self):
  raw=(ROOT/'sim/results/tb_cascade.log').read_bytes();s=raw.decode('utf-16') if raw.startswith(b'\xff\xfe') else raw.decode('utf-8-sig')
  rows=[parse_diag(l.split(' ',1)[1]) for l in s.splitlines() if l.startswith('UART_DIAG ')]
  self.assertGreaterEqual(len(rows),3);self.assertTrue(all(rows))
 def test_model_with_pixel_quantization(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'sim/results') as td:
   p=Path(td)/'capture.txt';rows=synthetic(p);model=identify(rows)
   self.assertLess(abs(model['b']+20),5);self.assertGreaterEqual(model['R2_holdout'],.70)
   result=analyze(p);self.assertEqual(result['status'],'ACCEPTED_PENDING_PHYSICAL_VALIDATION');self.assertFalse(result['physical_pass'])
   self.assertEqual(result['parameters']['polarity'],0)
   self.assertEqual(len(encode_config(result['parameters'])),54)
 def test_inconsistent_direction_rejected(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'sim/results') as td:
   rows=synthetic(Path(td)/'bad.txt',True)
   with self.assertRaises(ValueError):identify(rows)
 def test_no_actual_calibration_rejected(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'sim/results') as td:
   p=Path(td)/'plain.txt';p.write_text('VIS=5 old log\n')
   with self.assertRaises(ValueError):analyze(p)
 def test_aborted_latest_not_silently_replaced(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'sim/results') as td:
   p=Path(td)/'capture.txt';synthetic(p)
   with p.open('a',encoding='utf-8') as f:f.write(encode_diag({'time_ms':6000,'frame_ms':5990,'sequence':12,'selection':3,'flags':11,'cal_status':4}))
   with self.assertRaises(ValueError):analyze(p)
 def test_unmeasured_high_gain_not_forced(self):
  model={'b':-40.,'c':.15,'d':0.,'delay_ms':20,'neutral':0}
  # No qualified candidate is a useful,explicit result; never invent a physical pass.
  result=choose_gains(model,100)
  if result:self.assertEqual(result['parameters']['selection'],1)

if __name__=='__main__':unittest.main(verbosity=2)
