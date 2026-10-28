from pathlib import Path
import hashlib,json,zipfile
root=Path(__file__).resolve().parent
read=lambda p:p.read_text(encoding='utf-8-sig').replace('\r\n','\n')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
lineage=json.loads(read(root/'cascade_lineage.json'));archive=Path(lineage['archive']);before=archive/'project'
def response_servo(s):
 s=s.replace('EXTERNAL_CONTROL=0,FOLLOW_DEADBAND=1\n','EXTERNAL_CONTROL=0,FOLLOW_DEADBAND=1,\n FOLLOW_SETUP_CYCLES=SETUP_CYCLES,FOLLOW_SETTLE_CYCLES=SETTLE_CYCLES\n')
 anchor=' wire [31:0] allowed_error=EXTERNAL_CONTROL && following ? FOLLOW_DEADBAND : DEADBAND;'
 s=s.replace(anchor,anchor+'\n wire [31:0] setup_limit=EXTERNAL_CONTROL && following ? FOLLOW_SETUP_CYCLES : SETUP_CYCLES;\n wire [31:0] settle_limit=EXTERNAL_CONTROL && following ? FOLLOW_SETTLE_CYCLES : SETTLE_CYCLES;')
 s=s.replace('phase_count==SETUP_CYCLES-1','phase_count==setup_limit-1').replace('phase_count==SETTLE_CYCLES-1','phase_count==settle_limit-1')
 return s
def hold_enable(s):
 s=s.replace('DEBOUNCE_CYCLES=1000000)','DEBOUNCE_CYCLES=1000000,HOLD_ON_FAULT=0)')
 s=s.replace('!inhibit & latched','(HOLD_ON_FAULT || !inhibit) & latched')
 s=s.replace('|| inhibit) begin','|| (inhibit && !HOLD_ON_FAULT)) begin')
 s=s.replace('else if(armed) begin latched<=~latched; armed<=0; end','else if(armed) begin\n                    // A fault permits releasing an existing hold, never re-enabling.\n                    if(!inhibit || latched)latched<=~latched;\n                    armed<=0;\n                end')
 return s
def hold_servo(s):
 s=s.replace('EXTERNAL_CONTROL=0,FOLLOW_DEADBAND=1,','EXTERNAL_CONTROL=0,FOLLOW_DEADBAND=1,HOLD_ON_FAULT=0,')
 s=s.replace('& (fault==0) & (encoder_errors==0);','& (HOLD_ON_FAULT || ((fault==0) && (encoder_errors==0)));')
 s=s.replace('motor_en & step_r & permit;','motor_en & step_r & permit & (fault==0) & (encoder_errors==0);')
 s=s.replace('if(fault!=0)begin enabled<=0;', 'if(fault!=0)begin if(!HOLD_ON_FAULT)enabled<=0;')
 s=s.replace('fault<=3;enabled<=0;', 'fault<=3;if(!HOLD_ON_FAULT)enabled<=0;')
 return s
def hold_monitor(s):
 return s.replace('enable_latch #(.DEBOUNCE_CYCLES(DEBOUNCE_CYCLES))','enable_latch #(.DEBOUNCE_CYCLES(DEBOUNCE_CYCLES),.HOLD_ON_FAULT(1))').replace('vision_servo_core #(.EXTERNAL_CONTROL(1),','vision_servo_core #(.EXTERNAL_CONTROL(1),.HOLD_ON_FAULT(1),')
def archive_check():
 for rel,h in json.loads(read(archive/'manifest.json'))['files'].items():assert sha(archive/rel)==h,rel
 with zipfile.ZipFile(lineage['archive_zip']) as z:assert z.testzip() is None
 assert sha(root/'output/vision_follow_20261022_neutral.bit')==lineage['old_bit_sha256']
def check_hold():
 archive_check()
 allowed={'rtl/enable_latch.v','rtl/vision_servo_core.v','rtl/vision_monitor.v','rtl/vision_monitor_all.v','build.ps1'}
 for rel,h in json.loads(read(before/'build_sources.json')).items():
  if rel not in allowed:assert sha(root/rel)==h,'Hold scope changed: '+rel
 assert read(root/'rtl/enable_latch.v')==hold_enable(read(before/'rtl/enable_latch.v'))
 assert read(root/'rtl/vision_servo_core.v')==hold_servo(read(before/'rtl/vision_servo_core.v'))
 assert read(root/'rtl/vision_monitor.v')==hold_monitor(read(before/'rtl/vision_monitor.v'))

