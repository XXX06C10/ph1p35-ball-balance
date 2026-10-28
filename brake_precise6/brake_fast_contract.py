from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parent
def read(p):return p.read_text(encoding='utf-8-sig').replace('\r\n','\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check():
 meta=json.loads(read(R/'brake_fast_lineage.json'));a=Path(meta['archive']);old=a/'snapshot'
 for rel,h in json.loads(read(a/'manifest.json'))['files'].items():assert sha(a/rel)==h,'archive changed '+rel
 assert sha(R/'output/region100.bit')==meta['parent_bit_sha256']
 assert sha(R/'output/asym_range.bit')=='46a2b676a6bfeaa3168620aaedd53e40e95128d16a1af6c9f081f5b90be49f7c'
 baseline=json.loads(read(old/'build_sources.json'));allowed={'rtl/vision_monitor.v','rtl/vision_monitor_all.v','rtl/vision_region100.v','rtl/vision_cascade_control.v','rtl/vision_servo_core.v','build.ps1','user_source/hdl_source/design_top_wrapper.v'}
 for rel,h in baseline.items():
  if rel not in allowed:assert sha(R/rel)==h,'unexpected compiled edit '+rel
 assert set(json.loads(read(R/'build_sources.json')))==set(baseline),'unexpected new compiled input'
 assert read(R/'build.ps1')==read(old/'build.ps1').replace("'region100')","'region100','brake_fast')").replace("'brake_fast')","'brake_fast','brake_precise')").replace("'brake_precise')","'brake_precise','brake_precise2')")
 s=read(R/'user_source/hdl_source/design_top_wrapper.v');assert '.REGION_FAST(1)) u_vision_monitor(' in s
 assert s.replace('.REGION100(1),.REGION_FAST(1))','.REGION100(1))')==read(old/'user_source/hdl_source/design_top_wrapper.v'),'top edits exceeded selector'
 s=read(R/'rtl/vision_monitor.v').replace('REGION100=0,REGION_FAST=0,','REGION100=0,').replace('vision_cascade_control #(.CHECKPOINT_FINISH(REGION_FAST),','vision_cascade_control #(').replace('.NEUTRAL_BITS(TW),.BRAKE_FAST(REGION_FAST)','.NEUTRAL_BITS(TW)').replace(".flags({1'b0,(REGION_FAST && n_quiescing),",".flags({2'd0,")
 assert s==read(old/'rtl/vision_monitor.v'),'monitor edits exceeded selector/diagnostic14'
 core=read(R/'rtl/vision_servo_core.v')
 for marker in ('reg [31:0] fast_check_age=0;',
                'fast_credit>=1000 || fast_check_age>=FAST_MS_CYCLES*20-1',
                'if(state==CHECK && fast_rate_hz!=0)',
                'fast_dir_wait<=fast_positive!=dir_r;dir_r<=fast_positive;fast_check_age<=0;state<=SETUP;'):
  assert marker in core,'independent CHECK retry missing '+marker
 for guard in ('action_timer>=TIMEOUT_CYCLES-1','spent>=MOVE_BUDGET','fast_displacement==0','NO_RESPONSE_LIMIT','wide_position>pmax || wide_position<pmin'):
  assert guard in core,'original core guard lost '+guard
 s=read(R/'rtl/vision_cascade_control.v').replace('WIDE_RANGE=0,TARGET_BITS=8,CHECKPOINT_FINISH=0','WIDE_RANGE=0,TARGET_BITS=8').replace(' reg checkpoint_finish=0;\n','').replace('quiescing && !checkpoint_finish && checkpoint_ms>=40','quiescing && checkpoint_ms>=40').replace('if((quiescing || checkpoint_due) && !checkpoint_finish)','if(quiescing || checkpoint_due)').replace('checkpoint_finish<=0;','')
 first=s.index('   // A rejected quiet checkpoint');last=s.index('   if((quiescing',first) if '   if((quiescing' in s[first:] else s.index('   if(quiescing || checkpoint_due)',first)
 s=s[:first]+s[last:]
 assert s==read(old/'rtl/vision_cascade_control.v'),'controller edits exceeded boundedfinish;timer/budget/core must remain frozen'
 s=read(R/'rtl/vision_region100.v').replace('parameter NEUTRAL_BITS=16,BRAKE_FAST=0','parameter NEUTRAL_BITS=16').replace('(BRAKE_FAST || distance<=120) ?','distance<=120 ?')
 s=s.replace(" // Fast braking first suppresses velocity over the wide100px approach, then\n // hands over to a narrow precision hold. The wide profile remains available.\n","")
 s=s.replace(" wire [15:0] capture_radius=BRAKE_FAST ? 16'd35 : radius-10;\n wire [15:0] trend_radius=BRAKE_FAST ? 16'd60 : radius-5;",
             " wire [15:0] capture_radius=radius-10;\n wire [15:0] trend_radius=radius-5;")
 s=s.replace("wire exit_now=distance>(BRAKE_FAST ? 70 : radius) || speed>(BRAKE_FAST ? 384 : 1280) || (distance>=trend_radius && outward && speed>=(BRAKE_FAST ? 192 : 320));",
             "wire exit_now=distance>radius || speed>1280 || (distance>=trend_radius && outward && speed>=320);")
 s=s.replace("wire leaving=holding && ((BRAKE_FAST && distance>75) || (!BRAKE_FAST && distance>radius+40) || (exit_now && exit_frames>=1));",
             "wire leaving=holding && (distance>radius+40 || (exit_now && exit_frames>=1));")
 first=s.index(' // A bounded desired ball speed');last=s.index(' reg [3:0] pipe=0;',first);s=s[:first]+s[last:]
 s=s.replace('p_stage<=final_p;d_stage<=final_d;','p_stage<=p_term;d_stage<=d_product>>>4;')
 s=s.replace('hold_stage<=0;stall_frames<=0;end','hold_stage<=0;end')
 s=s.replace('entry_frames<=0;exit_frames<=0;stall_frames<=0;end','entry_frames<=0;exit_frames<=0;end')
 s=s.replace('phase<=2;stall_frames<=0;end','phase<=2;end')
 s=s.replace('entry_frames<=0;exit_frames<=0;changed<=0;stall_frames<=0;end','entry_frames<=0;exit_frames<=0;changed<=0;end')
 s=s.replace(" // A stalled low-speed ball uses a controlled50Hz restart. High-speed braking\n // retains the original200Hz authority.\n","")
 s=s.replace("assign max_hz=stall_assist ? 16'd50 : (BRAKE_FAST && range_speed>=2560 ? 16'd200 : (BRAKE_FAST && (range_speed>1280 || motor_far) ? 16'd100 : range_distance<=120 ? (motor_far || range_speed>1280 ? 16'd50 : 16'd20) : (range_distance<=240 ? 16'd100 : 16'd200)));",
             "assign max_hz=range_distance<=120 ? (motor_far || range_speed>1280 ? 16'd50 : 16'd20) : (range_distance<=240 ? 16'd100 : 16'd200);")
 s=s.replace("assign slew_rate=stall_assist ? 16'd80 : (BRAKE_FAST && range_speed>=2560 ? 16'd256 : (BRAKE_FAST && (range_speed>1280 || motor_far) ? 16'd160 : range_distance<=120 ? (motor_far || range_speed>1280 ? 16'd80 : 16'd12) : (range_distance<=240 ? 16'd100 : 16'd160)));",
             "assign slew_rate=range_distance<=120 ? (motor_far || range_speed>1280 ? 16'd80 : 16'd12) : (range_distance<=240 ? 16'd100 : 16'd160);")
 s=s.replace('wire exit_now=distance>radius || speed>(BRAKE_FAST ? 384 : 1280) || (distance>=(BRAKE_FAST ? radius-25 : trend_radius) && outward && speed>=(BRAKE_FAST ? 192 : 320));','wire exit_now=distance>radius || speed>1280 || (distance>=trend_radius && outward && speed>=320);')
 s=s.replace("assign max_hz=BRAKE_FAST && range_speed>=2560 ? 16'd200 : (BRAKE_FAST && (range_speed>1280 || motor_far) ? 16'd100 : range_distance<=120 ?","assign max_hz=range_distance<=120 ?").replace("(range_distance<=240 ? 16'd100 : 16'd200));","(range_distance<=240 ? 16'd100 : 16'd200);")
 s=s.replace("assign slew_rate=BRAKE_FAST && range_speed>=2560 ? 16'd256 : (BRAKE_FAST && (range_speed>1280 || motor_far) ? 16'd160 : range_distance<=120 ?","assign slew_rate=range_distance<=120 ?").replace("(range_distance<=240 ? 16'd100 : 16'd160));","(range_distance<=240 ? 16'd100 : 16'd160);")
 s=s.replace("    if(stall_candidate)begin if(stall_frames<16)stall_frames<=stall_frames+1'b1;end else stall_frames<=0;\n","")
 assert s==read(old/'rtl/vision_region100.v'),'policy modifications exceeded declared speed/preview branch'
 for rel,h in json.loads(read(old/'region100_verification.json'))['paired_host_sha256'].items():assert sha(R/rel)==h,'old paired host changed '+rel
 codec=". (Join-Path $PSScriptRoot 'asym_protocol.ps1')"
 assert read(R/'host/brake_fast_panel_cn.ps1').split(codec)[0]==read(old/'host/region100_panel_cn.ps1').split(codec)[0],'wire codecs changed'
 print('BRAKE_FAST_CONTRACT_PASS exact core/guards/timer/budget/bounds/detector/HDMI/pins/clocks/wireformats;boundedfinish and speed-policy only')
if __name__=='__main__':check()
