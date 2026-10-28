`timescale 1ns/1ps
module tb_smooth_policy;
 reg clk=0;always #5 clk=~clk;reg rst=0,update=0,valid=1,clear=0,pol=0;
 reg [10:0] x=1260;reg signed [31:0] v=0;reg [15:0] radius=3;
 wire signed [31:0] target,gold_target,fv,gold_fv;wire changed,gold_changed,holding,gold_hold;wire [15:0] hz,gold_hz,slew,gold_slew;
 vision_region_hold #(.WIDE_RANGE(1),.NEUTRAL_BITS(16),.LIVE_ZONE(1),.RECOVER_ASYM(1)) dut(.clk(clk),.rst_n(rst),.run(1'b1),.updated(update),.valid(valid),.stale(1'b0),.clear(clear),.neutral_capture(1'b0),.polarity(pol),.x(x),.center(16'd960),.limit(8'd5),.velocity_q4(v),.work_min(-32'sd151),.work_max(32'sd395),.neutral(16'sd31),.target_q8(target),.changed(changed),.holding(holding),.max_hz(hz),.slew_rate(slew),.filtered_velocity_q4(fv),.hold_radius_setting(radius));
 vision_region_asym_gold #(.WIDE_RANGE(1),.NEUTRAL_BITS(16)) gold(.clk(clk),.rst_n(rst),.run(1'b1),.updated(update),.valid(valid),.stale(1'b0),.clear(clear),.neutral_capture(1'b0),.polarity(pol),.x(x),.center(16'd960),.limit(8'd5),.velocity_q4(v),.work_min(-32'sd151),.work_max(32'sd395),.neutral(16'sd31),.target_q8(gold_target),.changed(gold_changed),.holding(gold_hold),.max_hz(gold_hz),.slew_rate(gold_slew),.filtered_velocity_q4(gold_fv));
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 task sample(input integer err,vv);begin x=960+err;v=vv;update=1;tick(1);update=0;tick(9);end endtask
 integer i,err;
 initial begin
  tick(4);rst=1;
  for(i=0;i<600;i=i+1)begin
   case(i%8)0:err=300;1:err=180;2:err=100;3:err=50;4:err=-50;5:err=-100;6:err=-180;7:err=-300;endcase
   if(i>=300)err=err*3;pol=(i%300)>150;sample(err,((i%9)-4)*(i>=300 ? 6400 : 640));
   if(target!==gold_target || fv!==gold_fv || hz!==gold_hz || slew!==gold_slew || changed!==gold_changed || holding || gold_hold)$fatal(1,"asym middle mismatch i=%0d T=%d/%d v=%d/%d Hz=%d/%d",i,target,gold_target,fv,gold_fv,hz,gold_hz);
  end
  $display("SMOOTH_GOLD_EQUIVALENCE_PASS 600realupdates,upto1600pixels_s,bothsigns,4framevelocity,PD,50/100/200limits,nonzeroN");
  pol=0;clear=1;tick(1);clear=0;sample(600,0);sample(600,0);sample(600,0);sample(600,0);
  if(target!=181*256)$fatal(1,"full-window motion incorrectly limited by L5");
  radius=50;clear=1;tick(1);clear=0;sample(40,0);sample(40,0);sample(40,0);
  if(!holding || target!=31*256)$fatal(1,"latest live region/neutral return lost");
  valid=0;sample(-500,20000);if(target!=31*256)$fatal(1,"invalid result changes reference");
  $display("SMOOTH_POLICY_PASS exacttrustedmiddle,fullwindow,noP.Lcap,livezone,invalidfreeze");$finish;
 end
endmodule
