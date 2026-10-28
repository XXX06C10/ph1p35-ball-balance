"""Archive confirmed easy2, then enable bounded predictive speed-envelope control."""
from pathlib import Path
import json,hashlib,zipfile,shutil
r=Path(__file__).resolve().parent;look=Path('D:/AAAProject/FPGA/AAA_LookHere')
read=lambda p:p.read_text(encoding='utf-8-sig')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a=look/'成功版本归档/20261025_easy3前_已确认easy2还不错';assert not a.exists();a.mkdir()
zpath=look/'VIS5_连续纠偏修复_easy2_20261024.zip';shutil.copy2(zpath,a/zpath.name)
with zipfile.ZipFile(zpath) as z:assert z.testzip() is None;z.extractall(a/'published')
(a/'physical').mkdir()
for p in (r/'host/logs').glob('20261025_12*.txt'):shutil.copy2(p,a/'physical'/p.name)
shutil.copy2(r/'braking_log_analysis.json',a/'physical/braking_log_analysis.json')
(a/'human_feedback.json').write_text(json.dumps({'confirmation':'这一版还不错','request':'increase amplitude,anticipatory braking,three-stage approach,keep simple K3/K2','intervention':'user confirms hand contact/ball movement during latest logs;do not identify true dynamics from these runs','no_precision_acceptance':True},ensure_ascii=False,indent=2),encoding='utf-8')
(a/'manifest.json').write_text(json.dumps({'files':{p.relative_to(a).as_posix():sha(p) for p in a.rglob('*') if p.is_file()}},ensure_ascii=False,indent=2),encoding='utf-8')
(r/'easy3_lineage.json').write_text(json.dumps({'archive':str(a),'parent_bit_sha256':sha(r/'output/vision_follow_20261022_easy2.bit'),'reference':json.loads(read(r/'references/user_lqt_20261025/source.json')),'feedback':'qualitative easy2 improvement;logs contain manual intervention','relative_limit':60,'absolute_target':60,'feedback_limit':64,'max_hz':200,'slew_rate':200,'velocity_gain_q8':64,'prediction_base_ms':80,'reversal_ms_per_count':5,'physical_model_identified':False,'stopping_distance_is_approximate':True},ensure_ascii=False,indent=2),encoding='utf-8')
def edit(rel,old,new):
 p=r/rel;s=read(p);assert old in s,rel+':missing edit';p.write_text(s.replace(old,new),encoding='utf-8-sig' if rel.endswith('.ps1') else 'utf-8')
