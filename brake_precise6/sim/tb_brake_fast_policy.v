`timescale 1ns/1ps
module tb_brake_fast_policy;
 reg clk=0;always #5 clk=~clk;reg rst=0,u=0,valid=1,clear=0,pol=0;
 reg [10:0] x=960;reg signed [31:0] v=0,p=-1;wire signed [31:0] t,fv;wire hold,c;wire [15:0] hz,sl;
 integer i;
 vision_region100 #(.BRAKE_FAST(1)) dut(.clk(clk),.rst_n(rst),.run(1'b1),.updated(u),.valid(valid),.stale(1'b0),.clear(clear),.neutral_capture(1'b0),.polarity(pol),.x(x),.center(16'd960),.velocity_q4(v),.work_min(-32'sd183),.work_max(32'sd363),.position(p),.neutral(-16'sd1),.zone_setting(16'd100),.target_q8(t),.changed(c),.holding(hold),.max_hz(hz),.slew_rate(sl),.filtered_velocity_q4(fv));
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 task sample(input integer e,vv);begin x=960+e;v=vv;u=1;tick(1);u=0;tick(9);end endtask
 task reset_h;begin clear=1;tick(1);clear=0;end endtask
 initial begin
  tick(4);rst=1;sample(30,0);sample(30,0);sample(30,0);
  if(!hold || t!=-256 || hz!=20 || sl!=12)$fatal(1,"precision hold changed");
  reset_h;for(i=0;i<32;i=i+1)sample(50,0);
  if(hold || t<=-256)$fatal(1,"50px static error must approach centre");
  reset_h;for(i=0;i<32;i=i+1)sample(80,0);
  if(hold || t<=-256)$fatal(1,"80px static error must not remain at old wide boundary");
  reset_h;p=-19;for(i=0;i<86;i=i+1)sample(-375,0);
  if(t>=-40*256 || hz<50)$fatal(1,"far stalled ball lacks bounded stiction escape T=%d Hz=%d",t,hz);
  sample(60,-512);sample(60,-512);sample(60,-512);if(hold)$fatal(1,"moderate24px_s drift must leave HOLD before crossing region");
  reset_h;p=-26;sample(27,17381);sample(27,17381);
  if(hold || t<=0 || hz!=200 || sl!=256)$fatal(1,"195545 crossing not given immediate fast braking");
  $display("BRAKE_FAST_REPLAY_PASS e27,v1086,Pminus26:opposite target,200Hz,256counts_s");
  reset_h;p=-1;sample(-300,16000);sample(-300,16000);
  if(t<=0 || hz!=200)$fatal(1,"must brake before center");
  reset_h;sample(600,0);sample(600,0);
  if(t!=24*256)$fatal(1,"static far speed envelope should request25counts,notlargeP+D");
  reset_h;sample(600,60000);sample(600,60000);if(t!=363*256)$fatal(1,"full positive work boundary lost");
  reset_h;sample(-600,-60000);sample(-600,-60000);if(t!=-183*256)$fatal(1,"full negative work boundary lost");
  reset_h;sample(30,0);sample(30,0);sample(30,0);if(!hold || t!=-256)$fatal(1,"low-speed precision restoration");
  valid=0;sample(500,20000);if(t!=-256 || c)$fatal(1,"bad frame changed target");
  $display("BRAKE_FAST_POLICY_PASS earlybraking,200px_sgoal,125mslookahead,fullwindow,precision35_exit70,farstiction_escape,invalidfreeze");$finish;
 end
endmodule
