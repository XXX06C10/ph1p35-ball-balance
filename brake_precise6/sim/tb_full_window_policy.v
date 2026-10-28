`timescale 1ns/1ps
module tb_full_window_policy;
 reg clk=0;always #5 clk=~clk;reg rst=0,updated=0,clear=0,valid=1;reg [10:0] x=960;reg signed [31:0] velocity=0;
 reg [15:0] radius=3;reg [7:0] lim=60;reg signed [15:0] neutral=0;
 wire signed [31:0] target;wire holding;wire [15:0] hz;
 vision_region_hold #(.WIDE_RANGE(1),.NEUTRAL_BITS(16),.LIVE_ZONE(1)) dut(
 .clk(clk),.rst_n(rst),.run(1'b1),.updated(updated),.valid(valid),.stale(1'b0),.clear(clear),.neutral_capture(1'b0),.polarity(1'b0),
 .x(x),.center(16'd960),.limit(lim),.velocity_q4(velocity),.work_min(-32'sd182),.work_max(32'sd364),.neutral(neutral),.target_q8(target),.holding(holding),.max_hz(hz),.hold_radius_setting(radius));
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 task sample(input integer xx,v);begin x=960+xx;velocity=v;updated=1;tick(1);updated=0;tick(9);end endtask
 task reset_policy;begin clear=1;tick(1);clear=0;end endtask
 task check(input integer ok,input string why);begin if(!ok)$fatal(1,"FULL_WINDOW_POLICY %s target=%d HOLD=%b",why,target,holding);end endtask
 integer i;reg signed [31:0] saved;
 initial begin
  tick(3);rst=1;sample(600,0);check(target==150*256,"native target exceeds removed48count cap");
  sample(-600,0);check(target==-150*256,"negative native target exceeds removed48count cap");
  lim=16;sample(600,0);check(target==150*256,"legacy P.L cannot reintroduce a native amplitude cap");lim=60;
  neutral=350;sample(600,0);check(target==364*256,"absolute fixed safety envelope wins over soft cap");neutral=0;
  for(i=0;i<4;i=i+1)sample(900,16000);check(target==364*256,"positive target uses full fixed work bound");
  for(i=0;i<4;i=i+1)sample(-900,-16000);check(target==-182*256,"negative target uses full fixed work bound");
  reset_policy;sample(24,0);sample(24,0);sample(24,0);check(holding && target==0 && dut.hold_radius==30 && dut.hold_exit==45,"recorded24pixel plateau now qualifies return-flat HOLD");
  for(i=0;i<80;i=i+1)begin sample(20+i%23,0);check(holding && target==0,"capture-region noise never pursues every pixel");end
  sample(46,0);check(holding,"single exit frame tolerated");sample(44,0);sample(46,0);sample(47,0);check(!holding,"two outside45 results resume control");
  reset_policy;for(i=0;i<5;i=i+1)sample(0,1600);check(!holding && target>0 && hz==200,"fast center crossing brakes instead of blindly stopping in region");
  for(i=0;i<5;i=i+1)sample(0,-1600);check(!holding && target<0,"opposite crossing retains braking sign");
  reset_policy;radius=50;for(i=0;i<3;i=i+1)sample(45,0);check(holding && dut.hold_exit==75,"runtime50pixel profile");
  for(i=0;i<10;i=i+1)sample(65,0);check(holding && target==0,"wide hysteresis profile stays flat");
  reset_policy;radius=20;for(i=0;i<3;i=i+1)sample(18,0);check(holding && dut.hold_exit==30,"runtime20pixel profile");
  saved=target;valid=0;sample(700,20000);check(target==saved,"invalid coordinates do not change reference");
  $display("FULL_WINDOW_POLICY_PASS full-fixed-envelope,no-extra-P.L-cap,20/30/50live-zones,30/45default,fastcrossbrake,absoluteclamp,invalidfreeze");$finish;
 end
endmodule
