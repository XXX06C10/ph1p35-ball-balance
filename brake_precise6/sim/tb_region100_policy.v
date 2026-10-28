`timescale 1ns/1ps
module tb_region100_policy;
 reg clk=0;always #5 clk=~clk;reg rst=0,update=0,valid=1,clear=0,pol=0,run=1;
 reg [10:0] x=1260;reg signed [31:0] v=0,pos=31;reg [15:0] zone=100;
 wire signed [31:0] target,fv;wire changed,holding;wire [15:0] hz,slew;
 vision_region100 dut(.clk(clk),.rst_n(rst),.run(run),.updated(update),.valid(valid),.stale(1'b0),.clear(clear),.neutral_capture(1'b0),.polarity(pol),.x(x),.center(16'd960),.velocity_q4(v),.work_min(-32'sd151),.work_max(32'sd395),.neutral(16'sd31),.position(pos),.target_q8(target),.changed(changed),.holding(holding),.max_hz(hz),.slew_rate(slew),.filtered_velocity_q4(fv),.zone_setting(zone));
 wire signed [31:0] legacy_target;
 vision_region_hold #(.WIDE_RANGE(1),.NEUTRAL_BITS(16),.LIVE_ZONE(1),.RECOVER_ASYM(1)) old_policy(
 .clk(clk),.rst_n(rst),.run(run),.updated(update),.valid(valid),.stale(1'b0),.clear(clear),.neutral_capture(1'b0),.polarity(pol),.x(x),.center(16'd960),.limit(8'd60),.velocity_q4(v),.work_min(-32'sd151),.work_max(32'sd395),.neutral(16'sd31),.target_q8(legacy_target),.hold_radius_setting(16'd3));
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 task sample(input integer err,vv);begin x=960+err;v=vv;update=1;tick(1);update=0;tick(9);end endtask
 task reset_history;begin clear=1;tick(1);clear=0;end endtask
 integer i,oldtarget;initial begin
  tick(4);rst=1;
  sample(90,0);sample(90,0);if(holding)$fatal(1,"premature hold");sample(90,0);
  if(!holding || target!=31*256 || hz!=20 || slew!=12)$fatal(1,"90px true low speed must level and hold");
  if(legacy_target!=31*256+90*32)$fatal(1,"legacy90px tilt not reproduced");
  $display("REGION100_REPLAY_PASS same90pxstatic:legacy+11.25counts,newneutral,noamplitudeclamp");
  for(i=0;i<40;i=i+1)sample((i%2) ? 98 : 92,(i%2) ? 32 : -32);
  if(!holding || target!=31*256)$fatal(1,"tiny noise must not hunt or shift neutral");
  sample(101,0);if(!holding)$fatal(1,"single edge frame must not chatter");sample(99,0);if(!holding)$fatal(1,"edge recovery");
  sample(101,0);sample(101,0);if(holding)$fatal(1,"persistent >100px must resume");
  reset_history;sample(90,640);sample(90,640);sample(90,640);if(holding)$fatal(1,"moving ball must not be falsely held");
  reset_history;for(i=0;i<5;i=i+1)sample(60,0);if(target!=31*256)$fatal(1,"fine position deadzone");
  reset_history;sample(100,0);if(target!=31*256+480 || hz!=20 || slew!=12)$fatal(1,"100px correction too strong T=%d",target);
  pos=80;sample(100,0);if(hz!=50 || slew!=80)$fatal(1,"large existing tilt must flatten promptly");pos=31;
  reset_history;sample(240,0);if(target!=91*256 || hz!=100)$fatal(1,"continuous transition240px");
  reset_history;sample(900,0);if(target!=256*256 || hz!=200)$fatal(1,"far control/full amplitude restricted");
  reset_history;sample(900,20000);sample(900,20000);sample(900,20000);sample(900,20000);
  if(target!=395*256)$fatal(1,"positive full window not reachable");
  reset_history;sample(-900,-20000);sample(-900,-20000);sample(-900,-20000);sample(-900,-20000);
  if(target!=-151*256)$fatal(1,"negative full window not reachable");
  pol=1;reset_history;sample(900,0);if(target!=-151*256)$fatal(1,"polarity and fixed envelope");
  oldtarget=target;valid=0;sample(-900,16000);if(target!=oldtarget || changed)$fatal(1,"invalid frame changed target");
  valid=1;zone=80;reset_history;sample(70,0);sample(70,0);sample(70,0);if(!holding || dut.radius!=80 || dut.capture_radius!=70)$fatal(1,"runtime80");
  zone=3;reset_history;sample(90,0);sample(90,0);sample(90,0);if(!holding || dut.radius!=100)$fatal(1,"oldDZ fallback100");
  run=0;tick(2);if(holding || changed)$fatal(1,"stop resets policy");
  $display("REGION100_POLICY_PASS capture90_exit100,noise_hysteresis,low_speed_qualification,softfine20Hz12counts_s,full_fixed_window,noP.Lclamp,invalidfreeze,polarity");$finish;
 end
endmodule
