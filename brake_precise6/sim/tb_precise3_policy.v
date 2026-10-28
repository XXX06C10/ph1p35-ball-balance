`timescale 1ns/1ps
module tb_precise3_policy;
 reg clk=0;always #5 clk=~clk;reg rst=0,u=0,valid=1,clear=0;
 reg [10:0] x=1005;reg signed [31:0] v=0;wire signed [31:0] t;wire hold;integer i;
 vision_region100 #(.BRAKE_FAST(1)) dut(.clk(clk),.rst_n(rst),.run(1'b1),.updated(u),.valid(valid),.stale(1'b0),.clear(clear),.neutral_capture(1'b0),.polarity(1'b0),.x(x),.center(16'd960),.velocity_q4(v),.work_min(-32'sd182),.work_max(32'sd364),.position(32'sd0),.neutral(16'sd0),.zone_setting(16'd100),.target_q8(t),.holding(hold));
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 task sample(input integer e,vv);begin x=960+e;v=vv;u=1;tick(1);u=0;tick(9);end endtask
 initial begin
  tick(3);rst=1;
  // Latest44..47px parking with intermittent15px/s derivative noise.
  for(i=0;i<32;i=i+1)sample(45+i%2,i%3==0 ? 240 : 0);
  if(hold || t!=8*256)$fatal(1,"jitter parking failed stage8 T%0d",t);
  for(i=0;i<10;i=i+1)sample(45+i%2,i%3==0 ? 240 : 0);
  if(t!=16*256)$fatal(1,"stage16 missing T%0d",t);
  for(i=0;i<10;i=i+1)sample(45+i%2,i%3==0 ? 240 : 0);
  if(t!=24*256)$fatal(1,"stage24 missing");
  for(i=0;i<60;i=i+1)sample(45,0);
  if(t!=24*256)$fatal(1,"near recovery exceeds24");
  sample(39,-480);sample(38,-480);
  if(dut.stall_assist || t==24*256)$fatal(1,"movement did not withdraw assistance");
  clear=1;tick(1);clear=0;
  for(i=0;i<22;i=i+1)sample(32+i%2,240);
  if(!hold || t!=0)$fatal(1,"500ms coordinate trend capture failed");
  sample(76,0);if(hold)$fatal(1,"hold outward escape lost");
  clear=1;tick(1);clear=0;
  for(i=0;i<20;i=i+1)sample(45+i,0);
  if(dut.stall_assist)$fatal(1,"moving coordinate falsely classified parked");
  valid=0;sample(45,0);if(dut.quiet_frames!=0 || dut.stall_frames!=0)$fatal(1,"invalid history not reset");
  $display("PRECISE3_POLICY_PASS jitter44_47,stages8_16_24,motionwithdraw,trend35capture,invalidreset");$finish;
 end
endmodule
