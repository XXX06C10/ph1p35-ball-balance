from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'host'))
from asym_protocol import parse_diag,encode_diag,parse_record
from cascade_protocol import DEFAULT,encode_config,decode_config
class AsymHost(unittest.TestCase):
 def test_wide_signed_diagnostic(self):
  r={'neutral':200,'position':-182,'reference_q8':364*256,'work_min':-182,'work_max':364,'feedback_min':-204,'feedback_max':398,'selection':1}
  line=encode_diag(r);self.assertEqual(len(line),148);d=parse_diag(line)
  for k,v in r.items():self.assertEqual(d[k],v)
  self.assertIsNone(parse_diag(line[:20]+'Z'+line[21:]));self.assertIsNone(parse_diag(line[:-5]))
 def test_old_config_unchanged(self):
  p=DEFAULT|{'sequence':9,'selection':1};self.assertEqual(decode_config(encode_config(p)),p)
 def test_actual_wide_uart(self):
  p=Path(__file__).parent/'results/tb_asym_range.log';b=p.read_bytes();text=b.decode('utf-16' if b.startswith(b'\xff\xfe') else 'utf-8-sig')
  self.assertIn('ASYM_RANGE_PASS',text);ds=[];vs=[]
  for line in text.splitlines():
   if line.startswith('ASYM_WIRE D2'):
    d=parse_diag(line.split(' ',1)[1]);self.assertIsNotNone(d);ds.append(d)
   elif line.startswith('ASYM_WIRE VIS=6'):
    d=parse_record(line.split(' ',1)[1]);self.assertIsNotNone(d);vs.append(d)
  self.assertTrue(any(d['reference_q8']>127*256 for d in ds));self.assertTrue(any(d['reference_q8']< -128*256 for d in ds))
  self.assertTrue(any(d['T']==364 for d in vs));self.assertTrue(any(d['T']==-182 for d in vs))
  self.assertTrue(all(d['work_min']==-182 and d['work_max']==364 for d in ds if d['flags']&8192))
  self.assertTrue(any(d['neutral']==200 for d in ds))
if __name__=='__main__':unittest.main()
