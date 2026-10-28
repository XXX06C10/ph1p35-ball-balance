"""VIS6 full32-bit T/AT and D2 wide neutral/fixed bounds. No hardware IO."""
from pathlib import Path
import json
R=Path(__file__).resolve().parents[1]
SCHEMA=json.loads((R/'wide_diagnostic_schema.json').read_text())
LAYOUT=json.loads((R/'wide_frame_layout.json').read_text())['layout']
def parse_diag(line):
 try:
  line=line.strip();assert len(line)==146 and line.startswith('D2')
  raw=bytes.fromhex(line[2:]);check=0
  for b in raw:check^=b
  assert check==0;out={};i=0
  for k,bits in SCHEMA['fields']:
   n=bits//8;out[k]=int.from_bytes(raw[i:i+n],'big',signed=k in SCHEMA['signed']);i+=n
  assert i==71 and out['selection']<=3
  return out
 except (ValueError,AssertionError):return None
def encode_diag(d):
 raw=b''.join((int(d.get(k,0))&((1<<b)-1)).to_bytes(b//8,'big') for k,b in SCHEMA['fields']);crc=0
 for v in raw:crc^=v
 return 'D2'+(raw+bytes([crc])).hex().upper()+'\r\n'
def parse_record(line):
 try:
  parts=line.strip().split(' ');assert len(parts)==len(LAYOUT);out={}
  for part,(name,n,_,kind) in zip(parts,LAYOUT):
   key,value=part.split('=');assert key==name and len(value)==n
   if kind=='literal':assert value=='6';continue
   v=int(value,16)
   if key in ('E1','E2','P','T','AT','MT','ME','MC') and v>=2**31:v-=2**32
   if key=='VE' and v>=32768:v-=65536
   out[key]=v
  assert out['MD']<=2
  return out
 except (ValueError,AssertionError):return None
