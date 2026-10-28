`timescale 1ns/1ps
module tb_precise4_noise;
 reg clk=0;always #5 clk=~clk;reg rst=0,u=0,valid=1,clear=0;
 reg [10:0] x=815;reg signed [31:0] v=0;
 wire signed [31:0] t,fv,gold;wire hold;integer i,positive,negative;
 vision_region100 #(.BRAKE_FAST(1)) dut(.clk(clk),.rst_n(rst),.run(1'b1),.updated(u),.valid(valid),.stale(1'b0),.clear(clear),.neutral_capture(1'b0),.polarity(1'b0),.x(x),.center(16'd862),.velocity_q4(v),.work_min(-32'sd182),.work_max(32'sd364),.position(32'sd0),.neutral(16'sd0),.zone_setting(16'd100),.target_q8(t),.holding(hold),.filtered_velocity_q4(fv));
 vision_region100_precise3 #(.BRAKE_FAST(1)) parent(.clk(clk),.rst_n(rst),.run(1'b1),.updated(u),.valid(valid),.stale(1'b0),.clear(clear),.neutral_capture(1'b0),.polarity(1'b0),.x(x),.center(16'd862),.velocity_q4(v),.work_min(-32'sd182),.work_max(32'sd364),.position(32'sd0),.neutral(16'sd0),.zone_setting(16'd100),.target_q8(gold));
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 task sample(input integer e,vv);begin x=862+e;v=vv;u=1;tick(1);u=0;tick(9);end endtask
 task reset_h;begin clear=1;tick(1);clear=0;end endtask
 initial begin
  tick(3);rst=1;
  // Latest trace: ball jitter only6px, derivative can exceed80px/s.
  for(i=0;i<90;i=i+1)sample(-47+(i%7)-3,(i%4<2 ? 80 : -80)*16);
  if(hold || t!=-24*256 || fv!=0 || !dut.parked)$fatal(1,"noisy parked47px must sustain bounded24counts T=%d",t);
  if(gold<=0 || parent.stall_assist)$fatal(1,"accepted parent failure not reproduced");
  $display("PRECISE3_NOISE_REPRO_PASS parent target=%0d new=%0d rawcoordinate jitter6px",gold,t);
  sample(-20,200*16);if(dut.parked || dut.stall_assist || fv==0)$fatal(1,"real displacement must restore braking immediately");
  reset_h;for(i=0;i<90;i=i+1)sample(-210+(i%7)-3,(i%4<2 ? 60 : -60)*16);
  if(t!=-48*256 || !dut.parked)$fatal(1,"far parked assist interrupted by fake velocity");
  reset_h;for(i=0;i<30;i=i+1)sample(-100+i,16);
  if(dut.parked || dut.stall_assist)$fatal(1,"continuous slow motion classified parked");
  reset_h;for(i=0;i<60;i=i+1)sample(-100+i/8,0);
  if(dut.parked)$fatal(1,"mean drift guard failed for4px_s crawl");
  reset_h;for(i=0;i<40;i=i+1)sample(25+(i%5)-2,(i%2 ? 50 : -50)*16);
  if(!hold || t!=0)$fatal(1,"stationary centre fails hold due derivative noise");
  valid=0;tick(2);if(dut.parked || dut.quiet_frames!=0)$fatal(1,"invalid dwell survived");
  $display("PRECISE4_NOISE_PASS parked47and210,80px_sfakevelocity,realmotionexit,slowdriftreject,centrehold,invalidreset");$finish;
 end
endmodule

// 100px product region: soft position attraction, velocity damping, hysteretic level hold.
// This module never rebases encoder/STEP origins or changes the fixed work window.
module vision_region100_precise3 #(parameter NEUTRAL_BITS=16,BRAKE_FAST=0)(
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
 assign filtered_velocity_q4=(BRAKE_FAST || distance<=120) ? $signed(pair_a)>>>1 : ($signed(pair_a)+$signed(pair_b))>>>2;
 wire [31:0] speed=filtered_velocity_q4<0 ? -filtered_velocity_q4 : filtered_velocity_q4;
 wire [15:0] radius=zone_setting<60 ? 16'd100 : (zone_setting>100 ? 16'd100 : zone_setting);
 // Fast braking first suppresses velocity over the wide100px approach, then
 // hands over to a narrow precision hold. The wide profile remains available.
 wire [15:0] capture_radius=BRAKE_FAST ? 16'd35 : radius-10;
 wire [15:0] trend_radius=BRAKE_FAST ? 16'd60 : radius-5;
 wire outward=(error>0 && filtered_velocity_q4>0) || (error<0 && filtered_velocity_q4<0);
 // Coordinate trend is independent of derivative quantization. Four pixels of
 // excursion over >=16 genuine30fps results qualifies as parked, but a current
 // speed above24px/s still rejects capture and immediately cancels assistance.
 reg [6:0] quiet_frames=0;reg [10:0] quiet_min=0,quiet_max=0;
 wire [10:0] next_min=(quiet_frames==0 || x<quiet_min) ? x : quiet_min;
 wire [10:0] next_max=(quiet_frames==0 || x>quiet_max) ? x : quiet_max;
 wire quiet_now=(next_max-next_min)<=4 && speed<=384;
 wire trend_quiet=quiet_frames>=15 && quiet_now;
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
 wire stall_assist=stall_candidate && stall_frames>=29 && trend_quiet && quiet_frames>=29 && speed<=128;
 // Start gently, then add8counts each10 genuine frames (~333ms). Within100px
 // cap only this restart contribution at24counts; the normal working window
 // and high-speed braking authority stay unchanged.
 wire [23:0] stall_magnitude=stall_frames<39 ? 24'd2048 :
  (stall_frames<49 ? 24'd4096 : ((distance<=100 || stall_frames<59) ? 24'd6144 :
  (stall_frames<69 ? 24'd8192 : (stall_frames<79 ? 24'd10240 : 24'd12288))));
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
    if(stall_assist)escape_release<=1;
    else if(holding && motor_offset<=4 && motor_offset>=-4 && speed<=192)escape_release<=0;
    if(stall_candidate)begin if(stall_frames<90)stall_frames<=stall_frames+1'b1;end else stall_frames<=0;
    if(quiet_now)begin quiet_min<=next_min;quiet_max<=next_max;if(quiet_frames<90)quiet_frames<=quiet_frames+1'b1;end
    else begin quiet_frames<=0;quiet_min<=x;quiet_max<=x;end
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
  if(!rst_n || !run || !valid || stale || clear || neutral_capture)begin quiet_frames<=0;quiet_min<=0;quiet_max<=0;escape_release<=0;end
 end
endmodule
