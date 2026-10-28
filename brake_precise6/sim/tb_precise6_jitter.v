`timescale 1ns/1ps
module tb_precise6_jitter;
 reg clk=0;always #5 clk=~clk;reg rst=0,u=0,valid=1,clear=0,run=1,stale=0,capture=0;
 reg [10:0] x=908;reg signed [31:0] v=0,pos=0;
 wire signed [31:0] t,gold,fv;integer i,cancelled,prevx,new_assist,old_assist;reg signed [15:0] replay[0:160];
 vision_region100 #(.BRAKE_FAST(1)) dut(.clk(clk),.rst_n(rst),.run(run),.updated(u),.valid(valid),.stale(stale),.clear(clear),.neutral_capture(capture),.polarity(1'b0),.x(x),.center(16'd960),.velocity_q4(v),.work_min(-32'sd182),.work_max(32'sd364),.position(pos),.neutral(16'sd0),.zone_setting(16'd100),.target_q8(t),.filtered_velocity_q4(fv));
 vision_region100_precise5 #(.BRAKE_FAST(1)) parent(.clk(clk),.rst_n(rst),.run(run),.updated(u),.valid(valid),.stale(stale),.clear(clear),.neutral_capture(capture),.polarity(1'b0),.x(x),.center(16'd960),.velocity_q4(v),.work_min(-32'sd182),.work_max(32'sd364),.position(pos),.neutral(16'sd0),.zone_setting(16'd100),.target_q8(gold));
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 task sample(input integer e,vv);begin pos=t>>>8;x=960+e;v=vv;u=1;tick(1);u=0;tick(9);end endtask
 task reset_h;begin clear=1;tick(2);clear=0;end endtask
 initial begin
  tick(3);rst=1;
  for(i=0;i<100;i=i+1)begin sample(-52,0);if(dut.escape_active || t!=gold)$fatal(1,"noise-free static differs from parent");end
  for(i=0;i<60;i=i+1)begin sample(-52+i,10*16);if(dut.escape_active || t!=gold)$fatal(1,"noise-free movement differs from parent");end
  reset_h;for(i=0;i<90;i=i+1)begin sample(-52,80*16);if(dut.escape_active || t!=gold)$fatal(1,"one-direction speed mistaken for jitter");end
  reset_h;for(i=0;i<90;i=i+1)begin sample(-52,(i%4<2 ? 20 : -20)*16);if(dut.escape_active || t!=gold)$fatal(1,"small velocity quantization changed parent");end
  $display("PRECISE6_NOISE_FREE_EQUIVALENCE_PASS static_and_motion");
  reset_h;
  for(i=0;i<40;i=i+1)sample(-52,(i%4<2 ? 80 : -80)*16);
  if(!dut.escape_active)$fatal(1,"initial static qualification missing");
  cancelled=0;
  for(i=0;i<350;i=i+1)begin
   sample(-52+(i%24<12 ? -4 : 4),(i%4<2 ? 80 : -80)*16);
   if(!parent.stall_assist)cancelled=cancelled+1;
   if(!dut.stall_assist || fv!=0)$fatal(1,"8px jitter cancelled acquired escape i=%d",i);
  end
  if(cancelled<50 || t!=-64*256)$fatal(1,"parent reproduction or new progression missing cancellations=%d T=%d",cancelled,t);
  $display("PRECISE5_JITTER_REPRO_PASS old_cancelled=%0d new_near64",cancelled);
  sample(-30,200*16);if(dut.escape_active || dut.stall_assist || fv==0)$fatal(1,"large movement must immediately restore brake");
  // Even a newly-qualified quiet window may not override acquired-anchor movement.
  reset_h;for(i=0;i<40;i=i+1)sample(-52,(i%4<2 ? 80 : -80)*16);
  force dut.quiet_frames=7'd40;force dut.quiet_min=11'd900;force dut.quiet_max=11'd908;
  force dut.quiet_anchor_q4=17'sd14400;force dut.quiet_mean_q4=17'sd14400;
  sample(-60,0);if(dut.stall_assist || dut.escape_active)$fatal(1,"old quiet qualification overrode real motion");
  release dut.quiet_frames;release dut.quiet_min;release dut.quiet_max;release dut.quiet_anchor_q4;release dut.quiet_mean_q4;
  reset_h;for(i=0;i<40;i=i+1)sample(107,(i%4<2 ? 80 : -80)*16);
  for(i=0;i<350;i=i+1)begin sample(107+(i%24<12 ? -4 : 4),(i%4<2 ? 80 : -80)*16);if(!dut.stall_assist)$fatal(1,"far jitter cancelled");end
  if(t!=96*256)$fatal(1,"far96 missing");
  for(i=0;i<12;i=i+1)sample(107+i/2,0);
  sample(114,0);sample(115,0);if(dut.escape_active)$fatal(1,"sustained slow displacement not released");
  reset_h;for(i=0;i<60;i=i+1)sample(-52,(i%4<2 ? 80 : -80)*16);valid=0;tick(2);if(dut.escape_active)$fatal(1,"invalid reset");valid=1;
  for(i=0;i<60;i=i+1)sample(-52,(i%4<2 ? 80 : -80)*16);stale=1;tick(2);if(dut.escape_active)$fatal(1,"stale reset");stale=0;
  for(i=0;i<60;i=i+1)sample(-52,(i%4<2 ? 80 : -80)*16);run=0;tick(2);if(dut.escape_active)$fatal(1,"stop reset");run=1;
  for(i=0;i<60;i=i+1)sample(-52,(i%4<2 ? 80 : -80)*16);capture=1;tick(2);if(dut.escape_active)$fatal(1,"K3 reset");capture=0;

  // Exact coordinate errors from 211211 log epoch1 120..126s; derived30fps velocity
  // and ideal arrived motor feedback isolate policy, not a physical replay.
  replay[0]=-16'sd48;
  replay[1]=-16'sd48;
  replay[2]=-16'sd48;
  replay[3]=-16'sd48;
  replay[4]=-16'sd48;
  replay[5]=-16'sd51;
  replay[6]=-16'sd50;
  replay[7]=-16'sd50;
  replay[8]=-16'sd51;
  replay[9]=-16'sd50;
  replay[10]=-16'sd50;
  replay[11]=-16'sd51;
  replay[12]=-16'sd50;
  replay[13]=-16'sd51;
  replay[14]=-16'sd50;
  replay[15]=-16'sd50;
  replay[16]=-16'sd50;
  replay[17]=-16'sd51;
  replay[18]=-16'sd50;
  replay[19]=-16'sd50;
  replay[20]=-16'sd50;
  replay[21]=-16'sd51;
  replay[22]=-16'sd50;
  replay[23]=-16'sd50;
  replay[24]=-16'sd50;
  replay[25]=-16'sd50;
  replay[26]=-16'sd50;
  replay[27]=-16'sd48;
  replay[28]=-16'sd50;
  replay[29]=-16'sd48;
  replay[30]=-16'sd48;
  replay[31]=-16'sd50;
  replay[32]=-16'sd48;
  replay[33]=-16'sd50;
  replay[34]=-16'sd48;
  replay[35]=-16'sd48;
  replay[36]=-16'sd47;
  replay[37]=-16'sd47;
  replay[38]=-16'sd47;
  replay[39]=-16'sd48;
  replay[40]=-16'sd47;
  replay[41]=-16'sd48;
  replay[42]=-16'sd45;
  replay[43]=-16'sd47;
  replay[44]=-16'sd48;
  replay[45]=-16'sd47;
  replay[46]=-16'sd47;
  replay[47]=-16'sd45;
  replay[48]=-16'sd47;
  replay[49]=-16'sd47;
  replay[50]=-16'sd48;
  replay[51]=-16'sd50;
  replay[52]=-16'sd51;
  replay[53]=-16'sd50;
  replay[54]=-16'sd54;
  replay[55]=-16'sd53;
  replay[56]=-16'sd50;
  replay[57]=-16'sd54;
  replay[58]=-16'sd53;
  replay[59]=-16'sd53;
  replay[60]=-16'sd53;
  replay[61]=-16'sd53;
  replay[62]=-16'sd53;
  replay[63]=-16'sd53;
  replay[64]=-16'sd53;
  replay[65]=-16'sd53;
  replay[66]=-16'sd53;
  replay[67]=-16'sd53;
  replay[68]=-16'sd53;
  replay[69]=-16'sd53;
  replay[70]=-16'sd53;
  replay[71]=-16'sd53;
  replay[72]=-16'sd53;
  replay[73]=-16'sd53;
  replay[74]=-16'sd53;
  replay[75]=-16'sd53;
  replay[76]=-16'sd53;
  replay[77]=-16'sd53;
  replay[78]=-16'sd53;
  replay[79]=-16'sd53;
  replay[80]=-16'sd53;
  replay[81]=-16'sd53;
  replay[82]=-16'sd53;
  replay[83]=-16'sd53;
  replay[84]=-16'sd53;
  replay[85]=-16'sd53;
  replay[86]=-16'sd53;
  replay[87]=-16'sd53;
  replay[88]=-16'sd53;
  replay[89]=-16'sd53;
  replay[90]=-16'sd53;
  replay[91]=-16'sd53;
  replay[92]=-16'sd53;
  replay[93]=-16'sd53;
  replay[94]=-16'sd53;
  replay[95]=-16'sd53;
  replay[96]=-16'sd53;
  replay[97]=-16'sd53;
  replay[98]=-16'sd53;
  replay[99]=-16'sd53;
  replay[100]=-16'sd53;
  replay[101]=-16'sd53;
  replay[102]=-16'sd53;
  replay[103]=-16'sd53;
  replay[104]=-16'sd54;
  replay[105]=-16'sd53;
  replay[106]=-16'sd53;
  replay[107]=-16'sd51;
  replay[108]=-16'sd53;
  replay[109]=-16'sd53;
  replay[110]=-16'sd53;
  replay[111]=-16'sd53;
  replay[112]=-16'sd51;
  replay[113]=-16'sd53;
  replay[114]=-16'sd51;
  replay[115]=-16'sd51;
  replay[116]=-16'sd53;
  replay[117]=-16'sd50;
  replay[118]=-16'sd53;
  replay[119]=-16'sd51;
  replay[120]=-16'sd51;
  replay[121]=-16'sd53;
  replay[122]=-16'sd48;
  replay[123]=-16'sd50;
  replay[124]=-16'sd50;
  replay[125]=-16'sd50;
  replay[126]=-16'sd50;
  replay[127]=-16'sd53;
  replay[128]=-16'sd53;
  replay[129]=-16'sd51;
  replay[130]=-16'sd56;
  replay[131]=-16'sd54;
  replay[132]=-16'sd53;
  replay[133]=-16'sd54;
  replay[134]=-16'sd54;
  replay[135]=-16'sd53;
  replay[136]=-16'sd54;
  replay[137]=-16'sd54;
  replay[138]=-16'sd54;
  replay[139]=-16'sd54;
  replay[140]=-16'sd54;
  replay[141]=-16'sd54;
  replay[142]=-16'sd54;
  replay[143]=-16'sd54;
  replay[144]=-16'sd54;
  replay[145]=-16'sd54;
  replay[146]=-16'sd54;
  replay[147]=-16'sd54;
  replay[148]=-16'sd54;
  replay[149]=-16'sd54;
  replay[150]=-16'sd54;
  replay[151]=-16'sd54;
  replay[152]=-16'sd54;
  replay[153]=-16'sd54;
  replay[154]=-16'sd54;
  replay[155]=-16'sd54;
  replay[156]=-16'sd54;
  replay[157]=-16'sd54;
  replay[158]=-16'sd54;
  replay[159]=-16'sd53;
  replay[160]=-16'sd54;
  reset_h;prevx=replay[0];new_assist=0;old_assist=0;
  for(i=0;i<161;i=i+1)begin
   sample(replay[i],(replay[i]-prevx)*30*16);prevx=replay[i];
   if(dut.stall_assist)new_assist=new_assist+1;
   if(parent.stall_assist)old_assist=old_assist+1;
  end
  $display("PRECISE6_COORDINATE_REPLAY new_assist=%0d old_assist=%0d",new_assist,old_assist);
  if(new_assist<=old_assist+30)$fatal(1,"coordinate replay no material continuity improvement");
  $display("PRECISE6_JITTER_PASS acquired8pxjitter,near64,far96,realmotion,slowwithdraw,invalid,stale,stop,K3");$finish;
 end
endmodule
// 100px product region: soft position attraction, velocity damping, hysteretic level hold.
// This module never rebases encoder/STEP origins or changes the fixed work window.
module vision_region100_precise5 #(parameter NEUTRAL_BITS=16,BRAKE_FAST=0)(
 input wire clk,rst_n,run,updated,valid,stale,clear,neutral_capture,polarity,
 input wire [10:0] x,input wire [15:0] center,
 input wire signed [31:0] velocity_q4,work_min,work_max,position,
 input wire signed [NEUTRAL_BITS-1:0] neutral,input wire [15:0] zone_setting,
 output reg signed [31:0] target_q8=0,output reg changed=0,holding=0,
 output reg [1:0] phase=2,output wire [15:0] max_hz,slew_rate,
 output wire signed [31:0] filtered_velocity_q4
);
 wire signed [12:0] error=$signed({1'b0,x})-$signed({1'b0,center});
 wire [12:0] distance=error<0 ? -error : error;
 reg signed [17:0] vh1=0,vh2=0,vh3=0;
 wire signed [19:0] pair_a=$signed(velocity_q4[17:0])+$signed(vh1);
 wire signed [19:0] pair_b=$signed(vh2)+$signed(vh3);
 wire parked;
 wire signed [31:0] raw_velocity_q4=(BRAKE_FAST || distance<=120) ? $signed(pair_a)>>>1 : ($signed(pair_a)+$signed(pair_b))>>>2;
 // Suppress derivative noise only after independent raw-coordinate dwell.
 // Moving control retains the precise3 velocity/filter and braking law.
 assign filtered_velocity_q4=(BRAKE_FAST && parked) ? 32'sd0 : raw_velocity_q4;
 wire [31:0] speed=filtered_velocity_q4<0 ? -filtered_velocity_q4 : filtered_velocity_q4;
 wire [15:0] radius=zone_setting<60 ? 16'd100 : (zone_setting>100 ? 16'd100 : zone_setting);
 // Fast braking first suppresses velocity over the wide100px approach, then
 // hands over to a narrow precision hold. The wide profile remains available.
 wire [15:0] capture_radius=BRAKE_FAST ? 16'd35 : radius-10;
 wire [15:0] trend_radius=BRAKE_FAST ? 16'd60 : radius-5;
 wire outward=(error>0 && filtered_velocity_q4>0) || (error<0 && filtered_velocity_q4<0);
 // Position dwell is independent of derivative noise. Re-arm an old window
 // after its mean has drifted; a later stationary position can then qualify.
 reg [6:0] quiet_frames=0;reg [10:0] quiet_min=0,quiet_max=0;
 wire [10:0] next_min=(quiet_frames==0 || x<quiet_min) ? x : quiet_min;
 wire [10:0] next_max=(quiet_frames==0 || x>quiet_max) ? x : quiet_max;
 reg signed [16:0] quiet_mean_q4=0,quiet_anchor_q4=0;
 wire signed [16:0] raw_x_q4=$signed({2'b0,x,4'b0});
 wire signed [17:0] mean_delta=$signed(raw_x_q4)-$signed(quiet_mean_q4);
 wire signed [16:0] next_mean=quiet_frames==0 ? raw_x_q4 : quiet_mean_q4+($signed(mean_delta)>>>2);
 wire signed [17:0] mean_drift=$signed(next_mean)-$signed(quiet_anchor_q4);
 wire rearm_quiet=BRAKE_FAST && quiet_frames>=29 && (mean_drift>32 || mean_drift< -32);
 wire coordinate_quiet=(next_max-next_min)<=8;
 wire quiet_now=BRAKE_FAST ? coordinate_quiet : ((next_max-next_min)<=4 && speed<=384);
 assign parked=run && valid && !stale && !clear && !neutral_capture && quiet_frames>=29 && coordinate_quiet && mean_drift<=32 && mean_drift>=-32;
 wire trend_quiet=BRAKE_FAST ? (quiet_frames>=15 && coordinate_quiet && mean_drift<=32 && mean_drift>=-32) : (quiet_frames>=15 && quiet_now);
 wire enter_now=distance<=capture_radius && (speed<=192 || (BRAKE_FAST && trend_quiet));
 wire exit_now=distance>(BRAKE_FAST ? 70 : radius) || speed>(BRAKE_FAST ? 384 : 1280) || (distance>=trend_radius && outward && speed>=(BRAKE_FAST ? 192 : 320));
 reg [2:0] entry_frames=0;reg [1:0] exit_frames=0;
 wire entering=!holding && enter_now && entry_frames>=2;
 wire leaving=holding && ((BRAKE_FAST && distance>75) || (!BRAKE_FAST && distance>radius+40) || (exit_now && exit_frames>=1));
 // Continuous position gain: zero inside60px;2.8125counts at120px;
 //60counts at240px; beyond240px exactly the trusted far-position gain.
 wire [23:0] p_magnitude=distance<=60 ? 24'd0 : (distance<=120 ? (distance-60)*24'd12 : (distance<=240 ? 24'd720+(distance-120)*24'd122 : distance*24'd64));
 wire signed [24:0] p_term=error<0 ? -$signed({1'b0,p_magnitude}) : $signed({1'b0,p_magnitude});
 wire [7:0] d_gain=distance<=120 ? 8'd24 : (distance<240 ? 8'd24+(((distance-120)*13'd77)>>7) : 8'd96);
 // Smooth8px/s velocity noise deadband only in the fine region. No extrapolated x.
 wire signed [31:0] fine_velocity=distance<=120 ? (filtered_velocity_q4>128 ? filtered_velocity_q4-128 : (filtered_velocity_q4< -128 ? filtered_velocity_q4+128 : 0)) : filtered_velocity_q4;
 wire signed [31:0] d_product=$signed(fine_velocity[17:0])*$signed({1'b0,d_gain});
 // A bounded desired ball speed replaces large P+D tilts outside the fine zone.
 //125ms lookahead affects this control calculation only; raw coordinates stay raw.
 wire signed [19:0] predicted_error=$signed(error)+($signed(filtered_velocity_q4)>>>7);
 wire [19:0] predicted_distance=predicted_error<0 ? -predicted_error : predicted_error;
 wire [19:0] speed_envelope=predicted_distance<=90 ? 0 : (predicted_distance-90)>>1;
 wire [8:0] goal_speed=speed_envelope>200 ? 9'd200 : speed_envelope[8:0];
 wire signed [19:0] goal_velocity_q4=predicted_error>0 ? -$signed({1'b0,goal_speed,4'b0}) : (predicted_error<0 ? $signed({1'b0,goal_speed,4'b0}) : 20'sd0);
 wire signed [31:0] speed_error_q4=$signed(filtered_velocity_q4)-$signed(goal_velocity_q4);
 wire speed_control=BRAKE_FAST && (distance>120 || speed>1280);
 wire signed [31:0] controlled_p=speed_control ? 0 : $signed(p_term);
 wire signed [31:0] controlled_d=speed_control ? $signed(speed_error_q4)<<<1 : (BRAKE_FAST ? $signed(fine_velocity)<<<1 : $signed(d_product)>>>4);
 // Parked ball assistance uses coordinate excursion rather than requiring
 // every derivative sample to be almost zero. Motion returns to braking.
 reg [6:0] stall_frames=0;
 // Sixteen genuine results are approximately0.53s at30fps.
 wire stall_candidate=BRAKE_FAST && distance>35 && quiet_now;
 wire stall_assist=stall_candidate && stall_frames>=29 && parked;
 // Start gently, then add8counts each10 genuine frames (~333ms). Within100px
 // cap only this restart contribution at24counts; the normal working window
 // and high-speed braking authority stay unchanged.
 wire [23:0] base_stall_magnitude=stall_frames<39 ? 24'd2048 :
  (stall_frames<49 ? 24'd4096 : ((distance<=100 || stall_frames<59) ? 24'd6144 :
  (stall_frames<69 ? 24'd8192 : (stall_frames<79 ? 24'd10240 : 24'd12288))));
 // Only advance after 30 genuine parked frames AT the current motor target.
 // Additional escape contribution is bounded; ordinary moving limits are unchanged.
 reg [5:0] escape_extra=0,escape_wait=0;
 wire [5:0] extra_limit=distance<=100 ? 6'd40 : 6'd48;
 wire [5:0] bounded_extra=escape_extra>extra_limit ? extra_limit : escape_extra;
 wire [23:0] stall_magnitude=base_stall_magnitude+{10'd0,bounded_extra,8'd0};
 wire signed [31:0] escape_motor_error=position-($signed(target_q8)>>>8);
 wire escape_arrived=escape_motor_error>=-2 && escape_motor_error<=2;
 wire escape_eligible=stall_assist && !holding && stall_frames>=79 && escape_arrived;
 wire signed [24:0] stall_target=error<0 ? -$signed(stall_magnitude) : $signed(stall_magnitude);
 wire signed [31:0] final_p=stall_assist ? $signed(stall_target) : controlled_p;
 wire signed [31:0] final_d=stall_assist ? 32'sd0 : controlled_d;
 reg [3:0] pipe=0;reg hold_stage=0;
 reg signed [31:0] p_stage=0,d_stage=0,sum_stage=0,absolute_stage=0;
 reg signed [NEUTRAL_BITS-1:0] n_stage=0;
 reg [12:0] range_distance=0;reg [31:0] range_speed=0;
 wire signed [31:0] motor_offset=position-$signed(neutral);
 wire motor_far=motor_offset>32 || motor_offset< -32;
 reg escape_release=0;
 wire escape_braking=BRAKE_FAST && escape_release && !stall_assist;
 // Slow only the small-angle trim. Flatten a previously large tilt promptly.
 // A stalled low-speed ball uses a controlled50Hz restart. High-speed braking
 // retains the original200Hz authority.
 assign max_hz=stall_assist ? 16'd50 : (BRAKE_FAST && range_speed>=2560 ? 16'd200 : (BRAKE_FAST && (escape_braking || range_speed>1280 || motor_far) ? 16'd100 : range_distance<=120 ? (motor_far || range_speed>1280 ? 16'd50 : 16'd20) : (range_distance<=240 ? 16'd100 : 16'd200)));
 assign slew_rate=stall_assist ? 16'd40 : (BRAKE_FAST && range_speed>=2560 ? 16'd256 : (BRAKE_FAST && (escape_braking || range_speed>1280 || motor_far) ? 16'd160 : range_distance<=120 ? (motor_far || range_speed>1280 ? 16'd80 : 16'd12) : (range_distance<=240 ? 16'd100 : 16'd160)));
 always @(posedge clk)begin
  if(!rst_n)begin target_q8<=0;changed<=0;holding<=0;phase<=2;vh1<=0;vh2<=0;vh3<=0;pipe<=0;entry_frames<=0;exit_frames<=0;range_distance<=0;range_speed<=0;p_stage<=0;d_stage<=0;sum_stage<=0;absolute_stage<=0;n_stage<=0;hold_stage<=0;stall_frames<=0;end
  else begin
   changed<=0;pipe<={pipe[2:0],updated && run && valid && !stale && !clear && !neutral_capture};
   if(pipe[0])sum_stage<=hold_stage ? 0 : (polarity ? -(p_stage+d_stage) : p_stage+d_stage);
   if(pipe[1])begin absolute_stage<=$signed(n_stage)*256+sum_stage;end
   if(pipe[2] && run && valid && !stale && !clear && !neutral_capture)begin target_q8<=absolute_stage>work_max*256 ? work_max*256 : (absolute_stage<work_min*256 ? work_min*256 : absolute_stage);end
   if(pipe[3] && run && valid && !stale && !clear && !neutral_capture)changed<=1;
   if(updated && run && valid && !stale && !clear && !neutral_capture)begin
    vh1<=velocity_q4[17:0];vh2<=vh1;vh3<=vh2;
    p_stage<=final_p;d_stage<=final_d;n_stage<=neutral;hold_stage<=(holding && !leaving) || entering;
    range_distance<=distance;range_speed<=speed;
    if(!parked || holding)begin escape_extra<=0;escape_wait<=0;end
    else if(escape_eligible)begin
     if(escape_wait==29)begin escape_wait<=0;if(bounded_extra<extra_limit)escape_extra<=bounded_extra+6'd8;end
     else escape_wait<=escape_wait+1'b1;
    end else escape_wait<=0;
    if(stall_assist)escape_release<=1;
    else if(holding && motor_offset<=4 && motor_offset>=-4 && speed<=192)escape_release<=0;
    if(stall_candidate && !rearm_quiet)begin if(stall_frames<90)stall_frames<=stall_frames+1'b1;end else stall_frames<=0;
    if(quiet_now && !rearm_quiet)begin quiet_min<=next_min;quiet_max<=next_max;if(quiet_frames<90)quiet_frames<=quiet_frames+1'b1;end
    else begin quiet_frames<=0;quiet_min<=x;quiet_max<=x;end
    quiet_mean_q4<=next_mean;
    if(quiet_frames==7 || quiet_frames==0)quiet_anchor_q4<=next_mean;
    if(!holding)begin
     exit_frames<=0;
     if(enter_now)begin if(entry_frames<3)entry_frames<=entry_frames+1'b1;end else entry_frames<=0;
     if(entering)begin holding<=1;entry_frames<=0;phase<=3;end
     else if((error>0 && filtered_velocity_q4<0) || (error<0 && filtered_velocity_q4>0))phase<=1;
     else phase<=distance<=120 ? 2 : 0;
    end else begin
     entry_frames<=0;phase<=3;
     if(exit_now)begin if(exit_frames<2)exit_frames<=exit_frames+1'b1;end else exit_frames<=0;
     if(leaving)begin holding<=0;exit_frames<=0;phase<=2;end
    end
   end
   if(!valid || stale)begin vh1<=0;vh2<=0;vh3<=0;pipe<=0;entry_frames<=0;exit_frames<=0;stall_frames<=0;end
   if(!run)begin vh1<=0;vh2<=0;vh3<=0;pipe<=0;holding<=0;entry_frames<=0;exit_frames<=0;phase<=2;stall_frames<=0;end
   if(clear || neutral_capture)begin vh1<=0;vh2<=0;vh3<=0;pipe<=0;target_q8<=$signed(neutral)*256;holding<=0;phase<=2;entry_frames<=0;exit_frames<=0;changed<=0;stall_frames<=0;end
  end
  if(!rst_n || !run || !valid || stale || clear || neutral_capture)begin quiet_frames<=0;quiet_min<=0;quiet_max<=0;escape_release<=0;quiet_mean_q4<=0;quiet_anchor_q4<=0;escape_extra<=0;escape_wait<=0;end
 end
endmodule