def check_cascade():
 archive_check()
 hold=Path('D:/AAAProject/FPGA/AAA_LookHere/交付_20261024_保护保持锁定')
 for rel,h in json.loads(read(hold/'manifest.json'))['files'].items():assert sha(hold/rel)==h,'Saved hold release changed: '+rel
 allowed={'rtl/enable_latch.v','rtl/vision_servo_core.v','rtl/vision_monitor.v','rtl/vision_monitor_all.v','rtl/vision_report_tx.v','build.ps1','compose.py','user_source/hdl_source/design_top_wrapper.v'}
 old_sources=json.loads(read(before/'build_sources.json'));current=json.loads(read(root/'build_sources.json'))
 additions={'rtl/vision_cascade_config.v','rtl/vision_cascade_outer.v','rtl/vision_cascade_control.v','rtl/vision_cascade_diag.v'}
 assert set(current)-set(old_sources)==additions and not set(old_sources)-set(current),'Unexpected compiled input set change'
 for rel,h in old_sources.items():
  if rel not in allowed:assert sha(root/rel)==h,'Unapproved baseline edit: '+rel
 assert read(root/'rtl/enable_latch.v')==hold_enable(read(before/'rtl/enable_latch.v'))
 original_hold=hold_servo(read(before/'rtl/vision_servo_core.v'));servo=read(root/'rtl/vision_servo_core.v')
 assert servo[servo.rindex('    case(state)'):]==original_hold[original_hold.rindex('    case(state)'):],'Manual pulse/feedback FSM changed'
 start='   if(fault!=0)begin'
 old_guard=original_hold[original_hold.index(start):original_hold.index('   end else begin\n    if(active)action_timer')]
 guard=servo[servo.index(start):servo.index('   end else if(fast_active)begin')]
 assert guard==old_guard,'Shared fault/origin/feedback/timeout/cancel guards changed'
 assert servo.count('origin<=encoder_count')==1 and servo.count('command_position<=0')==1,'Reference orMC reset added'
 for literal in ['POSITION_LIMIT=64','FEEDBACK_LIMIT=64','MOVE_BUDGET=64','NO_RESPONSE_LIMIT=3','TARGET_LIMIT=60','DEADBAND=2','FOLLOW_DEADBAND=1','TIMEOUT_CYCLES=250000000']:
  assert literal in servo,'Bound changed '+literal
 assert 'motor_en & step_r & permit & (fault==0) & (encoder_errors==0)' in servo
 top=read(before/'user_source/hdl_source/design_top_wrapper.v').replace('vision_monitor u_vision_monitor(', 'vision_monitor #(.DEFAULT_RUNTIME(0),.DEFAULT_DEADZONE(3),.DEFAULT_LIMIT(60),.CASCADE_DEFAULT(1),.CASCADE_PRESET(1)) u_vision_monitor(')
 assert read(root/'user_source/hdl_source/design_top_wrapper.v')==top,'Top changed beyond explicit startup defaults'
 import re
 old_report=read(before/'rtl/vision_report_tx.v');new_report=read(root/'rtl/vision_report_tx.v')
 functions=lambda source:re.findall(r'function[\s\S]*?endfunction',source)
 assert functions(old_report)==functions(new_report),'VIS5 serializer byte function changed'
 snapshots=lambda source:[line.strip() for line in source.splitlines() if '_snapshot<=' in line]
 assert snapshots(old_report)==snapshots(new_report),'VIS5 field snapshot mapping changed'
 for p in ['enable_latch.v','vision_move_core.v','encoder_ab_counter.v','vision_config_rx.v','vision_follow_control.v','vision_shadow_target.v','vision_result_guard.v']:
  if p!='enable_latch.v':assert sha(root/'rtl'/p)==sha(before/'rtl'/p),p
 if __name__=='__main__':print('CASCADE_CONTRACT_PASS: immutable archives,manual FSM/shared guards,PVS/VIS5 bytes,camera/pins/clocks frozen')
if __name__=='__main__':check_cascade()
