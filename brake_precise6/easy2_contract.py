"""Freeze easy baseline except explicit checkpoint/observer/range edits."""
from pathlib import Path
import json,hashlib
r=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 raw=p.read_bytes();return (raw.decode('utf-16') if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else raw.decode('utf-8-sig')).replace('\r\n','\n')
def check_easy2():
 v=json.loads(read(r/'easy2_lineage.json'));a=Path(v['archive'])
 for rel,h in json.loads(read(a/'manifest.json'))['files'].items():assert sha(a/rel)==h,'easy archive modified '+rel
 assert sha(r/'output/vision_follow_20261022_easy.bit')==v['parent_bit_sha256'],'old easy bit overwritten'
 parent=next((a/'published').rglob('delivery_manifest.json')).parent
 allowed={'build.ps1','rtl/vision_monitor.v','rtl/vision_monitor_all.v','rtl/vision_cascade_control.v','rtl/vision_cascade_outer.v','rtl/vision_servo_core.v','user_source/hdl_source/design_top_wrapper.v'}
 for rel,h in json.loads(read(parent/'build_sources.json')).items():
  if rel not in allowed:assert sha(r/rel)==h,'unapproved compiled edit '+rel
 old=read(parent/'rtl/vision_servo_core.v');cur=read(r/'rtl/vision_servo_core.v')
 assert old[old.rindex('    case(state)'):]==cur[cur.rindex('    case(state)'):],'manual FSM changed'
 start='   if(fault!=0)begin'
 guard=lambda s:s[s.index(start):s.index('   end else if(fast_active)begin')]
 assert guard(old)==guard(cur),'shared faults/origin/P/timeout/cancel guard changed'
 for token in ['POSITION_LIMIT=64','FEEDBACK_LIMIT=64','MOVE_BUDGET=64','TIMEOUT_CYCLES=250000000','TARGET_LIMIT=60']:
  assert token in cur
 assert cur.count('origin<=encoder_count')==1 and cur.count('command_position<=0')==1
 assert 'checkpoint_difference<=19\'sd1024' in cur and 'fast_count==0 && checkpoint_consistent' in cur
 assert 'active<=0;done<=0;state<=READY;phase_count<=0;completed_count<=' in cur
 assert read(r/'rtl/vision_cascade_outer.v')==read(parent/'rtl/vision_cascade_outer.v').replace('residual_now>512 || residual_now< -512','residual_now>2048 || residual_now< -2048')
 assert read(r/'user_source/hdl_source/design_top_wrapper.v')==read(parent/'user_source/hdl_source/design_top_wrapper.v').replace('.DEFAULT_DEADZONE(3),.CASCADE_DEFAULT(1)','.DEFAULT_DEADZONE(3),.DEFAULT_LIMIT(48),.CASCADE_DEFAULT(1)')
 assert sha(r/'sim/replay_old_all.v')==sha(parent/'rtl/vision_monitor_all.v'),'old replay was not actual archived source'
 # Inherited RGB runs CASCADE_DEFAULT0, so c_selected/checkpoint/fast_mode are0.
 # The entire legacy supervisor, manual FSM and common guards remain frozen.
 assert read(r/'sim/tb_rgb.v')==read(parent/'sim/tb_rgb.v') and 'CASCADE_DEFAULT' not in read(r/'sim/tb_rgb.v')
 assert 'c_selected && n_checkpoint' in read(r/'rtl/vision_monitor.v')
 for rel in ['vision_follow_control.v','vision_shadow_target.v','vision_result_guard.v','vision_config_rx.v','encoder_ab_counter.v']:
  assert sha(r/'rtl'/rel)==sha(parent/'rtl'/rel)
if __name__=='__main__':check_easy2();print('EASY2_CONTRACT_PASS: archives,manual/common guards,camera/IO/clocks frozen;scoped checkpoint,observer and range')
