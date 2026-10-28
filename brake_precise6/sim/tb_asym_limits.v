`timescale 1ns/1ps
module tb_asym_limits;
 reg clk=0;always #5 clk=~clk;reg rst=0,capture=0,ready=1,en=0;
 reg signed [31:0] p=31,mc=8;
 wire q;wire signed [31:0] a,ma,lo,hi,pl,ph,ml,mh;
 vision_asym_limits dut(clk,rst,capture,ready,en,p,mc,q,a,ma,lo,hi,pl,ph,ml,mh);
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 initial begin
  tick(3);rst=1;capture=1;tick(1);capture=0;if(q)$fatal(1,"disabled K3 qualified");
  en=1;capture=1;tick(1);capture=0;if(!q || a!=31 || ma!=8 || lo!=-151 || hi!=395 || pl!=-173 || ph!=429 || ml!=-151 || mh!=318)$fatal(1,"asym conversion/anchor");
  p=300;mc=200;capture=1;tick(1);capture=0;if(a!=31 || lo!=-151 || hi!=395 || ma!=8)$fatal(1,"K3 moved mechanical envelope");
  en=0;tick(2);en=1;tick(2);if(a!=31 || !q)$fatal(1,"enable rebased limits");
  rst=0;tick(1);if(q)$fatal(1,"reload did not invalidate anchor");
  $display("ASYM_LIMITS_PASS inward -182/+364 target,-204/+398 feedback,-159/+310 pulse limits,fixed K3 anchor");$finish;
 end
endmodule
