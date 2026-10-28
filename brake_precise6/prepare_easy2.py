"""Archive easy, then add feedback-verified continuous segment checkpoints."""
from pathlib import Path
import json,hashlib,shutil,zipfile
r=Path(__file__).resolve().parent;look=Path('D:/AAAProject/FPGA/AAA_LookHere')
read=lambda p:p.read_text(encoding='utf-8-sig')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a=look/'成功版本归档/20261024_easy2前';assert not a.exists();a.mkdir()
bundle=look/'VIS5_一键回中_easy_20261024.zip';shutil.copy2(bundle,a/bundle.name)
with zipfile.ZipFile(bundle) as z:assert z.testzip() is None;z.extractall(a/'published')
(a/'physical').mkdir()
for p in (r/'host/logs').glob('20261024_213*.txt'):shutil.copy2(p,a/'physical'/p.name)
shutil.copy2(r/'easy_failure_analysis.json',a/'physical/easy_failure_analysis.json')
(a/'manifest.json').write_text(json.dumps({'files':{p.relative_to(a).as_posix():sha(p) for p in a.rglob('*') if p.is_file()}},ensure_ascii=False,indent=2),encoding='utf-8')
(r/'easy2_lineage.json').write_text(json.dumps({'archive':str(a),'parent_bit_sha256':sha(r/'output/vision_follow_20261022_easy.bit'),'observed_fault':'F5 SP64 EN1 AB errors0,5760ms run,145 total steps','checkpoint':{'trigger_pulses':48,'trigger_ms':3500,'quiet_ms':40,'ratio_tolerance_counts':4},'relative_limit':48,'absolute_target':60,'feedback_limit':64,'physical_stability':False},ensure_ascii=False,indent=2),encoding='utf-8')
def edit(rel,old,new):
 p=r/rel;s=read(p);assert old in s,rel+' missing edit';p.write_text(s.replace(old,new),encoding='utf-8-sig' if rel.endswith('.ps1') else 'utf-8')
edit('rtl/vision_servo_core.v','FAST_MS_CYCLES=50000,','FAST_MS_CYCLES=50000,CHECKPOINT_CAPABLE=0,')
edit('rtl/vision_servo_core.v','input wire fast_mode,input wire signed [15:0] fast_rate_hz,','input wire fast_mode,input wire signed [15:0] fast_rate_hz,input wire checkpoint,')
anchor=' wire fast_wrong=(fast_commands>0 && fast_displacement<0) || (fast_commands<0 && fast_displacement>0);'
edit('rtl/vision_servo_core.v',anchor,anchor+'''
 // Checkpoints never change origin,MC,limits or clear a fault. Each segment must
 // first drain real feedback; compare its net motion to the measured1.28 ratio.
 reg signed [31:0] checkpoint_p=0,checkpoint_m=0;
 wire signed [9:0] checkpoint_dp=$signed(position[8:0])-$signed(checkpoint_p[8:0]);
 wire signed [9:0] checkpoint_dm=$signed(command_position[8:0])-$signed(checkpoint_m[8:0]);
 wire signed [18:0] checkpoint_pw={{9{checkpoint_dp[9]}},checkpoint_dp};
 wire signed [18:0] checkpoint_mw={{9{checkpoint_dm[9]}},checkpoint_dm};
 wire signed [18:0] checkpoint_difference=(checkpoint_pw<<<8)-((checkpoint_mw<<<8)+(checkpoint_mw<<<6)+(checkpoint_mw<<<3));
 wire checkpoint_consistent=checkpoint_difference<=19'sd1024 && checkpoint_difference>=-19'sd1024 && wrong_direction==0;
''')
edit('rtl/vision_servo_core.v','fast_ms<=0;fast_age<=0;fast_credit<=0;fast_count<=0;fast_commands<=0;fast_anchor<=0;fast_dir_wait<=0;','fast_ms<=0;fast_age<=0;fast_credit<=0;fast_count<=0;fast_commands<=0;fast_anchor<=0;fast_dir_wait<=0;checkpoint_p<=0;checkpoint_m<=0;')
edit('rtl/vision_servo_core.v','action_timer<=0;active<=1;done<=0;state<=CHECK;cancel_reason<=0;reject_reason<=0;accepted_count<=accepted_count+1\'b1;',
 'action_timer<=0;active<=1;done<=0;state<=CHECK;cancel_reason<=0;reject_reason<=0;accepted_count<=accepted_count+1\'b1;checkpoint_p<=position;checkpoint_m<=command_position;')
