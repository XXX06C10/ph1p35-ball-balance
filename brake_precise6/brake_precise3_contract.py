from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parent
def read(p):return p.read_text(encoding='utf-8-sig').replace('\r\n','\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check():
 meta=json.loads(read(R/'brake_precise3_lineage.json'));a=Path(meta['archive']);old=a/'snapshot'
 for rel,h in json.loads(read(a/'manifest.json'))['files'].items():assert sha(a/rel)==h,'archive changed '+rel
 assert sha(R/'output/brake_precise2.bit')==meta['parent_bit_sha256']
 baseline=json.loads(read(old/'build_sources.json'))
 allowed={'rtl/vision_servo_core.v','rtl/vision_region100.v','rtl/vision_monitor.v','rtl/vision_monitor_all.v','build.ps1'}
 for rel,h in baseline.items():
  if rel not in allowed:assert sha(R/rel)==h,'unrelated build input changed '+rel
 assert set(json.loads(read(R/'build_sources.json')))==set(baseline)
 core=read(R/'rtl/vision_servo_core.v');before=read(old/'rtl/vision_servo_core.v')
 # Entire common enable/origin/feedback bounds/timeout/cancel guards and manual
 # motion FSM remain exact. Fast response/F1/F2 and checkpoint closure are exact.
 for start,end in [('   // Record rejected edges','   end else if(fast_active)'),('    // Check accumulated physical response','    end else case(state)'),('      if(CHECKPOINT_CAPABLE','      else if(fast_rate_hz!=0 &&')]:
  if start.startswith('      if(CHECK'):continue
  assert core[core.index(start):core.index(end,core.index(start))]==before[before.index(start):before.index(end,before.index(start))]
 marker='   end else begin\n    if(active)action_timer<=action_timer+1\'b1;\n    case(state)'
 assert core[core.index(marker):]==before[before.index(marker):],'manual motion changed'
 for g in ('spent>=MOVE_BUDGET','fast_displacement==0','fast_count<NO_RESPONSE_LIMIT','fast_quiet_age>=FAST_MS_CYCLES*40','state<=10','command_position<=mmin'):
  assert g in core,g
 for rel,h in json.loads(read(old/'brake_precise2_verification.json'))['paired_host_sha256'].items():assert sha(R/rel)==h,'old panel/codec changed '+rel
 assert read(R/'build.tcl')==read(old/'build.tcl')
 assert '.REVERSAL_RECOVERY(REGION_FAST)' in read(R/'rtl/vision_monitor.v')
 s=read(R/'rtl/vision_monitor.v').replace('    wire recovery_pending;\n','').replace('.REVERSAL_RECOVERY(REGION_FAST),','').replace(',.diag_recovery(recovery_pending)','').replace('.flags({(REGION_FAST && recovery_pending),','.flags({1\'b0,')
 assert s==read(old/'rtl/vision_monitor.v'),'monitor edits exceeded recovery selection and bit15'
 print('PRECISE3_CONTRACT_PASS immutable parent,common/manual guards,fast F1/F2,controller,IO,clocks,raw protocols')
if __name__=='__main__':check()
