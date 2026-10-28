from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parent
def read(p):return p.read_text(encoding='utf-8-sig').replace('\r\n','\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check():
 m=json.loads(read(R/'brake_precise4_lineage.json'));a=Path(m['archive']);old=a/'snapshot'
 for rel,h in json.loads(read(a/'manifest.json'))['files'].items():assert sha(a/rel)==h,'archive changed '+rel
 assert sha(R/'output/brake_precise3.bit')==m['parent_bit_sha256']
 base=json.loads(read(old/'build_sources.json'))
 for rel,h in base.items():
  if rel not in ('rtl/vision_region100.v','rtl/vision_monitor_all.v','build.ps1'):assert sha(R/rel)==h,'unexpected compiled edit '+rel
 assert set(json.loads(read(R/'build_sources.json')))==set(base)
 for rel,h in json.loads(read(old/'brake_precise3_verification.json'))['paired_host_sha256'].items():assert sha(R/rel)==h,'old host modified '+rel
 s=read(R/'rtl/vision_region100.v');b=read(old/'rtl/vision_region100.v')
 # All gains, speed envelope, restart levels/slew and the hardware executor are frozen.
 for start,end in [(' // Continuous position gain:',' // Parked ball assistance'),(' // Start gently,',' always @(posedge clk)')]:
  assert s[s.index(start):s.index(end,s.index(start))]==b[b.index(start):b.index(end,b.index(start))],'moving gains/targets changed'
 assert 'mean_drift<=32 && mean_drift>=-32' in s and 'quiet_frames>=29' in s
 print('PRECISE4_CONTRACT_PASS accepted core/guards/pins/clocks/protocol/moving gains unchanged;coordinate dwell only')
if __name__=='__main__':check()