edit('rtl/vision_cascade_config.v','DEFAULT_PRESET ? 40','DEFAULT_PRESET ? 64')
edit('rtl/vision_cascade_config.v','DEFAULT_PRESET ? 100','DEFAULT_PRESET ? 200')
edit('rtl/vision_cascade_config.v','DEFAULT_PRESET ? 102','DEFAULT_PRESET ? 200')
edit('user_source/hdl_source/design_top_wrapper.v','.DEFAULT_LIMIT(48)','.DEFAULT_LIMIT(60)')
edit('build.ps1',"'easy','easy2'","'easy','easy2','easy3'")
edit('build.ps1',"$Release='easy2'","$Release='easy3'")
edit('cascade_contract.py','.DEFAULT_LIMIT(48)','.DEFAULT_LIMIT(60)')
edit('rtl/vision_monitor.v','n_updated,n_stable,n_checkpoint;','n_updated,n_stable,n_checkpoint;\n    wire [1:0] n_control_phase;')
edit('rtl/vision_monitor.v','.updated(n_updated),.stable(n_stable),.time_ms(n_time),.frame_time_ms(n_frame_time));','.updated(n_updated),.stable(n_stable),.time_ms(n_time),.frame_time_ms(n_frame_time),\n     .predictive(c_selected && c_builtin),.control_phase(n_control_phase));')
edit('rtl/vision_monitor.v',".flags({7'd0,c_profile_ready,", ".flags({4'd0,(c_selected && c_builtin),n_control_phase,c_profile_ready,")
edit('rtl/vision_cascade_outer.v','output wire [31:0] frame_time_ms','output wire [31:0] frame_time_ms,\n input wire predictive,output reg [1:0] control_phase=2')
edit('rtl/vision_cascade_outer.v','reg [11:0] pipe=0','reg [12:0] pipe=0')
anchor=' wire signed [29:0] delay_product=$signed(velocity_q4[17:0])*$signed({1\'b0,delay_fraction});'
edit('rtl/vision_cascade_outer.v',anchor,'''
 // Bounded reversal lookahead:80ms plus5ms/count to the available braking angle.
 // No mechanical mm/angle model is inferred from manually disturbed logs.
 wire brake_positive=polarity ? velocity_q4<0 : velocity_q4>=0;
 wire signed [9:0] brake_target_raw=$signed(neutral)+(brake_positive ? $signed({1'b0,limit}) : -$signed({1'b0,limit}));
 wire signed [9:0] brake_target=brake_target_raw>60 ? 10'sd60 : (brake_target_raw< -60 ? -10'sd60 : brake_target_raw);
 wire signed [9:0] brake_span_raw=brake_positive ? brake_target-$signed(position[8:0]) : $signed(position[8:0])-brake_target;
 wire [6:0] brake_span=brake_span_raw<0 ? 0 : (brake_span_raw>120 ? 120 : brake_span_raw[6:0]);
 wire [11:0] look_fraction=12'd328+({5'd0,brake_span}<<4)+({5'd0,brake_span}<<2)+({5'd0,brake_span}>>1);
 wire [11:0] effective_fraction=predictive ? look_fraction : {1'b0,delay_fraction};
 wire signed [29:0] delay_product=$signed(velocity_q4[17:0])*$signed({1'b0,effective_fraction});
 reg signed [28:0] measured_velocity_product=0;
 wire signed [28:0] fast_velocity_product=$signed(dx)*$signed({1'b0,reciprocal_reg});
 wire signed [31:0] fast_velocity_raw=$signed(measured_velocity_product>>>4);
 wire signed [31:0] fast_velocity_next=($signed(velocity_q4)+clamp_speed(fast_velocity_raw))>>>1;
 reg signed [17:0] goal_velocity_q4=0;reg [1:0] phase_candidate=2;
 wire approaching=(err>0 && velocity_q4<0) || (err<0 && velocity_q4>0);
 wire predicted_crossing=(err>0 && predicted_error<=0) || (err<0 && predicted_error>=0);
 wire [17:0] predicted_distance=predicted_error<0 ? -predicted_error : predicted_error;
 wire [13:0] effective_distance=approaching ? (predicted_crossing ? 14'd0 : {1'b0,predicted_distance[16:4]}) : {1'b0,abs_error[12:0]};
 function [9:0] velocity_envelope;
  input [13:0] d;reg [14:0] value;
  begin
   if(d<=64)value=d<<1;
   else if(d<=256)value=128+((d-64)>>1);
   else value=224+((d-256)>>2);
   velocity_envelope=value>400 ? 10'd400 : value[9:0];
  end
 endfunction
 wire [9:0] speed_goal=velocity_envelope(effective_distance);
 wire signed [17:0] velocity_error_q4=predictive ? $signed(velocity_q4[17:0])-goal_velocity_q4 : $signed(velocity_q4[17:0]);
''')
edit('rtl/vision_cascade_outer.v','d_product=$signed(velocity_q4[17:0])*','d_product=$signed(velocity_error_q4)*')
edit('rtl/vision_cascade_outer.v','integral_product<=0;integral_increment<=0;integral_q16<=0;integral_ms<=0;stable_ms<=0;stable<=0;updated<=0;', 'integral_product<=0;integral_increment<=0;integral_q16<=0;integral_ms<=0;stable_ms<=0;stable<=0;updated<=0;measured_velocity_product<=0;goal_velocity_q4<=0;phase_candidate<=2;control_phase<=2;')
edit('rtl/vision_cascade_outer.v',"pipe<={pipe[10:0],frame", "pipe<={pipe[11:0],frame")
edit('rtl/vision_cascade_outer.v','if(pipe[0])begin advance_q4<=','if(pipe[0])begin measured_velocity_product<=fast_velocity_product;advance_q4<=')
edit('rtl/vision_cascade_outer.v','velocity_q4<=innovation_reset ? 0 : clamp_speed(next_velocity);','velocity_q4<=innovation_reset ? 0 : (predictive ? clamp_speed(fast_velocity_next) : clamp_speed(next_velocity));')
old='''   if(pipe[7])begin p_stage<=p_product;d_stage<=d_product;end
   if(pipe[8])begin
    pterm<=(err<=$signed({1'b0,deadzone}) && err>=-$signed({1'b0,deadzone})) ? 0 : $signed(p_stage>>>8);
    dterm<=velocity_q4<48 && velocity_q4> -48 ? 0 : $signed(d_stage>>>4);
    integral_increment<=$signed(i_scaled>>>16);
   end
   if(pipe[9])pd_sum<=polarity ? -(pterm+dterm) : (pterm+dterm);
   if(pipe[10])relative_stage<=relative_clipped;
   if(pipe[11] && valid && !stale && !clear && !neutral_capture)begin target_q8<=absolute_clipped;updated<=1;end'''