edit('rtl/vision_servo_core.v',"      if(visual_target>TARGET_LIMIT || visual_target< -TARGET_LIMIT || fast_magnitude>200)begin", "      if(CHECKPOINT_CAPABLE && checkpoint && following && fast_rate_hz==0 && fast_count==0 && checkpoint_consistent)begin\n       // A verified quiet segment boundary is not a position-arrived event.\n       active<=0;done<=0;state<=READY;phase_count<=0;completed_count<=completed_count+1'b1;\n      end else if(visual_target>TARGET_LIMIT || visual_target< -TARGET_LIMIT || fast_magnitude>200)begin")
edit('rtl/vision_cascade_control.v','input wire core_ready,core_busy,input wire [3:0] fault,','input wire core_ready,core_busy,input wire [7:0] core_spent,input wire [3:0] fault,')
edit('rtl/vision_cascade_control.v','output reg run=0,request=0,output wire following,external_cancel,','output reg run=0,request=0,output wire following,external_cancel,checkpoint,')
anchor=' reg signed [18:0] prediction_offset=0;reg [5:0] quiet_ms=20;'
edit('rtl/vision_cascade_control.v',anchor,anchor+'''
 reg quiescing=0;reg [5:0] checkpoint_ms=0;reg [11:0] segment_ms=0;
 wire checkpoint_due=run && selection==1 && core_busy && (core_spent>=48 || (segment_ms>=3500 && core_spent!=0));
 assign checkpoint=run && selection==1 && quiescing && checkpoint_ms>=40;
''')
edit('rtl/vision_cascade_control.v','prediction_offset<=0;quiet_ms<=20;','prediction_offset<=0;quiet_ms<=20;quiescing<=0;checkpoint_ms<=0;segment_ms<=0;')
edit('rtl/vision_cascade_control.v','    mc<=0;\n    if(quiet_ms<20)', '''    mc<=0;
    if(run && core_busy)begin if(segment_ms<4095)segment_ms<=segment_ms+1'b1;end else segment_ms<=0;
    if(quiescing)begin if(checkpoint_ms<63)checkpoint_ms<=checkpoint_ms+1'b1;end else checkpoint_ms<=0;
    if(quiet_ms<20)''')
