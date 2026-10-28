from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parent
def read(p):return p.read_text(encoding='utf-8-sig').replace('\r\n','\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check():
 m=json.loads(read(R/'brake_precise5_lineage.json'));a=Path(m['archive']);old=a/'snapshot'
 for rel,h in json.loads(read(a/'manifest.json'))['files'].items():assert sha(a/rel)==h,'archive changed '+rel
 assert sha(R/'output/brake_precise4.bit')==m['parent_bit_sha256']
 assert sha(R/'output/brake_precise3.bit')=='4878031b5703a9e0d1f17f36258dfc2e48ecc45594f6fc5443229d185f30fbdb'
 base=json.loads(read(old/'build_sources.json'))
 for rel,h in base.items():
  if rel not in ('rtl/vision_region100.v','rtl/vision_monitor_all.v','build.ps1'):assert sha(R/rel)==h,'unexpected compiled edit '+rel
 assert set(json.loads(read(R/'build_sources.json')))==set(base)
 for rel,h in json.loads(read(old/'brake_precise4_verification.json'))['paired_host_sha256'].items():assert sha(R/rel)==h,'old host modified '+rel
 s=read(R/'rtl/vision_region100.v');b=read(old/'rtl/vision_region100.v')
 for start,end in [(' wire enter_now=',' // Continuous position gain:'),(' // Continuous position gain:',' // Parked ball assistance'),(' wire signed [31:0] final_p=',' always @(posedge clk)'),('    if(!holding)begin','   if(!valid || stale)')]:
  assert s[s.index(start):s.index(end,s.index(start))]==b[b.index(start):b.index(end,b.index(start))],'frozen moving/hold law changed'
 assert 'mean_drift<=32 && mean_drift>=-32' in s and 'quiet_frames>=29' in s
 assert 'escape_wait==29' in s and "6'd40 : 6'd48" in s and 'escape_arrived' in s
 print('PRECISE5_CONTRACT_PASS core/guards/pins/clocks/protocol/moving gains/hold frozen;dwell rearm and bounded arrival-gated escape')
if __name__=='__main__':check()
