"""Freeze user-accepted easy2 motor/checkpoint/camera lineage."""
from pathlib import Path
import json,hashlib
r=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 raw=p.read_bytes();return (raw.decode('utf-16') if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else raw.decode('utf-8-sig')).replace('\r\n','\n')
def check_easy3():
 v=json.loads(read(r/'easy3_lineage.json'));a=Path(v['archive'])
 for rel,h in json.loads(read(a/'manifest.json'))['files'].items():assert sha(a/rel)==h,'accepted archive changed '+rel
 assert sha(r/'output/vision_follow_20261022_easy2.bit')==v['parent_bit_sha256'],'accepted easy2 bit changed'
 parent=next((a/'published').rglob('delivery_manifest.json')).parent
 allowed={'build.ps1','rtl/vision_monitor.v','rtl/vision_monitor_all.v','rtl/vision_cascade_outer.v','rtl/vision_cascade_config.v','rtl/vision_servo_core.v','user_source/hdl_source/design_top_wrapper.v'}
 for rel,h in json.loads(read(parent/'build_sources.json')).items():
  if rel not in allowed:assert sha(r/rel)==h,'compiled edit outside predictive scope '+rel
 for rel in ['vision_cascade_control.v','enable_latch.v','encoder_ab_counter.v','vision_result_guard.v','vision_config_rx.v','vision_follow_control.v','vision_shadow_target.v','vision_report_tx.v','vision_cascade_diag.v']:
  assert sha(r/'rtl'/rel)==sha(parent/'rtl'/rel),'motor/health/protocol changed '+rel
 old_servo=read(parent/'rtl/vision_servo_core.v')
 servo=old_servo.replace(' reg signed [31:0] checkpoint_p=0,checkpoint_m=0;', ''' reg signed [31:0] checkpoint_p=0,checkpoint_m=0;
 // Drain the validated20ms feedback latency before a DIR reversal. The quiet
 // clock runs across segment boundaries; no pending feedback is forgiven.
 reg [31:0] fast_quiet_age=FAST_MS_CYCLES*20;reg fast_step_previous=0;''')
 servo=servo.replace('checkpoint_p<=0;checkpoint_m<=0;','checkpoint_p<=0;checkpoint_m<=0;fast_quiet_age<=FAST_MS_CYCLES*20;fast_step_previous<=0;')
 servo=servo.replace('''  end else begin
   if(!fast_active || !active || !enable_raw || !permit || fault!=0)begin''','''  end else begin
   fast_step_previous<=motor_step;
   if(motor_step && !fast_step_previous)fast_quiet_age<=0;
   else if(fast_quiet_age<FAST_MS_CYCLES*20)fast_quiet_age<=fast_quiet_age+1'b1;
   if(!fast_active || !active || !enable_raw || !permit || fault!=0)begin''')
 servo=servo.replace('fast_positive==dir_r || fast_count==0','fast_positive==dir_r || (fast_count==0 && fast_quiet_age>=FAST_MS_CYCLES*20)')
 assert read(r/'rtl/vision_servo_core.v')==servo,'motor edits exceeded only reversal feedback drain'
 start='   if(fault!=0)begin';guard=lambda s:s[s.index(start):s.index('   end else if(fast_active)begin')]
 assert guard(servo)==guard(old_servo) and servo[servo.rindex('    case(state)'):]==old_servo[old_servo.rindex('    case(state)'):]
 expected=read(parent/'rtl/vision_cascade_config.v').replace('DEFAULT_PRESET ? 40','DEFAULT_PRESET ? 64').replace('DEFAULT_PRESET ? 100','DEFAULT_PRESET ? 200').replace('DEFAULT_PRESET ? 102','DEFAULT_PRESET ? 200')
 assert read(r/'rtl/vision_cascade_config.v')==expected
 assert read(r/'user_source/hdl_source/design_top_wrapper.v')==read(parent/'user_source/hdl_source/design_top_wrapper.v').replace('.DEFAULT_LIMIT(48)','.DEFAULT_LIMIT(60)')
 monitor=read(parent/'rtl/vision_monitor.v').replace('n_updated,n_stable,n_checkpoint;','n_updated,n_stable,n_checkpoint;\n    wire [1:0] n_control_phase;')
 monitor=monitor.replace('.updated(n_updated),.stable(n_stable),.time_ms(n_time),.frame_time_ms(n_frame_time));','.updated(n_updated),.stable(n_stable),.time_ms(n_time),.frame_time_ms(n_frame_time),\n     .predictive(c_selected && c_builtin),.control_phase(n_control_phase));')
 monitor=monitor.replace(".flags({7'd0,c_profile_ready,", ".flags({4'd0,(c_selected && c_builtin),n_control_phase,c_profile_ready,")
 assert read(r/'rtl/vision_monitor.v')==monitor,'unexpected integration change'
 # Inherited RGB uses CASCADE_DEFAULT0,so the unchanged legacy path remains active.
 assert read(r/'sim/tb_rgb.v')==read(parent/'sim/tb_rgb.v') and 'CASCADE_DEFAULT' not in read(r/'sim/tb_rgb.v')
 ref=r/'references/user_lqt_20261025';meta=json.loads(read(ref/'source.json'))
 for rel,h in meta['files'].items():assert sha(ref/rel)==h,'reference modified '+rel
if __name__=='__main__':check_easy3();print('EASY3_CONTRACT_PASS: manual/checkpoint/common guards,video/IO/clocks/serializers frozen;only fast reversal drain added')
