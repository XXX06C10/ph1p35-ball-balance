`timescale 1ns/1ps
module tb_overlay_lead;
 reg clk=0;always #5 clk=~clk;reg rst=0,sof=0,frame=0,valid=1,confirmed=1,bad=0;
 reg [10:0] x=60,y=40,ol=40,orr=79,ot=28,ob=51,l=38,r=82,t=26,b=54;
 reg [10:0] rl=0,rr=159,rt=0,rb=79;integer width=40;
 wire dv,active;wire [10:0] dl,dr,dt,db;
 vision_overlay_lead #(.IMG_WIDTH(160),.IMG_HEIGHT(80)) dut(clk,rst,sof,frame,valid,confirmed,bad,x,y,ol,orr,ot,ob,l,r,t,b,rl,rr,rt,rb,dv,active,dl,dr,dt,db);
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 task start;begin sof=1;tick(1);sof=0;tick(3);end endtask
 task result(input integer xx,yy);begin
  x=xx;y=yy;ol=xx>width/2 ? xx-width/2 : 0;orr=xx+width/2-1<160 ? xx+width/2-1 : 159;
  ot=yy>12 ? yy-12 : 0;ob=yy+11<80 ? yy+11 : 79;
  l=xx>22 ? xx-22 : 0;r=xx+22<160 ? xx+22 : 159;t=yy>14 ? yy-14 : 0;b=yy+14<80 ? yy+14 : 79;
  frame=1;tick(1);frame=0;tick(2);end endtask
 task sample(input integer xx,yy);begin start;result(xx,yy);end endtask
 task ck(input integer ok,input string msg);begin if(!ok)$fatal(1,"OVERLAY %s dx=%d L=%d raw=%d",msg,dut.lead_x,dl,l);end endtask
 initial begin
  tick(3);rst=1;sample(60,40);ck(dv && !active && dl==l,"first good result is raw");
  sample(68,40);ck(active && dl==l+8 && dr==r+8,"adjacent constant velocity predicts one frame");
  sample(76,40);ck(active && dl==l+8,"sustained lead");
  sample(70,40);ck(!active && dl==l,"reversal suppresses extrapolation");sample(64,40);ck(active && dl==l-6,"reverse direction recovers");
  sample(65,40);ck(!active,"two-pixel quantization is not extrapolated");
  sample(105,56);ck(active && dl==l+20 && db<=79,"half-object and image boundary cap");
  start;start;result(113,56);ck(!active,"a gap is not a one-frame velocity");
  valid=0;sample(121,56);ck(!dv && !active && !dut.previous_valid,"invalid never manufactures a detected box");
  valid=1;sample(125,56);ck(!active,"first recovery remains raw");sample(129,56);ck(active,"second adjacent recovery can lead");
  bad=1;sample(133,56);ck(!dv && !active,"bad frame resets display history");bad=0;
  confirmed=0;sample(135,56);ck(dv && !active,"unconfirmed candidate stays raw");confirmed=1;sample(139,56);
  rl=20;rr=149;sample(147,56);ck(active && dr<=149 && dl>=20,"ROI clipping");
  rst=0;tick(1);ck(!dv && !active,"ROI/reset clears stale prediction");rst=1;width=6;sample(50,40);sample(58,40);ck(active && dl==l+3,"actual object halfwidth,not enlarged display marker");
  $display("OVERLAY_LEAD_PASS constantvelocity,halfobjectcap24,reversal,noise,gaps,invalid,bad,confirmation,ROIreset,rawfallback");$finish;
 end
endmodule
