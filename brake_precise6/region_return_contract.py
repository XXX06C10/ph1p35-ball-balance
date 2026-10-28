from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parent
def read(p):return p.read_text(encoding='utf-8-sig').replace('\r\n','\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check():
 a=Path(json.loads(read(R/'region_return_lineage.json'))['archive']);old=a/'snapshot'
 for rel,h in json.loads(read(a/'manifest.json'))['files'].items():assert sha(a/rel)==h,'immutable archive '+rel
 allowed={'build.ps1','compose.py','rtl/vision_monitor.v','rtl/vision_monitor_all.v','rtl/vision_servo_core.v','rtl/vision_cascade_control.v','rtl/vision_cascade_outer.v','user_source/hdl_source/design_top_wrapper.v'}
 for rel,h in json.loads(read(old/'build_sources.json')).items():
  if rel not in allowed:assert sha(R/rel)==h,'compiled edit outside regional integration '+rel
 before=read(old/'rtl/vision_servo_core.v');now=read(R/'rtl/vision_servo_core.v')
 expected=before.replace('CHECKPOINT_CAPABLE=0,','CHECKPOINT_CAPABLE=0,TAIL_CHECKPOINT=0,')
 expected=expected.replace('else if(fast_quiet_age<FAST_MS_CYCLES*20)','else if(fast_quiet_age<FAST_MS_CYCLES*(TAIL_CHECKPOINT ? 40 : 20))')
 start=now.index(' // Optional regional-mode tail settlement:');end=now.index(' wire checkpoint_consistent=',start)
 expected=expected.replace(' wire checkpoint_consistent=',now[start:end]+' wire checkpoint_consistent=')
 expected=expected.replace('fast_rate_hz==0 && fast_count==0 && checkpoint_consistent)','fast_rate_hz==0 && (fast_count==0 || verified_tail) && checkpoint_consistent)')
 expected=expected.replace("active<=0;done<=0;state<=READY;phase_count<=0;completed_count<=completed_count+1'b1;", "active<=0;done<=0;state<=READY;phase_count<=0;completed_count<=completed_count+1'b1;\n       if(verified_tail)begin fast_count<=0;fast_commands<=0;fast_anchor<=wide_position;fast_age<=0;end",1)
 assert now==expected,'core change outside optional tail checkpoint'
 marker='    case(state)';assert now[now.rindex(marker):]==before[before.rindex(marker):],'slow manual FSM changed'
 guard='   if(fault!=0)begin';finish='   end else if(fast_active)begin'
 assert now[now.index(guard):now.index(finish)]==before[before.index(guard):before.index(finish)],'common faults/limits changed'
 assert read(R/'rtl/vision_cascade_control.v')==read(old/'rtl/vision_cascade_control.v'),'inner controller/segment logic changed'
 expected=read(old/'rtl/vision_cascade_outer.v').replace('parameter MS_CYCLES=50000','parameter MS_CYCLES=50000,REGION_VELOCITY=0').replace('capture_quiet<=predictive && err','capture_quiet<=predictive && !REGION_VELOCITY && err')
 assert read(R/'rtl/vision_cascade_outer.v')==expected,'outer observer changed beyond noise gate selection'
 assert read(R/'user_source/hdl_source/design_top_wrapper.v')==read(old/'user_source/hdl_source/design_top_wrapper.v').replace('.CASCADE_DEFAULT(0),.CASCADE_PRESET(0),.REGION_PROBE(1)','.CASCADE_DEFAULT(1),.CASCADE_PRESET(1),.REGION_RETURN(1)')
 for rel in ('host/vision_panel_cn.ps1','host/cascade_controls.ps1','host/cascade_protocol.ps1','host/cascade_protocol.py','diagnostic_schema.json'):
  assert sha(R/rel)==sha(old/rel),'old protocol/panel changed '+rel
 print('REGION_RETURN_CONTRACT_PASS: video/pins/clocks/protocol,manual/common guards frozen;optional verified-tail settlement only')
if __name__=='__main__':check()