edit('rtl/vision_cascade_control.v','if((selection==1 && valid && pending) || selection==2 || (selection==3 && valid))begin','if(!quiescing && !checkpoint_due && ((selection==1 && valid && pending) || selection==2 || (selection==3 && valid)))begin')
edit('rtl/vision_cascade_control.v','else if(run && permit && core_ready && !request_wait &&','else if(run && permit && core_ready && !request_wait && !quiescing &&')
anchor='   if(run && (fault!=0 || !enable_request || !k4_n || !permit || expired || key_event))begin'
edit('rtl/vision_cascade_control.v',anchor,'''   if(checkpoint_due)quiescing<=1;
   if(quiescing || checkpoint_due)begin frequency_hz<=0;inner_moving<=0;rate_pending<=0;end
   if(quiescing && run && permit && core_ready)begin
    quiescing<=0;checkpoint_ms<=0;segment_ms<=0;request_wait<=0;
    reference_q8<=position*256;last_reference_q8<=position*256;
    frequency_hz<=0;feedback_term<=0;ff_term<=0;rate_pending<=0;inner_moving<=0;
    prediction_offset<=position*256-command_q8;quiet_ms<=20;
   end
'''+anchor)
edit('rtl/vision_cascade_control.v','if(!run)begin frequency_hz<=0;pending<=0;inner_moving<=0;end','if(!run)begin frequency_hz<=0;pending<=0;inner_moving<=0;quiescing<=0;checkpoint_ms<=0;segment_ms<=0;end')
edit('rtl/vision_monitor.v','wire n_run,n_request,n_following,n_external_cancel,n_neutral_ready,n_updated,n_stable;','wire n_run,n_request,n_following,n_external_cancel,n_neutral_ready,n_updated,n_stable,n_checkpoint;')
edit('rtl/vision_monitor.v','.FAST_CAPABLE(1),.FAST_MS_CYCLES(MS_CYCLES)', '.FAST_CAPABLE(1),.CHECKPOINT_CAPABLE(1),.FAST_MS_CYCLES(MS_CYCLES)')
edit('rtl/vision_monitor.v','.fast_mode(c_selected && (n_run || busy)),.fast_rate_hz(n_frequency),','.fast_mode(c_selected && (n_run || busy)),.fast_rate_hz(n_frequency),.checkpoint(c_selected && n_checkpoint),')
edit('rtl/vision_monitor.v','.core_ready(ready),.core_busy(busy),.fault(fault),.step(motor_step),.run(n_run)', '.core_ready(ready),.core_busy(busy),.core_spent(spent),.fault(fault),.step(motor_step),.checkpoint(n_checkpoint),.run(n_run)')
edit('rtl/vision_cascade_outer.v','residual_now>512 || residual_now< -512','residual_now>2048 || residual_now< -2048')
edit('user_source/hdl_source/design_top_wrapper.v','.DEFAULT_DEADZONE(3),.CASCADE_DEFAULT(1)', '.DEFAULT_DEADZONE(3),.DEFAULT_LIMIT(48),.CASCADE_DEFAULT(1)')
edit('build.ps1',"'cascade','easy'","'cascade','easy','easy2'")
edit('build.ps1',"$Release='easy'","$Release='easy2'")
edit('cascade_contract.py','.DEFAULT_DEADZONE(3),.CASCADE_DEFAULT(1)', '.DEFAULT_DEADZONE(3),.DEFAULT_LIMIT(48),.CASCADE_DEFAULT(1)')
# Preserve every protocol encoder/parser while adjusting presentation/default only.
edit('host/vision_panel_cn.ps1',"694 0 60 32","694 0 60 48")
edit('host/vision_panel_cn.ps1','$limit.Value -ne 32','$limit.Value -ne 48')
edit('host/vision_panel_cn.ps1','$deadzone.Value=3;$limit.Value=32','$deadzone.Value=3;$limit.Value=48')
edit('host/vision_panel_cn.ps1','幅度32','幅度48')
edit('host/vision_panel_cn.ps1','限幅32','限幅48')
edit('host/vision_panel_cn.ps1','easy新bit','easy2新bit')
edit('host/cascade_controls.ps1','easy.bit','easy2.bit')
edit('host/cascade_controls.ps1','段脉冲={2}/64','段脉冲={2}/64（连续模式48起核对换段）')
agents=r/'AGENTS.md';agents.write_text('# easy2 continuous segment repair authorization\n\nUser reports immediate F5 at SP64 and requests larger up/down range. Explicit change: AUTO selection1 cooperatively yields at48pulses or3.5s with real40ms quiet,feedback drained and net1.28ratio within4counts; no fault reset, no per-frame budget reset. F1-F8/core64pulse5s/MC/P64/absolute60 retained. Relative preset32->48; high-speed observer innovation reset32->128px. Manual/calibration paths unchanged. K1/K3/K2 UX preserved. Archive easy2_lineage immutable. Only publish_easy2.py current. Real centering still pending.\n\n'+read(agents),encoding='utf-8')
print('EASY2_PREPARED')
