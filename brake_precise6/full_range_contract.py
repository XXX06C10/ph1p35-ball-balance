from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parent
def read(p):return p.read_text(encoding='utf-8-sig').replace('\r\n','\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check():
 a=Path(json.loads(read(R/'full_range_lineage.json'))['archive']);old=a/'snapshot'
 for rel,h in json.loads(read(a/'manifest.json'))['files'].items():assert sha(a/rel)==h,'archive changed '+rel
 allowed={'rtl/vision_region_hold.v','rtl/vision_monitor_all.v','build.ps1'}
 for rel,h in json.loads(read(old/'build_sources.json')).items():
  if rel not in allowed:assert sha(R/rel)==h,'unexpected compiled edit '+rel
 assert read(R/'build.ps1')==read(old/'build.ps1').replace("'brake_hold','settle30')","'brake_hold','settle30','full_range')")
 s=read(R/'rtl/vision_region_hold.v').replace("cap=$signed({1'b0,limit,8'b0});","cap=LIVE_ZONE && limit>48 ? 18'sd12288 : $signed({1'b0,limit,8'b0});").replace('relative_stage<=WIDE_RANGE ? raw_stage :','relative_stage<=WIDE_RANGE && !LIVE_ZONE ? raw_stage :')
 assert s==read(old/'rtl/vision_region_hold.v'),'regional edits exceeded removal of extra48/P.L cap'
 assert '纠偏幅度已到上限' not in read(R/'host/full_range_controls.ps1'),'misleading48count UI remained'
 for rel,h in json.loads(read(old/'settle30_verification.json'))['paired_host_sha256'].items():assert sha(R/rel)==h,'old host changed '+rel
 codec=". (Join-Path $PSScriptRoot 'asym_protocol.ps1')"
 assert read(R/'host/full_range_panel_cn.ps1').split(codec)[0]==read(old/'host/settle_panel_cn.ps1').split(codec)[0],'wire codecs changed'
 for b in ['tb_settle_plant','tb_settle_runtime','tb_motion','tb_asym_faults','tb_region_policy']:
  assert sha(R/f'sim/{b}.v')==sha(old/f'sim/{b}.v'),'existing regression assertion changed '+b
 print('FULL_RANGE_CONTRACT_PASS only extra cap removed;exact native gains/zone/core/faults/limits/pins/clocks/wire formats retained')
if __name__=='__main__':check()
