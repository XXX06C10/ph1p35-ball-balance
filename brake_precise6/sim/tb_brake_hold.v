`timescale 1ns/1ps
module tb_brake_hold;
 reg clk=0;always #5 clk=~clk;reg rst=0,updated=0,valid=1,clear=0;
 reg [10:0] x=990;reg signed [31:0] velocity=0;
 wire signed [31:0] target,old_target;wire holding,changed;wire [1:0] phase;wire [15:0] hz,slew,old_hz;
 vision_region_hold #(.WIDE_RANGE(1),.NEUTRAL_BITS(16)) policy(
 .clk(clk),.rst_n(rst),.run(1'b1),.updated(updated),.valid(valid),.stale(1'b0),.clear(clear),.neutral_capture(1'b0),.polarity(1'b0),
 .x(x),.center(16'd960),.limit(8'd60),.velocity_q4(velocity),.work_min(-32'sd182),.work_max(32'sd364),.neutral(16'sd0),
 .target_q8(target),.changed(changed),.holding(holding),.phase(phase),.max_hz(hz),.slew_rate(slew));
 vision_region_hold legacy(.clk(clk),.rst_n(rst),.run(1'b1),.updated(updated),.valid(valid),.stale(1'b0),.clear(clear),.neutral_capture(1'b0),.polarity(1'b0),
 .x(x),.center(16'd960),.limit(8'd60),.velocity_q4(velocity),.work_min(-32'sd182),.work_max(32'sd364),.neutral(8'sd0),.target_q8(old_target),.max_hz(old_hz));
 reg key=0,busy=0,region_hold=1,neutral_capture=0;reg signed [31:0] position=1,mc_position=0,desired=0;reg signed [15:0] neutral_level=0;
 wire run,request;wire signed [15:0] frequency;wire signed [31:0] reference;
 vision_cascade_control #(.MS_CYCLES(10),.WIDE_RANGE(1),.TARGET_BITS(16)) ctl(
 .clk(clk),.rst_n(rst),.key_event(key),.k4_n(1'b1),.enable_request(1'b1),.settings_ready(1'b1),.center_confirmed(1'b1),
 .valid(1'b1),.hold_valid(1'b1),.stale(1'b0),.frame(1'b0),.config_changed(1'b0),.neutral_capture(neutral_capture),.profile_ready(1'b1),.region_holding(region_hold),
 .selection(8'd1),.amplitude(8'd8),.limit(8'd60),.max_hz(16'd50),.inner_kp(16'd8192),.feedforward(16'd0),.slew_rate(16'd200),.runtime_seconds(16'd0),.kp(16'd1),.kv(16'd1),
 .roi_left(16'd0),.roi_right(16'd1279),.center(16'd960),.x(11'd960),.position(position),.raw_target_q8(desired),.command_position(mc_position),.outer_updated(1'b1),.neutral_ready(1'b1),
 .neutral(neutral_level),.work_min(-32'sd182),.work_max(32'sd364),.core_ready(1'b1),.core_busy(busy),.core_spent(8'd0),.fault(4'd0),.step(1'b0),
 .run(run),.request(request),.reference_q8(reference),.frequency_hz(frequency));
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 task sample(input integer xx,vv);begin x=xx;velocity=vv;updated=1;tick(1);updated=0;tick(9);end endtask
 task check(input integer ok,input string msg);begin if(!ok)$fatal(1,"BRAKE_HOLD %s T=%d H=%b hz=%d f=%d",msg,target,holding,hz,frequency);end endtask
 integer i;reg signed [31:0] a,b;
 initial begin
  tick(3);rst=1;tick(2);key=1;tick(1);key=0;busy=1;tick(600);
  check(run && reference==0 && frequency==0,"matching K3 STEP phase tolerates encoder quantization");
  position=2;tick(600);check(frequency==0,"matching STEP phase tolerates two-count encoder neighborhood");
  position=3;tick(600);check(frequency<0,"real motor deviation beyond2counts still corrected");
  position=1;tick(600);check(frequency==0,"stop at matching phase inside encoder neighborhood");
  position=2;tick(600);check(frequency==0,"no fractional restart after stopping");
  region_hold=0;tick(600);check(frequency<0,"non-HOLD correction retains original endpoint band");
  region_hold=1;mc_position=1;position=1;tick(600);check(frequency<0,"one real STEP away from neutral is returned,not forgiven");
  mc_position=0;position=0;tick(600);check(frequency==0,"exact STEP phase neutral stops without reverse hunting");
  key=1;tick(1);key=0;tick(30);mc_position=8;position=31;neutral_level=31;desired=31*256;
  neutral_capture=1;tick(1);neutral_capture=0;tick(30);key=1;tick(1);key=0;tick(600);
  check(run && ctl.neutral_command_position==8 && frequency==0,"K3 records nonzero STEP phase without rebasing MC");
  mc_position=9;position=32;tick(600);check(frequency<0,"nonzero neutral corrects one STEP phase error");
  mc_position=8;position=31;tick(600);check(frequency==0,"captured nonzero neutral stays stopped");
  sample(992,0);a=target;sample(993,0);b=target;check(b-a>0 && b-a<=64,"smooth32pixel gain transition");
  sample(1056,0);a=target;sample(1057,0);check(target-a>0 && target-a<256,"smooth96pixel gain transition");
  for(i=0;i<5;i=i+1)sample(990,-1600);
  check(!holding && phase==1 && hz==200 && slew==200 && old_hz==50 && target<0,"fast inward ball preserves full braking authority nearcenter");
  for(i=0;i<4;i=i+1)sample(990,-640);check(hz==200,"40pixel/s hysteresis retains braking cap");
  for(i=0;i<5;i=i+1)sample(990,0);check(hz==50,"slow fine adjustment returns to50Hz");
  clear=1;tick(1);clear=0;for(i=0;i<5;i=i+1)sample(972,64);
  check(holding && target==0 && phase==3,"low-speed actual ball enters unchanged15pixel HOLD");
  for(i=0;i<80;i=i+1)begin sample(970+i%8,(i%2 ? 64 : -64));check(holding && target==0,"center jitter never chases each pixel");end
  sample(986,0);check(holding,"one outside25 frame tolerated");sample(987,0);check(!holding,"second outside25 reactivates correction");
  a=target;valid=0;sample(1200,-3000);check(target==a && !policy.fast_motion,"invalid frame cannot invent a braking update");valid=1;
  $display("BRAKE_HOLD_PASS speed-aware200Hz,continuous32/96gains,velocitydeadband,15/25hold,K3STEPphase-neutral,encoder-quantization,invalidfreeze");$finish;
 end
 initial begin #1000000;$fatal(1,"brake test timeout");end
endmodule
