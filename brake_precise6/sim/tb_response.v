`timescale 1ns/1ps
// All wall-time counts use MS_CYCLES=50: production clocks divided by1000.
module response_motion #(parameter FAST=1,DELAY_MS=6)(output reg done=0,output reg [31:0] forward_ms=0,reverse_ms=0);
 reg clk=0;always #5 clk=~clk;reg rst=0,frame=0,rx=1;
 reg [3:0] keys=15;reg [10:0] bx=960;reg [1:0] enc=0,phase=0;
 wire tx,en,dir,step;wire [3:0] led;wire [15:0] cs,ae,ag,rl,rt,rr,rb;
 vision_monitor #(.MS_CYCLES(50),.DEBOUNCE_CYCLES(10),.ENABLE_CYCLES(5000),.POR_CYCLES(8),.UART_DIV(4),.REPORT_CYCLES(20000),
 .SETUP_CYCLES(1000),.HALF_CYCLES(125),.SETTLE_CYCLES(2500),.TIMEOUT_CYCLES(250000),
 .CONTROL_MS(FAST ? 20 : 100),.FOLLOW_SETUP_CYCLES(FAST ? 250 : 1000),.FOLLOW_SETTLE_CYCLES(FAST ? 500 : 2500),
 .DEFAULT_SLEW(FAST ? 8 : 2)) dut(
 clk,rst,keys,enc,2'b0,frame,bx,11'd500,1'b1,1'b0,4'd15,rx,tx,en,dir,step,led,16'd0,16'd0,1'b0,cs,ae,ag,rl,rt,rr,rb);
 integer cycles=0,fc=0,pulses=0,commands=0,encoded=0,goal=0,diff=0,i=0,start_cycle=0,last_pulse=0,manual_pulses=0;
 reg manual=0;time dir_changed=0,high_started=0;
 always @(negedge clk)begin
  cycles=cycles+1;frame<=0;
  if(fc==1649)begin fc=0;frame<=1;end else fc=fc+1;
  if(rst && dut.fault!=0)$fatal(1,"response normal false fault FAST=%0d F=%0d P=%d",FAST,dut.fault,dut.position);
 end
 always @(dir)begin if(step)$fatal(1,"response DIR changed during STEP");dir_changed=$time;end
 always @(posedge step)begin
  if($time-dir_changed<(manual || !FAST ? 10000 : 2500))$fatal(1,"response DIR setup shortened");
  high_started=$time;
  if(manual)begin
   if(manual_pulses>0 && cycles-last_pulse<3750)$fatal(1,"return pulse period changed");
   manual_pulses=manual_pulses+1;last_pulse=cycles;
  end
  pulses=pulses+1;commands=commands+(dir ? 1 : -1);goal=commands*32/25;diff=goal-encoded;
  repeat(DELAY_MS*50)@(negedge clk);
  for(i=0;i<(diff<0 ? -diff : diff);i=i+1)begin
   repeat(25)@(negedge clk);phase=phase+(diff>0 ? 2'd3 : 2'd1);
   case(phase)0:enc=0;1:enc=1;2:enc=3;3:enc=2;endcase
  end
  encoded=goal;
 end
 always @(negedge step)if(rst && en && high_started && $time-high_started<1250)$fatal(1,"response high width changed");
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 task click(input integer key);begin keys[key]=0;tick(30);keys[key]=1;tick(35);end endtask
 task sendbyte(input [7:0] b);integer j;begin rx=0;tick(4);for(j=0;j<8;j=j+1)begin rx=b[j];tick(4);end rx=1;tick(4);end endtask
 task return_packet;integer j;string p;reg [7:0] sum;begin
  sum=1^2^12^8^60;p=$sformatf("S0001020C08003C%02h",sum);
  for(j=0;j<p.len();j=j+1)sendbyte(p[j]);sendbyte(10);tick(50);
 end endtask
 initial begin
  tick(5);rst=1;tick(2000);click(2);click(0);wait(dut.request_ready);
  if(dut.gain!=3 || dut.limit!=32 || dut.deadzone!=5 || dut.slew!=(FAST ? 8 : 2) || dut.runtime_seconds!=60)$fatal(1,"new defaults mismatch");
  bx=1093;tick(2000);start_cycle=cycles;click(1);
  wait(dut.auto_run && dut.position>=15 && !dut.busy && dut.drive_target==16);forward_ms=(cycles-start_cycle)/50;
  bx=827;start_cycle=cycles;
  wait(dut.position<=-15 && !dut.busy && dut.drive_target==-16);reverse_ms=(cycles-start_cycle)/50;
  if(dut.errors1!=0 || dut.target!=-16 || !dut.auto_run)$fatal(1,"response true AB reversal failed");
  click(1);if(dut.auto_run || dut.stop_reason!=7)$fatal(1,"response K2 stop");
  return_packet;tick(2000);manual=1;click(1);wait(dut.ready && dut.position>=-2 && dut.position<=2);
  if(manual_pulses<8)$fatal(1,"manual return timing unexercised");
  $display("RESPONSE_MOTION_PASS FAST=%0d delay_ms=%0d forward_ms=%0d reverse_ms=%0d pulses=%0d manual_pulses=%0d",FAST,DELAY_MS,forward_ms,reverse_ms,pulses,manual_pulses);
  done=1;
 end
 initial begin : capture
  reg [7:0] b;integer j;string line;reg emitted;line="";emitted=0;
  forever begin @(negedge tx);repeat(6)@(posedge clk);#1;for(j=0;j<8;j=j+1)begin b[j]=tx;repeat(4)@(posedge clk);#1;end
   if(tx!=1)$fatal(1,"response UART stop");line={line,b};
   if(b==10)begin if(line.len()!=429)$fatal(1,"response UART length");if(FAST && !emitted && dut.auto_run)begin $display("UART_RESPONSE %s",line);emitted=1;end line="";end
  end
 end
endmodule

module response_arithmetic(output reg done=0);
 reg clk=0;always #5 clk=~clk;
 reg rst=0,key=0,frame=0,valid=1;reg [10:0] x=960;reg [7:0] g=3,l=32,sl=8;reg [15:0] dz=5;
 wire run;wire signed [7:0] t,at;wire signed [15:0] vel;
 vision_follow_control #(.MS_CYCLES(1),.CONTROL_MS(20)) dut(
 .clk(clk),.rst_n(rst),.key_event(key),.k4_n(1'b1),.enable_request(1'b1),.config_changed(1'b0),
 .visual_valid(valid),.follow_valid(1'b1),.visual_stale(1'b0),.settings_ready(1'b1),.center_confirmed(1'b1),.frame(frame),.neutral_capture(1'b0),
 .x(x),.center(16'd960),.deadzone(dz),.runtime_seconds(16'd0),.gain(g),.limit(l),.mode(8'd1),.damping(8'd0),.slew(sl),
 .manual_target(8'sd0),.core_ready(1'b1),.core_busy(1'b0),.fault(4'd0),.step(1'b0),.position(32'sd0),
 .run(run),.candidate(t),.drive_target(at),.velocity(vel));
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 integer i;reg signed [7:0] held;
 initial begin
  tick(4);rst=1;tick(2);
  for(i=0;i<=12;i=i+1)begin
   g=i;x=966;#1;if(t!=2)$fatal(1,"fine positive outside DZ at G%0d",i);
   x=954;#1;if(t!=-2)$fatal(1,"fine negative outside DZ at G%0d",i);
   x=965;#1;if(t!=0)$fatal(1,"inside DZ must be zero");
  end
  g=3;x=991;#1;if(t!=4)$fatal(1,"ceil fixes logged31pixel T3 plateau");
  g=131;#1;if(t!=-4)$fatal(1,"direction bit changed");g=3;l=1;x=966;#1;if(t!=1)$fatal(1,"minimum must respect L1");
  l=0;#1;if(t!=0)$fatal(1,"L0 must suppress correction");
  l=60;g=0;x=1200;key=1;tick(1);key=0;frame=1;tick(1);frame=0;tick(99);
  if(!run || at!=8)$fatal(1,"SL8 must stay8counts/100ms at20ms ticks, got %d",at);
  held=at;valid=0;tick(60);if(at!=held || !run || vel!=0 || dut.slew_remainder!=0)$fatal(1,"loss must freeze ramp and rate credit");
  valid=1;frame=1;tick(1);frame=0;tick(19);if(at-held>2 || vel!=0)$fatal(1,"recovery accumulated burst/velocity");
  key=1;tick(1);key=0;tick(2);sl=1;key=1;tick(1);key=0;frame=1;tick(1);frame=0;tick(99);
  if(at!=1)$fatal(1,"SL1 fractional100ms rate stalled or grew, AT=%d",at);
  $display("RESPONSE_ARITHMETIC_PASS: DZ/fine ceil/min2,all gains,inversion,L0/L1,SL8/SL1 units,coast/recovery no stored burst");done=1;
 end
endmodule

module tb_response;
 wire a,b,c;wire [31:0] af,ar,bf,br,cf,cr;wire math_done;wire [8:1] faults;
 response_motion #(.FAST(0)) old_case(a,af,ar);
 response_motion #(.FAST(1)) new_case(b,bf,br);
 response_motion #(.FAST(1),.DELAY_MS(12)) delayed_case(c,cf,cr);
 response_arithmetic math_case(math_done);
 genvar j;generate for(j=1;j<=8;j=j+1)begin: guards fast_fault_case #(.CASE(j)) f(faults[j]);end endgenerate
 initial begin wait(a && b && c && math_done && (&faults));
  if(bf*2>=af || br*2>=ar)$fatal(1,"response improvement less than2x old%0d/%0d new%0d/%0d",af,ar,bf,br);
  $display("RESPONSE_ALL_PASS: production timing ratios,>=2x step/reversal improvement,true1.28AB including12ms latency,manual75ms unchanged,eight fast guards,429byte UART");$finish;
 end
 initial begin #30000000;$fatal(1,"response timeout old=%b new=%b delayed=%b math=%b faults=%b",a,b,c,math_done,faults);end
endmodule

`timescale 1ns/1ps
module fast_fault_case #(parameter CASE=1)(output reg finished=0);
 reg clk=0;always #5 clk=~clk;
 reg rst=0,en_req=1,k4=1,k2=1;reg signed [31:0] encoder=0;reg [15:0] errors=0;
 wire en,dir,step,ready,busy;wire [3:0] fault;wire [7:0] spent;
 vision_servo_core #(.EXTERNAL_CONTROL(1),.DEBOUNCE_CYCLES(3),.ENABLE_CYCLES(8),.SETUP_CYCLES(6),.HALF_CYCLES(4),.SETTLE_CYCLES(5),.FOLLOW_SETUP_CYCLES(2),.FOLLOW_SETTLE_CYCLES(2),
 .TIMEOUT_CYCLES(CASE==4 ? 1 : 2000),.MOVE_BUDGET(CASE==5 ? 1 : 64)) dut(
 .clk(clk),.rst_n(rst),.enable_request(en_req),.k4_n(k4),.k2_n(k2),.request(~k2),.following(1'b1),.external_cancel(1'b0),.external_cancel_reason(4'd0),.encoder_count(encoder),.encoder_errors(errors),
 .visual_valid(1'b1),.visual_stale(1'b0),.settings_ready(1'b1),.config_changed(1'b0),.visual_target(8'sd5),
 .motor_en(en),.motor_dir(dir),.motor_step(step),.ready(ready),.busy(busy),.fault(fault),.spent(spent));
 always @(posedge step)begin
  if(CASE==2)encoder<=encoder+(dir ? 1 : -1);
  else if(CASE==5)encoder<=encoder+(dir ? -1 : 1);
 end
 task tick(input integer n);begin repeat(n)@(negedge clk);end endtask
 initial begin
  tick(4);rst=1;tick(60);wait(ready);tick(12);
  if(CASE==6)dut.command_position=64;
  k2=0;tick(15);k2=1;
  if(CASE==3)begin wait(busy);errors=1;end
  if(CASE==7)begin wait(busy);encoder=-65;end
  if(CASE==8)begin wait(busy);force dut.state=15;tick(1);release dut.state;end
  wait(fault!=0);#1;
  if(fault!=CASE || en || step)$fatal(1,"fault fixture %0d got fault=%0d en=%b",CASE,fault,en);
  if(CASE==1 && spent!=3)$fatal(1,"no-response budget changed");
  if(CASE==2 && spent!=2)$fatal(1,"wrong direction threshold changed");
  tick(10);en_req=0;tick(10);en_req=1;k2=0;tick(30);
  if(fault!=CASE || en || step)$fatal(1,"fault %0d bypassed by re-enable",CASE);
  rst=0;tick(3);if(fault!=0)$fatal(1,"reset did not clear fault");
  $display("PASS fast fault %0d: latched, output stopped, no re-enable bypass",CASE);finished=1;
 end
endmodule

