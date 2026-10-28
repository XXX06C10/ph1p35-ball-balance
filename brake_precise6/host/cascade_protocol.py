"""C01/D1 additive protocol. Standard-library only; legacy VIS5/P/V/S unchanged."""
from pathlib import Path
import json,struct
ROOT=Path(__file__).resolve().parents[1]
SCHEMA=json.loads((ROOT/'diagnostic_schema.json').read_text(encoding='utf-8-sig'))
FIELDS=[('version',1),('sequence',2),('selection',1),('diagnostics',1),('kp',2),('kv',2),('ki',2),('bias',2),('inner_kp',2),('feedforward',2),('max_hz',2),('delay_ms',1),('amplitude',1),('slew_rate',2),('polarity',1),('reserved',1)]
DEFAULT={'version':1,'sequence':0,'selection':0,'diagnostics':1,'kp':512,'kv':128,'ki':0,'bias':0,'inner_kp':8192,'feedforward':200,'max_hz':50,'delay_ms':0,'amplitude':4,'slew_rate':256,'polarity':0,'reserved':0}
def validate(p):
 assert set(p)==set(DEFAULT),'Missing/unknown C fields'
 assert all(isinstance(v,int) and not isinstance(v,bool) for v in p.values()),'C values must be integers'
 assert p['version']==1 and 0<=p['sequence']<=65535 and 0<=p['selection']<=3 and p['diagnostics'] in (0,1)
 assert 0<=p['kp']<=16384 and 0<=p['kv']<=2048 and 0<=p['ki']<=3277 and -2048<=p['bias']<=2048
 assert 256<=p['inner_kp']<=32768 and 0<=p['feedforward']<=256 and p['max_hz'] in (50,100,200)
 assert 0<=p['delay_ms']<=120 and p['amplitude'] in ((4,8) if p['selection']==3 else (4,8,16))
 assert 8<=p['slew_rate']<=256 and p['polarity'] in (0,1) and p['reserved']==0
 return p
def encode_config(p):
 validate(p);payload=b''.join((p[k] & ((1<<(n*8))-1)).to_bytes(n,'big') for k,n in FIELDS)
 xor=0
 for b in payload:xor^=b
 return 'C'+(payload+bytes([xor])).hex().upper()+'\n'
def decode_config(line):
 try:
  line=line.strip();assert len(line)==53 and line[0]=='C';raw=bytes.fromhex(line[1:]);xor=0
  for b in raw:xor^=b
  assert xor==0;p={};at=0
  for k,n in FIELDS:p[k]=int.from_bytes(raw[at:at+n],'big',signed=k=='bias');at+=n
  return validate(p)
 except (ValueError,AssertionError):return None
def parse_diag(line):
 try:
  line=line.strip();assert line.startswith('D1') and len(line)==SCHEMA['wire_bytes']-2
  raw=bytes.fromhex(line[2:]);xor=0
  for b in raw:xor^=b
  assert xor==0;result={};at=0
  for k,bits in SCHEMA['fields']:
   n=bits//8;result[k]=int.from_bytes(raw[at:at+n],'big',signed=k in SCHEMA['signed']);at+=n
  assert at==len(raw)-1 and result['selection']<=3
  return result
 except (ValueError,AssertionError):return None
def encode_diag(p):
 raw=b''.join((int(p.get(k,0))&((1<<bits)-1)).to_bytes(bits//8,'big') for k,bits in SCHEMA['fields']);xor=0
 for b in raw:xor^=b
 return 'D1'+(raw+bytes([xor])).hex().upper()+'\r\n'
if __name__=='__main__':
 p=DEFAULT|{'sequence':1,'selection':2,'amplitude':8};s=encode_config(p);assert len(s)==54 and decode_config(s)==p
 assert decode_config(s[:-3]+'FF\n') is None
 q={k:0 for k,b in SCHEMA['fields']};q.update(position=-31,reference_q8=-31*256,velocity_q4=-160,frequency_hz=-50,neutral=-31)
 assert parse_diag(encode_diag(q))==q
 print('CASCADE_PROTOCOL_PASS C54/D94 XOR,signed fields and bounds')
