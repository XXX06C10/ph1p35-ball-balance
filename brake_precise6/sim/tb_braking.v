`timescale 1ns/1ps
module tb_braking;
 reg clk=0;always #5 clk=~clk;reg rst=0,frame=0,valid=1,clear=0,pol=0;reg [10:0] x=960;
 reg signed [31:0] p=0;wire signed [31:0] target,v;wire [1:0] stage;wire updated;integer i;
 vision_cascade_outer #(.MS_CYCLES(10)) dut(.clk(clk),.rst_n(rst),.run(1'b1),.frame(frame),.valid(valid),.stale(1'b0),.clear(clear),.neutral_capture(1'b0),.polarity(pol),
 .x(x),.center(16'd960),.deadzone(16'd3),.kp(16'd819),.kv(16'd64),.ki(16'd0),.limit(8'd60),.delay_ms(8'd20),.bias(16'sd0),.position(p),.target_q8(target),.velocity_q4(v),.updated(updated),.predictive(1'b1),.control_phase(stage));
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 task sample;begin frame=1;tick(1);frame=0;tick(30);end endtask
 task check(input integer ok,input string s);begin if(!ok)$fatal(1,"BRAKING %s T=%0d phase=%0d V=%0d",s,target,stage,v);end endtask
 initial begin
  tick(5);rst=1;tick(30);force dut.velocity_q4=0;x=1260;sample();check(target>50*256 && target<=60*256 && stage==0,"far ball accelerates toward center within60");
  x=760;p=-40;force dut.velocity_q4=8000;sample();check(target>50*256 && stage==1,"reverse before center for rightward500px/s with wrong-side angle");
  x=1160;p=40;force dut.velocity_q4=-8000;sample();check(target< -50*256 && stage==1,"symmetric predictive braking");
  x=960;p=0;force dut.velocity_q4=8000;sample();check(target>50*256 && stage==1,"center crossing at speed still brakes");
  force dut.velocity_q4=0;sample();check(target==0 && stage==2,"center stationary goes neutral,run remains external");
  x=760;p=-40;force dut.velocity_q4=8000;pol=1;sample();check(target<0,"reversed plant sign preserves braking direction");
  valid=0;tick(10);check(target<0,"invalid result does not fabricate a new target");release dut.velocity_q4;
  valid=1;pol=0;p=0;x=960;clear=1;tick(2);clear=0;
  for(i=0;i<40;i=i+1)begin
   case(i%4)0:x=960;1:x=962;2:x=960;3:x=958;endcase
   tick(330);sample();if(i>8)check(target==0 && v==0 && stage==2,"four-frame center noise window produces quiet hold");
  end
  x=980;tick(330);sample();x=1000;tick(330);sample();check(v>1000 && target>0,"true motion exits quiet window promptly");
  $display("BRAKING_NOISE_PASS center2pixel noise quiet,true motion released");
  $display("BRAKING_ALL_PASS: drive,pre-center brake,both signs,fast center crossing,quiet hold,invalid target freeze");$finish;
 end
 initial begin #1000000;$fatal(1,"braking timeout");end
endmodule
