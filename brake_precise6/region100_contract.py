from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parent
def read(p):return p.read_text(encoding='utf-8-sig').replace('\r\n','\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check():
 meta=json.loads(read(R/'region100_lineage.json'));a=Path(meta['archive']);old=a/'snapshot'
 for rel,h in json.loads(read(a/'manifest.json'))['files'].items():assert sha(a/rel)==h,'archive changed '+rel
 assert sha(R/'output/asym_smooth.bit')==meta['parent_bit_sha256']
 assert sha(R/'output/asym_range.bit')=='46a2b676a6bfeaa3168620aaedd53e40e95128d16a1af6c9f081f5b90be49f7c'
 baseline=json.loads(read(old/'build_sources.json'));current=json.loads(read(R/'build_sources.json'))
 allowed={'rtl/vision_monitor.v','rtl/vision_monitor_all.v','compose.py','build.ps1','user_source/hdl_source/design_top_wrapper.v'}
 for rel,h in baseline.items():
  if rel not in allowed:assert sha(R/rel)==h,'unexpected compiled edit '+rel
 assert set(current)-set(baseline)=={'rtl/vision_region100.v'}
 assert read(R/'compose.py')==read(old/'compose.py').replace("parts=['vision_overlay_lead.v'","parts=['vision_region100.v','vision_overlay_lead.v'")
 assert read(R/'build.ps1')==read(old/'build.ps1').replace("'asym_smooth')","'asym_smooth','region100')")
 s=read(R/'user_source/hdl_source/design_top_wrapper.v');assert '.REGION100(1)) u_vision_monitor(' in s
 s=s.replace('.ASYM_SMOOTH(1),.REGION100(1))','.ASYM_SMOOTH(1))').replace('.DEFAULT_DEADZONE(100)','.DEFAULT_DEADZONE(3)')
 assert s==read(old/'user_source/hdl_source/design_top_wrapper.v'),'top changed beyond policy/default'
 s=read(R/'rtl/vision_monitor.v').replace('ASYM_SMOOTH=0,REGION100=0,','ASYM_SMOOTH=0,')
 first=s.index('    wire signed [31:0] old_region_raw,');last=s.index('    vision_region_hold #',first);s=s[:first]+s[last:]
 start=s.index('    vision_region_hold #');end=s.index('    vision_asym_limits',start);block=s[start:end]
 for a,b in [('old_region_raw','n_region_raw'),('old_region_changed','n_region_changed'),('old_region_holding','n_region_holding'),('old_region_phase','n_region_phase'),('old_region_hz','n_region_hz'),('old_region_slew','n_region_slew'),('old_region_velocity','n_region_velocity')]:block=block.replace(a,b)
 block=block.replace('.run(n_run && n_region_active && !REGION100)','.run(n_run && n_region_active)');s=s[:start]+block+s[end:]
 assert s==read(old/'rtl/vision_monitor.v'),'monitor edit beyond parallel native policy selector'
 for rel,h in json.loads(read(old/'asym_smooth_verification.json'))['paired_host_sha256'].items():assert sha(R/rel)==h,'old paired host changed '+rel
 codec=". (Join-Path $PSScriptRoot 'asym_protocol.ps1')"
 assert read(R/'host/region100_panel_cn.ps1').split(codec)[0]==read(old/'host/asym_smooth_panel_cn.ps1').split(codec)[0],'wire codecs changed'
 print('REGION100_CONTRACT_PASS exact detector/display/core/inner/guards/window/pins/clocks/protocol;only outer policy and defaults selected')
if __name__=='__main__':check()
