from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parent
def read(p):return p.read_text(encoding='utf-8-sig').replace('\r\n','\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check():
 meta=json.loads(read(R/'asym_range_lineage.json'));a=Path(meta['archive']);old=a/'snapshot'
 for rel,h in json.loads(read(a/'manifest.json'))['files'].items():assert sha(a/rel)==h,'archive altered '+rel
 allowed={'build.ps1','compose.py','rtl/vision_monitor.v','rtl/vision_monitor_all.v','rtl/vision_servo_core.v','rtl/vision_cascade_control.v','rtl/vision_cascade_outer.v','rtl/vision_region_hold.v','rtl/vision_report_tx.v','rtl/vision_cascade_diag.v','user_source/hdl_source/design_top_wrapper.v'}
 for rel,h in json.loads(read(old/'build_sources.json')).items():
  if rel not in allowed:assert sha(R/rel)==h,'unapproved compiled edit '+rel
 assert read(R/'user_source/hdl_source/design_top_wrapper.v')==read(old/'user_source/hdl_source/design_top_wrapper.v').replace('.REGION_RETURN(1)) u_vision_monitor(','.REGION_RETURN(1),.ASYM_RANGE(1)) u_vision_monitor(')
 mon=read(R/'rtl/vision_monitor.v');dense=read(R/'evidence/asym_dense_attempt1/rtl/vision_monitor.v')
 folded=mon.replace('assign n_raw_q8=ASYM_RANGE ? n_region_raw : n_region_active ?','assign n_raw_q8=n_region_active ?').replace('assign n_control_phase=ASYM_RANGE ? n_region_phase : n_region_active ?','assign n_control_phase=n_region_active ?').replace(".predictive(ASYM_RANGE ? 1'b1 : (c_selected && c_builtin))",'.predictive(c_selected && c_builtin)')
 assert folded==dense,'optimization exceeded native-only branch selection'
 now=read(R/'rtl/vision_servo_core.v');before=read(old/'rtl/vision_servo_core.v')
 normalized=now.replace('{{(32-TARGET_BITS){visual_target[TARGET_BITS-1]}},visual_target}','{{24{visual_target[7]}},visual_target}')
 normalized=normalized.replace('visual_target>tmax || visual_target<tmin','visual_target>TARGET_LIMIT || visual_target< -TARGET_LIMIT').replace('visual_target<=tmax && visual_target>=tmin','visual_target<=TARGET_LIMIT && visual_target>=-TARGET_LIMIT')
 normalized=normalized.replace('command_position>=mmax','command_position>=POSITION_LIMIT').replace('command_position<=mmin','command_position<=-POSITION_LIMIT').replace('wide_position>pmax || wide_position<pmin','wide_position>FEEDBACK_LIMIT || wide_position< -FEEDBACK_LIMIT')
 marker='    case(state)';assert normalized[normalized.rindex(marker):]==before[before.rindex(marker):],'manual FSM changed beyond explicit bounds/width'
 for first,last in [('   if(fault!=0)begin','   end else if(fast_active)begin'),('    if(fast_due)begin','    end else case(state)')]:
  assert normalized[normalized.index(first):normalized.index(last)]==before[before.index(first):before.index(last)],'common guard/feedback checks changed'
 assert 'MOVE_BUDGET=64,NO_RESPONSE_LIMIT=3' in now and 'TIMEOUT_CYCLES=250000000' in now
 for module in ('vision_result_guard.v','vision_center_key.v','enable_latch.v','encoder_ab_counter.v','vision_config_rx.v'):
  assert sha(R/'rtl'/module)==sha(old/'rtl'/module),'stop/parser path changed '+module
 report=read(R/'rtl/vision_report_tx.v');old_report=read(old/'rtl/vision_report_tx.v')
 start='    function [7:0] message_byte;';end='    always @(posedge clk)begin'
 assert report[report.index(start):report.index(end)].replace('begin if(WIDE_RANGE)message_byte=wide_message_byte(index);else case(index)','begin case(index)')==old_report[old_report.index(start):old_report.index(end)],'legacy VIS5 wire changed'
 for path in ('host/region_return_panel_cn.ps1','host/region_return_controls.ps1','host/cascade_protocol.py','host/cascade_protocol.ps1','diagnostic_schema.json','frame_layout.json'):
  assert sha(R/path)==sha(old/path),'old protocol/panel changed '+path
 assert -18< -204*360/4096 < -182*360/4096 < 0 < 364*360/4096 <398*360/4096<35
 assert -18 < -159*360/3200 and 310*360/3200<35
 print('ASYM_CONTRACT_PASS archived parent,unchanged video/IO/clocks/stops/manual timing;explicit wide bounds/protocol only')
if __name__=='__main__':check()
