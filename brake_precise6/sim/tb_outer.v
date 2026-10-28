`timescale 1ns/1ps
module tb_outer;
 reg clk=0;always #5 clk=~clk;reg rst=0,run=0,frame=0,valid=1,clear=0,capture=0,invert=0;
 reg [10:0] x=960;reg [15:0] center=960,kp=512,kv=128,ki=0;reg signed [31:0] pos=0;
 wire signed [31:0] target,vel;wire signed [15:0] legacy;wire signed [7:0] neutral;wire ready,updated,stable;wire [1:0] phase_unused;wire [31:0] now_ms,frame_ms;
 vision_cascade_outer #(.MS_CYCLES(10)) dut(clk,rst,run,frame,valid,1'b0,clear,capture,invert,x,center,16'd5,kp,kv,ki,8'd60,8'd0,16'sd0,pos,32'sd0,32'sd0,target,vel,legacy,neutral,ready,updated,stable,now_ms,frame_ms,1'b0,phase_unused);
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 task result(input integer ms);begin tick(ms*10);frame=1;tick(1);frame=0;tick(20);end endtask
 task check(input integer ok,input string s);begin if(!ok)$fatal(1,"OUTER %s Tq=%d Vq=%d",s,target,vel);end endtask
 integer i;reg signed [31:0] saved;
 initial begin
  tick(5);rst=1;run=1;result(30);
  for(i=0;i<25;i=i+1)begin x=x+3;result(30);end
  check(vel>1400 && vel<1700,"actual dt30ms gives100px/s after filtering");
  center=x;result(30);check(target>256,"center crossing retains velocity braking");
  $display("OUTER_VELOCITY_PASS actual_dt_ms30 V_pixels_s=%f inside-center braking",$itor(vel)/16.0);
  invert=1;result(30);check(target<0,"calibrated sign flips correction");
  valid=0;saved=target;tick(1000);check(target==saved && vel==0,"loss holds target and resets velocity");
  valid=1;result(60);check(vel==0,"first recovery frame establishes velocity baseline");
  $display("OUTER_LOSS_PASS hold,no derivative spike");
  invert=0;run=0;x=960;center=960;pos=31;capture=1;tick(1);capture=0;tick(10);run=1;result(33);check(target==31*256,"nonzero neutral31 preserved");
  run=0;pos=-31;capture=1;tick(1);capture=0;tick(10);run=1;result(33);check(target==-31*256,"nonzero neutral-31 preserved");
  run=0;pos=63;capture=1;tick(1);capture=0;tick(5);check(!ready,"invalid neutral not wrapped");
  pos=0;capture=1;tick(1);capture=0;kp=0;kv=0;ki=655;run=1;x=980;
  for(i=0;i<180;i=i+1)result(30);
  check(target>128 && target<512,"fractional slow integral no forced2count jump");
  x=1200;for(i=0;i<600;i=i+1)result(30);check(dut.integral_q16<=262144 && dut.integral_q16>=-262144,"integral bounded");
  $display("OUTER_INTEGRAL_PASS bounded4counts,small fractional targets");
  clear=1;tick(1);clear=0;x=960;ki=0;for(i=0;i<110;i=i+1)result(30);check(stable,"three-second stable ball");
  x=1000;result(30);check(!stable,"disturbance clears stable");
  clear=1;tick(1);clear=0;run=1;x=500;center=960;kp=512;kv=40;result(33);
  for(i=0;i<8;i=i+1)begin x=x+45;result(33);end
  check(vel>8000,"45pixel/frame motion retains velocity estimate instead of repeated reset");
  $display("OUTER_FAST_VELOCITY_PASS Vq4=%0d",vel);
  $display("OUTER_ALL_PASS: dt velocity,center braking,sign,loss,neutral,integral,stable3s");$finish;
 end
 initial begin #20000000;$fatal(1,"outer timeout");end
endmodule
