`timescale 1ns/1ps
module tb_region_policy;
 reg clk=0;always #5 clk=~clk;reg rst=0,run=1,updated=0,valid=1,stale=0,clear=0,cap=0,pol=0;
 reg [10:0] x=960;reg signed [31:0] v=0;reg signed [7:0] n=0;
 wire signed [31:0] target;wire changed,holding;wire [1:0] phase;wire [15:0] hz,slew;
 vision_region_hold dut(clk,rst,run,updated,valid,stale,clear,cap,pol,x,16'd960,8'd60,v,32'sd0,32'sd0,n,target,changed,holding,phase,hz,slew,,16'd0);
 task tick(input integer m);begin repeat(m)@(negedge clk);end endtask
 task sample(input integer xx,vv);begin x=xx;v=vv;updated=1;tick(1);updated=0;tick(8);end endtask
 task check(input integer ok,input string msg);begin if(!ok)$fatal(1,"REGION_POLICY %s q=%d H=%b phase=%d",msg,target,holding,phase);end endtask
 integer i;reg signed [31:0] saved;
 initial begin
  tick(4);rst=1;tick(2);sample(1260,0);check(target>40*256 && target<=60*256 && hz==200,"far bounded drive");
  sample(960,3200);check(!holding && target>8*256,"fast center crossing must brake,not hold");
  clear=1;tick(1);clear=0;sample(970,0);sample(969,0);check(!holding,"entry requires3real results");sample(971,0);check(holding && phase==3 && target==0,"low speed enters15pixelhold");
  for(i=0;i<100;i=i+1)begin sample(960+(i%5)*5,0);check(holding && target==0,"inside25 never pixel-hunts");end
  sample(986,0);check(holding,"one frame outside25 tolerated");sample(984,0);check(holding,"hysteresis resets exit count");sample(986,0);sample(988,0);check(!holding,"two outside25 restart");
  sample(1000,0);check(target>0 && hz==50,"near regional drive capped50Hz");
  saved=target;valid=0;sample(0,10000);check(target==saved,"invalid coordinates never calculate reference");valid=1;
  clear=1;tick(1);clear=0;pol=1;sample(1060,0);check(target<0,"plant polarity retained");
  pol=0;clear=1;tick(1);clear=0;n=31;cap=1;tick(1);cap=0;sample(960,0);sample(960,0);sample(960,0);check(target==31*256 && holding,"nonzeroK3neutral no encoder rebase");
  sample(1010,0);check(!holding,"large push immediate exit");
  n=0;clear=1;tick(1);clear=0;for(i=0;i<1000;i=i+1)sample(1000,0);
  check(dut.trim_q8==0,"position error cannot invent a new neutral");
  sample(960,0);sample(960,0);sample(960,0);check(holding && target==0,"hold returns capturedK3neutral");
  $display("REGION_POLICY_PASS:15/25hysteresis,3frameentry,velocitybrake,noisehold,polarity,nonzeroN,fixedK3neutral,invalidfreeze");$finish;
 end
endmodule