new='''   if(pipe[7])begin
    if(abs_error<=deadzone && abs_speed<=128)goal_velocity_q4<=0;
    else goal_velocity_q4<=err>0 ? -$signed({4'd0,speed_goal,4'b0}) : (err<0 ? $signed({4'd0,speed_goal,4'b0}) : 18'sd0);
    if(abs_error<=24 && abs_speed<=640)phase_candidate<=2;
    else if(approaching && (predicted_crossing || abs_speed>((speed_goal+16)*16)))phase_candidate<=1;
    else phase_candidate<=0;
   end
   if(pipe[8])begin p_stage<=p_product;d_stage<=d_product;end
   if(pipe[9])begin
    pterm<=predictive || (err<=$signed({1'b0,deadzone}) && err>=-$signed({1'b0,deadzone})) ? 0 : $signed(p_stage>>>8);
    dterm<=predictive ? $signed(d_stage>>>4) : (velocity_q4<48 && velocity_q4> -48 ? 0 : $signed(d_stage>>>4));
    integral_increment<=$signed(i_scaled>>>16);
   end
   if(pipe[10])pd_sum<=polarity ? -(pterm+dterm) : (pterm+dterm);
   if(pipe[11])relative_stage<=relative_clipped;
   if(pipe[12] && valid && !stale && !clear && !neutral_capture)begin target_q8<=absolute_clipped;updated<=1;control_phase<=predictive ? phase_candidate : 2'd0;end'''
edit('rtl/vision_cascade_outer.v',old,new)
edit('rtl/vision_cascade_outer.v','if(clear || neutral_capture)begin legacy_velocity_q4<=0;', 'if(clear || neutral_capture)begin control_phase<=2;goal_velocity_q4<=0;legacy_velocity_q4<=0;')
edit('sim/tb_outer.v','frame_ms);',"frame_ms,1'b0);")
# Positional fixture needs the trailing phase output too.
edit('sim/tb_outer.v',"frame_ms,1'b0);", "frame_ms,1'b0,phase_unused);")
edit('sim/tb_outer.v','wire ready,updated,stable;','wire ready,updated,stable;wire [1:0] phase_unused;')
edit('sim/tb_easy.v','dut.c_kv==40','dut.c_kv==64')
edit('sim/tb_easy.v','dut.c_max_hz==100','dut.c_max_hz==200')
edit('sim/tb_easy.v','dut.c_slew==102','dut.c_slew==200')
edit('sim/tb_easy.v','.DEFAULT_LIMIT(48)','.DEFAULT_LIMIT(60)')
edit('sim/tb_cascade_plant.v','.DEFAULT_LIMIT(USE_PRESET ? 48 : 32)','.DEFAULT_LIMIT(USE_PRESET ? 60 : 32)')
edit('host/vision_panel_cn.ps1','easy2新bit','easy3新bit')
edit('host/vision_panel_cn.ps1','幅度48','幅度60')
edit('host/vision_panel_cn.ps1','限幅48','限幅60')
edit('host/vision_panel_cn.ps1','694 0 60 48','694 0 60 60')
edit('host/vision_panel_cn.ps1','$limit.Value -ne 48','$limit.Value -ne 60')
edit('host/vision_panel_cn.ps1','$deadzone.Value=3;$limit.Value=48','$deadzone.Value=3;$limit.Value=60')
edit('host/cascade_controls.ps1','easy2.bit','easy3.bit')
edit('host/cascade_controls.ps1',"$simpleState.Text=$live+", "$phaseName=if($D.flags -band 2048){@('加速送回','预判制动','中心微调','保留')[($D.flags -shr 9) -band 3]}else{'原控制'}\n $simpleState.Text=$live+'｜'+$phaseName+")
agents=r/'AGENTS.md';agents.write_text('# easy3 predictive braking authorization (2026-10-25)\n\nUser confirms easy2 qualitatively improved;requests larger amplitude,anticipatory three-stage stopping,and review of user-lqt GitHub repository. Latest logs have manual intervention;do not identify physical dynamics from them. Preserve accepted easy2 checkpoint,all core F1-F8/64pulse5s/MC/P64/absolute60/manual/IO/clocks. Relative60,preset200Hz/slew200,fast frame velocity and bounded actuator-reversal lookahead/speed envelope;explicit C custom keeps legacy PD. D1 reserved flags11/10:9 indicate predictive active/phase;wire sizes/XOR unchanged. K1/K3/K2 UX unchanged. Archive easy3_lineage immutable. Real acceptance pending. Only publish_easy3.py current.\n\n'+read(agents),encoding='utf-8')
print('EASY3_PREPARED')
