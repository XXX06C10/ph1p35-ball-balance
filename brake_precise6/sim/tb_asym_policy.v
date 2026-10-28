`timescale 1ns/1ps
module tb_asym_policy;
 reg clk=0;always #5 clk=~clk;reg rst=0,update=0,clear=0;reg [10:0] x=960;reg [15:0] center=960;
 wire signed [31:0] target;wire changed,holding;wire [1:0] phase;
 vision_region_hold #(.WIDE_RANGE(1),.NEUTRAL_BITS(16)) dut(.clk(clk),.rst_n(rst),.run(1'b1),.updated(update),.valid(1'b1),.stale(1'b0),.clear(clear),.neutral_capture(1'b0),.polarity(1'b0),.x(x),.center(center),.limit(8'd5),.velocity_q4(32'sd0),.work_min(-32'sd151),.work_max(32'sd395),.neutral(16'sd31),.target_q8(target),.changed(changed),.holding(holding),.phase(phase));
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 task sample(input integer xx,cc);begin x=xx;center=cc;update=1;tick(1);update=0;tick(9);end endtask
 initial begin
  tick(3);rst=1;sample(1560,960);if(target!=181*256)$fatal(1,"old8bit limit or relative overflow target=%d",target);
  sample(1919,0);if(target!=395*256)$fatal(1,"positive absolute soft clamp");
  sample(0,1900);if(target!=-151*256)$fatal(1,"negative asymmetric soft clamp");
  clear=1;tick(1);clear=0;sample(960,960);sample(961,960);sample(960,960);if(!holding || target!=31*256)$fatal(1,"wide neutral hold");
  $display("ASYM_POLICY_PASS large signed target,both fixed absolute soft clamps,legacy L ignored,nonzero neutral HOLD");$finish;
 end
endmodule
